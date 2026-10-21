# Admin Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `template/frontend/`, the React admin panel (login, dashboard, items CRUD with publish toggle, users role/active management) driven by a committed hey-api client generated from the backend's `admin.json`.

**Architecture:** Vite SPA. TanStack Router file routes with a `beforeLoad` admin guard. Server state through generated TanStack Query options and mutations. A hand-written `src/lib/auth.ts` owns the in-memory access token and the single-flight cookie refresh, installed as interceptors on the generated bundled fetch client. Tests run against MSW using the real generated client.

**Tech Stack:** Vite 8, React 19, TypeScript `~6.0.3`, TanStack Router/Query/Table, `@hey-api/openapi-ts` 0.99.0 (exact), Tailwind v4, shadcn/ui, react-hook-form + zod, Vitest + Testing Library + MSW, ESLint 10 flat + Prettier, pnpm, nginx-unprivileged.

**Spec:** `docs/superpowers/specs/2026-10-20-project-template-design.md` (sections 4, 5, 6.3, 6.5, 6.7-6.10, 8). Acceptance criterion 4.

**Prerequisite:** plan 02 has produced `template/backend/openapi/admin.json`. Plan 01 has set `copier.yml` `_exclude` (node_modules, pnpm-lock.yaml, dist, caches). This plan creates only files under `template/frontend/` except the Copier answers file (plan 01).

**Develop in place:** all commands run from `template/frontend/`. Commit paths are relative to the template repo root.

## Global Constraints

- pnpm; Node `>=24`; no lockfile committed in the template (spec 5.7). Manifest pins: TypeScript `"~6.0.3"` (7.x breaks typescript-eslint), `@hey-api/openapi-ts` `"0.99.0"` (no caret). Everything else is a caret range with the 6.9 version as floor, re-checked at build start: React 19.3, Vite 8.3, TanStack Router 1.170 / Query 5.104, Tailwind 4.3, Vitest 5, ESLint 10, pnpm 12. Unnumbered libs (zod, MSW, react-hook-form, `@hookform/resolvers`, Playwright MCP, context7 MCP): latest stable at build start. Where a pin has a stated reason it stays.
- `src/client/` is generated, committed, never hand-edited, excluded from ESLint and Prettier, and CI-checked for drift.
- Ports: admin dev 5173, API 8000. Dev proxy `/api` to `http://localhost:8000`. `VITE_API_BASE_URL` default empty (same origin).
- Admin and API must share a site (refresh cookie is `SameSite=Strict`, `Path=/api/admin/auth`, name `refresh_token`). README.md and AGENTS.md say so.
- Access token in memory only. Never localStorage, sessionStorage, or cookies set by JS.
- Access token lifetime 900 s. Admin `logout` needs only the cookie.
- Field limits from the contract: `name` 1-200, `description` up to 2000, `limit` 1-100 default 20, `offset` >= 0, `sort` default `-created_at` (items: `name|created_at|updated_at`; users: `email|created_at`), `q` substring.
- Errors: domain errors are `application/problem+json` (`type,title,status,detail`); 422 keeps FastAPI's shape.
- `.claude/hooks/format.sh` reads hook JSON on stdin, formats only its own extensions inside this repo, always exits 0. Marker lines exactly `<!-- project-context:start -->`, `<!-- project-context:end -->`, `<!-- claude-tools:start -->`, `<!-- claude-tools:end -->`.
- Makefile targets: `dev test lint fmt check gen-api`.
- Conventional Commits.

## Generated symbol names

Hey-api derives names from operationIds (`auth-login` becomes camelCase). Every name below is **(confirm against generated client)** after Task 2:

| operationId | SDK fn | react-query | zod |
|---|---|---|---|
| `auth-login` | `authLogin` | `authLoginMutation` | `zLoginRequest` |
| `auth-refresh` | `authRefresh` | `authRefreshMutation` | |
| `auth-logout` | `authLogout` | `authLogoutMutation` | |
| `users-me` | `usersMe` | `usersMeOptions`, `usersMeQueryKey` | |
| `users-list` | `usersList` | `usersListOptions` | |
| `users-update` | `usersUpdate` | `usersUpdateMutation` | `zUserAdminUpdate` |
| `items-list` | `itemsList` | `itemsListOptions` | |
| `items-get` | `itemsGet` | `itemsGetOptions` | |
| `items-create` | `itemsCreate` | `itemsCreateMutation` | `zItemCreate` |
| `items-update` | `itemsUpdate` | `itemsUpdateMutation` | `zItemUpdate` |
| `items-delete` | `itemsDelete` | `itemsDeleteMutation` | |

Types: `ItemAdmin`, `UserAdmin`, `ItemAdminPage`, `UserAdminPage`, `LoginRequest`, `AdminTokenResponse`. Query keys are arrays whose first element has `_id` equal to the camelCase operation name; invalidation uses a predicate on `_id` (Task 3 helper), not hand-built keys.

## Review Focus

1. `redirect` search param on `/login` set to `//evil.com` or `https://evil.com`: expected to be ignored and land on `/` (Task 5 test).
2. Two browser tabs (or React StrictMode double-run) refreshing at once: the second presents an already-rotated cookie and trips backend reuse detection, revoking the family. Expected: cross-tab serialization via Web Locks (Task 3 test).
3. Logout while a refresh is in flight: the late refresh response must not resurrect the session (Task 3 test).
4. Deleting the only row on the last page leaves an empty page 2: expected to step back to the last non-empty page (Task 6 test).
5. Hand-edited URL params (`limit=9999`, `offset=-1`, `sort=bogus`, `q=%`): expected to fall back to defaults, never a 422 screen (Task 6 test).

## File Structure

```
template/frontend/
  package.json  tsconfig.json  vite.config.ts  eslint.config.js  .prettierrc  .prettierignore
  index.html  components.json  .gitignore  .env.example  Makefile  Dockerfile  nginx.conf
  openapi.json  openapi-ts.config.ts  README.md.jinja  AGENTS.md.jinja  CLAUDE.md.jinja  .mcp.json
  src/main.tsx  router.tsx  index.css  env.ts  client-config.ts  routeTree.gen.ts(generated)
  src/lib/{auth.ts,problem.ts,query.ts,utils.ts}
  src/client/                       generated
  src/components/ui/                shadcn
  src/components/data-table/{data-table.tsx,search.ts}
  src/components/{app-sidebar.tsx,item-form.tsx,login-form.tsx,confirm-dialog.tsx}
  src/routes/{__root,login,_app}.tsx  _app/{index.tsx,items/{index,new,$itemId}.tsx,users/index.tsx}
  src/test/{setup.ts,server.ts,handlers.ts,render.tsx,fixtures.ts}
  .github/{workflows/ci.yml,dependabot.yml}
  .claude/{settings.json,hooks/format.sh,skills/{new-admin-resource,api-client,ui-component}/SKILL.md,agents/frontend-reviewer.md}
```

---

### Task 1: Toolchain scaffold

**Files:** Create `package.json`, `tsconfig.json`, `vite.config.ts`, `eslint.config.js`, `.prettierrc`, `.prettierignore`, `index.html`, `.gitignore`, `.env.example`, `Makefile`, `src/main.tsx` (placeholder render), `src/index.css`, `src/test/setup.ts`, `src/smoke.test.ts` (deleted in this task's last step), `components.json` (via shadcn init), `src/lib/utils.ts`.

**Interfaces:** Produces scripts `dev, build, typecheck, lint, fmt, test, gen-api`. Alias `@/*` to `src/*`. Test setup file `src/test/setup.ts`.

- [ ] **Step 1: Write `package.json`.** `"name": "admin"`, `"private": true`, `"type": "module"`, `engines.node ">=24"`, `packageManager` pnpm 12 (verify at build start). Scripts: `dev` = `vite`, `build` = `tsc --noEmit && vite build`, `typecheck` = `tsc --noEmit`, `lint` = `eslint . && prettier --check .`, `fmt` = `prettier --write . && eslint --fix .`, `test` = `vitest run`, `gen-api` = `openapi-ts`. Dependencies per Global Constraints plus `@tanstack/react-router`, `@tanstack/react-query`, `@tanstack/react-table`, `react-hook-form`, `@hookform/resolvers`, `zod`, `sonner`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`. Dev: `@tanstack/router-plugin`, `@tailwindcss/vite`, `@vitejs/plugin-react`, `vitest`, `jsdom`, `@testing-library/{react,user-event,jest-dom}`, `msw`, `eslint` + `typescript-eslint` + `eslint-plugin-react-hooks` + `eslint-plugin-jsx-a11y` + `@eslint/js` + `globals`, `prettier`.
- [ ] **Step 2: `tsconfig.json`.** `strict`, `noUncheckedIndexedAccess`, `verbatimModuleSyntax`, `moduleResolution: "bundler"`, `jsx: "react-jsx"`, `types: ["vite/client", "vitest/globals", "@testing-library/jest-dom"]`, `paths: {"@/*": ["./src/*"]}` with no `baseUrl` (deprecated in TS 6). Include `src`, `vite.config.ts`, `openapi-ts.config.ts`.
- [ ] **Step 3: `vite.config.ts`** using `defineConfig` from `vitest/config`. Plugins in order: `tanstackRouter({ target: 'react', autoCodeSplitting: true })` (from `@tanstack/router-plugin/vite`), `react()`, `tailwindcss()`. `resolve.alias` `@` to `src`. `server.port 5173`, `server.proxy['/api'] = { target: process.env.API_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: false }`. `test`: `environment 'jsdom'`, `globals true`, `setupFiles ['./src/test/setup.ts']`, `env: { VITE_API_BASE_URL: 'http://api.test' }` (Node fetch cannot build relative-URL Requests; absolute base keeps MSW matching simple). (Verify plugin option names at build start.)
- [ ] **Step 4: ESLint flat config.** Ignore `dist`, `src/client`, `src/routeTree.gen.ts`. Presets: `@eslint/js` recommended, `typescript-eslint` `strictTypeChecked`-lite (`recommendedTypeChecked`) with `parserOptions.projectService`, react-hooks flat recommended, `jsx-a11y` flat recommended. Disallow `src/components/ui/**` from lint errors on `react-refresh`-style rules (shadcn files are vendored). `.prettierrc`: `{"singleQuote": true, "trailingComma": "all", "printWidth": 100}`. `.prettierignore`: `src/client`, `src/routeTree.gen.ts`, `dist`, `pnpm-lock.yaml`, `openapi.json`.
- [ ] **Step 5: `index.html`, `src/index.css` (`@import "tailwindcss";`), `.gitignore` (`node_modules dist coverage .env.local .env.*.local *.tsbuildinfo`), `.env.example`** with `VITE_API_BASE_URL=` and a commented `API_PROXY_TARGET=http://localhost:8000`.
- [ ] **Step 6: `Makefile`** (`.PHONY` all). `dev: pnpm dev`, `test: pnpm test`, `lint: pnpm lint`, `fmt: pnpm fmt`, `gen-api: pnpm gen-api`, `check: lint` then `pnpm typecheck`, `pnpm test`, `pnpm build` (recipe lines, so one failure stops). Dev target prints nothing extra.
- [ ] **Step 7: `src/test/setup.ts`** imports `@testing-library/jest-dom/vitest`; `afterEach(cleanup)`. MSW lifecycle is added in Task 3.
- [ ] **Step 8: Install and init shadcn.** Run `pnpm install`, then `pnpm dlx shadcn@latest init` (Vite template, Tailwind v4, base color neutral, alias `@/`; verify flags at build start; interactive prompts answered to match `components.json` with `aliases.components = "@/components"`, `ui = "@/components/ui"`). Then `pnpm dlx shadcn@latest add button input label card table badge select switch checkbox alert-dialog dropdown-menu sidebar skeleton separator sonner form` (verify `form` still exists; else use the field primitives it was replaced by and adapt Task 7).
- [ ] **Step 9: Smoke test.** `src/smoke.test.ts`: `it('runs', () => expect(1).toBe(1))`. Run `make check`; Expected: lint, typecheck, test, build all pass (build needs a stub `src/main.tsx` rendering `<div>admin</div>` and a stub `src/routes/__root.tsx` so the router plugin has input; create `__root.tsx` minimal with `createRootRoute`). Delete `src/smoke.test.ts`.
- [ ] **Step 10: Commit.** `git add template/frontend && git commit -m "feat(frontend): scaffold vite react toolchain"`.

---

### Task 2: OpenAPI client generation

**Files:** Create `openapi.json`, `openapi-ts.config.ts`, `src/env.ts`, `src/client-config.ts`, `src/env.test.ts`; generated `src/client/**`.

**Interfaces:** Produces `env: { VITE_API_BASE_URL: string }` from `src/env.ts`; `createClientConfig` in `src/client-config.ts`; generated SDK, react-query helpers, zod schemas under `@/client`.

- [ ] **Step 1: Copy the spec.** `cp ../backend/openapi/admin.json openapi.json`. Run `jq '.paths | keys' openapi.json`; Expected: exactly the 7 admin paths from spec 6.10 and no `/api/v1`. If missing, stop: plan 02 is incomplete.
- [ ] **Step 2: Failing test `src/env.test.ts`.** `parseEnv({})` returns `{ VITE_API_BASE_URL: '' }`; `parseEnv({ VITE_API_BASE_URL: 'https://x.test' })` returns that value; `parseEnv({ VITE_API_BASE_URL: 'not a url' })` throws (empty string allowed, otherwise `z.url()`). Run `pnpm vitest run src/env.test.ts`; Expected: FAIL (module missing).
- [ ] **Step 3: `src/env.ts`.** Export `parseEnv(raw: Record<string, unknown>)` (zod: `VITE_API_BASE_URL: z.union([z.literal(''), z.url()]).default('')`) and `export const env = parseEnv(import.meta.env)`. Run the test; Expected: PASS.
- [ ] **Step 4: `src/client-config.ts`.** `export const createClientConfig: CreateClientConfig = (config) => ({ ...config, baseUrl: env.VITE_API_BASE_URL, credentials: 'include' })`. `include` (not default `same-origin`) so sibling-subdomain deploys send the refresh cookie. Import type from `./client/client.gen` (confirm path).
- [ ] **Step 5: `openapi-ts.config.ts`.** `input: './openapi.json'`, `output: 'src/client'`, plugins: `{ name: '@hey-api/client-fetch', runtimeConfigPath: './src/client-config.ts' }`, `'@hey-api/typescript'`, `'@hey-api/sdk'`, `'@tanstack/react-query'`, `'zod'`. (Verify plugin names and `runtimeConfigPath` against 0.99.0 docs via context7 at build start; the bundled client is the default and no `@hey-api/client-fetch` package is installed.)
- [ ] **Step 6: Generate.** `pnpm gen-api`, then `pnpm typecheck`; Expected: both succeed. Confirm every symbol in the "Generated symbol names" table exists (`grep -E "export const (authLogin|usersMeOptions|itemsListOptions|zItemCreate)" -r src/client`); update this plan's table in place for any mismatch, and every later task uses the real names.
- [ ] **Step 7: Idempotence.** `pnpm gen-api && git diff --exit-code -- src/client` after staging; Expected: no diff.
- [ ] **Step 8: Commit.** `git add template/frontend && git commit -m "feat(frontend): generate typed api client from admin openapi"`.

---

### Task 3: Auth library (riskiest logic)

**Files:** Create `src/lib/auth.ts`, `src/lib/auth.test.ts`, `src/test/{server.ts,handlers.ts,fixtures.ts}`. Modify `src/test/setup.ts`.

**Interfaces:**
- Consumes: generated `client`, `authLogin`, `authRefresh`, `authLogout`, `AdminTokenResponse`, `LoginRequest`.
- Produces from `src/lib/auth.ts`:
  - `getAccessToken(): string | null`; `setAccessToken(t: string | null): void`
  - `refreshSession(): Promise<string | null>` (single-flight)
  - `ensureSession(): Promise<boolean>`
  - `login(creds: LoginRequest): Promise<void>` (throws the problem error on failure)
  - `logout(): Promise<void>` (never throws)
  - `onSessionExpired(cb: () => void): () => void` (returns unsubscribe)
  - `installAuthInterceptors(c: typeof client): void` (idempotent per client)
  - `__resetAuthForTests(): void`
- From `src/test/server.ts`: `server` (MSW `setupServer`). `src/test/handlers.ts`: `apiUrl(path: string): string` (prefix `http://api.test/api/admin`), `defaultHandlers` (login 200, refresh 200 `{access_token:'t-refreshed',token_type:'bearer',expires_in:900}`, `users/me` admin, empty item/user pages). `src/test/fixtures.ts`: `adminUser`, `makeItem(over?)`, `makeItemPage(n, total)`, `makeUser(over?)`, `problem(status, title, detail)`.
- Setup: `beforeAll(server.listen({ onUnhandledRequest: 'error' }))`, `afterEach(server.resetHandlers(); __resetAuthForTests())`, `afterAll(server.close)`, and `installAuthInterceptors(client)` once in `beforeAll`.

**Algorithm (binding).**
- State: `token`, `refreshPromise`, `epoch` (incremented by `logout` and `setAccessToken(null)` from expiry), `expiredListeners`, `retried: WeakSet<Request>`, `bodies: Map<Request, Request>`.
- Auth endpoints (`/auth/login`, `/auth/refresh`, `/auth/logout`, matched on URL pathname suffix) are never given a bearer header and never trigger refresh.
- Request interceptor: if token and not an auth endpoint, set `Authorization: Bearer <token>`. Store `request.clone()` in `bodies` so the body can be replayed.
- Response interceptor `(response, request)`: pass through unless `response.status === 401` and not an auth endpoint and `request` not in `retried`. Otherwise `newToken = await refreshSession()`. If `newToken`, build a replay from the stored clone with the new bearer header, add it to `retried`, `fetch` it, return that response (a second 401 is returned as is, no loop). If refresh returned null because refresh answered 401, `expire()` already ran; return the original 401 response. If refresh failed for any other reason (5xx, network), return the original 401 and leave state untouched (session not declared dead on transient errors).
- `refreshSession()`: if `refreshPromise` exists return it. Otherwise create it: capture `startEpoch = epoch`; run the call inside `navigator.locks.request('admin-auth-refresh', fn)` when `navigator.locks` exists, else call `fn` directly (cross-tab serialization: the second tab's call happens after the first tab's cookie rotation landed); `fn` calls `authRefresh` with the interceptor-skipped URL. 200: if `epoch !== startEpoch` discard and return null, else store token and return it. 401: `expire()` and return null. Other: return null. `finally`: `refreshPromise = null`.
- `expire()`: `token = null; epoch++`, notify listeners once per expiry (no notify if already no token and no session known).
- `logout()`: `epoch++`, `token = null`, call `authLogout` (swallow any failure), then notify nothing (caller navigates). `login()`: `authLogin`, throw on error, store token.
- `ensureSession()`: true if token; else `(await refreshSession()) !== null`.

- [ ] **Step 1: Write failing tests in `src/lib/auth.test.ts`** (each uses MSW handlers with call counters; calls go through the real SDK, e.g. `itemsList()`):
  1. `attaches bearer token to non-auth requests`: after `setAccessToken('a')`, `itemsList` request has `authorization === 'Bearer a'`; login request has none.
  2. `401 refreshes once then replays the original request with the new token`: items handler 401 unless bearer is `t-refreshed`; assert refresh hits === 1, items hits === 2, result status 200.
  3. `concurrent 401s share one refresh`: five parallel `itemsList()`; refresh hits === 1; all five 200.
  4. `refresh 401 expires the session`: token null afterwards, listener called exactly once, original 401 returned, no replay (items hits === 1).
  5. `a replayed request that 401s again is not refreshed again`: items always 401; refresh hits === 1; items hits === 2; result 401.
  6. `401 from login does not trigger refresh`: refresh hits === 0, `login` rejects.
  7. `401 from refresh does not recurse`: refresh hits === 1 after `refreshSession()`.
  8. `refresh 500 keeps session state`: expired listener not called, original 401 returned, token unchanged.
  9. `POST body survives replay`: `itemsCreate({ body: { name: 'x' } })` 401 then 201; the replayed request body equals `{"name":"x"}`.
  10. `refreshSession starts a fresh call after the previous settled`: two sequential calls, refresh hits === 2.
  11. `refresh request sends credentials include`: handler asserts `request.credentials === 'include'`.
  12. `ensureSession`: token present gives true and 0 refresh hits; no token plus refresh 200 gives true and token set; refresh 401 gives false.
  13. `logout calls auth-logout, clears token and survives a failing endpoint`: handler 500; promise resolves; token null.
  14. `logout during an in-flight refresh discards the refreshed token`: delay refresh with a gate; `logout()`; release gate; `getAccessToken()` is null.
  15. `uses navigator.locks when available`: stub `navigator.locks.request` with a fake that runs the callback; assert called with `'admin-auth-refresh'`; and works with `navigator.locks` undefined.
- [ ] **Step 2: Run** `pnpm vitest run src/lib/auth.test.ts`; Expected: FAIL (module missing).
- [ ] **Step 3: Implement `src/lib/auth.ts`** exactly per the algorithm above. Interceptor registration uses the client's `interceptors.request.use` / `interceptors.response.use` (response interceptor signature `(response, request, options)`; confirm against the generated client). Guard against double install with a `WeakSet<client>`.
- [ ] **Step 4: Run tests; Expected: all 15 PASS.** If replay in test 9 fails because the body stream is consumed, the clone stash is wrong, not the test.
- [ ] **Step 5: `src/lib/problem.ts` with test `problem.test.ts`.** `type Problem = { title: string; detail?: string; status?: number }`; `getProblem(err: unknown): Problem`. Tests: problem+json object gives its `title/detail/status`; FastAPI 422 body `{detail:[{msg:'x'}]}` gives title `Validation error` and detail `x`; a string (nginx HTML 502) or `undefined` gives title `Unexpected error`, no throw. `showProblem(err: unknown): void` calls `toast.error(title, { description: detail })` (sonner).
- [ ] **Step 6: `src/lib/query.ts`.** `invalidateOp(qc: QueryClient, ...ids: string[]): Promise<void>` using predicate `(q) => ids.includes((q.queryKey[0] as {_id?: string})._id ?? '')`. Test: with two cached keys `[{_id:'itemsList'}]` and `[{_id:'usersList'}]`, `invalidateOp(qc,'itemsList')` marks only the first invalid.
- [ ] **Step 7: Commit.** `git commit -m "feat(frontend): add in-memory auth with single-flight refresh"` (add `template/frontend/src/lib template/frontend/src/test`).

---

### Task 4: Router, root, guard, test harness

**Files:** Create `src/router.tsx`, `src/routes/__root.tsx`, `src/routes/_app.tsx` (guard only; layout in Task 5), `src/routes/login.tsx` (stub), `src/routes/_app/index.tsx` (stub), `src/test/render.tsx`, `src/routes/guard.test.tsx`; modify `src/main.tsx`. Generated `src/routeTree.gen.ts` is committed.

**Interfaces:**
- Produces `createAppRouter(opts?: { history?: RouterHistory; queryClient?: QueryClient }): Router` and `RouterContext = { queryClient: QueryClient }` from `src/router.tsx`. `renderApp(path: string): Promise<{ router, queryClient, user }>` from `src/test/render.tsx` (memory history, fresh QueryClient with `retry: false`, awaits `router.load()`, renders `<App/>` with `Toaster`). `ensureAdmin(qc: QueryClient): Promise<UserAdmin | null>` exported from `src/lib/auth.ts`'s sibling `src/lib/session.ts`.
- `ensureAdmin`: `ensureSession()` false gives null; else `qc.ensureQueryData(usersMeOptions())`; a 401/403 error gives null; a non-`admin` role gives `logout()` then null.

- [ ] **Step 1: Failing tests `guard.test.tsx`:**
  - `redirects anonymous visitor to /login keeping the target`: refresh 401; `renderApp('/items')`; `router.state.location.pathname === '/login'` and `search.redirect === '/items'`.
  - `restores the session from the refresh cookie on reload`: refresh 200 + `users/me` admin; `renderApp('/')` stays on `/` and `router.state.location.pathname === '/'`.
  - `rejects a non-admin user`: `users/me` returns role `user`; ends on `/login`; auth-logout handler was called.
  - `session expiry listener sends the user to /login`: after load, fire expiry (`logout`-less: call the listener path via a 401 on refresh); location becomes `/login`.
- [ ] **Step 2: Run; Expected: FAIL.**
- [ ] **Step 3: Implement.** `__root.tsx` uses `createRootRouteWithContext<RouterContext>()` rendering `<Outlet/>` plus `<Toaster/>`. `_app.tsx` `beforeLoad: async ({ context, location }) => { const u = await ensureAdmin(context.queryClient); if (!u) throw redirect({ to: '/login', search: { redirect: location.href } }); return { user: u } }`. `login.tsx` `validateSearch` accepts `redirect?: string`. `src/main.tsx`: `QueryClient` (default `staleTime` 30 s), `installAuthInterceptors(client)`, `onSessionExpired(() => { queryClient.clear(); void router.navigate({ to: '/login', search: { redirect: router.state.location.href } }) })`, render `<QueryClientProvider><RouterProvider/></QueryClientProvider>`.
- [ ] **Step 4: Run tests; Expected: PASS.** `pnpm typecheck` also passes with the generated route tree.
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): add router with admin guard"`.

---

### Task 5: Login page and app shell with dashboard

**Files:** Create `src/components/login-form.tsx`, `src/components/app-sidebar.tsx`, `src/lib/redirect.ts`, tests `src/routes/login.test.tsx`, `src/routes/dashboard.test.tsx`, `src/lib/redirect.test.ts`; modify `src/routes/login.tsx`, `src/routes/_app.tsx`, `src/routes/_app/index.tsx`.

**Interfaces:**
- `safeRedirect(value: string | undefined): string` returns `value` only if it starts with a single `/` (not `//`, not `/\`), else `'/'`.
- `LoginForm(props: { onSubmit: (v: LoginRequest) => Promise<void> })`; labels "Email" and "Password"; submit button "Sign in". Schema `zLoginRequest`. Server errors render in `role="alert"` using `getProblem().detail ?? title`.
- `AppSidebar(props: { email: string; onLogout: () => void })`: nav links "Dashboard" `/`, "Items" `/items`, "Users" `/users`; shows email; button "Log out".
- Dashboard: two `Card`s labelled "Items" and "Users" showing `total` from `itemsListOptions({ query: { limit: 1 } })` and `usersListOptions({ query: { limit: 1 } })`; `Skeleton` while loading.

- [ ] **Step 1: Failing tests.**
  - `redirect.test.ts`: `safeRedirect('/items?x=1')` is `'/items?x=1'`; `'//evil.com'`, `'https://evil.com'`, `'/\\evil.com'`, `undefined`, `''` all give `'/'`.
  - `login.test.tsx`: success navigates to `redirect` (`/items`) and the token is set; `//evil.com` navigates to `/`; 401 handler shows alert "Invalid credentials" (detail from fixture `problem(401,…)`); 403 shows its detail; 429 shows its detail and the button is re-enabled; empty submit shows validation message and sends no request; submit button is disabled while pending.
  - `dashboard.test.tsx`: handlers return totals 42 and 7; screen shows "42" and "7"; both list requests carried `limit=1` in the URL; "Log out" calls auth-logout and lands on `/login`.
- [ ] **Step 2: Run; Expected: FAIL.**
- [ ] **Step 3: Implement.** Login route: `onSubmit` = `login(values)` then `router.navigate({ to: safeRedirect(search.redirect) })`; use `useRouter`. `_app.tsx` component: shadcn `SidebarProvider` + `AppSidebar` + `<Outlet/>` in `<main>`; logout handler = `await logout(); queryClient.clear(); navigate('/login')`. Dashboard route is a plain component using `useQuery` (no loader; guard already waited).
- [ ] **Step 4: Run tests; Expected: PASS.**
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): add login page, sidebar layout and dashboard"`.

---

### Task 6: Generic DataTable bound to URL search params

**Files:** Create `src/components/data-table/search.ts`, `src/components/data-table/data-table.tsx`, `search.test.ts`, `data-table.test.tsx`.

**Interfaces:**
- `search.ts`:
  - `type ListSearch = { limit: number; offset: number; sort?: string; q?: string }`
  - `makeListSearchSchema(allowedSort: readonly string[])` returning a zod schema (usable as TanStack Router `validateSearch`, Standard Schema; verify at build start) with `limit` `.int().min(1).max(100).catch(20)`, `offset` `.int().min(0).catch(0)`, `sort` optional `.catch(undefined)` accepted only if (after stripping a leading `-`) it is in `allowedSort`, `q` optional trimmed string.
  - `toQuery(s: ListSearch): { limit: number; offset: number; sort: string; q?: string }` (defaults `sort` to `-created_at`; omits empty `q`).
- `DataTable<TData>` props: `columns: ColumnDef<TData>[]`, `data: TData[]`, `total: number`, `search: ListSearch`, `onSearchChange: (patch: Partial<ListSearch>) => void`, `isLoading?: boolean`, `searchPlaceholder?: string`, `defaultSort?: string`. A column is sortable only if `column.meta?.sortKey` is set. TanStack Table with `manualPagination`, `manualSorting`, `manualFiltering`.
- Behaviour: header click cycles ascending (`sortKey`), descending (`-sortKey`), default (`sort: undefined`); sort change resets `offset` to 0; `aria-sort` set on the header. Search input (`role="searchbox"`) debounced 300 ms, patch `{ q, offset: 0 }`. Footer shows `Showing {from}-{to} of {total}`; buttons "Previous" / "Next" patch `offset` by `limit`, disabled at bounds. Empty state text "No results". Effect: when `!isLoading && data.length === 0 && total > 0 && offset > 0`, call `onSearchChange({ offset: Math.max(0, (Math.ceil(total / limit) - 1) * limit) })`.

- [ ] **Step 1: Failing tests.**
  - `search.test.ts`: schema parses `{limit:'9999'}` to `limit 20`; `{offset:-1}` to `0`; `{sort:'bogus'}` to `sort undefined`; `{sort:'-name'}` kept when allowed; `{q:'%'}` kept verbatim; `toQuery({limit:20,offset:0})` equals `{limit:20,offset:0,sort:'-created_at'}`.
  - `data-table.test.tsx` (spy `onSearchChange`): renders rows and "Showing 1-20 of 45"; clicking "Name" header calls with `{sort:'name',offset:0}`, then `-name`, then `{sort:undefined,offset:0}` (rerender with new search each time); non-sortable header has no button; "Next" calls `{offset:20}`; "Previous" disabled at offset 0; "Next" disabled when `offset+limit >= total`; typing "abc" with fake timers fires one call `{q:'abc',offset:0}` after 300 ms and none before; empty data with total 0 shows "No results"; with `limit 20, total 45, offset 60, data=[]` it calls `{offset:40}`; skeleton rows shown when `isLoading`.
- [ ] **Step 2: Run; Expected: FAIL.**
- [ ] **Step 3: Implement** per the interfaces; component files hold no data fetching.
- [ ] **Step 4: Run tests; Expected: PASS.**
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): add url-driven generic data table"`.

---

### Task 7: Items routes

**Files:** Create `src/components/item-form.tsx`, `src/components/confirm-dialog.tsx`, `src/routes/_app/items/{index,new,$itemId}.tsx`, tests `src/components/item-form.test.tsx`, `src/routes/_app/items/items.test.tsx`.

**Interfaces:**
- `ItemFormValues = { name: string; description: string; is_published: boolean }`.
- `ItemForm(props: { defaultValues?: ItemFormValues; onSubmit: (v: ItemFormValues) => Promise<void>; submitLabel: string })`, react-hook-form + `zodResolver` over a schema derived from `zItemCreate` (name 1-200, description max 2000; empty description is sent as omitted). Labels "Name", "Description", "Published".
- `ConfirmDialog(props: { open: boolean; title: string; description: string; confirmLabel: string; onConfirm: () => void; onOpenChange: (o: boolean) => void })` (shadcn AlertDialog).
- Items list route: `validateSearch: makeListSearchSchema(['name','created_at','updated_at'])`; `useQuery(itemsListOptions({ query: toQuery(search) }))` with `placeholderData: keepPreviousData`; columns Name (sortKey `name`), Published (Switch, `aria-label="Publish {name}"`), Created (sortKey `created_at`), Actions (Edit link, Delete button). Publish toggle runs `itemsUpdateMutation` with body `{ is_published }`; delete opens ConfirmDialog then `itemsDeleteMutation`; both call `invalidateOp(qc, 'itemsList', 'itemsGet')`; errors via `showProblem`. "New item" button links `/items/new`.
- `$itemId` route: loader `ensureQueryData(itemsGetOptions({ path: { item_id: params.itemId } }))`; `notFoundComponent`/error 404 renders "Item not found" with a link back; submit runs `itemsUpdateMutation` then navigates to `/items`.
- `new` route: `itemsCreateMutation` with body `{ name, description?, is_published }` then navigate to `/items`.

- [ ] **Step 1: Failing tests.**
  - `item-form.test.tsx`: empty name shows "Name is required"-class error and does not call `onSubmit`; 201-char name and 2001-char description each block submit; valid values call `onSubmit({ name:'Widget', description:'', is_published:false })`; `defaultValues` populate inputs; button disabled while submitting.
  - `items.test.tsx`: list shows rows from handler; clicking "Publish Widget" sends PATCH `/items/{id}` body `{is_published:true}` then refetches; Delete shows dialog, cancel sends nothing, confirm sends DELETE and the refetched list no longer has the row; URL `?sort=bogus&limit=9999` renders without a 422 request (handler asserts `limit=20`); deleting the only row on page 2 (`offset=20`, total drops to 20) ends on `offset=0` (Review Focus 4); `/items/new` posts exactly `{"name":"Widget","is_published":false}` when description empty, then lands on `/items`; `/items/abc` with `items-get` 404 shows "Item not found"; edit page prefilled, saving sends PATCH with changed values; PATCH 500 shows an error toast and stays on the page.
- [ ] **Step 2: Run; Expected: FAIL.**
- [ ] **Step 3: Implement** per interfaces. Pass `search`/`onSearchChange` using `useSearch`/`navigate({ search: (prev) => ({ ...prev, ...patch }) })`; `replace: true` for `q`.
- [ ] **Step 4: Run tests; Expected: PASS.**
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): add items list, create, edit, publish and delete"`.

---

### Task 8: Users route

**Files:** Create `src/routes/_app/users/index.tsx`, `src/routes/_app/users/users.test.tsx`.

**Interfaces:** `validateSearch: makeListSearchSchema(['email','created_at'])`. Columns: Email (sortKey `email`), Role (shadcn `Select` with `admin|user`, `aria-label="Role for {email}"`), Active (Switch, `aria-label="Active {email}"`), Created (sortKey `created_at`). Mutations: `usersUpdateMutation` with body `{ role }` or `{ is_active }`; on success `invalidateOp(qc,'usersList','usersMe')`; on error `showProblem(err)` and always `invalidateOp` so the UI reverts to server state. Deactivating goes through `ConfirmDialog` (activating does not). No client-side invariant checks: the server's 409 is authoritative.

- [ ] **Step 1: Failing tests:** list renders users; changing role to admin sends PATCH `/users/{id}` body `{role:'admin'}`; deactivate confirm sends `{is_active:false}`, cancel sends nothing; a 409 `problem(409,'Conflict','Cannot deactivate the last active admin')` shows that detail in a toast and the control returns to the server value after refetch; sorting header and search patch the URL (handler sees `sort=email`, `q=abc`).
- [ ] **Step 2: Run; Expected: FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run; Expected: PASS.** Then `make check`; Expected: green.
- [ ] **Step 5: Commit.** `git commit -m "feat(frontend): add users role and activation management"`.

---

### Task 9: Production image

**Files:** Create `Dockerfile`, `nginx.conf`, `.dockerignore`.

**Interfaces:** Build arg `VITE_API_BASE_URL` (default empty). Container listens on 8080 as non-root.

- [ ] **Step 1: `Dockerfile`.** Stage `build` from `node:24-alpine`: `corepack enable`, `COPY package.json pnpm-lock.yaml* ./`, `pnpm install --frozen-lockfile` when the lockfile exists else `pnpm install` (generated repos always have a lockfile; template dev does not, spec 5.7), `COPY . .`, `ARG VITE_API_BASE_URL`, `pnpm build`. Final stage `nginxinc/nginx-unprivileged:stable-alpine` (pin a tag at build start), `COPY nginx.conf /etc/nginx/conf.d/default.conf`, `COPY --from=build /app/dist /usr/share/nginx/html`, `EXPOSE 8080`.
- [ ] **Step 2: `nginx.conf`.** `listen 8080;` `root /usr/share/nginx/html;` `location / { try_files $uri /index.html; }` `location = /index.html { add_header Cache-Control "no-cache"; }` `location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable"; }`. Comment: `/api` is not proxied here; a front proxy must route it (same-site requirement).
- [ ] **Step 3: Verify.** `docker build -t admin-test .`; `docker run --rm -d -p 8081:8080 --name admin-test admin-test`; `curl -s -o /dev/null -w '%{http_code}' localhost:8081/items/123` gives `200` and the body contains `<div id="root">`; `curl -I localhost:8081/assets/<any built file>` has immutable cache header; `docker exec admin-test id -u` is not `0`. `docker rm -f admin-test`.
- [ ] **Step 4: Commit.** `git commit -m "feat(frontend): add nginx production image"`.

---

### Task 10: CI and Dependabot

**Files:** Create `.github/workflows/ci.yml`, `.github/dependabot.yml`.

- [ ] **Step 1: `ci.yml`.** Triggers `push` (main) and `pull_request`. One job, `ubuntu-latest`, steps: `actions/checkout`, `pnpm/action-setup`, `actions/setup-node` (`node-version: 24`, `cache: pnpm`), `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, then drift: `pnpm gen-api && git diff --exit-code -- src/client`. Pin action majors to the latest at build start. Static file (no `.jinja`) so `${{ }}` is untouched by Copier.
- [ ] **Step 2: `dependabot.yml`.** Ecosystems `npm`, `github-actions`, `docker`, all weekly, npm grouped (`minor-and-patch`). npm `ignore`: `typescript` for `version-update:semver-major` and `semver-minor` (pinned `~6.0.3`); `@hey-api/openapi-ts` all updates (exact pre-1.0 pin; bumped by hand with a regeneration), each with a comment giving the reason.
- [ ] **Step 3: Verify locally.** `pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm gen-api && git diff --exit-code -- src/client`; Expected: exit 0. `python3 -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/ci.yml .github/dependabot.yml` exits 0.
- [ ] **Step 4: Commit.** `git commit -m "ci(frontend): add workflow and dependabot"`.

---

### Task 11: Claude config (settings, hook, skills, subagent, MCP)

**Files:** Create `.claude/settings.json`, `.claude/hooks/format.sh` (mode 755), `.claude/skills/{new-admin-resource,api-client,ui-component}/SKILL.md`, `.claude/agents/frontend-reviewer.md`, `.mcp.json`.

**Interfaces:** `settings.json`: `permissions.allow` = `Bash(pnpm *)`, `Bash(make *)`, `Bash(docker compose *)`; `permissions.deny` = `Read(./.env.local)`, `Read(./.env.*.local)`; `hooks.PostToolUse` = `[{ matcher: "Edit|Write", hooks: [{ type: "command", command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format.sh" }] }]`. `.mcp.json`: servers `context7` (`npx -y @upstash/context7-mcp@<pinned>`) and `playwright` (`npx @playwright/mcp@<pinned>`), pins resolved with `npm view <pkg> version` at build start.

- [ ] **Step 1: `format.sh`.** Read stdin; extract `tool_input.file_path` with `jq` if present else `python3`. Act only if the path is inside `$CLAUDE_PROJECT_DIR` (or the script's repo root), has extension `ts tsx js jsx json css md html`, exists, and is not under `src/client/`, `src/routeTree.gen.ts`, `node_modules/`, or `openapi.json`. Run `pnpm exec prettier --write <file>`; additionally `pnpm exec eslint --fix <file>` for `ts|tsx|js|jsx`. All failures swallowed; `exit 0` always.
- [ ] **Step 2: Verify the hook.**
  - Write `/tmp/x/src/bad.ts`-style case inside the repo: create `src/zz_bad.ts` with `const   a=1`; run `echo '{"tool_input":{"file_path":"'$PWD'/src/zz_bad.ts"}}' | .claude/hooks/format.sh`; Expected: exit 0 and file content now `const a = 1`. Remove the file.
  - Path outside the repo (`/etc/hosts`), path under `src/client/`, empty stdin, malformed JSON: each exits 0 and changes nothing.
- [ ] **Step 3: Skills** (each with `name`/`description` frontmatter, under 60 lines, concrete to this repo):
  - `new-admin-resource`: steps to add a resource `foo`: confirm operationIds exist in `openapi.json` and run `make gen-api` first; route files under `src/routes/_app/foo/{index,new,$fooId}.tsx`; `makeListSearchSchema` with the backend's allowed sort keys; columns with `meta.sortKey`; form schema from generated `zFooCreate`; mutations plus `invalidateOp`; sidebar entry in `app-sidebar.tsx`; tests mirroring `items.test.tsx`; `make check`.
  - `api-client`: copy `../backend/openapi/admin.json` (or run root `make sync-api`), `make gen-api`, use generated `*Options`/`*Mutation`, never edit `src/client/`, extend behavior only in `src/client-config.ts` and `src/lib/auth.ts`.
  - `ui-component`: `pnpm dlx shadcn@latest add <name>`, do not restyle vendored files beyond tokens, accessibility checklist (labels, focus order, `aria-sort`, dialog focus trap, contrast, keyboard path), colocate a Testing Library test using `getByRole`.
- [ ] **Step 4: `frontend-reviewer` subagent.** Frontmatter `name: frontend-reviewer`, read-only tools (`Read, Grep, Glob, Bash`). Checklist: hand edits in `src/client/`; token storage outside memory; refresh logic bypassing `src/lib/auth.ts`; logic in route files that belongs in components or lib; missing a11y; unvalidated search params; ignored mutation errors; query invalidation by hand-built keys; tests using implementation details; env read outside `src/env.ts`.
- [ ] **Step 5: Validate JSON.** `jq . .claude/settings.json .mcp.json` exits 0. Start a Claude Code session in `template/frontend` and confirm `/mcp` lists context7 and playwright (note result; do not block if sandbox cannot start MCP).
- [ ] **Step 6: Commit.** `git commit -m "feat(frontend): add claude code config"`.

---

### Task 12: AGENTS.md, CLAUDE.md, README

**Files:** Create `AGENTS.md.jinja`, `CLAUDE.md.jinja`, `README.md.jinja`.

**Interfaces:** Jinja variables available: `project_name`, `project_slug`, `project_description`. Wrap any literal `{{` in `{% raw %}`.

- [ ] **Step 1: `AGENTS.md.jinja`** (100-150 lines), sections in the spec 6.8 order: (1) `<!-- project-context:start -->` block with a one-paragraph default using `project_name`/`project_description` ("Admin panel for ... consumes the `/api/admin` surface via `openapi.json`") then `<!-- project-context:end -->`; (2) Stack; (3) Commands, exactly `make dev|test|lint|fmt|check|gen-api` with one-line meanings; (4) Architecture map (the file tree from this plan's File Structure, auth flow in 5 lines, data flow: route to generated options to DataTable); (5) Conventions (generated names from operationIds, search params via `makeListSearchSchema`, errors via `getProblem`, forms use generated zod, env only via `src/env.ts`, access token in memory only); (6) Testing (Vitest + Testing Library + MSW against the real client, `getByRole`, `onUnhandledRequest: 'error'`); (7) Definition of done: `make check` green, `make gen-api` no diff, spec copied when backend changed; (8) Never list: edit `src/client/`, store tokens in storage, hand-build query keys, break same-site deploy. Include a **Deploy** paragraph: "Admin and API must be served from the same site (one reverse proxy routing `/api` to the backend and `/` to this app, or sibling subdomains of one registrable domain) because the refresh cookie is `SameSite=Strict`."
- [ ] **Step 2: `CLAUDE.md.jinja`**: first line `@AGENTS.md`, a short Claude section (use `frontend-reviewer` before finishing; skills by situation), then `<!-- claude-tools:start -->` listing the 3 skills, the subagent, and the 2 MCP servers with when-to-use, then `<!-- claude-tools:end -->`.
- [ ] **Step 3: `README.md.jinja`**: quickstart (`pnpm install`, `make dev`, needs backend on 8000), commands table, regenerate client, **Deploy** section repeating the same-site requirement and the Docker run line (`docker build -t {{ project_slug }}-admin .`, port 8080, a front proxy must route `/api`), env table (`VITE_API_BASE_URL`, `API_PROXY_TARGET`).
- [ ] **Step 4: Verify.** `wc -l AGENTS.md.jinja` between 100 and 150; `grep -c -E '^<!-- (project-context|claude-tools):(start|end) -->$'` on each file gives 2 and 2 respectively for AGENTS and CLAUDE (`project-context` pair in AGENTS, `claude-tools` pair in CLAUDE); `grep -n "SameSite=Strict" AGENTS.md.jinja README.md.jinja` hits both; every `make <target>` mentioned in AGENTS.md.jinja exists in `Makefile` (`grep -o 'make [a-z-]*' AGENTS.md.jinja | sort -u` compared to `grep -E '^[a-z-]+:' Makefile`).
- [ ] **Step 5: Commit.** `git commit -m "docs(frontend): add agents, claude and readme templates"`.

---

### Task 13: Acceptance run (criterion 4)

**Files:** none new; fixes land in earlier tasks' files.

- [ ] **Step 1: Re-sync spec.** `diff ../backend/openapi/admin.json openapi.json`; Expected: no output (else copy and `make gen-api`, commit `chore(frontend): resync openapi`).
- [ ] **Step 2: `make check`** from clean (`rm -rf node_modules dist && pnpm install`); Expected: lint, typecheck, vitest, build all pass.
- [ ] **Step 3: `make gen-api`**; `git status --porcelain src/client`; Expected: empty.
- [ ] **Step 4: Start the stack.** `make -C ../backend up` (health: `curl -s localhost:8000/health/ready` is 200), `make -C ../backend create-admin` (use the email/password it documents), `make dev`.
- [ ] **Step 5: Drive with Playwright MCP** at `http://localhost:5173`; each must hold:
  1. Wrong password shows an error alert; correct admin login lands on dashboard with counts.
  2. Items: create "Widget" (unpublished); edit its name; toggle publish on; confirm `curl localhost:8000/api/v1/items` now contains it; delete it with confirmation and the row disappears.
  3. Users: register a second user via `POST /api/v1/users/register`, change that user's role to admin, then back; try to deactivate the only other admin path (self or last admin) and see the 409 detail toast.
  4. Reload the page on `/items`: stays logged in (refresh cookie) with no login screen.
  5. Log out, press Back: guard sends to `/login`.
  6. In devtools or via `list_network_requests`, no request except `/api/admin/auth/*` carries cookies' tokens and `localStorage`/`sessionStorage` hold no token.
- [ ] **Step 6: Record results** in the task report; fix and recommit any failure in the owning task's files. No commit if nothing changed.

---

## Self-review notes

- Spec coverage: package/pins (T1), tsconfig/vite proxy/ESLint/Prettier/Tailwind/shadcn (T1), hey-api config + `runtimeConfigPath` + committed client + env (T2), auth lib (T3), router/guard (T4), login/layout/dashboard `limit=1` (T5), DataTable (T6), items with publish/delete (T7), users 409 (T8), Dockerfile (T9), CI/Dependabot incl. drift (T10), AI config (T11), AGENTS/CLAUDE/README with same-site and markers (T12), acceptance 4 (T13).
- Type consistency: `ListSearch`, `makeListSearchSchema`, `toQuery`, `invalidateOp`, `showProblem`, `getProblem`, `ensureAdmin`, `safeRedirect` are defined once and referenced by those names.
