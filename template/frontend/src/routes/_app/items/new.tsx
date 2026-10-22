import { useMutation } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';

import { itemsCreateMutation } from '@/client/@tanstack/react-query.gen';
import { ItemForm } from '@/components/item-form';
import { showProblem } from '@/lib/problem';

function NewItemPage() {
  const navigate = useNavigate();
  const create = useMutation({ ...itemsCreateMutation(), onError: showProblem });
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">New item</h1>
      <ItemForm
        submitLabel="Create"
        onSubmit={async ({ name, description, is_published }) => {
          await create.mutateAsync({
            body: { name, ...(description ? { description } : {}), is_published },
          });
          await navigate({ to: '/items', search: { limit: 20, offset: 0 } });
        }}
      />
    </div>
  );
}

export const Route = createFileRoute('/_app/items/new')({ component: NewItemPage });
