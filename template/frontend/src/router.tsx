import type { QueryClient } from '@tanstack/react-query';
import { createRouter, type RouterHistory } from '@tanstack/react-router';

import { onSessionExpired } from '@/lib/auth';

import { routeTree } from './routeTree.gen';

export type RouterContext = { queryClient: QueryClient };

export function createAppRouter(opts: { history?: RouterHistory; queryClient: QueryClient }) {
  return createRouter({
    routeTree,
    history: opts.history,
    context: { queryClient: opts.queryClient },
    defaultPreload: 'intent',
  });
}

type AppRouter = ReturnType<typeof createAppRouter>;

declare module '@tanstack/react-router' {
  interface Register {
    router: AppRouter;
  }
}

/** Shared by main.tsx and the test harness so both react to session expiry the same way. */
export function bindSessionExpiry(router: AppRouter, queryClient: QueryClient): () => void {
  return onSessionExpired(() => {
    queryClient.clear();
    void router.navigate({ to: '/login', search: { redirect: router.state.location.href } });
  });
}
