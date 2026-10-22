import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { apiUrl } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('dashboard', () => {
  it('shows totals fetched with limit=1', async () => {
    const urls: URL[] = [];
    const page =
      (total: number) =>
      ({ request }: { request: Request }) => {
        urls.push(new URL(request.url));
        return HttpResponse.json({ items: [], total });
      };
    server.use(http.get(apiUrl('/items'), page(42)), http.get(apiUrl('/users'), page(7)));
    await renderApp('/');
    expect(await screen.findByText('42')).toBeInTheDocument();
    expect(await screen.findByText('7')).toBeInTheDocument();
    expect(urls).toHaveLength(2);
    urls.forEach((u) => expect(u.searchParams.get('limit')).toBe('1'));
  });

  it('log out calls auth-logout and lands on /login', async () => {
    const logout = vi.fn();
    server.use(
      http.post(apiUrl('/auth/logout'), () => {
        logout();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { router, user } = await renderApp('/');
    expect(await screen.findByText('admin@example.com')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Log out' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(logout).toHaveBeenCalledOnce();
  });
});
