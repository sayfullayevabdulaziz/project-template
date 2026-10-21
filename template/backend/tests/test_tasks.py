import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs
from taskiq import InMemoryBroker
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisStreamBroker

from app.auth.models import RefreshToken
from app.auth.tasks import purge_expired_refresh_tokens
from app.core.broker import broker, build_broker
from app.core.config import Settings
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
