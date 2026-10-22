import type { QueryClient } from '@tanstack/react-query';

/** Invalidate every cached query generated for the given SDK operation ids. */
export function invalidateOp(qc: QueryClient, ...ids: string[]): Promise<void> {
  return qc.invalidateQueries({
    predicate: (q) => ids.includes((q.queryKey[0] as { _id?: string })._id ?? ''),
  });
}
