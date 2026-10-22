import { z } from 'zod';

export type ListSearch = { limit: number; offset: number; sort?: string; q?: string };

// Schema for TanStack Router `validateSearch`; bad values fall back instead of throwing.
export function makeListSearchSchema(allowedSort: readonly string[]) {
  return z.object({
    limit: z.coerce.number().int().min(1).max(100).catch(20),
    offset: z.coerce.number().int().min(0).catch(0),
    sort: z
      .string()
      .refine((s) => allowedSort.includes(s.replace(/^-/, '')))
      .optional()
      .catch(undefined),
    q: z.string().trim().optional().catch(undefined),
  });
}

export function toQuery(s: ListSearch) {
  return {
    limit: s.limit,
    offset: s.offset,
    sort: s.sort ?? '-created_at',
    ...(s.q ? { q: s.q } : {}),
  };
}
