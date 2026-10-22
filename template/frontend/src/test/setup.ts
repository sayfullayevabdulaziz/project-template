import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';

import { client } from '@/client/client.gen';
import { __resetAuthForTests, installAuthInterceptors } from '@/lib/auth';

import { server } from './server';

beforeAll(() => {
  // jsdom lacks matchMedia; the sidebar's useIsMobile needs it.
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: (media: string) => ({
      matches: false,
      media,
      addEventListener: () => {},
      removeEventListener: () => {},
    }),
  });
  // jsdom lacks ResizeObserver; Radix Switch (form controls) measures itself with it.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  server.listen({ onUnhandledFrame: 'error' });
  installAuthInterceptors(client);
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
  __resetAuthForTests();
});
afterAll(() => server.close());
