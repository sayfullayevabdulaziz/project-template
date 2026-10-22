import { createFileRoute, Link } from '@tanstack/react-router';
import { useCallback } from 'react';

import { makeListSearchSchema, type ListSearch } from '@/components/data-table/search';
import { ItemsTable } from '@/components/items-table';
import { Button } from '@/components/ui/button';

function ItemsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const onSearchChange = useCallback(
    (patch: Partial<ListSearch>) =>
      void navigate({ search: (prev) => ({ ...prev, ...patch }), replace: 'q' in patch }),
    [navigate],
  );
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Items</h1>
        <Button asChild>
          <Link to="/items/new">New item</Link>
        </Button>
      </div>
      <ItemsTable search={search} onSearchChange={onSearchChange} />
    </div>
  );
}

export const Route = createFileRoute('/_app/items/')({
  validateSearch: makeListSearchSchema(['name', 'created_at', 'updated_at']),
  component: ItemsPage,
});
