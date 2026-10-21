# Project Template Design: FastAPI backend, React admin panel, Flutter mobile, layered AI config

- Date: 2026-10-20
- Status: Draft — awaiting user review

## 1. Intent and why

The user keeps rewriting the same boilerplate for every new project. Their request, verbatim:

> I'm tired of always writing the same boilerplate for every new project I start. That's why I want to set up a solid template, and I need your help with this. It will contain 'backend/', 'frontend/', and 'mobile/' folders. Each one will have its own separate repository and AI configuration (skills, tools, agents, etc.). The root folder will also have an AI configuration that understands the overall project context and uses it to generate 'CLAUDE.md' and 'AGENTS.md' files for each folder. Backend: Built using a stack of FastAPI, PostgreSQL, Pydantic 2, SQLAlchemy 2, TaskIQ, and Observability tools. Frontend: ReactJS. Mobile: Built with Flutter. Please follow best practices when creating this template.

Later additions from the user:

- "now frontend/ folder is for admin panel".
- "I usually write code for both the admin panel and mobile in one backend repo. How can this be made general in project architecture". The API surfaces section (6.3) is the answer.

The result is one Copier template that generates a workspace root plus three independent git repos:

- `backend/`: one FastAPI service serving every client.
- `frontend/`: React admin panel.
- `mobile/`: Flutter end-user app.

Each repo carries its own Claude Code config (skills, subagent, hooks, MCP/plugins) plus `AGENTS.md` for other tools. The root carries a project-level AI config that reads a product brief (`PROJECT.md`) and generates or refreshes each repo's `CLAUDE.md` and `AGENTS.md`.

**Success:** one command generates a new project, and every repo in it is runnable, tested, and AI-ready. Concretely, each repo's `make check` is green, the local stack runs end to end, and `/sync-context` fills the AI docs from `PROJECT.md`.

## 2. Goals / Non-goals / Anti-goals

### Goals

- Generate workspace + `backend/` + `frontend/` + `mobile/` in one `copier copy`. Each is its own git repo with its own `.copier-answers.yml`.
- Ship a working example resource (`items`) plus built-in auth with roles, end to end in all three repos.
- Make the backend serve N client apps through API surfaces. Adding a client is a routine change.
- Give each repo a uniform command surface and a Claude Code config that works from that repo.
- Let the root AI config produce and refresh every repo's `AGENTS.md` / `CLAUDE.md` from `PROJECT.md` and the repos' real files.
- Allow `copier update` per repo after template releases.

### Non-goals (skipped on purpose)

- Password reset and email verification.
- Forced-update / min-app-version endpoint.
- Native mobile flavors (env comes from `--dart-define-from-file`).
- Localization (l10n).
- Client crash reporting.
- React Compiler (extra Babel/rolldown setup on Vite 8).
- Playwright e2e test suites (Playwright MCP is kept for driving the running stack).
- TaskIQ result backend.
- Postgres MCP (stale; use `docker compose exec db psql`).
- freezed, riverpod_generator.
- Renovate (Dependabot is used).
- FVM.
- A staleness hook for generated AI docs.
- A repository layer in the backend (add per module when queries grow).
- An admin framework (refine, react-admin, etc.).

### Anti-goals (failures even if everything "works")

- A `copier update` that overwrites project edits, or re-runs tasks and clobbers the generated project.
- Lockfile merge conflicts on update (hence no shipped lockfiles).
- AI docs (`AGENTS.md`, `CLAUDE.md`) whose commands drift from the real Makefile.
- `/sync-context` touching text outside its markers, or producing a diff on a second run.
- Admin endpoints or admin-only fields reaching the mobile client or `public.json`.
- Business logic duplicated per client, or placed in surface files instead of services.
- A breaking change to `/api/v1` made in place.
- Generated clients (`frontend/src/client/`, `mobile/lib/src/data/api/`) hand-edited, or drifting from the committed specs.
- Secrets readable by the AI via `.env` files.
- A nested `copier copy` that depends on a temp clone path and breaks during `copier update`.
- A template that only works from a relative path or an uncommitted state without saying so.

## 3. Constraints

### Toolchain on the user's machine

- Present: uv, Node 24, pnpm, Docker, git, Homebrew dart.
- Missing: `flutter` on PATH, `copier`.
- `/Users/abdulaziz/Code/project-template` is empty and not a git repo.
- Installing `copier` (`uv tool install copier`) needs the user's approval first. The Flutter SDK is not installed: by the user's choice, no mobile runtime checks run locally.

### Verified technical constraints (research pass, 2026-10-20)

- Copier `_subdirectory` can be templated. Each `template/<component>/` needs its own `{{ _copier_conf.answers_file }}.jinja`.
- During `copier update`, tasks run up to 3 times, so every task is gated on `_copier_operation == 'copy'`.
- Nested copies must use `{{ _copier_python }} -m copier`, `_copier_answers._src_path` and `_commit`, and an absolute path or `gh:` URL. Never use `_copier_conf.src_path` (it is a temp clone during update).
- `flutter create` only adds missing files, but it adds `test/widget_test.dart` if absent. The template must ship its own.
- FastAPI >= 0.142 has built-in OpenTelemetry. Do not add `opentelemetry-instrumentation-fastapi`.
- SQLAlchemy 2.1 needs `sqlalchemy[asyncio]`.
- TypeScript 7 breaks typescript-eslint, so pin TypeScript `~6.0.3`.
- `@hey-api/openapi-ts` is pre-1.0, so pin it exactly. Its fetch client is bundled.
- Claude Code loads `.claude/settings.json` and project skills only from the session's start folder. CLAUDE.md lookup walks parent directories.
- Claude Code reads AGENTS.md natively only when no CLAUDE.md exists up the tree, so the per-repo `@AGENTS.md` import in CLAUDE.md is required.
- The Postgres MCP (`postgres-mcp`) last released 2025-05, so it is cut.

### Session rule

Start Claude inside the repo you change, because its hooks, permissions and skills load only from the start folder. Start at the workspace root for cross-repo work and `/sync-context`. A root hook dispatches formatting to the edited file's repo.

### Process constraint

No scaffolding, installs, or code until the user approves this spec. After approval, the implementation plan comes from `superpowers:writing-plans`.

## 4. Decisions made by the user

- Generator: Copier, with `copier update` per repo.
- Starter code: an example resource end to end plus built-in auth with roles.
- AI tooling: Claude Code fully configured plus `AGENTS.md` (CLAUDE.md imports it).
- Frontend: Vite SPA admin panel with TanStack Router/Query/Table and shadcn/ui, all code owned. No admin framework.
- Three folders `backend/`, `frontend/`, `mobile/`, each its own repository with its own AI configuration.
- A root AI configuration that generates `CLAUDE.md` and `AGENTS.md` for each folder.
- Backend stack: FastAPI, PostgreSQL, Pydantic 2, SQLAlchemy 2, TaskIQ, observability tools.
- `frontend/` is the admin panel. `mobile/` is Flutter.
- One backend repo serves both admin panel and mobile, structured generally.
- Hosting: GitHub (GitHub Actions CI, Dependabot, oasdiff action).
- Backend type checker: ty (stable), not mypy.
- Mobile verification: the mobile repo is built, but `flutter analyze`, tests, and simulator runs are not executed on this machine. Mobile is reported as unverified locally; GitHub Actions (template CI and the mobile repo's CI) runs analyze and tests once pushed.

## 5. Assistant's calls (review these)

The user did not decide these. Flag any that are wrong.

1. Backend is domain modules x API surfaces (`admin`, `public`), feature-first layout (surface routers live inside each module). Not taken: a surface-first tree (`app/api/admin/items.py`), which splits each feature across two folders.
2. The root is its own git repo. Its `.gitignore` excludes `/backend /frontend /mobile`.
3. Python package is `app`. Dart package is `package_name` (the bundle id needs it). `lib/` uses relative imports so only `test/` files are Jinja-templated.
4. Uniform command surface. Every repo has `make dev|test|lint|fmt|check`; the frontend Makefile wraps pnpm. Clients (`frontend`, `mobile`) add `gen-api` (regenerate the client from `openapi.json`). Backend adds `openapi` (export `openapi/*.json`), `up`/`down` (its compose stack), `migrate`, `migration m="…"`, and `create-admin`. Root has `up`, `down`, `sync-api`, `check`.
5. Vendor-neutral OpenTelemetry to OTLP, with local `grafana/otel-lgtm`. Changing vendor means changing the OTLP endpoint.
6. The session rule in section 3, including the root dispatch hook.
7. Lockfiles are not shipped. They are generated in copy-only tasks. Manifests pin compatible ranges.
8. Every item in the Non-goals list above (the user did not approve any of those cuts).
9. Auth design: 15-minute access JWT, 30-day rotating opaque refresh token with reuse detection, cookie transport for admin, body transport for public (details in 6.4).
10. Redis, `RedisStreamBroker`, `pwdlib[argon2]`, PyJWT, structlog, testcontainers, react-hook-form + zod, MSW, and the other libraries named in sections 6.4 to 6.6. The user named only the stack in their request.
11. Playwright MCP in the admin repo, context7 MCP in every repo, and the official Flutter Claude plugin in mobile.
12. The skill and subagent names and scopes in section 6.7.
13. The example resource's shape: `items` with `is_published`; admins manage all items, public clients read published ones.
14. The AGENTS.md size target (about 100 to 150 lines) and the marker-block mechanism for `/sync-context`.
15. Admin `logout` is exempt from `require_admin`. The refresh cookie alone authenticates it, so an admin whose access token expired can still log out. It revokes the token family and clears the cookie.
16. Limits: login 5 attempts per 15 minutes per IP + email; register 10 per hour per IP. JWT secret at least 32 bytes. Page size default 20, max 100.
17. Admin deploy: the production image is a multi-stage pnpm build served by `nginxinc/nginx-unprivileged` with an SPA fallback. Admin and API must be served from the same site, either one reverse proxy routing `/api` to the backend and `/` to the admin, or sibling subdomains of one registrable domain. This is required because the refresh cookie is `SameSite=Strict`. The root `compose.yaml` admin dev server is a `node` container running `pnpm dev --host` with the repo bind-mounted.
18. Unnumbered library versions (pwdlib, PyJWT, zod, MSW, Playwright MCP, etc.) are pinned to the latest stable at build start. If the build-start re-check contradicts a pin that has a stated reason (TypeScript `~6.0.3`, `@hey-api/openapi-ts` exact), that pin stays. Everything else moves to latest stable.
19. Remotes: the template only does local `git init` plus an initial commit per repo. The user creates remotes and pushes; the README shows the commands. There is no cross-repo CI. Instead, root `make check` also fails when `frontend/openapi.json` or `mobile/openapi.json` differs from the backend's surface spec (stale client).
20. Updates: the root runs `copier update` against its own answers (`component: workspace`). Each component updates inside its own repo, in any order. Nested copies pass every shared answer with `-d` (`project_name`, `project_slug`, `project_description`, `org_domain`, `author_name`, `author_email`), so component updates never re-prompt.
21. Missing Flutter at copy time: the mobile repo is still generated. Its copy task runs `make bootstrap` (`flutter create …`, `flutter pub get`, `dart run build_runner build`) only if `flutter` is on PATH. Otherwise it prints a warning to run `make bootstrap` later. Other components are unaffected.
22. Cookie `Secure` flag comes from `APP_COOKIE_SECURE` (default `true`). `.env.example` sets it to `false`, because local dev runs over http and Safari rejects `Secure` cookies there. In dev the Vite proxy keeps admin and API on one origin, so no CORS is needed. CORS with credentials is enabled only for the configured admin origins (sibling-subdomain deploys).
23. Admin invariants (in the service, with tests): an admin can promote a user to admin. An admin cannot demote or deactivate themselves. The last active admin cannot be demoted or deactivated.
24. Data shape: UUIDv7 primary keys (`uuid.uuid7()`, Python 3.14). Item fields: `id, name, description, is_published, created_by_id (FK users), created_at, updated_at`. `ItemPublic` = `id, name, description`. Items are hard-deleted. User fields: `id, email, password_hash, role, is_active, created_at, updated_at`. `UserPublic` = `id, email`. `UserAdmin` adds `role, is_active, created_at`.
25. Breaking-change guard: backend CI runs `oasdiff breaking` on `openapi/public.json` against the base branch and fails on breaking changes. The admin surface is not checked, because it is unversioned by design.
26. `/sync-context` runs manually (README: after filling `PROJECT.md`). No copy task invokes Claude.
27. Cross-repo contract in 6.10: paths, operationIds, schema names, field limits, env names, ports, markers. Also: passwords are 12 to 128 characters. Register returns 409 for a taken email; that enumeration is accepted because there is no email verification, and the rate limit mitigates it. API docs are served only when `APP_ENV=dev`. There is no combined OpenAPI document.

## 6. Design

### 6.1 Template mechanics (Copier)

Template repo layout:

```
project-template/
  copier.yml                  # questions; _subdirectory: "template/{{ component }}"
  README.md                   # generate, update, develop, release (tag vX.Y.Z)
  Makefile                    # test-template: generate from absolute path into scratch dir, run every repo's make check
  .github/workflows/ci.yml    # runs test-template
  template/{workspace,backend,frontend,mobile}/
    {{ _copier_conf.answers_file }}.jinja   # in EACH component dir -> per-repo .copier-answers.yml
```

`copier.yml`:

- Questions: `component` (workspace|backend|frontend|mobile, default workspace), `project_name`, `project_slug` (derived, kebab-case; repo/dir names), `package_name` (derived: `project_slug` with `-` replaced by `_`; Dart package and bundle id suffix), `project_description`, `org_domain` (reverse DNS), `author_name`, `author_email`. Component-specific questions are gated with `when: "{{ component == 'x' }}"`.
- Every `_tasks` entry is gated `when: "{{ _copier_operation == 'copy' }}"`.
- `_message_after_update` reminds the user to re-lock (`uv lock` / `pnpm install` / `flutter pub get`).

Workspace tasks:

- Fail fast if `_copier_answers._src_path` is relative.
- `git init`.
- For each component run: `{{ _copier_python }} -m copier copy --trust --defaults --vcs-ref {{ _copier_answers._commit }} -d component=<c> -d project_name=… -d project_slug=… -d project_description=… -d org_domain=… -d author_name=… -d author_email=… {{ _copier_answers._src_path }} <c>`. Every shared answer is passed so component updates never re-prompt.
- Never use `_copier_conf.src_path`.

Component tasks:

- `git init`.
- Backend: `uv lock`.
- Frontend: `pnpm install`.
- Mobile: if `flutter` is on PATH, run `make bootstrap` (`flutter create --org {{ org_domain }} --project-name {{ package_name }} --platforms android,ios .`, then `flutter pub get`, then `dart run build_runner build`). Otherwise print a warning to run `make bootstrap` later. The template ships its own `test/widget_test.dart` so the default one is not created.
- Then an initial commit.

Usage and releases:

- `copier copy --trust gh:<user>/project-template my-app`, or an absolute local path.
- Releases are git tags (PEP 440) so `copier update` sees versions.
- Nested copies use the committed `_commit`, so commit before testing.

### 6.2 Workspace root and `/sync-context`

`template/workspace/` contents:

- `PROJECT.md`: the product brief the user fills. Sections: purpose, users/roles, clients and the surface each uses, glossary, core entities and rules, integrations, environments, cross-repo conventions (UTC, money as integer minor units, ID format). This is the main input for the root AI.
- `AGENTS.md`: short, because it is also loaded by Claude sessions inside sub-repos (CLAUDE.md lookup walks parent dirs). Contents: repo map; surface to client map; contract-first rule (backend `openapi/<surface>.json` is the source of truth); change order backend, then `make sync-api`, then clients; each repo commits separately; the session rule; a generated `project-context` block (one-paragraph summary). `CLAUDE.md` is `@AGENTS.md` plus a Claude section.
- `compose.yaml`: `include: backend/compose.yaml` plus the admin dev server.
- `Makefile`:
  - `up`, `down`.
  - `sync-api`: run `make -C backend openapi`, copy `backend/openapi/admin.json` to `frontend/openapi.json` and `backend/openapi/public.json` to `mobile/openapi.json`, then run each client's `make gen-api`. The surface-to-client mapping is one variable per client.
  - `check`: runs each repo's `make check`. It also fails if `frontend/openapi.json` or `mobile/openapi.json` differs from the backend spec it copies (stale client).
- `.claude/settings.json`: permissions for `make`, `make -C <repo>`, `docker compose`, and git read commands. A PostToolUse `Edit|Write` hook runs `.claude/hooks/format-dispatch.sh`, which resolves which repo holds `tool_input.file_path` and runs that repo's `.claude/hooks/format.sh` if present.
- `.claude/skills/sync-context/SKILL.md` plus `references/` with AGENTS/CLAUDE skeletons per stack. This is the requested generator:
  1. Read `PROJECT.md`. For each present repo read the manifest, Makefile, top-level tree, `.claude/skills|agents`, `.mcp.json`, and settings plugins. For backend also read the surface registry.
  2. In `<repo>/AGENTS.md`, rewrite only `<!-- project-context:start -->…<!-- project-context:end -->`. It covers what the repo is for in this product, relevant entities/roles/glossary, which surface it serves or consumes, sibling repos, and the contract location. Also correct drift in the commands section to match the Makefile.
  3. In `<repo>/CLAUDE.md`, refresh `<!-- claude-tools:start -->…end` (which skills/agent/MCP to use when).
  4. Create full files from the skeletons if missing. Refresh the root's own block. Be idempotent (second run produces no diff). Report a per-file summary. Never touch text outside markers.

### 6.3 API surfaces: one backend, many clients

The backend splits along two axes. Domain modules (`auth`, `users`, `items`) own models, business logic, and invariants. API surfaces (who calls) own HTTP shape and policy. A surface is an `APIRouter` tree with its own prefix, auth policy, versioning rule, response schemas, and OpenAPI file.

| | `admin` | `public` (end-user clients: mobile now, web later; not "unauthenticated") |
|---|---|---|
| Prefix | `/api/admin` | `/api/v1` |
| Caller | admin panel, deployed with the backend | mobile binaries; old versions stay installed for months |
| Versioning | none; expand, migrate, contract | path version; a breaking change ships as `/api/v2` and v1 stays until old apps are gone |
| Auth | surface-level `require_admin` on every route except login/refresh/logout; login rejects non-admins; refresh token in HttpOnly cookie | per-route `CurrentUser`; refresh token in body |
| Spec / client | `openapi/admin.json` to `frontend/` | `openapi/public.json` to `mobile/` |

Rules:

- Business logic lives only in `<module>/service.py`. Surface files `<module>/api_admin.py` and `api_public.py` stay thin: parse, authorize, call the service, map to that surface's schema. A rule enforced in the service holds for every client.
- Response schemas are per surface (`ItemAdmin`, `ItemPublic`). A field reaches the public surface only by being added to `ItemPublic`. Input schemas are shared when identical.
- `app/api/surfaces.py` is the registry: `(name, prefix, router)` per surface. `main.py` mounts from it. `scripts/export_openapi.py` writes one spec per entry filtered by prefix, so the mobile client never contains admin endpoints.
- Spans and metrics carry `api.surface`, so Grafana splits traffic, latency, and errors per client.
- Adding a client (for example public web or a partner API): add `app/api/<surface>.py`, a registry entry, and `api_<surface>.py` in the modules it needs. The client copies `openapi/<surface>.json`. This is spelled out in the backend AGENTS.md and the `new-feature-module` skill.
- Guard tests iterate the registry so new routes are covered automatically: every admin route except login/refresh/logout returns 401 for anonymous callers and 403 for role `user`; `public.json` contains no admin path.

Template example: items have `is_published`. Admins list, create, edit, and delete all items. Public clients list and read published items only (`ItemPublic` is `id, name, description`).

### 6.4 Backend (`template/backend/`)

Stack: uv, FastAPI, Pydantic 2 + pydantic-settings, SQLAlchemy 2 async + asyncpg, Alembic, TaskIQ (RedisStreamBroker, which acks) + taskiq-fastapi + TaskiqScheduler, Redis, OpenTelemetry, structlog, pwdlib[argon2], PyJWT, ruff, ty (Astral type checker; configured under `[tool.ty]` in `pyproject.toml` with warnings treated as errors, run via `uv run ty check`; verify config keys against ty docs at build start), pytest + testcontainers. ty has no Pydantic plugin; Pydantic models and SQLAlchemy `Mapped[]` type-check through their native annotations.

```
src/app/
  main.py          # create_app(): lifespan (engine, broker startup/shutdown when not worker), mount surfaces from registry,
                   #   problem+json handlers, CORS (admin origin) from settings, FastAPI built-in telemetry (exclude health)
  cli.py           # create-admin (argparse)
  health.py        # /health/live, /health/ready (db + redis ping)
  api/surfaces.py  # registry
  api/admin.py     # auth.api_admin (+ /auth) and a protected sub-router with require_admin holding users/items admin routers
  api/public.py    # auth.api_public, users.api_public, items.api_public
  core/config.py      Settings(BaseSettings), APP_ prefix, SecretStr, JWT secret required + min length
  core/db.py          engine, async_sessionmaker, get_session (commit/rollback), Base with MetaData naming convention
  core/security.py    argon2 hash/verify, access JWT encode/decode, refresh token gen + sha256
  core/deps.py        CurrentUser, require_admin
  core/rate_limit.py  Redis fixed-window limiter dependency (login, register)
  core/errors.py      domain exceptions -> RFC 9457
  core/pagination.py  Page[T] {items,total}; limit/offset/sort/q params
  core/logging.py     structlog JSON stdout + trace_id/span_id
  core/telemetry.py   tracer/meter/log providers, OTLP exporter, SQLAlchemy/asyncpg/redis/httpx instrumentation, api.surface attribute
  core/broker.py      RedisStreamBroker + taskiq OpenTelemetryMiddleware, TaskiqScheduler(LabelScheduleSource); InMemoryBroker when APP_ENV=test
  auth/   models (RefreshToken: token_hash, family_id, expires_at, revoked_at) schemas service
          api_admin (login/refresh/logout, cookie transport, admin-only login) api_public (same, body transport)
          tasks (purge_expired_refresh_tokens, daily)
  users/  models (User: email unique, password_hash, role admin|user, is_active) schemas (UserAdmin, UserPublic) service
          api_admin (list, change role, deactivate) api_public (register, me) tasks (send_welcome_email stub)
  items/  models (Item: id, name, description, is_published, created_by_id, created_at, updated_at) schemas (ItemCreate, ItemUpdate, ItemAdmin, ItemPublic) service api_admin (CRUD) api_public (published list/detail)
scripts/export_openapi.py   # openapi/admin.json, openapi/public.json
migrations/   async env.py; first revision: users, refresh_tokens, items
tests/        testcontainers Postgres, savepoint-per-test session, httpx ASGITransport, fixtures anon/user/admin clients,
              tests per module per surface (tests/items/test_api_admin.py, test_api_public.py), tests/test_surfaces.py (guards)
openapi/      committed specs; CI fails on drift
compose.yaml  postgres, redis, otel-lgtm, migrate (one-shot), api, worker, scheduler
Dockerfile    multi-stage uv, non-root, healthcheck
Makefile pyproject.toml .env.example .pre-commit-config.yaml .github/workflows/ci.yml .github/dependabot.yml
```

Rules:

- No repository layer. The service talks to SQLAlchemy. Add one per module when queries grow.
- Stable operationIds via `generate_unique_id_function` (`{tag}-{route_name}`) so generated TS/Dart clients get clean names.
- Tasks are typed and idempotent.
- Primary keys are UUIDv7 (`uuid.uuid7()`). Items are hard-deleted. Field lists are in section 5, item 24.
- Backend CI runs `oasdiff breaking` on `openapi/public.json` against the base branch and fails on breaking changes.

Auth (every detail is a requirement):

- Access token: JWT, 15 minutes.
- Refresh token: opaque, 30 days, stored as sha256 (never the raw token), rotated on every use.
- Reuse detection: presenting an already-rotated refresh token revokes its whole family (`family_id`).
- Admin surface transport: refresh token in a cookie with `HttpOnly; Secure; SameSite=Strict; Path=/api/admin/auth`. The access token lives in memory only (admin SPA).
- Public surface transport: refresh token in the request/response body, stored by the app in `flutter_secure_storage`.
- Both transports call the same `auth.service`.
- Admin-only login: the admin login rejects non-admin users.
- Cookie `Secure` flag comes from `APP_COOKIE_SECURE` (default `true`; `.env.example` sets `false` for http localhost). CORS with credentials only for configured admin origins.
- Admin invariants (service level, tested): admins may promote users. An admin cannot demote or deactivate themselves. The last active admin cannot be demoted or deactivated.
- Admin logout needs only the refresh cookie (no `require_admin`). It revokes the family and clears the cookie.
- Login is rate-limited to 5 attempts per 15 minutes per IP + email. Register is limited to 10 per hour per IP. Both use the Redis fixed-window limiter.
- Inactive users (`is_active = false`) are rejected.
- JWT secret is required and must be at least 32 bytes, validated at settings load (`SecretStr`).
- Passwords hashed with argon2 (`pwdlib[argon2]`).
- `purge_expired_refresh_tokens` runs daily as a scheduled task.

Observability:

- One trace spans HTTP, SQL, enqueue, and worker.
- Logs carry trace ids.
- Grafana is at `localhost:3000`, filterable by `api.surface`.
- Health endpoints are excluded from FastAPI telemetry.

### 6.5 Admin panel (`template/frontend/`)

Stack: Vite 8, React 19, TypeScript strict, TanStack Router (file-based, `beforeLoad` admin guard) + Query + Table, `@hey-api/openapi-ts` (bundled fetch client; plugins `@tanstack/react-query` and zod; base URL via `runtimeConfigPath`) generating `src/client/` from `openapi.json`, Tailwind v4 + shadcn/ui, react-hook-form + zod, ESLint flat config (typescript-eslint, react-hooks, jsx-a11y) + Prettier, Vitest + Testing Library + MSW.

`openapi.json` is a copy of backend `openapi/admin.json`. Generated code is committed, never hand-edited, and CI checks for drift.

Deploy: the production image is a multi-stage pnpm build served by `nginxinc/nginx-unprivileged` with an SPA fallback. Admin and API must share a site (one reverse proxy, or sibling subdomains of one registrable domain), because the refresh cookie is `SameSite=Strict`. The README and AGENTS.md say this explicitly.

```
src/main.tsx  src/router.tsx  src/env.ts (zod-validated VITE_ env)  src/client-config.ts (runtimeConfigPath target)
src/lib/auth.ts              # in-memory access token, single-flight refresh on 401 via client interceptor (cookie), logout
src/client/                  # generated
src/components/ui/           # shadcn
src/components/data-table/   # generic DataTable: server pagination/sort/search bound to URL search params
src/routes/__root.tsx  login.tsx  _app.tsx (sidebar layout + guard)  _app/index.tsx (dashboard counts)
           _app/items/{index,new,$itemId}.tsx  _app/users/index.tsx
vite.config.ts               # dev proxy /api -> backend (same origin keeps refresh cookie working locally)
Dockerfile Makefile .github/workflows/ci.yml .github/dependabot.yml
```

### 6.6 Mobile (`template/mobile/`)

Stack: Flutter (pinned in pubspec `environment`; CI reads it), Riverpod 3 (no codegen), go_router (auth redirect), dio + auth interceptor (single-flight refresh, body transport), `swagger_parser` + retrofit + json_serializable via build_runner from `openapi.json`, flutter_secure_storage, `--dart-define-from-file=config/dev.json`, flutter_lints + strict-casts / strict-inference / strict-raw-types.

`openapi.json` is a copy of backend `openapi/public.json`. The template does not ship the generated client, because generating it needs the Flutter SDK. `make bootstrap` runs `gen-api`, generated projects commit the output, and their CI checks for drift.

Architecture follows the official Flutter guide: a UI layer (screens plus view models as Riverpod notifiers) and a data layer (repositories plus services). Tests use hand-written fakes (`class FakeItemsRepository implements ItemsRepository`), no mocking library.

```
lib/main.dart  lib/src/app.dart
lib/src/core/{config, network, router, theme}
lib/src/data/api/                 # generated
lib/src/features/auth/{data,ui}   # login, register, session state
lib/src/features/items/{data,ui}  # paginated published list, detail
test/*.dart.jinja (incl. widget_test.dart)  integration_test/  config/dev.json.example
swagger_parser.yaml  analysis_options.yaml  Makefile  .github/workflows/ci.yml  .github/dependabot.yml
```

### 6.7 AI configuration per repo

Backend:

- Hook `.claude/hooks/format.sh`: `ruff format` and `ruff check --fix` on the edited `.py`, wired as PostToolUse `Edit|Write`.
- Permissions: allow `uv run *`, `make *`, `docker compose *`. Deny `Read(./.env)` and `Read(./.env.*.local)` (keeps `.env.example` readable).
- Skills:
  - `new-feature-module`: mirror `items/` (model, schemas per surface, service, `api_<surface>.py` per surface that needs it, registry wiring, migration, tests, re-export specs). Also covers adding a new surface.
  - `db-migration`: autogenerate and review (naming, downgrade, zero-downtime, never edit applied revisions).
  - `background-task`: task, retries, idempotency, schedule, InMemoryBroker test.
- Subagent `backend-reviewer`: checks logic outside services, admin fields leaking into public schemas, authz, async correctness, N+1, transaction scope, migration safety, breaking changes on `/api/v1`.
- `.mcp.json`: context7.

Admin panel:

- Hook `format.sh`: prettier plus `eslint --fix`. Deny `.env*.local`.
- Skills: `new-admin-resource` (route files, columns, form from the generated client, guard, tests), `api-client` (regenerate, use generated queryOptions/mutations, never hand-edit), `ui-component` (shadcn add plus an a11y checklist).
- Subagent `frontend-reviewer`.
- `.mcp.json`: context7 and Playwright MCP (`npx @playwright/mcp@<pinned>`).

Mobile:

- Hook `format.sh`: `dart format`.
- Skills: `new-feature` (repository, service, notifier, screen, route, fakes, tests), `api-client` (regenerate plus build_runner).
- Subagent `flutter-reviewer`.
- Official Flutter Claude plugin (`dart-flutter@dart-flutter` from `flutter/agent-plugins`) declared via `extraKnownMarketplaces` and `enabledPlugins` in `.claude/settings.json`. It supplies the Dart/Flutter MCP, so there is no separate `dart mcp-server` entry. Confirm the marketplace repo belongs to the official `flutter` GitHub org before enabling.
- `.mcp.json`: context7.

Workspace root: see 6.2 (`settings.json`, `format-dispatch.sh`, `sync-context`).

### 6.8 AGENTS.md / CLAUDE.md shape

Applies to each repo. The template ships them; `/sync-context` refines them.

AGENTS.md (about 100 to 150 lines), in this order:

1. `project-context` marker block.
2. Stack.
3. Commands.
4. Architecture map (backend: modules x surfaces).
5. Conventions.
6. Testing.
7. Definition of done: `make check` green, specs/client regenerated, migration reviewed.
8. Never list: edit generated code, edit applied migrations, commit secrets, put logic in surface files, break `/api/v1` in place.

CLAUDE.md is `@AGENTS.md` plus a `claude-tools` marker block. The import is required: Claude reads AGENTS.md natively only when no CLAUDE.md exists up the tree, and the workspace CLAUDE.md always exists. Copier's 3-way merge on update keeps marker-block edits.

### 6.9 Versions

Verified against PyPI / npm / pub.dev on 2026-10-20. Re-check at build start.

- Backend: Python 3.14, FastAPI 0.150, Pydantic 2.14, pydantic-settings 2.16, SQLAlchemy 2.1 (`sqlalchemy[asyncio]`), Alembic 1.20, asyncpg 0.32, taskiq 0.13 (`taskiq[opentelemetry]`), taskiq-redis 1.2, taskiq-fastapi 0.5, OTel SDK 1.45, structlog 26.1, ruff 0.17, ty (latest at build start; Astral, same release train as ruff/uv), testcontainers 4.15, Copier 9.19.
- Admin: React 19.3, Vite 8.3, TypeScript `~6.0.3` (7.x breaks typescript-eslint), TanStack Router 1.170 / Query 5.104, Tailwind 4.3, `@hey-api/openapi-ts` 0.99.0 (exact pin), Vitest 5, ESLint 10, pnpm 12, Node >= 24.
- Mobile: Flutter 3.47 / Dart 3.13, flutter_riverpod 3.4, go_router 18, dio 5.11, swagger_parser 1.45, retrofit 4.10.

### 6.10 Cross-repo contract (shared by all implementation plans)

The plans for template, backend, admin, and mobile are written separately. These names are fixed so they agree.

**Template development.** Each component is developed and tested in place under `template/<component>/`. `copier.yml` `_exclude` keeps dev artifacts out of generated output: `.venv`, `node_modules`, `uv.lock`, `pnpm-lock.yaml`, `pubspec.lock`, `.dart_tool`, `build`, `dist`, caches. Only files that need answers get the `.jinja` suffix: README, AGENTS.md, CLAUDE.md, the answers file, a few config files, mobile `pubspec.yaml` and `Makefile`, and mobile `test/` and `integration_test/` files. Full generation is tested by `make test-template`.

**OpenAPI.** The main app has `openapi_url=None`, so there is no combined spec. `app/api/surfaces.py` exposes `surface_openapi(app: FastAPI, surface: Surface) -> dict`, built with `fastapi.openapi.utils.get_openapi` over that surface's routes only. When `APP_ENV=dev`, each surface serves `{prefix}/openapi.json` and `{prefix}/docs`. `scripts/export_openapi.py` uses the same function. operationId = `{tag}-{route.name}`, where tags are module names (`auth`, `users`, `items`) and route names are set with `name=` (`list`, `get`, `create`, `update`, `delete`, `login`, `refresh`, `logout`, `register`, `me`). Duplicate operationIds across surfaces are harmless because each spec stands alone. Page schemas are explicit subclasses (`ItemAdminPage(Page[ItemAdmin])`) so spec names stay clean.

**Admin surface `/api/admin`:**

| Method + path | operationId | Request | Response |
|---|---|---|---|
| POST `/auth/login` | `auth-login` | `LoginRequest{email, password}` | 200 `AdminTokenResponse{access_token, token_type="bearer", expires_in=900}` + Set-Cookie; 401 bad credentials or inactive; 403 not admin; 429 |
| POST `/auth/refresh` | `auth-refresh` | cookie `refresh_token` | 200 `AdminTokenResponse` + rotated cookie; 401 |
| POST `/auth/logout` | `auth-logout` | cookie | 204, cookie cleared |
| GET `/users/me` | `users-me` | — | `UserAdmin` |
| GET `/users` | `users-list` | `limit, offset, sort, q` | `UserAdminPage` |
| PATCH `/users/{user_id}` | `users-update` | `UserAdminUpdate{role?, is_active?}` | `UserAdmin`; 409 on admin-invariant violation |
| GET `/items` | `items-list` | `limit, offset, sort, q` | `ItemAdminPage` |
| GET `/items/{item_id}` | `items-get` | — | `ItemAdmin`; 404 |
| POST `/items` | `items-create` | `ItemCreate{name, description?, is_published=false}` | 201 `ItemAdmin` |
| PATCH `/items/{item_id}` | `items-update` | `ItemUpdate{name?, description?, is_published?}` | `ItemAdmin`; 404 |
| DELETE `/items/{item_id}` | `items-delete` | — | 204; 404 |

**Public surface `/api/v1`:**

| Method + path | operationId | Request | Response |
|---|---|---|---|
| POST `/auth/login` | `auth-login` | `LoginRequest` | 200 `TokenPair{access_token, refresh_token, token_type="bearer", expires_in=900}`; 401; 429 |
| POST `/auth/refresh` | `auth-refresh` | `RefreshRequest{refresh_token}` | 200 `TokenPair`; 401 |
| POST `/auth/logout` | `auth-logout` | `RefreshRequest` | 204 |
| POST `/users/register` | `users-register` | `RegisterRequest{email, password}` | 201 `UserPublic`; 409 email taken; 429 |
| GET `/users/me` | `users-me` | — | `UserPublic` |
| GET `/items` | `items-list` | `limit, offset, sort, q` | `ItemPublicPage` (published only) |
| GET `/items/{item_id}` | `items-get` | — | `ItemPublic`; 404 if missing or unpublished |

Every public route except `auth-*` and `users-register` requires `CurrentUser` (a bearer access token). Items are browsable only after login.

**Field rules:**
- `email` is `EmailStr`, stored lowercased.
- `password` is 12 to 128 characters.
- `name` is 1 to 200 characters.
- `description` is optional, up to 2000 characters.
- `limit` defaults to 20 (range 1 to 100); `offset` is at least 0.
- `sort` is a field name with an optional `-` prefix. Items allow `name`, `created_at`, `updated_at`; users allow `email`, `created_at`. The default is `-created_at`.
- `q` is a case-insensitive substring match on item `name` or user `email`.
- `Page[T]` = `{items: list[T], total: int}`.
- Admin dashboard counts come from `items-list` / `users-list` with `limit=1` and read `total`. There is no extra endpoint.

**Tokens and errors:**
- The access JWT is HS256. Claims: `sub` (user id), `role`, `type="access"`, `iat`, `exp`.
- Domain errors are `application/problem+json` (`type, title, status, detail`).
- Validation errors keep FastAPI's default 422 shape.
- The admin refresh cookie is named `refresh_token`, with `Max-Age` of 30 days and the attributes in 6.4.

**Env and ports:**

Backend env:
- `APP_ENV` (`dev|test|prod`)
- `APP_DATABASE_URL`
- `APP_REDIS_URL`
- `APP_JWT_SECRET`
- `APP_COOKIE_SECURE`
- `APP_CORS_ORIGINS`
- standard `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME`
- uvicorn's `FORWARDED_ALLOW_IPS`: the reverse proxy IPs, so rate limits see real client IPs (uvicorn runs with `--proxy-headers`)

Client config:
- Admin: `VITE_API_BASE_URL` (default empty = same origin).
- Mobile: `config/dev.json` key `API_BASE_URL`; the example uses `http://localhost:8000`, with a comment that the Android emulator needs `http://10.0.2.2:8000`.

Ports:
- API 8000
- admin dev 5173
- Grafana 3000
- Postgres 5432
- Redis 6379
- OTLP 4317/4318

**AI-config interfaces:**
- Marker lines are exactly `<!-- project-context:start -->`, `<!-- project-context:end -->`, `<!-- claude-tools:start -->`, `<!-- claude-tools:end -->`.
- Each repo's `.claude/hooks/format.sh` reads the Claude Code hook JSON on stdin. It formats `tool_input.file_path` only if the extension is its own and the file sits inside that repo. It always exits 0, so it never blocks an edit.
- The root `format-dispatch.sh` passes the same stdin to `<repo>/.claude/hooks/format.sh`.

## 7. Left to the builder

The design deliberately does not fix these:

- Exact file contents and wording of skills, subagents, `AGENTS.md`, `CLAUDE.md`, and the `sync-context` skeletons.
- Makefile internals (target names are fixed in section 5, item 4).
- shadcn component selection, theme, and visual design.
- Exact Compose healthchecks and dependency ordering.
- The `grafana/otel-lgtm` image tag.
- How `format-dispatch.sh` parses stdin JSON (prefer `jq` if installed, else python3).
- CI workflow details for each repo and the exact drift-check commands.
- The `.copier-answers.yml` fields beyond what Copier writes by default.
- Dependabot ecosystems and schedule.
- Contents of `config/dev.json.example`, `.env.example`, and the sample `PROJECT.md` used for verification.
- Dashboard counts shown on the admin index route.

## 8. Acceptance criteria

1. Template generation: with the template committed, `make test-template` generates the workspace from an absolute path into a scratch dir and produces four git repos (workspace, backend, frontend, mobile). Each has its own `.copier-answers.yml` recording its `component` and every shared answer. Without `flutter` on PATH, generation still succeeds and mobile prints the `make bootstrap` warning.
2. Backend `make check` passes ruff, ty, and pytest. The tests cover:
   - Refresh rotation and reuse detection on both transports.
   - Surface guard tests: admin routes (except login/refresh/logout) return 401 anonymous and 403 for role `user`; `public.json` contains no admin path.
   - Admin-only login.
   - Admin invariants: no self-demotion or self-deactivation; the last active admin is protected.
   - Published-only public listing.
   - Rate limit.
   - Items CRUD.
   - Both tasks (`send_welcome_email`, `purge_expired_refresh_tokens`).
3. Backend runtime: `make up` brings the stack up and `/health/ready` returns 200. `make create-admin` works, then login and item creation succeed. Registering a user makes the worker log `send_welcome_email`. Grafana shows one trace HTTP to SQL to task, tagged with `api.surface`.
4. Admin `make check` passes (lint, typecheck, vitest, build). `make gen-api` yields no diff. Driving the running stack via Playwright MCP: login; items create, edit, publish, delete; change a user's role; reload keeps the session (refresh cookie).
5. Mobile (not run locally, by the user's choice; template CI and the mobile repo's CI on GitHub Actions run analyze and test, and the simulator run is left to the user): `flutter analyze` and `flutter test` pass. The generated client has no admin endpoints. On a simulator or emulator against the local API: register, login, list published items only, and restart keeps the session.
6. Update path: tag `v0.1.0`, make a trivial template change, tag `v0.1.1`. `copier update` in a generated `backend/` applies cleanly, no tasks re-run, and a filled `project-context` block is kept.
7. Root AI: with a sample `PROJECT.md`, `/sync-context` fills the blocks in all four AGENTS.md / CLAUDE.md sets and changes nothing outside markers. A rerun produces no diff. A root-session edit of a backend `.py` file gets ruff-formatted via the dispatch hook.
8. After all of the above, ask the user whether to commit and tag `v0.1.0`.

## 9. Build order

0. Ask before installing `copier` (`uv tool install copier`). Do not install Flutter. Re-check versions.
1. `copier.yml`, answers-file templates, workspace template, template README/Makefile.
2. Backend (surfaces registry first, then modules), then export both specs.
3. Admin panel from `admin.json`.
4. Mobile from `public.json`.
5. AI configs (hooks, skills, subagents, MCP/plugins), AGENTS.md/CLAUDE.md content, and root `sync-context`.
6. Per-repo CI, template CI, and `make test-template`.
7. Run the acceptance criteria above. Then ask to commit and tag `v0.1.0`.
