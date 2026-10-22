import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { client } from '@/client/client.gen';
import { __resetAuthForTests, installAuthInterceptors } from '@/lib/auth';

import { server } from './server';

beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' });
  installAuthInterceptors(client);
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
  __resetAuthForTests();
});
afterAll(() => server.close());
