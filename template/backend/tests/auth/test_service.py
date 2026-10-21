import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import service
from app.auth.models import RefreshToken
from app.core.config import Settings
from app.core.errors import Forbidden, Unauthorized
from app.core.security import hash_password, hash_refresh_token
from app.users.models import Role, User

MakeUser = Callable[..., Awaitable[User]]
PASSWORD = "correct horse battery"
SETTINGS = Settings(
    _env_file=None,
    database_url="postgresql+asyncpg://unused",
    redis_url="redis://unused",
    jwt_secret="x" * 40,
)


async def rows(session: AsyncSession, **where: object) -> list[RefreshToken]:
    stmt = (
        select(RefreshToken)
        .filter_by(**where)
        .order_by(RefreshToken.created_at, RefreshToken.id)
        .execution_options(populate_existing=True)
    )
    return list(await session.scalars(stmt))


async def login(
    session: AsyncSession, email: str = "user@example.com", **kw: bool
) -> service.Issued:
    return await service.login(session, email, PASSWORD, settings=SETTINGS, **kw)


async def refresh(session: AsyncSession, raw: str, **kw: bool) -> service.Issued:
    return await service.refresh(session, raw, settings=SETTINGS, **kw)


async def test_login_issues_tokens_and_stores_only_hash(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user = await make_user()
    user_id = user.id
    issued = await login(session)
    [row] = await rows(session)
    assert row.token_hash == hash_refresh_token(issued.refresh_token)
    assert issued.refresh_token not in {row.token_hash, str(row.id), str(row.family_id)}
    assert row.user_id == user_id
    assert row.revoked_at is None
    delta = row.expires_at - datetime.now(UTC)
    assert abs(delta - timedelta(days=30)) < timedelta(seconds=5)
    claims = jwt.decode(issued.access_token, "x" * 40, algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 900
    assert claims["sub"] == str(user_id)


async def test_login_wrong_password_and_unknown_user_same_error(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user()
    with pytest.raises(Unauthorized) as wrong:
        await service.login(session, "user@example.com", "nope", settings=SETTINGS)
    with pytest.raises(Unauthorized) as unknown:
        await service.login(session, "ghost@example.com", "nope", settings=SETTINGS)
    assert wrong.value.detail == unknown.value.detail == "invalid credentials"


async def test_login_inactive_user_unauthorized(session: AsyncSession, make_user: MakeUser) -> None:
    await make_user(is_active=False)
    with pytest.raises(Unauthorized, match="invalid credentials"):
        await login(session)


async def test_login_email_case_insensitive(session: AsyncSession, make_user: MakeUser) -> None:
    await make_user("user@example.com")
    assert (await login(session, "USER@Example.COM")).access_token


async def test_admin_login_rejects_non_admin_with_forbidden(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user()
    with pytest.raises(Forbidden):
        await login(session, require_admin=True)
    assert await rows(session) == []


async def test_admin_login_wrong_password_is_unauthorized_not_forbidden(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user()
    with pytest.raises(Unauthorized):
        await service.login(
            session, "user@example.com", "nope", settings=SETTINGS, require_admin=True
        )


async def test_admin_login_admin_ok(session: AsyncSession, make_user: MakeUser) -> None:
    await make_user(role=Role.admin)
    assert (await login(session, require_admin=True)).access_token


async def test_refresh_rotates(session: AsyncSession, make_user: MakeUser) -> None:
    await make_user()
    first = await login(session)
    second = await refresh(session, first.refresh_token)
    assert second.refresh_token != first.refresh_token
    old, new = await rows(session)
    assert old.token_hash == hash_refresh_token(first.refresh_token)
    assert new.token_hash == hash_refresh_token(second.refresh_token)
    assert old.revoked_at is not None
    assert new.revoked_at is None
    assert old.family_id == new.family_id


async def test_refresh_reuse_revokes_family(session: AsyncSession, make_user: MakeUser) -> None:
    await make_user()
    t1 = await login(session)
    t2 = await refresh(session, t1.refresh_token)
    await session.commit()  # setup persists; the rollback below may only undo the service's work
    with pytest.raises(Unauthorized):
        await refresh(session, t1.refresh_token)
    await session.rollback()  # what get_session does on raise; only a real commit survives it
    stored = await rows(session)
    assert len(stored) == 2
    assert all(r.revoked_at is not None for r in stored)
    with pytest.raises(Unauthorized):
        await refresh(session, t2.refresh_token)


async def test_reuse_does_not_touch_other_family(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user()
    t1 = await login(session)
    other = await login(session)
    await refresh(session, t1.refresh_token)
    with pytest.raises(Unauthorized):
        await refresh(session, t1.refresh_token)
    [other_row] = await rows(session, token_hash=hash_refresh_token(other.refresh_token))
    assert other_row.revoked_at is None
    assert (await refresh(session, other.refresh_token)).refresh_token


async def test_refresh_expired_unauthorized(session: AsyncSession, make_user: MakeUser) -> None:
    await make_user()
    t1 = await login(session)
    await session.execute(
        update(RefreshToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    with pytest.raises(Unauthorized):
        await refresh(session, t1.refresh_token)
    assert all(r.revoked_at is None for r in await rows(session))  # no family revoke


@pytest.mark.parametrize("raw", ["", "garbage"])
async def test_refresh_unknown_and_garbage_unauthorized(session: AsyncSession, raw: str) -> None:
    with pytest.raises(Unauthorized):
        await refresh(session, raw)


async def test_refresh_inactive_user_revokes_family(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user = await make_user()
    t1 = await login(session)
    user.is_active = False
    await session.commit()  # setup persists; the rollback below may only undo the service's work
    with pytest.raises(Unauthorized):
        await refresh(session, t1.refresh_token)
    await session.rollback()  # see test_refresh_reuse_revokes_family
    stored = await rows(session)
    assert len(stored) == 1
    assert all(r.revoked_at is not None for r in stored)


async def test_admin_refresh_rejects_demoted_user(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user = await make_user(role=Role.admin)
    t1 = await login(session, require_admin=True)
    user.role = Role.user
    await session.commit()  # setup persists; the rollback below may only undo the service's work
    with pytest.raises(Unauthorized):
        await refresh(session, t1.refresh_token, require_admin=True)
    await session.rollback()  # see test_refresh_reuse_revokes_family
    stored = await rows(session)
    assert len(stored) == 1
    assert all(r.revoked_at is not None for r in stored)


async def test_logout_revokes_family_and_is_idempotent(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user()
    t1 = await login(session)
    await refresh(session, t1.refresh_token)
    other = await login(session)
    await service.logout(session, t1.refresh_token)
    await service.logout(session, t1.refresh_token)
    rs = await rows(session)
    revoked = [r for r in rs if r.revoked_at is not None]
    assert len(revoked) == 2
    assert [r.token_hash for r in rs if r.revoked_at is None] == [
        hash_refresh_token(other.refresh_token)
    ]


@pytest.mark.parametrize("raw", ["", "garbage"])
async def test_logout_unknown_token_noop(
    session: AsyncSession, make_user: MakeUser, raw: str
) -> None:
    await make_user()
    await login(session)
    await service.logout(session, raw)
    assert all(r.revoked_at is None for r in await rows(session))


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


async def test_purge_expired_deletes_only_expired(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user()
    old = await login(session)
    live = await login(session)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(old.refresh_token))
        .values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )
    assert await service.purge_expired(session) == 1
    [row] = await rows(session)
    assert row.token_hash == hash_refresh_token(live.refresh_token)
    assert UUID(str(row.id))
