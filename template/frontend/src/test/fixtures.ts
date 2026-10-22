import type { ItemAdmin, ItemAdminPage, UserAdmin } from '@/client';

export const adminUser: UserAdmin = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'admin@example.com',
  role: 'admin',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
};

let seq = 0;

export function makeItem(over: Partial<ItemAdmin> = {}): ItemAdmin {
  seq += 1;
  return {
    id: `00000000-0000-0000-0000-${String(seq).padStart(12, '0')}`,
    name: `Item ${seq}`,
    description: null,
    is_published: false,
    created_by_id: adminUser.id,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...over,
  };
}

export function makeItemPage(n: number, total = n): ItemAdminPage {
  return { items: Array.from({ length: n }, () => makeItem()), total };
}

export function makeUser(over: Partial<UserAdmin> = {}): UserAdmin {
  seq += 1;
  return {
    ...adminUser,
    id: `00000000-0000-0000-0001-${String(seq).padStart(12, '0')}`,
    email: `user${seq}@example.com`,
    role: 'user',
    ...over,
  };
}

/** RFC 9457 problem+json body, as the backend emits it. */
export function problem(status: number, title: string, detail?: string) {
  return { type: 'about:blank', status, title, detail };
}
