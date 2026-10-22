import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeAll, describe, expect, it } from 'vitest';

import type { UserAdmin } from '@/client';
import { makeUser, problem } from '@/test/fixtures';
import { apiUrl } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

type Calls = { lists: URL[]; patches: unknown[] };

/** Stateful in-memory users API; every request is recorded in `calls`. */
function useUsersApi(initial: UserAdmin[]) {
  let db = [...initial];
  const calls: Calls = { lists: [], patches: [] };
  server.use(
    http.get(apiUrl('/users'), ({ request }) => {
      const url = new URL(request.url);
      calls.lists.push(url);
      const offset = Number(url.searchParams.get('offset'));
      const limit = Number(url.searchParams.get('limit'));
      return HttpResponse.json({ items: db.slice(offset, offset + limit), total: db.length });
    }),
    http.patch(apiUrl('/users/:id'), async ({ params, request }) => {
      const body = (await request.json()) as Partial<UserAdmin>;
      calls.patches.push(body);
      db = db.map((u) => (u.id === params.id ? { ...u, ...body } : u));
      return HttpResponse.json(db.find((u) => u.id === params.id));
    }),
  );
  return calls;
}

beforeAll(() => {
  // jsdom lacks the pointer-capture and scroll APIs Radix Select calls.
  Object.assign(Element.prototype, {
    hasPointerCapture: () => false,
    releasePointerCapture: () => {},
    scrollIntoView: () => {},
  });
});

// sonner's toast store is module-global, so toast titles must be unique per test.
describe('users list', () => {
  it('shows rows from the API', async () => {
    useUsersApi([makeUser({ email: 'a@x.io' }), makeUser({ email: 'b@x.io', role: 'admin' })]);
    await renderApp('/users');
    expect(await screen.findByText('a@x.io')).toBeInTheDocument();
    expect(screen.getByText('b@x.io')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Role for a@x.io' })).toHaveTextContent('user');
    expect(screen.getByRole('combobox', { name: 'Role for b@x.io' })).toHaveTextContent('admin');
    expect(screen.getByRole('switch', { name: 'Active a@x.io' })).toBeChecked();
  });

  it('changing role to admin sends PATCH {role:"admin"} and refetches', async () => {
    const calls = useUsersApi([makeUser({ email: 'a@x.io' })]);
    const { user } = await renderApp('/users');
    await user.click(await screen.findByRole('combobox', { name: 'Role for a@x.io' }));
    await user.click(await screen.findByRole('option', { name: 'admin' }));
    await waitFor(() => expect(calls.patches).toEqual([{ role: 'admin' }]));
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Role for a@x.io' })).toHaveTextContent('admin'),
    );
  });

  it('cancel in the deactivate dialog sends nothing; confirm sends {is_active:false}', async () => {
    const calls = useUsersApi([makeUser({ email: 'a@x.io' })]);
    const { user } = await renderApp('/users');
    await user.click(await screen.findByRole('switch', { name: 'Active a@x.io' }));
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(calls.patches).toEqual([]);
    expect(screen.getByRole('switch', { name: 'Active a@x.io' })).toBeChecked();

    await user.click(screen.getByRole('switch', { name: 'Active a@x.io' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Deactivate' }),
    );
    await waitFor(() => expect(calls.patches).toEqual([{ is_active: false }]));
    await waitFor(() =>
      expect(screen.getByRole('switch', { name: 'Active a@x.io' })).not.toBeChecked(),
    );
  });

  it('activating an inactive user needs no confirmation', async () => {
    const calls = useUsersApi([makeUser({ email: 'a@x.io', is_active: false })]);
    const { user } = await renderApp('/users');
    await user.click(await screen.findByRole('switch', { name: 'Active a@x.io' }));
    await waitFor(() => expect(calls.patches).toEqual([{ is_active: true }]));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('shows the 409 detail in a toast and the control returns to the server value', async () => {
    const calls = useUsersApi([makeUser({ email: 'last@x.io', role: 'admin' })]);
    server.use(
      http.patch(apiUrl('/users/:id'), () =>
        HttpResponse.json(problem(409, 'Conflict', 'Cannot deactivate the last active admin'), {
          status: 409,
        }),
      ),
    );
    const { user } = await renderApp('/users');
    await user.click(await screen.findByRole('switch', { name: 'Active last@x.io' }));
    const before = calls.lists.length;
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Deactivate' }),
    );
    expect(await screen.findByText('Cannot deactivate the last active admin')).toBeInTheDocument();
    await waitFor(() => expect(calls.lists.length).toBeGreaterThan(before));
    expect(screen.getByRole('switch', { name: 'Active last@x.io' })).toBeChecked();
  });

  it('sort header and search patch the URL and reach the API', async () => {
    const calls = useUsersApi([makeUser({ email: 'a@x.io' })]);
    const { router, user } = await renderApp('/users');
    await screen.findByText('a@x.io');
    await user.click(screen.getByRole('button', { name: /^Email/ }));
    await waitFor(() => expect(calls.lists.at(-1)!.searchParams.get('sort')).toBe('email'));
    await user.type(screen.getByRole('searchbox'), 'abc');
    await waitFor(() => expect(calls.lists.at(-1)!.searchParams.get('q')).toBe('abc'));
    expect(calls.lists.at(-1)!.searchParams.get('sort')).toBe('email');
    expect(router.state.location.search).toMatchObject({ sort: 'email', q: 'abc' });
  });

  it('falls back to defaults for hand-edited URL params instead of a 422', async () => {
    const calls = useUsersApi([makeUser({ email: 'a@x.io' })]);
    await renderApp('/users?sort=bogus&limit=9999&offset=-1');
    expect(await screen.findByText('a@x.io')).toBeInTheDocument();
    expect(calls.lists).toHaveLength(1);
    const q = calls.lists[0]!.searchParams;
    expect(q.get('limit')).toBe('20');
    expect(q.get('offset')).toBe('0');
    expect(q.get('sort')).toBe('-created_at');
  });
});
