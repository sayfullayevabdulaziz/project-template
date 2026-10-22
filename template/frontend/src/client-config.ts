import type { CreateClientConfig } from './client/client.gen';
import { env } from './env';

// 'include' (not the default 'same-origin') so sibling-subdomain deploys send the refresh cookie.
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: env.VITE_API_BASE_URL,
  credentials: 'include',
});
