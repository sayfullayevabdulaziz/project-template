from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken
from app.auth.repository import RefreshTokenRepository
from app.users.models import User

MakeUser = Callable[..., Awaitable[User]]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


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
