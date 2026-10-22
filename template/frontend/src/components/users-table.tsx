import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ColumnDef } from '@tanstack/react-table';
import { useMemo, useState } from 'react';

import type { Role, UserAdmin } from '@/client';
import { usersListOptions, usersUpdateMutation } from '@/client/@tanstack/react-query.gen';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { DataTable } from '@/components/data-table/data-table';
import { toQuery, type ListSearch } from '@/components/data-table/search';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { showProblem } from '@/lib/problem';
import { invalidateOp } from '@/lib/query';

type Props = {
  search: ListSearch;
  /** Must be referentially stable: DataTable's empty-last-page effect depends on it. */
  onSearchChange: (patch: Partial<ListSearch>) => void;
};

const ROLES: Role[] = ['admin', 'user'];

export function UsersTable({ search, onSearchChange }: Props) {
  const qc = useQueryClient();
  const [deactivating, setDeactivating] = useState<UserAdmin | null>(null);
  const list = useQuery({
    ...usersListOptions({ query: toQuery(search) }),
    placeholderData: keepPreviousData,
  });
  const update = useMutation({
    ...usersUpdateMutation(),
    onSuccess: () => invalidateOp(qc, 'usersList', 'usersMe'),
    onError: showProblem,
    // Refetch even on failure so the controls snap back to the server's value.
    onSettled: () => invalidateOp(qc, 'usersList'),
  });
  const { mutate } = update;

  const columns = useMemo<ColumnDef<UserAdmin>[]>(
    () => [
      { accessorKey: 'email', header: 'Email', meta: { sortKey: 'email' } },
      {
        id: 'role',
        header: 'Role',
        cell: ({ row }) => (
          <Select
            value={row.original.role}
            onValueChange={(role) =>
              mutate({ path: { user_id: row.original.id }, body: { role: role as Role } })
            }
          >
            <SelectTrigger size="sm" aria-label={`Role for ${row.original.email}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map((r) => (
                <SelectItem key={r} value={r}>
                  {r}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ),
      },
      {
        id: 'is_active',
        header: 'Active',
        cell: ({ row }) => (
          <Switch
            aria-label={`Active ${row.original.email}`}
            checked={row.original.is_active}
            onCheckedChange={(is_active) =>
              is_active
                ? mutate({ path: { user_id: row.original.id }, body: { is_active } })
                : setDeactivating(row.original)
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
    ],
    [mutate],
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
        searchPlaceholder="Search users"
      />
      <ConfirmDialog
        open={deactivating !== null}
        title="Deactivate user?"
        description={`${deactivating?.email ?? ''} will no longer be able to sign in.`}
        confirmLabel="Deactivate"
        onConfirm={() =>
          deactivating && mutate({ path: { user_id: deactivating.id }, body: { is_active: false } })
        }
        onOpenChange={(o) => !o && setDeactivating(null)}
      />
    </>
  );
}
