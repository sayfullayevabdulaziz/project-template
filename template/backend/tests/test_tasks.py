import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, MutableMapping
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.testing import capture_logs
from taskiq import InMemoryBroker
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisStreamBroker

from app.auth.models import RefreshToken
from app.auth.tasks import purge_expired_refresh_tokens
from app.core.broker import broker, build_broker
from app.core.config import Settings
from app.core.db import get_task_session
from app.users.models import User
from app.users.tasks import send_welcome_email

MakeUser = Callable[..., Awaitable[User]]


def _settings(env: str) -> Settings:
    return Settings.model_validate(
        {
            "env": env,
            "database_url": "postgresql+asyncpg://u:p@localhost/db",
            "redis_url": "redis://localhost:6379/0",
            "jwt_secret": "x" * 40,
        }
    )


def test_build_broker_test_env_is_inmemory():
    assert isinstance(build_broker(_settings("test")), InMemoryBroker)


def test_build_broker_prod_is_redis_stream():
    assert isinstance(build_broker(_settings("prod")), RedisStreamBroker)


def test_prod_broker_has_retry_middleware():
    # retry_on_error/max_retries labels are inert without it
    middlewares = build_broker(_settings("prod")).middlewares
    assert any(isinstance(m, SimpleRetryMiddleware) for m in middlewares)


def _events(logs: list[MutableMapping[str, Any]], name: str) -> list[MutableMapping[str, Any]]:
    return [e for e in logs if e["event"] == name]


async def test_send_welcome_email_logs_event(task_broker: InMemoryBroker, make_user: MakeUser):
    user = await make_user()
    with capture_logs() as logs:
        result = await send_welcome_email.kiq(str(user.id))
        await result.wait_result()
    [event] = _events(logs, "send_welcome_email")
    assert event["user_id"] == str(user.id)


async def test_send_welcome_email_missing_user_is_noop_and_repeatable(task_broker: InMemoryBroker):
    missing = str(uuid.uuid4())
    with capture_logs() as logs:
        for _ in range(2):
            result = await send_welcome_email.kiq(missing)
            assert not (await result.wait_result()).is_err
    assert _events(logs, "send_welcome_email") == []


async def test_register_enqueues_welcome_email(
    task_broker: InMemoryBroker, anon_client: httpx.AsyncClient
):
    with capture_logs() as logs:
        r = await anon_client.post(
            "/api/v1/users/register",
            json={"email": "new@example.com", "password": "correct horse battery"},
        )
        await task_broker.wait_all()
    assert r.status_code == 201
    # the event is only logged when the task found the committed user row
    [event] = _events(logs, "send_welcome_email")
    assert event["user_id"] == r.json()["id"]


async def test_register_commits_before_enqueueing(
    task_broker: InMemoryBroker,
    anon_client: httpx.AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # The task shares the request's session here, so only call ordering can prove the worker
    # (a separate connection in production) would see the row.
    calls: list[str] = []
    real_commit = session.commit

    async def spy_commit() -> None:
        await real_commit()
        calls.append("commit")

    monkeypatch.setattr(session, "commit", spy_commit)
    real_kiq = send_welcome_email.kiq

    async def spy(*args: Any, **kwargs: Any) -> Any:
        calls.append("kiq")
        return await real_kiq(*args, **kwargs)

    monkeypatch.setattr(send_welcome_email, "kiq", spy)
    r = await anon_client.post(
        "/api/v1/users/register",
        json={"email": "order@example.com", "password": "correct horse battery"},
    )
    assert r.status_code == 201
    assert calls == ["commit", "kiq"]


def _fake_request(factory: async_sessionmaker[AsyncSession]) -> Request:
    state = SimpleNamespace(session_factory=factory)
    return cast(Request, SimpleNamespace(app=SimpleNamespace(state=state)))


async def test_get_task_session_commits_on_success(
    committed_session_factory: async_sessionmaker[AsyncSession],
):
    request = _fake_request(committed_session_factory)
    gen = get_task_session(request)
    (await anext(gen)).add(User(email="task@example.com", password_hash="x"))
    with pytest.raises(StopAsyncIteration):  # normal exit: the dependency commits
        await anext(gen)
    async with committed_session_factory() as fresh:
        assert await fresh.scalar(select(User.email)) == "task@example.com"


async def test_get_task_session_rolls_back_on_error(
    committed_session_factory: async_sessionmaker[AsyncSession],
):
    request = _fake_request(committed_session_factory)
    gen = get_task_session(request)
    s = await anext(gen)
    s.add(User(email="task@example.com", password_hash="x"))
    await s.flush()
    with pytest.raises(RuntimeError):
        await cast(AsyncGenerator[AsyncSession], gen).athrow(RuntimeError())
    async with committed_session_factory() as fresh:
        assert await fresh.scalar(select(User.email)) is None


async def test_purge_expired_refresh_tokens_task(
    task_broker: InMemoryBroker, session: AsyncSession, make_user: MakeUser
):
    user = await make_user()
    now = datetime.now(UTC)
    for name, delta in (("old", -timedelta(hours=1)), ("live", timedelta(hours=1))):
        session.add(
            RefreshToken(
                user_id=user.id, token_hash=name, family_id=uuid.uuid4(), expires_at=now + delta
            )
        )
    await session.flush()

    result = await purge_expired_refresh_tokens.kiq()
    assert (await result.wait_result()).return_value == 1
    assert list(await session.scalars(select(RefreshToken.token_hash))) == ["live"]


def test_purge_has_daily_schedule_label():
    assert purge_expired_refresh_tokens.labels["schedule"] == [{"cron": "0 3 * * *"}]


async def test_scheduler_reads_label_source():
    source = LabelScheduleSource(broker)
    await source.startup()  # schedules are collected from task labels on startup
    schedules = await source.get_schedules()
    assert purge_expired_refresh_tokens.task_name in {s.task_name for s in schedules}
