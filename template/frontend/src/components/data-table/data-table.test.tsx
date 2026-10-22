import type { ColumnDef } from '@tanstack/react-table';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DataTable } from './data-table';
import type { ListSearch } from './search';

type Row = { id: number; name: string; note: string };

const columns: ColumnDef<Row>[] = [
  { accessorKey: 'name', header: 'Name', meta: { sortKey: 'name' } },
  { accessorKey: 'note', header: 'Note' },
];

const rows = (n: number): Row[] =>
  Array.from({ length: n }, (_, i) => ({ id: i, name: `row-${i}`, note: `n-${i}` }));

const base: ListSearch = { limit: 20, offset: 0 };

function setup(over: Partial<React.ComponentProps<typeof DataTable<Row>>> = {}) {
  const onSearchChange = vi.fn();
  const props = {
    columns,
    data: rows(20),
    total: 45,
    search: base,
    onSearchChange,
    ...over,
  };
  const view = render(<DataTable<Row> {...props} />);
  const rerender = (search: ListSearch) =>
    view.rerender(<DataTable<Row> {...props} search={search} />);
  return { ...view, onSearchChange, rerender, user: userEvent.setup() };
}

afterEach(() => vi.useRealTimers());

describe('DataTable', () => {
  it('renders rows and the range footer', () => {
    setup();
    expect(screen.getByText('row-0')).toBeInTheDocument();
    expect(screen.getByText('row-19')).toBeInTheDocument();
    expect(screen.getByText('Showing 1-20 of 45')).toBeInTheDocument();
  });

  it('cycles sort asc, desc, default and resets offset', async () => {
    const { onSearchChange, rerender, user } = setup({ search: { ...base, offset: 20 } });
    const header = () => screen.getByRole('columnheader', { name: 'Name' });
    expect(header()).toHaveAttribute('aria-sort', 'none');

    await user.click(screen.getByRole('button', { name: 'Name' }));
    expect(onSearchChange).toHaveBeenLastCalledWith({ sort: 'name', offset: 0 });
    rerender({ ...base, sort: 'name' });
    expect(header()).toHaveAttribute('aria-sort', 'ascending');

    await user.click(screen.getByRole('button', { name: 'Name' }));
    expect(onSearchChange).toHaveBeenLastCalledWith({ sort: '-name', offset: 0 });
    rerender({ ...base, sort: '-name' });
    expect(header()).toHaveAttribute('aria-sort', 'descending');

    await user.click(screen.getByRole('button', { name: 'Name' }));
    expect(onSearchChange).toHaveBeenLastCalledWith({ sort: undefined, offset: 0 });
    expect(onSearchChange).toHaveBeenCalledTimes(3);
  });

  it('gives non-sortable headers no button', () => {
    setup();
    expect(screen.queryByRole('button', { name: 'Note' })).not.toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Note' })).not.toHaveAttribute('aria-sort');
  });

  it('pages with Next and Previous', async () => {
    const { onSearchChange, user } = setup();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(onSearchChange).toHaveBeenCalledWith({ offset: 20 });
  });

  it('disables Next on the last page', () => {
    setup({ search: { ...base, offset: 40 }, data: rows(5) });
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByText('Showing 41-45 of 45')).toBeInTheDocument();
  });

  it('debounces search by 300 ms', async () => {
    vi.useFakeTimers();
    const { onSearchChange } = setup();
    // user-event's async wrapper hangs under vitest fake timers (RTL only detects jest's); fireEvent is sync.
    const box = screen.getByRole('searchbox');
    for (const v of ['a', 'ab', 'abc']) fireEvent.change(box, { target: { value: v } });
    await vi.advanceTimersByTimeAsync(299);
    expect(onSearchChange).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(onSearchChange).toHaveBeenCalledOnce();
    expect(onSearchChange).toHaveBeenCalledWith({ q: 'abc', offset: 0 });
  });

  it('shows No results for empty data', () => {
    const { onSearchChange } = setup({ data: [], total: 0 });
    expect(screen.getByText('No results')).toBeInTheDocument();
    expect(onSearchChange).not.toHaveBeenCalled();
  });

  it('jumps to the last page when the current page is past the end', () => {
    const { onSearchChange } = setup({ data: [], total: 45, search: { ...base, offset: 60 } });
    expect(onSearchChange).toHaveBeenCalledWith({ offset: 40 });
  });

  it('does not jump while loading', () => {
    const { onSearchChange } = setup({
      data: [],
      total: 45,
      search: { ...base, offset: 60 },
      isLoading: true,
    });
    expect(onSearchChange).not.toHaveBeenCalled();
  });

  it('shows skeleton rows while loading', () => {
    const { container } = setup({ data: [], isLoading: true });
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
    expect(screen.queryByText('No results')).not.toBeInTheDocument();
  });
});
