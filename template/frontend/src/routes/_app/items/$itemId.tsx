import { useMutation, useQueryClient, useSuspenseQuery } from '@tanstack/react-query';
import { createFileRoute, Link, notFound, useNavigate } from '@tanstack/react-router';

import { itemsGetOptions, itemsUpdateMutation } from '@/client/@tanstack/react-query.gen';
import { ItemForm } from '@/components/item-form';
import { getProblem, showProblem } from '@/lib/problem';
import { invalidateOp } from '@/lib/query';

function EditItemPage() {
  const { itemId } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: item } = useSuspenseQuery(itemsGetOptions({ path: { item_id: itemId } }));
  const update = useMutation({
    ...itemsUpdateMutation(),
    onSuccess: () => invalidateOp(qc, 'itemsList', 'itemsGet'),
    onError: showProblem,
  });
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Edit item</h1>
      <ItemForm
        submitLabel="Save"
        defaultValues={{
          name: item.name,
          description: item.description ?? '',
          is_published: item.is_published,
        }}
        onSubmit={async ({ name, description, is_published }) => {
          // null (not omitted) so clearing the description actually clears it on PATCH.
          await update.mutateAsync({
            path: { item_id: itemId },
            body: { name, description: description || null, is_published },
          });
          await navigate({ to: '/items', search: { limit: 20, offset: 0 } });
        }}
      />
    </div>
  );
}

function ItemNotFound() {
  return (
    <div className="flex flex-col items-start gap-2">
      <h1 className="text-2xl font-semibold">Item not found</h1>
      <Link to="/items" search={{ limit: 20, offset: 0 }} className="underline">
        Back to items
      </Link>
    </div>
  );
}

export const Route = createFileRoute('/_app/items/$itemId')({
  loader: async ({ context, params }) => {
    try {
      await context.queryClient.ensureQueryData(
        itemsGetOptions({ path: { item_id: params.itemId } }),
      );
    } catch (err) {
      // eslint-disable-next-line @typescript-eslint/only-throw-error -- router control-flow object, not an Error
      if (getProblem(err).status === 404) throw notFound();
      throw err;
    }
  },
  component: EditItemPage,
  notFoundComponent: ItemNotFound,
});
