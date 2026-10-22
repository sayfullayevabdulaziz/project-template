import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { itemsCreate, itemsList } from '@/client';
import { apiUrl } from '@/test/handlers';
import { problem } from '@/test/fixtures';
import { server } from '@/test/server';

import {
  ensureSession,
  getAccessToken,
  login,
  logout,
  onSessionExpired,
  refreshSession,
  setAccessToken,
} from './auth';

const page = { items: [], total: 0 };
const unauthorized = () => HttpResponse.json(problem(401, 'Unauthorized'), { status: 401 });

/** Refresh handler that counts hits and answers with `respond`. */
function refreshCounter(
  respond: () => Response | Promise<Response> = () =>
    HttpResponse.json({ access_token: 't-refreshed', token_type: 'bearer', expires_in: 900 }),
) {
  const hits = { n: 0 };
  server.use(
    http.post(apiUrl('/auth/refresh'), () => {
      hits.n += 1;
      return respond();
    }),
  );
  return hits;
}

/** Items handler that 401s unless the bearer is `t-refreshed`. */
function itemsNeedingRefreshedToken() {
  const hits = { n: 0 };
  server.use(
    http.get(apiUrl('/items'), ({ request }) => {
      hits.n += 1;
      return request.headers.get('authorization') === 'Bearer t-refreshed'
        ? HttpResponse.json(page)
        : unauthorized();
    }),
  );
  return hits;
}

describe('auth', () => {
  afterEach(() => {
    Reflect.deleteProperty(navigator, 'locks');
  });

  it('attaches bearer token to non-auth requests', async () => {
    const seen: Record<string, string | null> = {};
    server.use(
      http.get(apiUrl('/items'), ({ request }) => {
        seen.items = request.headers.get('authorization');
        return HttpResponse.json(page);
      }),
      http.post(apiUrl('/auth/login'), ({ request }) => {
        seen.login = request.headers.get('authorization');
        return HttpResponse.json({ access_token: 't-login', token_type: 'bearer' });
      }),
    );
    setAccessToken('a');
    await itemsList();
    await login({ email: 'a@example.com', password: 'pw' });
    expect(seen.items).toBe('Bearer a');
    expect(seen.login).toBeNull();
  });

  it('401 refreshes once then replays the original request with the new token', async () => {
    const refresh = refreshCounter();
    const items = itemsNeedingRefreshedToken();
    setAccessToken('stale');
    const res = await itemsList();
    expect(refresh.n).toBe(1);
    expect(items.n).toBe(2);
    expect(res.response?.status).toBe(200);
    expect(getAccessToken()).toBe('t-refreshed');
  });

  it('concurrent 401s share one refresh', async () => {
    const refresh = refreshCounter();
    itemsNeedingRefreshedToken();
    setAccessToken('stale');
    const results = await Promise.all(Array.from({ length: 5 }, () => itemsList()));
    expect(refresh.n).toBe(1);
    expect(results.map((r) => r.response?.status)).toEqual([200, 200, 200, 200, 200]);
  });

  it('refresh 401 expires the session', async () => {
    refreshCounter(unauthorized);
    const items = itemsNeedingRefreshedToken();
    const expired = vi.fn();
    onSessionExpired(expired);
    setAccessToken('stale');
    const res = await itemsList();
    expect(getAccessToken()).toBeNull();
    expect(expired).toHaveBeenCalledTimes(1);
    expect(res.response?.status).toBe(401);
    expect(items.n).toBe(1);
  });

  it('a replayed request that 401s again is not refreshed again', async () => {
    const refresh = refreshCounter();
    const items = { n: 0 };
    server.use(
      http.get(apiUrl('/items'), () => {
        items.n += 1;
        return unauthorized();
      }),
    );
    setAccessToken('stale');
    const res = await itemsList();
    expect(refresh.n).toBe(1);
    expect(items.n).toBe(2);
    expect(res.response?.status).toBe(401);
  });

  it('401 from login does not trigger refresh', async () => {
    const refresh = refreshCounter();
    server.use(
      http.post(apiUrl('/auth/login'), () =>
        HttpResponse.json(problem(401, 'Invalid credentials'), { status: 401 }),
      ),
    );
    await expect(login({ email: 'a@example.com', password: 'bad' })).rejects.toMatchObject({
      title: 'Invalid credentials',
    });
    expect(refresh.n).toBe(0);
  });

  it('401 from refresh does not recurse', async () => {
    const refresh = refreshCounter(unauthorized);
    expect(await refreshSession()).toBeNull();
    expect(refresh.n).toBe(1);
  });

  it('refresh 500 keeps session state', async () => {
    refreshCounter(() => HttpResponse.json(problem(500, 'Boom'), { status: 500 }));
    itemsNeedingRefreshedToken();
    const expired = vi.fn();
    onSessionExpired(expired);
    setAccessToken('stale');
    const res = await itemsList();
    expect(expired).not.toHaveBeenCalled();
    expect(res.response?.status).toBe(401);
    expect(getAccessToken()).toBe('stale');
  });

  it('POST body survives replay', async () => {
    refreshCounter();
    const bodies: string[] = [];
    server.use(
      http.post(apiUrl('/items'), async ({ request }) => {
        bodies.push(await request.text());
        return request.headers.get('authorization') === 'Bearer t-refreshed'
          ? HttpResponse.json({}, { status: 201 })
          : unauthorized();
      }),
    );
    setAccessToken('stale');
    const res = await itemsCreate({ body: { name: 'x' } });
    expect(res.response?.status).toBe(201);
    expect(bodies).toEqual(['{"name":"x"}', '{"name":"x"}']);
  });

  it('refreshSession starts a fresh call after the previous settled', async () => {
    const refresh = refreshCounter();
    await refreshSession();
    await refreshSession();
    expect(refresh.n).toBe(2);
  });

  it('refresh request sends credentials include', async () => {
    // MSW's node interceptor rebuilds the request with credentials 'same-origin', so a handler
    // cannot see it; observe the Request the app hands to fetch instead.
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    refreshCounter();
    const token = await refreshSession();
    const sent = fetchSpy.mock.calls.map(([input]) => input).find((i) => i instanceof Request);
    fetchSpy.mockRestore();
    expect(token).toBe('t-refreshed');
    expect(sent).toBeInstanceOf(Request);
    expect((sent as Request).url).toBe(apiUrl('/auth/refresh'));
    expect((sent as Request).credentials).toBe('include');
  });

  it('ensureSession', async () => {
    const refresh = refreshCounter();
    setAccessToken('a');
    expect(await ensureSession()).toBe(true);
    expect(refresh.n).toBe(0);

    setAccessToken(null);
    expect(await ensureSession()).toBe(true);
    expect(getAccessToken()).toBe('t-refreshed');

    setAccessToken(null);
    refreshCounter(unauthorized);
    expect(await ensureSession()).toBe(false);
  });

  it('logout calls auth-logout, clears token and survives a failing endpoint', async () => {
    const hits = { n: 0 };
    server.use(
      http.post(apiUrl('/auth/logout'), () => {
        hits.n += 1;
        return HttpResponse.json(problem(500, 'Boom'), { status: 500 });
      }),
    );
    setAccessToken('a');
    await expect(logout()).resolves.toBeUndefined();
    expect(hits.n).toBe(1);
    expect(getAccessToken()).toBeNull();
  });

  it('logout during an in-flight refresh discards the refreshed token', async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    let arrived!: () => void;
    const started = new Promise<void>((resolve) => (arrived = resolve));
    refreshCounter(async () => {
      arrived();
      await gate;
      return HttpResponse.json({ access_token: 't-refreshed', token_type: 'bearer' });
    });
    const pending = refreshSession();
    await started;
    await logout();
    release();
    expect(await pending).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it('uses navigator.locks when available', async () => {
    const request = vi.fn((_name: string, cb: () => Promise<unknown>) => cb());
    Object.defineProperty(navigator, 'locks', { value: { request }, configurable: true });
    refreshCounter();
    expect(await refreshSession()).toBe('t-refreshed');
    expect(request).toHaveBeenCalledWith('admin-auth-refresh', expect.any(Function));

    Object.defineProperty(navigator, 'locks', { value: undefined, configurable: true });
    setAccessToken(null);
    expect(await refreshSession()).toBe('t-refreshed');
  });
});
