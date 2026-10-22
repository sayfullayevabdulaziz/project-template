import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: './openapi.json',
  output: 'src/client',
  plugins: [
    // Bundled fetch client; the entry is needed only to set runtimeConfigPath.
    { name: '@hey-api/client-fetch', runtimeConfigPath: './src/client-config' },
    '@hey-api/typescript',
    '@hey-api/sdk',
    '@tanstack/react-query',
    'zod',
  ],
});
