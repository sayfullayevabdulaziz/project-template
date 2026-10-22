import { createFileRoute, redirect } from '@tanstack/react-router';

import { ensureAdmin } from '@/lib/session';

export const Route = createFileRoute('/_app')({
  beforeLoad: async ({ context, location }) => {
    const user = await ensureAdmin(context.queryClient);
    if (!user) throw redirect({ to: '/login', search: { redirect: location.href } });
    return { user };
  },
});
