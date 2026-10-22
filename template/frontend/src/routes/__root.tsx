import { createRootRouteWithContext, Outlet } from '@tanstack/react-router';

import { Toaster } from '@/components/ui/sonner';
import type { RouterContext } from '@/router';

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => (
    <>
      <Outlet />
      <Toaster />
    </>
  ),
});
