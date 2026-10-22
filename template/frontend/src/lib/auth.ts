import { authLogin, authLogout, authRefresh, type LoginRequest } from '@/client';
import type { Client } from '@/client/client';

let token: string | null = null;
let refreshPromise: Promise<string | null> | null = null;
// Bumped whenever the session is dropped, so a refresh that started before it cannot revive it.
let epoch = 0;
const expiredListeners = new Set<() => void>();
const retried = new WeakSet<Request>();
// WeakMap, not Map: a request whose fetch throws never reaches the response interceptor to clean up.
const bodies = new WeakMap<Request, Request>();
const installed = new WeakSet<Client>();

const AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/logout'];
const isAuthEndpoint = (request: Request) => {
  const { pathname } = new URL(request.url);
  return AUTH_PATHS.some((p) => pathname.endsWith(p));
};

export const getAccessToken = () => token;

export function setAccessToken(t: string | null): void {
  if (t === null) epoch++;
  token = t;
}

function expire(): void {
  const hadSession = token !== null;
  setAccessToken(null);
  if (hadSession) expiredListeners.forEach((cb) => cb());
}

async function doRefresh(startEpoch: number): Promise<string | null> {
  const { data, response } = await authRefresh();
  if (response?.status === 401) {
    expire();
    return null;
  }
  if (!data || epoch !== startEpoch) return null;
  token = data.access_token;
  return token;
}

/** Single-flight: concurrent callers share one refresh call. */
export function refreshSession(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  const startEpoch = epoch;
  const fn = () => doRefresh(startEpoch);
  // Cross-tab serialization: another tab's refresh lands its cookie rotation before ours runs.
  const run =
    typeof navigator !== 'undefined' && navigator.locks
      ? navigator.locks.request('admin-auth-refresh', fn)
      : fn();
  refreshPromise = run.finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export async function ensureSession(): Promise<boolean> {
  return token !== null || (await refreshSession()) !== null;
}

export async function login(creds: LoginRequest): Promise<void> {
  const { data } = await authLogin({ body: creds, throwOnError: true });
  token = data.access_token;
}

export async function logout(): Promise<void> {
  setAccessToken(null);
  await authLogout().catch(() => undefined);
}

export function onSessionExpired(cb: () => void): () => void {
  expiredListeners.add(cb);
  return () => expiredListeners.delete(cb);
}

export function installAuthInterceptors(c: Client): void {
  if (installed.has(c)) return;
  installed.add(c);

  c.interceptors.request.use((request) => {
    if (token && !isAuthEndpoint(request)) request.headers.set('Authorization', `Bearer ${token}`);
    bodies.set(request, request.clone());
    return request;
  });

  c.interceptors.response.use(async (response, request, options) => {
    const stored = bodies.get(request);
    bodies.delete(request);
    if (response.status !== 401 || isAuthEndpoint(request) || retried.has(request) || !stored) {
      return response;
    }
    const newToken = await refreshSession();
    // null covers both refresh 401 (expire() already ran) and transient failures (state untouched).
    if (!newToken) return response;
    stored.headers.set('Authorization', `Bearer ${newToken}`);
    retried.add(stored);
    return (options.fetch ?? fetch)(stored);
  });
}

export function __resetAuthForTests(): void {
  setAccessToken(null);
  refreshPromise = null;
  expiredListeners.clear();
}
