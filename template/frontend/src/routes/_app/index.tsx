import { useQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';

import { itemsListOptions, usersListOptions } from '@/client/@tanstack/react-query.gen';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

function Count({ label, total }: { label: string; total: number | undefined }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <CardContent className="text-3xl font-semibold">
        {total === undefined ? <Skeleton className="h-9 w-16" /> : total}
      </CardContent>
    </Card>
  );
}

function Dashboard() {
  const items = useQuery(itemsListOptions({ query: { limit: 1 } }));
  const users = useQuery(usersListOptions({ query: { limit: 1 } }));
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Count label="Items" total={items.data?.total} />
      <Count label="Users" total={users.data?.total} />
    </div>
  );
}

export const Route = createFileRoute('/_app/')({ component: Dashboard });
