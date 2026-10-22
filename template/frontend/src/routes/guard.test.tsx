import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { usersMe } from '@/client';
import { server } from '@/test/server';
import { apiUrl } from '@/test/handlers';
import { makeUser, problem } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { waitFor } from '@testing-library/react';

const refresh401 = http.post(apiUrl('/auth/refresh'), () =>
  HttpResponse.json(problem(401, 'Unauthorized'), { status: 401 }),
);

describe('admin guard', () => {
  it('redirects anonymous visitor to /login keeping the target', async () => {
    server.use(refresh401);
    const { router } = await renderApp('/items');
    expect(router.state.location.pathname).toBe('/login');
    expect(router.state.location.search).toMatchObject({ redirect: '/items' });
  });

  it('restores the session from the refresh cookie on reload', async () => {
    const { router } = await renderApp('/');
    expect(router.state.location.pathname).toBe('/');
  });

  it('rejects a non-admin user', async () => {
    const logout = vi.fn();
    server.use(
      http.get(apiUrl('/users/me'), () => HttpResponse.json(makeUser())),
      http.post(apiUrl('/auth/logout'), () => {
        logout();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { router } = await renderApp('/');
    expect(router.state.location.pathname).toBe('/login');
    expect(logout).toHaveBeenCalledOnce();
  });

  it('session expiry listener sends the user to /login', async () => {
    const { router } = await renderApp('/');
    expect(router.state.location.pathname).toBe('/');
    server.use(
      http.get(apiUrl('/users/me'), () =>
        HttpResponse.json(problem(401, 'Unauthorized'), { status: 401 }),
      ),
      refresh401,
    );
    await usersMe();
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  });
});
