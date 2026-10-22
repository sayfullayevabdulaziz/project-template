import { createFileRoute } from '@tanstack/react-router';

// Stub so the sidebar has a typed /users target; replaced by the real page later.
export const Route = createFileRoute('/_app/users/')({
  component: () => <div>Users</div>,
});
