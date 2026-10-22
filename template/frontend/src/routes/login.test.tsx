import { waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { getAccessToken } from '@/lib/auth';
import { problem } from '@/test/fixtures';
import { apiUrl } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { screen } from '@testing-library/react';

const refresh401 = http.post(apiUrl('/auth/refresh'), () =>
  HttpResponse.json(problem(401, 'Unauthorized'), { status: 401 }),
);

async function renderLogin(search = '') {
  server.use(refresh401);
  const ctx = await renderApp(`/login${search}`);
  return ctx;
}

async function fillAndSubmit(user: Awaited<ReturnType<typeof renderLogin>>['user']) {
  await user.type(screen.getByLabelText('Email'), 'admin@example.com');
  await user.type(screen.getByLabelText('Password'), 'secret');
  await user.click(screen.getByRole('button', { name: 'Sign in' }));
}

describe('login page', () => {
  it('signs in and navigates to the redirect target', async () => {
    const { router, user } = await renderLogin('?redirect=/items');
    await fillAndSubmit(user);
    await waitFor(() => expect(router.state.location.pathname).toBe('/items'));
    expect(getAccessToken()).toBe('t-login');
  });

  it.each(['//evil.com', 'https://evil.com', '/\\evil.com'])(
    'ignores unsafe redirect %s and lands on /',
    async (bad) => {
      const { router, user } = await renderLogin(`?redirect=${encodeURIComponent(bad)}`);
      await fillAndSubmit(user);
      await waitFor(() => expect(router.state.location.pathname).toBe('/'));
      expect(router.state.location.href).toBe('/');
    },
  );

  it.each([
    [401, 'Unauthorized', 'Invalid credentials'],
    [403, 'Forbidden', 'Account disabled'],
    [429, 'Too Many Requests', 'Try again in 60 seconds'],
  ])('shows the problem detail for %i', async (status, title, detail) => {
    server.use(
      http.post(apiUrl('/auth/login'), () =>
        HttpResponse.json(problem(status, title, detail), { status }),
      ),
    );
    const { user } = await renderLogin();
    await fillAndSubmit(user);
    expect(await screen.findByRole('alert')).toHaveTextContent(detail);
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
    expect(getAccessToken()).toBeNull();
  });

  it('validates an empty submit without sending a request', async () => {
    const login = vi.fn();
    server.use(
      http.post(apiUrl('/auth/login'), () => {
        login();
        return HttpResponse.json({});
      }),
    );
    const { user } = await renderLogin();
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect((await screen.findAllByRole('alert')).length).toBeGreaterThan(0);
    expect(login).not.toHaveBeenCalled();
  });

  it('disables the submit button while pending', async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => (release = r));
    server.use(
      http.post(apiUrl('/auth/login'), async () => {
        await gate;
        return HttpResponse.json({
          access_token: 't-login',
          token_type: 'bearer',
          expires_in: 900,
        });
      }),
    );
    const { user } = await renderLogin();
    await fillAndSubmit(user);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in' })).toBeDisabled());
    release();
    await waitFor(() => expect(getAccessToken()).toBe('t-login'));
  });
});
