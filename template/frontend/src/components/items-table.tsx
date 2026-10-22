import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import type { ColumnDef } from '@tanstack/react-table';
import { useMemo, useState } from 'react';

import type { ItemAdmin } from '@/client';
import {
  itemsDeleteMutation,
  itemsListOptions,
  itemsUpdateMutation,
} from '@/client/@tanstack/react-query.gen';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { DataTable } from '@/components/data-table/data-table';
import { toQuery, type ListSearch } from '@/components/data-table/search';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { invalidateOp } from '@/lib/query';
import { showProblem } from '@/lib/problem';

type Props = {
  search: ListSearch;
  /** Must be referentially stable: DataTable's empty-last-page effect depends on it. */
  onSearchChange: (patch: Partial<ListSearch>) => void;
};

export function ItemsTable({ search, onSearchChange }: Props) {
  const qc = useQueryClient();
  const [deleting, setDeleting] = useState<ItemAdmin | null>(null);
  const list = useQuery({
    ...itemsListOptions({ query: toQuery(search) }),
    placeholderData: keepPreviousData,
  });
  const onSuccess = () => invalidateOp(qc, 'itemsList', 'itemsGet');
  const update = useMutation({ ...itemsUpdateMutation(), onSuccess, onError: showProblem });
  const remove = useMutation({ ...itemsDeleteMutation(), onSuccess, onError: showProblem });
  const { mutate: togglePublished } = update;

  const columns = useMemo<ColumnDef<ItemAdmin>[]>(
    () => [
      { accessorKey: 'name', header: 'Name', meta: { sortKey: 'name' } },
      {
        id: 'is_published',
        header: 'Published',
        cell: ({ row }) => (
          <Switch
            aria-label={`Publish ${row.original.name}`}
            checked={row.original.is_published}
            onCheckedChange={(is_published) =>
              togglePublished({ path: { item_id: row.original.id }, body: { is_published } })
            }
          />
        ),
      },
      {
        accessorKey: 'created_at',
        header: 'Created',
        meta: { sortKey: 'created_at' },
        cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link
                to="/items/$itemId"
                params={{ itemId: row.original.id }}
                aria-label={`Edit ${row.original.name}`}
              >
                Edit
              </Link>
            </Button>
            <Button
              variant="destructive"
              size="sm"
              aria-label={`Delete ${row.original.name}`}
              onClick={() => setDeleting(row.original)}
            >
              Delete
            </Button>
          </div>
        ),
      },
    ],
    [togglePublished],
  );

  return (
    <>
      <DataTable
        columns={columns}
        data={list.data?.items ?? []}
        total={list.data?.total ?? 0}
        search={search}
        onSearchChange={onSearchChange}
        isLoading={list.isPending}
        searchPlaceholder="Search items"
      />
      <ConfirmDialog
        open={deleting !== null}
        title="Delete item?"
        description={`"${deleting?.name ?? ''}" will be permanently deleted.`}
        confirmLabel="Delete"
        onConfirm={() => deleting && remove.mutate({ path: { item_id: deleting.id } })}
        onOpenChange={(o) => !o && setDeleting(null)}
      />
    </>
  );
}
