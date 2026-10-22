import { createFileRoute } from '@tanstack/react-router';
import { useCallback } from 'react';

import { makeListSearchSchema, type ListSearch } from '@/components/data-table/search';
import { UsersTable } from '@/components/users-table';

function UsersPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const onSearchChange = useCallback(
    (patch: Partial<ListSearch>) =>
      void navigate({ search: (prev) => ({ ...prev, ...patch }), replace: 'q' in patch }),
    [navigate],
  );
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Users</h1>
      <UsersTable search={search} onSearchChange={onSearchChange} />
    </div>
  );
}

export const Route = createFileRoute('/_app/users/')({
  validateSearch: makeListSearchSchema(['email', 'created_at']),
  component: UsersPage,
});
