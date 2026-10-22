---
name: background-task
description: Add a taskiq background or scheduled (cron) task. Use when work must run outside the request, be retried, or run on a schedule, such as emails, cleanup jobs or periodic syncs.
---

# Background task

1. Define the task in `src/app/<mod>/tasks.py` with `@broker.task(retry_on_error=True, max_retries=3)`. See `src/app/users/tasks.py`.
2. Arguments are primitives only (`str`, `int`, ...; pass `str(uuid)`, not ORM objects). Load fresh state inside the task with `session: AsyncSession = TASK_SESSION`, through `<Mod>Repository(session)` or a service built from it. Never call `session.get` or `select` in the task.
3. Make it idempotent: safe to retry and to run twice. A missing row is a no-op, not an error.
4. For cron, add a schedule label: `@broker.task(schedule=[{"cron": "0 * * * *"}])` (see `src/app/auth/tasks.py`).
5. Enqueue with `await task.kiq(...)` only after the transaction commits, so the worker sees the data.
6. Register the module: append `app.<mod>.tasks` to the `worker` command in `compose.yaml`. For scheduled tasks, also append it to the `scheduler` command.
7. Test with the `InMemoryBroker` pattern from `tests/test_tasks.py`: call the task function or `kiq` and assert the effect, including the second-run and missing-row cases.
8. Run `make check`.
