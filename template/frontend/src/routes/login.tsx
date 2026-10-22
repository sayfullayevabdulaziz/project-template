import { createFileRoute, useRouter } from '@tanstack/react-router';

import { LoginForm } from '@/components/login-form';
import { login } from '@/lib/auth';
import { safeRedirect } from '@/lib/redirect';

function LoginPage() {
  const router = useRouter();
  const { redirect } = Route.useSearch();
  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <LoginForm
        onSubmit={async (values) => {
          await login(values);
          await router.navigate({ href: safeRedirect(redirect) });
        }}
      />
    </main>
  );
}

export const Route = createFileRoute('/login')({
  validateSearch: (s: Record<string, unknown>): { redirect?: string } =>
    typeof s.redirect === 'string' ? { redirect: s.redirect } : {},
  component: LoginPage,
});
