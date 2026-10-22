import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { createRoot } from 'react-dom/client';

import { client } from '@/client/client.gen';
import { installAuthInterceptors } from '@/lib/auth';
import { bindSessionExpiry, createAppRouter } from '@/router';

import './index.css';

installAuthInterceptors(client);

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } });
const router = createAppRouter({ queryClient });
bindSessionExpiry(router, queryClient);

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
  </QueryClientProvider>,
);
