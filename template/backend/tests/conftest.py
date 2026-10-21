import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_JWT_SECRET", "x" * 40)

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

import pytest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from app.core.db import Base, make_engine, make_session_factory
from app.core.security import hash_password
from app.users.models import Role, User


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:17", driver="asyncpg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    with RedisContainer("redis:7") as r:
        yield f"redis://{r.get_container_host_ip()}:{r.get_exposed_port(6379)}/0"


@pytest.fixture(scope="session")
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    import app.core.models  # noqa: F401  # register every model on Base.metadata

    engine = make_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    yield client
    await client.aclose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as conn:
        outer = await conn.begin()
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as s:
            yield s
        await outer.rollback()


@pytest.fixture
async def committed_session_factory(
    engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    # For tests that need real commits and concurrent sessions (row locks); cleans up by truncating.
    yield make_session_factory(engine)
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture(autouse=True)
async def _flush_redis(redis_client: Redis) -> None:
    await redis_client.flushdb()


@pytest.fixture
def make_user(session: AsyncSession) -> Callable[..., Awaitable[User]]:
    async def _make(
        email: str = "user@example.com",
        *,
        role: Role = Role.user,
        is_active: bool = True,
        password: str = "correct horse battery",  # noqa: S107
    ) -> User:
        user = User(
            email=email, password_hash=hash_password(password), role=role, is_active=is_active
        )
        session.add(user)
        await session.flush()
        return user

    return _make
