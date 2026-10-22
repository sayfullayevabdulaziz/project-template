import { QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { createRoot } from 'react-dom/client';

import { client } from '@/client/client.gen';
import { installAuthInterceptors } from '@/lib/auth';
import { getProblem, showProblem } from '@/lib/problem';
import { bindSessionExpiry, createAppRouter } from '@/router';

import './index.css';

installAuthInterceptors(client);

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    // Skip 401: the auth interceptor already handles session expiry. Mutations toast on their own.
    onError: (err) => {
      if (getProblem(err).status !== 401) showProblem(err);
    },
  }),
  defaultOptions: { queries: { staleTime: 30_000 } },
});
const router = createAppRouter({ queryClient });
bindSessionExpiry(router, queryClient);

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
  </QueryClientProvider>,
);
