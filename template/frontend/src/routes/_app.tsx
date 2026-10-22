import { createFileRoute, Outlet, redirect, useNavigate } from '@tanstack/react-router';
import { useQueryClient } from '@tanstack/react-query';

import { AppSidebar } from '@/components/app-sidebar';
import { SidebarProvider } from '@/components/ui/sidebar';
import { logout } from '@/lib/auth';
import { ensureAdmin } from '@/lib/session';

function AppLayout() {
  const { user } = Route.useRouteContext();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return (
    <SidebarProvider>
      <AppSidebar
        email={user.email}
        onLogout={() =>
          void (async () => {
            await logout();
            queryClient.clear();
            await navigate({ to: '/login' });
          })()
        }
      />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </SidebarProvider>
  );
}

export const Route = createFileRoute('/_app')({
  beforeLoad: async ({ context, location }) => {
    const user = await ensureAdmin(context.queryClient);
    if (!user) throw redirect({ to: '/login', search: { redirect: location.href } });
    return { user };
  },
  component: AppLayout,
});
