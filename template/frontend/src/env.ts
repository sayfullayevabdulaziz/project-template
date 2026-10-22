import { z } from 'zod';

const schema = z.object({
  VITE_API_BASE_URL: z.union([z.literal(''), z.url()]).default(''),
});

export function parseEnv(raw: Record<string, unknown>) {
  return schema.parse(raw);
}

export const env = parseEnv(import.meta.env);
