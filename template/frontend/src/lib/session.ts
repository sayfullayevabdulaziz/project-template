import type { QueryClient } from '@tanstack/react-query';

import type { UserAdmin } from '@/client';
import { usersMeOptions } from '@/client/@tanstack/react-query.gen';
import { ensureSession, logout } from '@/lib/auth';
import { getProblem } from '@/lib/problem';

/** Current admin, or null when anonymous, expired or not an admin (the latter also logs out). */
export async function ensureAdmin(qc: QueryClient): Promise<UserAdmin | null> {
  if (!(await ensureSession())) return null;
  let me: UserAdmin;
  try {
    me = await qc.ensureQueryData(usersMeOptions());
  } catch (err) {
    const { status } = getProblem(err);
    if (status === 401 || status === 403) return null;
    throw err;
  }
  if (me.role !== 'admin') {
    await logout();
    qc.clear();
    return null;
  }
  return me;
}
