import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowData,
} from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import type { ListSearch } from './search';

declare module '@tanstack/react-table' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- must mirror the library's generics to merge
  interface ColumnMeta<TData extends RowData, TValue> {
    /** Server sort key; a column is sortable only when this is set. */
    sortKey?: string;
  }
}

const SKELETON_ROWS = 5;
const DEBOUNCE_MS = 300;

type Props<TData> = {
  columns: ColumnDef<TData>[];
  data: TData[];
  total: number;
  search: ListSearch;
  onSearchChange: (patch: Partial<ListSearch>) => void;
  isLoading?: boolean;
  searchPlaceholder?: string;
  defaultSort?: string;
};

export function DataTable<TData>({
  columns,
  data,
  total,
  search,
  onSearchChange,
  isLoading = false,
  searchPlaceholder = 'Search',
  defaultSort,
}: Props<TData>) {
  const { limit, offset } = search;
  const effectiveSort = search.sort ?? defaultSort;

  const table = useReactTable({
    columns,
    data,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    manualSorting: true,
    manualFiltering: true,
  });

  const [query, setQuery] = useState(search.q ?? '');
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  const onQueryChange = (value: string) => {
    setQuery(value);
    clearTimeout(timer.current);
    timer.current = setTimeout(
      () => onSearchChange({ q: value || undefined, offset: 0 }),
      DEBOUNCE_MS,
    );
  };

  // A deleted/filtered-down last page leaves us past the end; jump to the real last page.
  useEffect(() => {
    if (!isLoading && data.length === 0 && total > 0 && offset > 0) {
      onSearchChange({ offset: Math.max(0, (Math.ceil(total / limit) - 1) * limit) });
    }
  }, [isLoading, data.length, total, offset, limit, onSearchChange]);

  const cycleSort = (key: string) => {
    const next = search.sort === key ? `-${key}` : search.sort === `-${key}` ? undefined : key;
    onSearchChange({ sort: next, offset: 0 });
  };

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const colCount = table.getVisibleLeafColumns().length;

  return (
    <div className="flex flex-col gap-4">
      <Input
        role="searchbox"
        aria-label={searchPlaceholder}
        placeholder={searchPlaceholder}
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        className="max-w-sm"
      />
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id}>
                {group.headers.map((header) => {
                  const key = header.column.columnDef.meta?.sortKey;
                  const content = header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext());
                  const ariaSort = !key
                    ? undefined
                    : effectiveSort === key
                      ? 'ascending'
                      : effectiveSort === `-${key}`
                        ? 'descending'
                        : 'none';
                  const Icon =
                    ariaSort === 'ascending'
                      ? ArrowUp
                      : ariaSort === 'descending'
                        ? ArrowDown
                        : ArrowUpDown;
                  return (
                    <TableHead key={header.id} aria-sort={ariaSort}>
                      {key ? (
                        <Button variant="ghost" size="sm" onClick={() => cycleSort(key)}>
                          {content}
                          <Icon aria-hidden="true" />
                        </Button>
                      ) : (
                        content
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: SKELETON_ROWS }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={colCount}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : table.getRowModel().rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colCount} className="h-24 text-center text-muted-foreground">
                  No results
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{`Showing ${from}-${to} of ${total}`}</p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={offset <= 0}
            onClick={() => onSearchChange({ offset: Math.max(0, offset - limit) })}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={offset + limit >= total}
            onClick={() => onSearchChange({ offset: offset + limit })}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
