---
name: new-feature-module
description: Scaffold a new backend feature module (model, schemas, service, per-surface routers, migration, tests). Use when asked to add a resource, entity, endpoint set, or a new API surface to the backend.
---

# New feature module

Mirror `src/app/items/`. Replace `<mod>` with the module name.

1. Create `src/app/<mod>/` with `__init__.py`, `models.py`, `schemas.py`, `repository.py`, `service.py`, and one `api_<surface>.py` plus `schemas_<surface>.py` per surface needed.
2. `models.py`: the SQLAlchemy model on `Base`. Import it in `src/app/core/models.py` so Alembic and the test fixtures see it.
3. Schemas: `schemas_admin.py` holds `<Mod>Admin`, `<Mod>Create`, `<Mod>Update`; `schemas_public.py` holds `<Mod>Public`. `schemas.py` holds only field types and classes used by two or more surfaces. `api_<surface>.py` imports only its own `schemas_<surface>.py`; `tests/test_schema_boundaries.py` fails otherwise.
4. `repository.py` and `service.py`, as `items/` does. `repository.py` holds all SQLAlchemy queries: a `<Mod>Repo(Repo[<Mod>], Protocol)` and a `<Mod>Repository(BaseRepository[<Mod>])`. `service.py` holds all logic in a `<Mod>Service` class that takes the repository Protocol and plain values (not surface schemas), never the session, plus `<Mod>ServiceDep`. Routers inject the service and contain no business logic.
5. `api_admin.py` / `api_public.py`: thin routers with `prefix`, `tags=["<mod>"]`, and documented error `responses`. Follow `items/api_admin.py`.
6. Register routers. Admin: include in the `protected` router in `src/app/api/admin.py` (behind `require_admin`). Public: include in `src/app/api/public.py`.
7. Create the migration with the `db-migration` skill.
8. Add a `Fake<Mod>Repository` to `tests/fakes.py`. Tests under `tests/<mod>/`: `test_service.py` (on the fake), `test_repository.py` (on Postgres) plus `test_api_<surface>.py` for each surface, covering authz (401/403 on admin), validation, and not-found.
9. Run `make check`, then `make openapi` and commit the changed `openapi/*.json`.
10. If a frontend or mobile client consumes the API, run `make sync-api` from the workspace root.

## Adding a new surface

1. Add `src/app/api/<surface>.py` with an `APIRouter(prefix="/api/<surface>", dependencies=[Depends(tag_surface("<surface>"))])` and its auth policy (a `Depends(...)` on the router, as `admin.py` does with `require_admin`).
2. Add a `Surface("<surface>", "/api/<surface>", router)` to `SURFACES` in `src/app/api/surfaces.py`.
3. Add `api_<surface>.py` in each module that needs the surface, then include it from the new router.
4. The guard tests iterate `SURFACES`, so they cover the new surface automatically. Do not hard-code surface names in tests.
5. Run `make openapi`: it writes `openapi/<surface>.json`, which clients copy.
