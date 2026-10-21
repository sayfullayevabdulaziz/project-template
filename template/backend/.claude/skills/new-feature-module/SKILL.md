---
name: new-feature-module
description: Scaffold a new backend feature module (model, schemas, service, per-surface routers, migration, tests). Use when asked to add a resource, entity, endpoint set, or a new API surface to the backend.
---

# New feature module

Mirror `src/app/items/`. Replace `<mod>` with the module name.

1. Create `src/app/<mod>/` with `__init__.py`, `models.py`, `schemas.py`, `service.py`, and one `api_<surface>.py` per surface needed.
2. `models.py`: the SQLAlchemy model on `Base`. Import it in `src/app/core/models.py` so Alembic and the test fixtures see it.
3. `schemas.py`: separate schemas per surface (for example `<Mod>Admin`, `<Mod>Public`, `<Mod>Create`, `<Mod>Update`). Never reuse an admin schema on the public surface.
4. `service.py`: all logic and queries, taking an `AsyncSession`. Routers contain no business logic.
5. `api_admin.py` / `api_public.py`: thin routers with `prefix`, `tags=["<mod>"]`, and documented error `responses`. Follow `items/api_admin.py`.
6. Register routers. Admin: include in the `protected` router in `src/app/api/admin.py` (behind `require_admin`). Public: include in `src/app/api/public.py`.
7. Create the migration with the `db-migration` skill.
8. Tests under `tests/<mod>/`: `test_service.py` plus `test_api_<surface>.py` for each surface, covering authz (401/403 on admin), validation, and not-found.
9. Run `make check`, then `make openapi` and commit the changed `openapi/*.json`.
10. If a frontend or mobile client consumes the API, run `make sync-api` from the workspace root.

## Adding a new surface

1. Add `src/app/api/<surface>.py` with an `APIRouter(prefix="/api/<surface>", dependencies=[Depends(tag_surface("<surface>"))])` and its auth policy (a `Depends(...)` on the router, as `admin.py` does with `require_admin`).
2. Add a `Surface("<surface>", "/api/<surface>", router)` to `SURFACES` in `src/app/api/surfaces.py`.
3. Add `api_<surface>.py` in each module that needs the surface, then include it from the new router.
4. The guard tests iterate `SURFACES`, so they cover the new surface automatically. Do not hard-code surface names in tests.
5. Run `make openapi`: it writes `openapi/<surface>.json`, which clients copy.
