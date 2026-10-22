import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.models import RefreshToken
from app.auth.repository import RefreshTokenRepository
from app.auth.service import AuthService, Issued
from app.core.config import Settings
from app.core.errors import Unauthorized
from app.core.security import hash_password
from app.users.models import User
from app.users.repository import UserRepository

MakeUser = Callable[..., Awaitable[User]]
NOW = datetime(2026, 1, 1, tzinfo=UTC)
PASSWORD = "correct horse battery"
SETTINGS = Settings(
    _env_file=None,
    database_url="postgresql+asyncpg://unused",
    redis_url="redis://unused",
    jwt_secret="x" * 40,
)


async def seed(
    session: AsyncSession,
    user: User,
    token_hash: str,
    *,
    family_id: UUID | None = None,
    expires_at: datetime = NOW + timedelta(days=1),
    revoked_at: datetime | None = None,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        family_id=family_id or uuid4(),
        expires_at=expires_at,
        revoked_at=revoked_at,
    )
    session.add(row)
    await session.flush()
    return row


async def test_revoke_family_only_touches_that_family(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user = await make_user()
    family = uuid4()
    a = await seed(session, user, "a", family_id=family)
    b = await seed(session, user, "b", family_id=family)
    other = await seed(session, user, "c")

    await RefreshTokenRepository(session).revoke_family(family, at=NOW)
    await session.refresh(a)
    await session.refresh(b)
    await session.refresh(other)

    assert a.revoked_at == NOW
    assert b.revoked_at == NOW
    assert other.revoked_at is None


async def test_revoke_all_for_user_skips_already_revoked(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user = await make_user()
    bystander = await make_user("other@x.com")
    old = NOW - timedelta(days=3)
    revoked = await seed(session, user, "a", revoked_at=old)
    live = await seed(session, user, "b")
    theirs = await seed(session, bystander, "c")

    await RefreshTokenRepository(session).revoke_all_for_user(user.id)
    await session.refresh(revoked)
    await session.refresh(live)
    await session.refresh(theirs)

    assert revoked.revoked_at == old
    assert live.revoked_at is not None
    assert theirs.revoked_at is None


async def test_purge_expired_deletes_only_expired(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user = await make_user()
    await seed(session, user, "old", expires_at=NOW - timedelta(seconds=1))
    await seed(session, user, "live", expires_at=NOW + timedelta(seconds=1))
    repo = RefreshTokenRepository(session)

    assert await repo.purge_expired(NOW) == 1
    assert await repo.get_family_id("old") is None
    assert await repo.get_family_id("live") is not None


async def test_get_family_id_unknown_is_none(session: AsyncSession) -> None:
    assert await RefreshTokenRepository(session).get_family_id("nope") is None


async def rows(session: AsyncSession, **where: object) -> list[RefreshToken]:
    stmt = (
        select(RefreshToken)
        .filter_by(**where)
        .order_by(RefreshToken.created_at, RefreshToken.id)
        .execution_options(populate_existing=True)
    )
    return list(await session.scalars(stmt))


def _auth(session: AsyncSession) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session))


async def login(session: AsyncSession, email: str = "user@example.com", **kw: bool) -> Issued:
    return await _auth(session).login(email, PASSWORD, settings=SETTINGS, **kw)


async def refresh(session: AsyncSession, raw: str, **kw: bool) -> Issued:
    return await _auth(session).refresh(raw, settings=SETTINGS, **kw)


async def test_concurrent_refresh_one_wins(
    committed_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with committed_session_factory() as s:
        user = User(email="user@example.com", password_hash=hash_password(PASSWORD))
        s.add(user)
        await s.flush()
        issued = await login(s)
        await s.commit()

    # Deterministic interleave: A rotates but has not committed (holds the row lock); B must block
    # on FOR UPDATE, then see the revoked row once A commits and lose. Without the lock B would
    # finish while A is still open and both would win.
    async with committed_session_factory() as a, committed_session_factory() as b:
        winner = await refresh(a, issued.refresh_token)
        loser = asyncio.create_task(refresh(b, issued.refresh_token))
        await asyncio.sleep(0.3)
        assert not loser.done()
        await a.commit()
        assert winner.refresh_token != issued.refresh_token
        with pytest.raises(Unauthorized):
            await loser

    # the loser's reuse branch must have committed: winner's fresh token is revoked too
    async with committed_session_factory() as fresh:
        stored = await rows(fresh)
        assert len(stored) == 2
        assert all(r.revoked_at is not None for r in stored)
