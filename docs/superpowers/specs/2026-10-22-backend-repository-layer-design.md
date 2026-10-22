# Backend repository layer

Date: 2026-10-22
Scope: `template/backend/` (the Copier template for generated backend repos), plus the backend `AGENTS.md` skeleton in `template/workspace/` that `/sync-context` rebuilds from

## Intent

Services in the backend template run SQLAlchemy queries themselves, so every service test needs Postgres. The owner wants a repository layer between services and the database:

- A generic `BaseRepository` holds the common CRUD queries; each module subclasses it for its own queries (e.g. `get_by_email`).
- Services receive repositories and contain only business rules.
- Service tests run against hand-written in-memory fake repositories, with no Postgres and no mocking library. This matches the mobile template, which already uses `FakeItemsRepository implements ItemsRepository`.

This reverses a decision in `docs/superpowers/specs/2026-10-20-project-template-design.md` (line 53 non-goal, line 273 "No repository layer"). That spec must be updated as part of this work.

## Goals

- `core/repository.py` with a generic `BaseRepository[Model]`.
- `<module>/repository.py` in `items`, `users`, `auth` with a concrete repository and a `Protocol` describing it.
- Services become classes that take repository Protocols in `__init__`.
- Routers, tasks, `deps.py` and the CLI get services/repositories through constructors, not module imports.
- Service tests use fakes. Repository tests use Postgres and cover what fakes cannot (search, sort, filters, locks, unique races, bulk updates).
- Generated-project guidance (AGENTS.md, `new-feature-module` skill, `backend-reviewer` agent) teaches the new pattern.

## Non-goals

- No behavior change for any endpoint, task or CLI command. API tests stay as they are and must pass unchanged.
- No Unit of Work object. The request-scoped session from `get_session` still owns the transaction.
- No mocking library, no DI container library.

## Anti-goals (would be a failure even if it works)

- SQLAlchemy expressions (`select`, `where` clauses, `Item.name.ilike(...)`) passing from services into repositories. Fakes cannot evaluate them, which defeats the point.
- Repository methods taking surface schemas (`ItemCreate`, `UserAdminUpdate`). Services keep taking plain values; repositories take models and plain values.
- Module-level repository or service singletons (`user_repository = UserRepository(User)`). They only allow fakes through monkeypatching.
- Fakes that reimplement Postgres (search, sort, locking). Fakes stay dumb; Postgres behavior is tested on Postgres.

## Constraints

- Python 3.14 generics syntax (`class BaseRepository[M: Base]`), as `core/pagination.py` already uses.
- Type checker is `ty` (`make lint`). Fakes must satisfy the Protocols without `cast` or `# type: ignore`.
- IDs are UUIDv7 (`uuid7_pk()`), not ints.
- Every route must keep getting the session through `SessionDep` (function scope; see the comment in `core/db.py`). Service dependencies must depend on `SessionDep`, so the service, `get_current_user` and the router all share one cached session per request.
- Taskiq tasks get the session from `TASK_SESSION`; tests override `get_task_session`.

## Approaches considered

**A. Service classes with repositories injected via the constructor (chosen).** `ItemService(items: ItemRepo)`. One FastAPI dependency per module builds it from `SessionDep`. Tests do `ItemService(FakeItemRepository())`. Wiring lives in one place per module; cross-module needs (auth needs users and tokens; users needs tokens) are handled in the constructor. Same pattern as the mobile template. Cost: touches every router, both tasks, `cli.py` and every service test.

**B. Keep module-level service functions and add repository arguments** (`service.get(items_repo, item_id)`). Smaller first diff, but every caller builds and passes each repository, and multi-repository flows (`auth.login`, `users.admin_update`) push that onto every router, task and CLI call. Rejected.

**Dropped:** module singletons plus monkeypatching (the shape of the owner's example). It is the only way to fake them and the owner wants fakes.

The owner picked A.

## Design

### Layers and ownership

```
router / task / cli  ->  <Mod>Service  ->  <Mod>Repo (Protocol)
                                              ^ implemented by <Mod>Repository (SQLAlchemy)
                                              ^ implemented by Fake<Mod>Repository (tests)
```

- **Repositories** own every SQLAlchemy query. They return models, `None`, counts, or booleans. They never raise domain errors (`NotFound`, `Conflict`, ...). They never commit, except through the explicit `commit()` method below.
- **Services** own business rules and raise domain errors. They never import `sqlalchemy` or touch an `AsyncSession`.
- **Session and transaction** stay owned by `get_session` / `get_task_session` (commit on success, rollback on error). Repositories hold the session they were constructed with.
- Rule for AGENTS.md: "SQLAlchemy queries live only in `repository.py`."

### `core/repository.py`

```python
class BaseRepository[M: Base]:
    model: type[M]                 # set by each subclass
    search_column: str | None = None  # column for ListParams.q; None means q is ignored

    def __init__(self, session: AsyncSession) -> None: ...

    async def get(self, id: UUID) -> M | None          # session.get (identity map first)
    async def add(self, obj: M) -> M                   # add + flush + refresh (server defaults)
    async def save(self, obj: M) -> M                  # flush + refresh after the service set attributes
    async def delete(self, obj: M) -> None             # delete + flush
    async def commit(self) -> None                     # see "Mid-flow commits"
    async def _list(self, params: ListParams, *where) -> tuple[list[M], int]
```

- `_list` is protected: it is how subclasses build their public `list(...)` with named filters (e.g. `published_only`). It keeps today's behavior: `ilike` on `search_column` with `escape_like`, `apply_sort` (including the `id` tiebreaker), `limit`/`offset`, and a `count()` total.
- There is no generic `update`. Services set attributes on the model, then call `save`. The current "ignore `None` for NOT NULL fields, except `description`" rule stays in `ItemService.update`.
- Alongside it, a generic `Repo[M]` Protocol with `get`, `add`, `save`, `delete`, `commit`. Module Protocols extend it.

### Module repositories

Each `<mod>/repository.py` holds the Protocol and the SQLAlchemy class.

**items**
- `ItemRepo(Repo[Item], Protocol)`: `list(params, *, published_only: bool) -> tuple[list[Item], int]`.
- `ItemRepository`: `model = Item`, `search_column = "name"`.

**users**
- `UserRepo`: `get_by_email(email)`, `get_for_update(id)` (`with_for_update`, `populate_existing`), `count_active_admins(exclude_id) -> int`, `add_unique(user) -> User | None` (savepoint plus `IntegrityError`; returns `None` when the email is taken), `list(params)`.
- `UserRepository`: `model = User`, `search_column = "email"`. Lower-casing `q` stays (today `list_users` lower-cases it).

**auth**
- `RefreshTokenRepo`: `get_by_hash_for_update(token_hash)`, `get_family_id(token_hash)`, `revoke_family(family_id, at)`, `revoke_all_for_user(user_id)`, `purge_expired(now) -> int`.
- `RefreshTokenRepository`: `model = RefreshToken`.

### Services

- `ItemService(items: ItemRepo)`: `create(actor, *, name, description, is_published)`, `get(id, *, published_only)`, `list(params, *, published_only)`, `update(id, changes)`, `delete(id)`.
- `UserService(users: UserRepo, tokens: RefreshTokenRepo)`: `get`, `get_by_email`, `register`, `list`, `admin_update` (row lock through `get_for_update`, last-admin rule, revokes tokens on deactivation through `tokens.revoke_all_for_user`).
- `AuthService(users: UserRepo, tokens: RefreshTokenRepo)`: `login`, `refresh`, `logout`, `purge_expired`. `settings` stays a keyword argument of `login`/`refresh` as today, so `purge_expired` needs no settings. The timing-equalising `DUMMY_HASH` check and the `Issued` dataclass stay in the service.

Method names and signatures otherwise mirror today's functions. `list_items`/`list_users` become `list`.

### Wiring

Each module's `service.py` ends with its FastAPI dependency:

```python
def get_item_service(session: SessionDep) -> ItemService:
    return ItemService(ItemRepository(session))

ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
```

- Routers replace `session: Session` with `items: ItemServiceDep` (etc.).
- `users/api_public.register` keeps its explicit `session.commit()` before `send_welcome_email.kiq(...)`, so it takes both `UserServiceDep` and `SessionDep` (same cached session).
- Tasks build services inline from the task session: `AuthService(UserRepository(session), RefreshTokenRepository(session)).purge_expired()`. `send_welcome_email` uses `UserRepository(session).get(...)`.
- `core/deps.get_current_user` uses `UserRepository(session).get(...)` instead of `session.get(User, ...)`.
- `cli.create_admin` builds a `UserService` from its session.

### Mid-flow commits

Today `auth.refresh` and `auth.logout` call `session.commit()` before raising or returning, so a revocation survives the rollback in `get_session`. `purge_expired` commits too. These become `self.tokens.commit()`. A fake records that `commit()` was called, so service tests can assert "family revoked and committed".

### Fakes

- `tests/fakes.py`: `FakeRepository[M]` stores models in a dict keyed by id. `add` assigns a `uuid7()` id when missing, fills Python-side column defaults from `M.__table__.columns` (e.g. `is_published=False`, `role=user`, `is_active=True`), and sets `created_at`/`updated_at` to `now`. `get`, `save` (bumps `updated_at`), `delete`, `commit` (increments `commits`). `_list` applies `limit`/`offset` in insertion order and ignores `q` and `sort`: `# shortcut: no search/sort in fakes; covered by Postgres repository tests`.
- Per module, `tests/<mod>/fakes.py`: `FakeItemRepository`, `FakeUserRepository`, `FakeRefreshTokenRepository`. They implement the module-specific methods with plain Python (e.g. `get_by_email` lower-cases and scans; `add_unique` returns `None` on a duplicate email; `get_for_update` is `get`).
- Fakes satisfy the Protocols structurally. `ty check` verifies that, because service constructors are typed with the Protocols.

### Tests

- `tests/<mod>/test_service.py`: rewritten to use fakes. Keep every current business-rule case (admin invariants, token rotation and reuse, login timing path, item update `None` rule, `NotFound`/`Conflict`). They lose the `session`/`make_user` fixtures; a small in-test helper builds users.
- `tests/<mod>/test_repository.py` (new, Postgres via the existing `session` fixture): search with `escape_like`, sort with tiebreaker, `published_only`, `count_active_admins`, `add_unique` under a real unique violation, `revoke_family`, `revoke_all_for_user`, `purge_expired`.
- Concurrency tests that need real row locks or commits (`test_concurrent_refresh_one_wins`, anything using `committed_session_factory`) move to the repository tests, or to the API tests if they exercise the full flow. They keep running on Postgres.
- API tests (`test_api_*.py`) and `conftest.py` fixtures stay as they are.

### Docs and generated-project guidance

- `AGENTS.md.jinja`: the module table gains a `repository.py` column. The rules say "queries only in `repository.py`; services take repository Protocols and never touch the session; service tests use fakes, repository tests use Postgres".
- `.claude/skills/new-feature-module/SKILL.md`: add the repository step, the Protocol, the service class plus `<Mod>ServiceDep`, the fake, and `test_repository.py`.
- `.claude/agents/backend-reviewer.md`: flag queries outside repositories, and services importing `sqlalchemy`.
- `.claude/skills/background-task/SKILL.md`: step 2 still takes `session: AsyncSession = TASK_SESSION`, but the task builds a repository or service from it instead of querying the session directly.
- `template/workspace/.claude/skills/sync-context/references/agents-skeleton-backend.md`: replace "No repository layer. The service talks to SQLAlchemy." (line 43) with the new rule, and mention `repository.py` next to `service.py` (line 36). Otherwise `/sync-context` regenerates a backend `AGENTS.md` that contradicts the code. Keep it within the section order and length that `tests/test_sync_context_assets.py` checks.
- `docs/superpowers/specs/2026-10-20-project-template-design.md`: replace the "no repository layer" lines with a pointer to this spec.

### Notes for the builder

- `AuthService.refresh` re-reads the user with `populate_existing=True` today. Keep that, either through a `UserRepo.get(id, *, fresh: bool)` flag or a separate method.
- `cli.create_admin` promotes an existing user without an actor (no last-admin check applies to promotion). Give `UserService` an actor-less `promote_to_admin(user)` rather than reusing `admin_update`.
- `tests/test_cli.py` calls the old module functions and must be updated.
- `test_concurrent_refresh_one_wins` moves to `tests/auth/test_repository.py`. It builds a real `AuthService` from real repositories on `committed_session_factory`. API tests stay unchanged.
- `tests/test_session_scope.py` follows dependencies transitively, so `<Mod>ServiceDep -> SessionDep` passes it as is.
- No release has shipped (no git tags), so no generated repos need a migration path.

## Left to the builder

- Exact Protocol method signatures beyond those listed, and the names of private helpers.
- Whether `Repo[M]` and `BaseRepository` share one file (default: both in `core/repository.py`).
- How fakes are imported (`tests/` package layout, `__init__.py` files; `tests/users/` currently has none).
- Splitting work into commits. Each commit must leave `make check` green.
- Breaking a circular import if one appears. `users/service.py` imports `auth/repository.py`, and `auth/service.py` imports `users/repository.py`; neither repository imports a service, so there should be no cycle.

## Calls made without the owner

- No generic `update` on the base. `save` replaces it.
- No schema generics on the base. Repositories take models and plain values.
- Repositories never raise domain errors. `add_unique` returns `None` instead of raising `Conflict`.
- The service dependency lives at the bottom of `service.py`, not in a new `deps.py` per module.
- `get_current_user` and the tasks also go through repositories, so "queries only in `repository.py`" has no exceptions.
- The fake ignores search and sort.
- The workspace `sync-context` backend skeleton and the `background-task` skill are updated too, so no generated guidance contradicts the code.
