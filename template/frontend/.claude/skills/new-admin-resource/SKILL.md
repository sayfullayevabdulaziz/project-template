---
name: new-admin-resource
description: Add a new admin resource (list, create, edit, delete) to this frontend, mirroring the items resource. Use when adding a page for a backend resource such as "foo".
---

# Add an admin resource `foo`

Use `items` as the reference: `src/routes/_app/items/`, `src/components/items-table.tsx`, `src/components/item-form.tsx`.

1. **API first.** Confirm the operationIds (`foosList`, `foosGet`, `foosCreate`, `foosUpdate`, `foosDelete`) exist in `openapi.json`. If not, follow the `api-client` skill, then run `make gen-api`. Never edit `src/client/`.
2. **Routes** under `src/routes/_app/foo/`:
   - `index.tsx`: `validateSearch: makeListSearchSchema([...])` from `@/components/data-table/search`. Pass only the sort keys the backend allows (items: `name`, `created_at`, `updated_at`). Update search through `navigate({ search })`.
   - `new.tsx` and `$fooId.tsx`: thin; render a form component, call the mutation, navigate on success.
   - Do not hand-edit `src/routeTree.gen.ts`; the router plugin regenerates it.
3. **Table component** `src/components/foos-table.tsx`: `useQuery({ ...foosListOptions({ query: toQuery(search) }), placeholderData: keepPreviousData })`. Every sortable column sets `meta: { sortKey: '<api key>' }`.
4. **Form component** `src/components/foo-form.tsx`: build the schema with `zFooCreate.extend({...})` from `@/client/zod.gen`, use `react-hook-form` with `zodResolver` and the `Field` primitives. See `item-form.tsx`.
5. **Mutations:** spread the generated `foosCreateMutation()` etc. into `useMutation`, set `onError: showProblem` (never ignore errors), and `onSuccess: () => invalidateOp(qc, 'foosList', 'foosGet')` from `@/lib/query`. No hand-built query keys.
6. **Sidebar:** add `{ to: '/foo', label: 'Foos' }` to `links` in `src/components/app-sidebar.tsx`.
7. **Tests** mirroring `src/routes/_app/items/items.test.tsx` and `src/components/item-form.test.tsx`: list renders, sort and search update the URL, create/edit/delete call the API, errors surface. Query by role and label.
8. **Verify:** `make check` (lint, typecheck, test, build) must pass.
