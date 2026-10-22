from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken
from app.core.config import Settings
from app.core.errors import Forbidden, Unauthorized
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.users.models import Role, User
from app.users.repository import UserRepository


@dataclass
class Issued:
    access_token: str
    refresh_token: str  # raw; only its sha256 is stored


def _issue(session: AsyncSession, user: User, family_id: UUID, settings: Settings) -> Issued:
    now = datetime.now(UTC)
    raw = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            family_id=family_id,
            expires_at=now + settings.refresh_token_ttl,
        )
    )
    access = create_access_token(
        user.id,
        user.role.value,
        settings.jwt_secret.get_secret_value(),
        now=now,
        ttl=settings.access_token_ttl,
    )
    return Issued(access_token=access, refresh_token=raw)


async def _revoke_family(session: AsyncSession, family_id: UUID) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def login(
    session: AsyncSession,
    email: str,
    password: str,
    *,
    settings: Settings,
    require_admin: bool = False,
) -> Issued:
    user = await UserRepository(session).get_by_email(email)
    if user is None:
        verify_password(password, DUMMY_HASH)  # equalize timing with the known-user path
        raise Unauthorized("invalid credentials")
    if not verify_password(password, user.password_hash) or not user.is_active:
        raise Unauthorized("invalid credentials")
    if require_admin and user.role != Role.admin:  # only after the password is proven
        raise Forbidden("admin access required")
    return _issue(session, user, uuid7(), settings)


async def refresh(
    session: AsyncSession,
    raw_token: str,
    *,
    settings: Settings,
    require_admin: bool = False,
) -> Issued:
    row = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise Unauthorized("invalid refresh token")
    if row.revoked_at is not None:
        # reuse of a rotated token: assume theft, kill the family. Commit first because
        # get_session rolls back when we raise.
        await _revoke_family(session, row.family_id)
        await session.commit()
        raise Unauthorized("invalid refresh token")
    if row.expires_at <= datetime.now(UTC):
        raise Unauthorized("invalid refresh token")

    user = await session.get(User, row.user_id, populate_existing=True)
    if user is None or not user.is_active or (require_admin and user.role != Role.admin):
        await _revoke_family(session, row.family_id)
        await session.commit()
        raise Unauthorized("invalid refresh token")

    row.revoked_at = datetime.now(UTC)
    return _issue(session, user, row.family_id, settings)


async def logout(session: AsyncSession, raw_token: str) -> None:
    family_id = await session.scalar(
        select(RefreshToken.family_id).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )
    if family_id is not None:
        await _revoke_family(session, family_id)
        await session.commit()


async def purge_expired(session: AsyncSession, now: datetime | None = None) -> int:
    result = await session.scalars(
        delete(RefreshToken)
        .where(RefreshToken.expires_at < (now or datetime.now(UTC)))
        .returning(RefreshToken.id)
    )
    deleted = len(result.all())
    await session.commit()
    return deleted
