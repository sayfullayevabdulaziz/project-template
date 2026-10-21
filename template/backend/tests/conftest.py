import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_JWT_SECRET", "x" * 40)

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from app.core.config import Settings
from app.core.db import Base, get_session, make_engine, make_session_factory
from app.core.security import create_access_token, hash_password
from app.main import create_app
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


@pytest.fixture
async def app(
    session: AsyncSession,
    engine: AsyncEngine,
    redis_client: Redis,
    postgres_url: str,
    redis_url: str,
) -> AsyncIterator[FastAPI]:
    settings = Settings(
        env="test",
        database_url=postgres_url,
        redis_url=redis_url,
        jwt_secret=SecretStr("x" * 40),
    )
    app = create_app(settings)
    # ASGITransport does not run the lifespan, so wire app.state by hand.
    app.state.session_factory = make_session_factory(engine)
    app.state.redis = redis_client

    async def _session() -> AsyncIterator[AsyncSession]:
        yield session  # the savepoint session: request writes roll back with the test

    app.dependency_overrides[get_session] = _session
    yield app


@pytest.fixture
def make_token(app: FastAPI) -> Callable[..., str]:
    def _make(user: User, *, role: str | None = None, ttl: timedelta = timedelta(minutes=5)) -> str:
        secret = app.state.settings.jwt_secret.get_secret_value()
        return create_access_token(user.id, role or user.role.value, secret, ttl=ttl)

    return _make


def _client(app: FastAPI, token: str | None = None) -> httpx.AsyncClient:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers
    )


@pytest.fixture
async def anon_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with _client(app) as c:
        yield c


@pytest.fixture
async def user_client(
    app: FastAPI, make_user: Callable[..., Awaitable[User]], make_token: Callable[..., str]
) -> AsyncIterator[httpx.AsyncClient]:
    user = await make_user("plain@example.com")
    async with _client(app, make_token(user)) as c:
        yield c


@pytest.fixture
async def admin_client(
    app: FastAPI, make_user: Callable[..., Awaitable[User]], make_token: Callable[..., str]
) -> AsyncIterator[httpx.AsyncClient]:
    admin = await make_user("admin@example.com", role=Role.admin)
    async with _client(app, make_token(admin)) as c:
        yield c
