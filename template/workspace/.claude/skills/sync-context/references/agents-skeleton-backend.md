# <project name> backend

<!-- project-context:start -->
_Not generated yet. Fill PROJECT.md, then run /sync-context from the workspace root._
<!-- project-context:end -->

## Stack

uv, FastAPI, Pydantic 2 + pydantic-settings, SQLAlchemy 2 async + asyncpg, Alembic, TaskIQ + Redis, OpenTelemetry, structlog, pwdlib[argon2], PyJWT, ruff, ty, pytest + testcontainers.

## Commands

- `make dev`: run the API with reload.
- `make test`: run pytest.
- `make lint`: ruff and ty.
- `make fmt`: format with ruff.
- `make check`: lint, tests and the OpenAPI drift check.
- `make openapi`: export `openapi/admin.json` and `openapi/public.json`.
- `make up`: start the compose stack.
- `make down`: stop the compose stack.
- `make migrate`: apply Alembic migrations.
- `make migration`: autogenerate a migration.
- `make create-admin`: create an admin user.

## Architecture map

Domain modules own models, business logic and invariants. Surfaces own HTTP shape and policy.

| Module | `admin` (`/api/admin`) | `public` (`/api/v1`) |
|---|---|---|
| `auth` | `auth/api_admin.py` | `auth/api_public.py` |
| `users` | `users/api_admin.py` | `users/api_public.py` |
| `items` | `items/api_admin.py` | `items/api_public.py` |

- `src/app/api/surfaces.py` is the surface registry: `(name, prefix, router)`. `main.py` mounts from it.
- Business logic lives only in `<module>/service.py`. Surface files parse, authorize, call the service, map to that surface's schema.
- Response schemas are per surface (`ItemAdmin`, `ItemPublic`). A field reaches the public surface only by being added to the public schema.
- `src/app/core/` holds config, db, security, deps, errors, logging, telemetry and the broker.
- `openapi/` holds the committed specs. Clients copy them.

## Conventions

- No repository layer. The service talks to SQLAlchemy.
- Every timestamp is UTC. Money is integer minor units. IDs are UUIDv7.
- Errors are RFC 9457 problem+json from domain exceptions.
- Tasks are typed and idempotent.
- Stable operationIds: `{tag}-{route_name}`.
- Settings come from `APP_`-prefixed env vars; never read `os.environ` directly.

## Testing

- pytest with a testcontainers Postgres and a savepoint-per-test session.
- Tests per module per surface: `tests/<module>/test_api_admin.py`, `test_api_public.py`.
- `tests/test_surfaces.py` guards the registry: admin routes reject anonymous and non-admin callers, `public.json` has no admin path.
- Add a test with every route or rule you add.

## Definition of done

- `make check` is green.
- `make openapi` was run and the specs are committed.
- Any migration is reviewed by hand.
- Clients are updated: run `make sync-api` at the workspace root.

## Never

- Edit generated code.
- Edit an applied migration.
- Commit secrets.
- Put logic in surface files.
- Break `/api/v1` in place; ship `/api/v2`.
