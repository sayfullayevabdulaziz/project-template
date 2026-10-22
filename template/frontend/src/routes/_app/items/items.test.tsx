import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { ItemAdmin } from '@/client';
import { makeItem, problem } from '@/test/fixtures';
import { apiUrl } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

type Calls = { lists: URL[]; patches: unknown[]; deletes: string[]; posts: string[] };

/** Stateful in-memory items API; every request is recorded in `calls`. */
function useItemsApi(initial: ItemAdmin[]) {
  let db = [...initial];
  const calls: Calls = { lists: [], patches: [], deletes: [], posts: [] };
  server.use(
    http.get(apiUrl('/items'), ({ request }) => {
      const url = new URL(request.url);
      calls.lists.push(url);
      const offset = Number(url.searchParams.get('offset'));
      const limit = Number(url.searchParams.get('limit'));
      return HttpResponse.json({ items: db.slice(offset, offset + limit), total: db.length });
    }),
    http.get(apiUrl('/items/:id'), ({ params }) => {
      const item = db.find((i) => i.id === params.id);
      return item
        ? HttpResponse.json(item)
        : HttpResponse.json(problem(404, 'Not Found'), { status: 404 });
    }),
    http.patch(apiUrl('/items/:id'), async ({ params, request }) => {
      const body = (await request.json()) as Partial<ItemAdmin>;
      calls.patches.push(body);
      db = db.map((i) => (i.id === params.id ? { ...i, ...body } : i));
      return HttpResponse.json(db.find((i) => i.id === params.id));
    }),
    http.delete(apiUrl('/items/:id'), ({ params }) => {
      calls.deletes.push(String(params.id));
      db = db.filter((i) => i.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(apiUrl('/items'), async ({ request }) => {
      calls.posts.push(await request.text());
      return HttpResponse.json(makeItem({ name: 'Widget' }), { status: 201 });
    }),
  );
  return calls;
}

// sonner's toast store is module-global, so toast titles must be unique per test.
describe('items list', () => {
  it('shows rows from the API', async () => {
    useItemsApi([makeItem({ name: 'Widget' }), makeItem({ name: 'Gadget' })]);
    await renderApp('/items');
    expect(await screen.findByText('Widget')).toBeInTheDocument();
    expect(screen.getByText('Gadget')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'New item' })).toHaveAttribute('href', '/items/new');
  });

  it('publishes via PATCH and refetches', async () => {
    const calls = useItemsApi([makeItem({ name: 'Widget' })]);
    const { user } = await renderApp('/items');
    const toggle = await screen.findByRole('switch', { name: 'Publish Widget' });
    expect(toggle).not.toBeChecked();
    const before = calls.lists.length;
    await user.click(toggle);
    await waitFor(() => expect(calls.patches).toEqual([{ is_published: true }]));
    await waitFor(() =>
      expect(screen.getByRole('switch', { name: 'Publish Widget' })).toBeChecked(),
    );
    expect(calls.lists.length).toBeGreaterThan(before);
  });

  it('shows an error toast when the publish PATCH fails', async () => {
    useItemsApi([makeItem({ name: 'Widget' })]);
    server.use(
      http.patch(apiUrl('/items/:id'), () =>
        HttpResponse.json(problem(500, 'Publish failed'), { status: 500 }),
      ),
    );
    const { user } = await renderApp('/items');
    await user.click(await screen.findByRole('switch', { name: 'Publish Widget' }));
    expect(await screen.findByText('Publish failed')).toBeInTheDocument();
  });

  it('cancel in the delete dialog sends nothing; confirm deletes and refetches', async () => {
    const calls = useItemsApi([makeItem({ name: 'Widget' }), makeItem({ name: 'Gadget' })]);
    const { user } = await renderApp('/items');
    await user.click(await screen.findByRole('button', { name: 'Delete Widget' }));
    const dialog = await screen.findByRole('alertdialog');
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(calls.deletes).toEqual([]);

    await user.click(screen.getByRole('button', { name: 'Delete Widget' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }),
    );
    await waitFor(() => expect(calls.deletes).toHaveLength(1));
    await waitFor(() => expect(screen.queryByText('Widget')).not.toBeInTheDocument());
    expect(screen.getByText('Gadget')).toBeInTheDocument();
  });

  it('falls back to defaults for hand-edited URL params instead of a 422', async () => {
    const calls = useItemsApi([makeItem({ name: 'Widget' })]);
    await renderApp('/items?sort=bogus&limit=9999');
    expect(await screen.findByText('Widget')).toBeInTheDocument();
    const q = calls.lists[0]!.searchParams;
    expect(q.get('limit')).toBe('20');
    expect(q.get('offset')).toBe('0');
    expect(q.get('sort')).toBe('-created_at');
  });

  it('deleting the only row on the last page steps back to the last non-empty page', async () => {
    const items = Array.from({ length: 21 }, (_, i) => makeItem({ name: `Item-${i}` }));
    const calls = useItemsApi(items);
    const { router, user } = await renderApp('/items?offset=20');
    expect(await screen.findByText('Item-20')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete Item-20' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete' }),
    );
    await waitFor(() => expect(router.state.location.search.offset).toBe(0));
    expect(await screen.findByText('Item-0')).toBeInTheDocument();
    expect(screen.getByText('Showing 1-20 of 20')).toBeInTheDocument();
    expect(calls.lists.at(-1)!.searchParams.get('offset')).toBe('0');
  });
});

describe('new item', () => {
  it('posts exactly name and is_published when description is empty, then lands on /items', async () => {
    const calls = useItemsApi([]);
    const { router, user } = await renderApp('/items/new');
    await user.type(await screen.findByLabelText('Name'), 'Widget');
    await user.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/items'));
    expect(calls.posts).toEqual(['{"name":"Widget","is_published":false}']);
  });
});

describe('edit item', () => {
  it('shows "Item not found" with a link back on 404', async () => {
    useItemsApi([]);
    await renderApp('/items/abc');
    expect(await screen.findByText('Item not found')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to items/i })).toHaveAttribute(
      'href',
      '/items?limit=20&offset=0',
    );
  });

  it('prefills the form and saves changed values', async () => {
    const item = makeItem({ name: 'Widget', description: 'Old' });
    const calls = useItemsApi([item]);
    const { router, user } = await renderApp(`/items/${item.id}`);
    const name = await screen.findByLabelText('Name');
    expect(name).toHaveValue('Widget');
    expect(screen.getByLabelText('Description')).toHaveValue('Old');
    await user.clear(name);
    await user.type(name, 'Gadget');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/items'));
    expect(calls.patches).toEqual([{ name: 'Gadget', description: 'Old', is_published: false }]);
  });

  it('stays on the page and toasts when the PATCH returns 500', async () => {
    const item = makeItem({ name: 'Widget' });
    useItemsApi([item]);
    server.use(
      http.patch(apiUrl('/items/:id'), () =>
        HttpResponse.json(problem(500, 'Save failed'), { status: 500 }),
      ),
    );
    const { router, user } = await renderApp(`/items/${item.id}`);
    await screen.findByLabelText('Name');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Save failed')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(`/items/${item.id}`);
    expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled();
  });
});
