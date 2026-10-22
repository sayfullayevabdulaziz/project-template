---
name: db-migration
description: Create and review an Alembic database migration. Use when a model changes, a column or table is added, altered or dropped, or when asked to make or review a migration.
---

# Database migration

1. Change the model, and make sure its module is imported in `src/app/core/models.py`.
2. Generate: `make migration m="short message"` (needs a running database; `make up` starts the stack).
3. Open the new file in `migrations/versions/` and review it. Autogenerate is a draft.
4. Review checklist:
   - Constraint and index names follow the metadata naming convention. Do not hand-name them differently.
   - `downgrade()` exists and truly reverses `upgrade()`.
   - Zero-downtime: use expand, migrate, contract across separate releases. New columns are nullable or have a server default. Never drop or rename a column in the same release that stops using it.
   - Backfills on big tables run in batches, not in one statement.
   - Enum, type and `NOT NULL` changes are checked against existing rows.
   - No unrelated autogenerate noise (dropped tables, index churn).
5. Never edit a revision that has been applied anywhere (merged or deployed). Add a new revision instead.
6. Apply and test: `make migrate`, then `uv run pytest tests/test_migrations.py`.
7. Run `make check`.
