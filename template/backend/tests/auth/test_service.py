from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from app.auth.models import RefreshToken
from app.auth.service import AuthService, Issued
from app.core.config import Settings
from app.core.errors import Forbidden, Unauthorized
from app.core.security import hash_password, hash_refresh_token
from app.users.models import Role, User
from tests.fakes import FakeRefreshTokenRepository, FakeUserRepository

PASSWORD = "correct horse battery"
PASSWORD_HASH = hash_password(PASSWORD)
SETTINGS = Settings(
    _env_file=None,
    database_url="postgresql+asyncpg://unused",
    redis_url="redis://unused",
    jwt_secret="x" * 40,
)


@pytest.fixture
def users() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def tokens() -> FakeRefreshTokenRepository:
    return FakeRefreshTokenRepository()


@pytest.fixture
def svc(users: FakeUserRepository, tokens: FakeRefreshTokenRepository) -> AuthService:
    return AuthService(users, tokens)


async def make_user(
    users: FakeUserRepository,
    email: str = "user@example.com",
    *,
    role: Role = Role.user,
    is_active: bool = True,
) -> User:
    return await users.add(
        User(email=email, password_hash=PASSWORD_HASH, role=role, is_active=is_active)
    )


def rows(tokens: FakeRefreshTokenRepository) -> list[RefreshToken]:
    return list(tokens.rows.values())


async def login(svc: AuthService, email: str = "user@example.com", **kw: bool) -> Issued:
    return await svc.login(email, PASSWORD, settings=SETTINGS, **kw)


async def refresh(svc: AuthService, raw: str, **kw: bool) -> Issued:
    return await svc.refresh(raw, settings=SETTINGS, **kw)


async def test_login_issues_tokens_and_stores_only_hash(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    user = await make_user(users)
    issued = await login(svc)
    [row] = rows(tokens)
    assert row.token_hash == hash_refresh_token(issued.refresh_token)
    assert issued.refresh_token not in {row.token_hash, str(row.id), str(row.family_id)}
    assert row.user_id == user.id
    assert row.revoked_at is None
    delta = row.expires_at - datetime.now(UTC)
    assert abs(delta - timedelta(days=30)) < timedelta(seconds=5)
    claims = jwt.decode(issued.access_token, "x" * 40, algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 900
    assert claims["sub"] == str(user.id)


async def test_login_wrong_password_and_unknown_user_same_error(
    svc: AuthService, users: FakeUserRepository
) -> None:
    await make_user(users)
    with pytest.raises(Unauthorized) as wrong:
        await svc.login("user@example.com", "nope", settings=SETTINGS)
    with pytest.raises(Unauthorized) as unknown:
        await svc.login("ghost@example.com", "nope", settings=SETTINGS)
    assert wrong.value.detail == unknown.value.detail == "invalid credentials"


async def test_login_inactive_user_unauthorized(
    svc: AuthService, users: FakeUserRepository
) -> None:
    await make_user(users, is_active=False)
    with pytest.raises(Unauthorized, match="invalid credentials"):
        await login(svc)


async def test_login_email_case_insensitive(svc: AuthService, users: FakeUserRepository) -> None:
    await make_user(users, "user@example.com")
    assert (await login(svc, "USER@Example.COM")).access_token


async def test_admin_login_rejects_non_admin_with_forbidden(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    with pytest.raises(Forbidden):
        await login(svc, require_admin=True)
    assert rows(tokens) == []


async def test_admin_login_wrong_password_is_unauthorized_not_forbidden(
    svc: AuthService, users: FakeUserRepository
) -> None:
    await make_user(users)
    with pytest.raises(Unauthorized):
        await svc.login("user@example.com", "nope", settings=SETTINGS, require_admin=True)


async def test_admin_login_admin_ok(svc: AuthService, users: FakeUserRepository) -> None:
    await make_user(users, role=Role.admin)
    assert (await login(svc, require_admin=True)).access_token


async def test_refresh_rotates(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    first = await login(svc)
    second = await refresh(svc, first.refresh_token)
    assert second.refresh_token != first.refresh_token
    old, new = rows(tokens)
    assert old.token_hash == hash_refresh_token(first.refresh_token)
    assert new.token_hash == hash_refresh_token(second.refresh_token)
    assert old.revoked_at is not None
    assert new.revoked_at is None
    assert old.family_id == new.family_id


async def test_refresh_reuse_revokes_family(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    t1 = await login(svc)
    t2 = await refresh(svc, t1.refresh_token)
    with pytest.raises(Unauthorized):
        await refresh(svc, t1.refresh_token)
    assert tokens.commits == 1  # committed before raising: get_session rolls back on error
    stored = rows(tokens)
    assert len(stored) == 2
    assert all(r.revoked_at is not None for r in stored)
    with pytest.raises(Unauthorized):
        await refresh(svc, t2.refresh_token)


async def test_reuse_does_not_touch_other_family(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    t1 = await login(svc)
    other = await login(svc)
    await refresh(svc, t1.refresh_token)
    with pytest.raises(Unauthorized):
        await refresh(svc, t1.refresh_token)
    [other_row] = [
        r for r in rows(tokens) if r.token_hash == hash_refresh_token(other.refresh_token)
    ]
    assert other_row.revoked_at is None
    assert (await refresh(svc, other.refresh_token)).refresh_token


async def test_refresh_expired_unauthorized(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    t1 = await login(svc)
    for r in rows(tokens):
        r.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(Unauthorized):
        await refresh(svc, t1.refresh_token)
    assert all(r.revoked_at is None for r in rows(tokens))  # no family revoke


@pytest.mark.parametrize("raw", ["", "garbage"])
async def test_refresh_unknown_and_garbage_unauthorized(svc: AuthService, raw: str) -> None:
    with pytest.raises(Unauthorized):
        await refresh(svc, raw)


async def test_refresh_inactive_user_revokes_family(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    user = await make_user(users)
    t1 = await login(svc)
    user.is_active = False
    with pytest.raises(Unauthorized):
        await refresh(svc, t1.refresh_token)
    assert tokens.commits == 1  # see test_refresh_reuse_revokes_family
    stored = rows(tokens)
    assert len(stored) == 1
    assert all(r.revoked_at is not None for r in stored)


async def test_admin_refresh_rejects_demoted_user(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    user = await make_user(users, role=Role.admin)
    t1 = await login(svc, require_admin=True)
    user.role = Role.user
    with pytest.raises(Unauthorized):
        await refresh(svc, t1.refresh_token, require_admin=True)
    stored = rows(tokens)
    assert tokens.commits == 1  # see test_refresh_inactive_user_revokes_family
    assert len(stored) == 1
    assert all(r.revoked_at is not None for r in stored)


async def test_logout_revokes_family_and_is_idempotent(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    t1 = await login(svc)
    await refresh(svc, t1.refresh_token)
    other = await login(svc)
    await svc.logout(t1.refresh_token)
    await svc.logout(t1.refresh_token)
    rs = rows(tokens)
    revoked = [r for r in rs if r.revoked_at is not None]
    assert len(revoked) == 2
    assert [r.token_hash for r in rs if r.revoked_at is None] == [
        hash_refresh_token(other.refresh_token)
    ]


@pytest.mark.parametrize("raw", ["", "garbage"])
async def test_logout_unknown_token_noop(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository, raw: str
) -> None:
    await make_user(users)
    await login(svc)
    await svc.logout(raw)
    assert all(r.revoked_at is None for r in rows(tokens))
    assert tokens.commits == 0


async def test_purge_expired_deletes_only_expired(
    svc: AuthService, users: FakeUserRepository, tokens: FakeRefreshTokenRepository
) -> None:
    await make_user(users)
    old = await login(svc)
    live = await login(svc)
    [old_row] = [r for r in rows(tokens) if r.token_hash == hash_refresh_token(old.refresh_token)]
    old_row.expires_at = datetime.now(UTC) - timedelta(days=1)
    assert await svc.purge_expired() == 1
    assert tokens.commits == 1
    [row] = rows(tokens)
    assert row.token_hash == hash_refresh_token(live.refresh_token)
    assert UUID(str(row.id))
