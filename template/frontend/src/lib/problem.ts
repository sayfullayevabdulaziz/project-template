import { toast } from 'sonner';

export type Problem = { title: string; detail?: string; status?: number };

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

/** Normalize anything the API client can throw into a displayable problem. */
export function getProblem(err: unknown): Problem {
  if (isRecord(err) && typeof err.title === 'string') {
    const p: Problem = { title: err.title };
    if (typeof err.detail === 'string') p.detail = err.detail;
    if (typeof err.status === 'number') p.status = err.status;
    return p;
  }
  if (isRecord(err) && Array.isArray(err.detail)) {
    const msgs = err.detail.map((d) => (isRecord(d) && typeof d.msg === 'string' ? d.msg : ''));
    return { title: 'Validation error', detail: msgs.filter(Boolean).join('; ') };
  }
  return { title: 'Unexpected error' };
}

export function showProblem(err: unknown): void {
  const { title, detail } = getProblem(err);
  toast.error(title, { description: detail });
}
