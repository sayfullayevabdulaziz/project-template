import { QueryClient } from '@tanstack/react-query';
import { expect, it } from 'vitest';

import { invalidateOp } from './query';

it('invalidateOp invalidates only queries of the named operations', async () => {
  const qc = new QueryClient();
  qc.setQueryData([{ _id: 'itemsList' }], { items: [], total: 0 });
  qc.setQueryData([{ _id: 'usersList' }], { items: [], total: 0 });
  await invalidateOp(qc, 'itemsList');
  expect(qc.getQueryState([{ _id: 'itemsList' }])?.isInvalidated).toBe(true);
  expect(qc.getQueryState([{ _id: 'usersList' }])?.isInvalidated).toBe(false);
});
