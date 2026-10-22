import { createFileRoute } from '@tanstack/react-router';

// Stub so the guard has a protected /items target; replaced by the real page later.
export const Route = createFileRoute('/_app/items/')({
  component: () => <div>Items</div>,
});
