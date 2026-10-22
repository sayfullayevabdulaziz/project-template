from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid7

from fastapi import Depends

from app.auth.models import RefreshToken
from app.auth.repository import RefreshTokenRepo, RefreshTokenRepository
from app.core.config import Settings
from app.core.db import SessionDep
from app.core.errors import Forbidden, Unauthorized
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.users.models import Role, User
from app.users.repository import UserRepo, UserRepository


@dataclass
class Issued:
    access_token: str
    refresh_token: str  # raw; only its sha256 is stored


class AuthService:
    def __init__(self, users: UserRepo, tokens: RefreshTokenRepo) -> None:
        self.users = users
        self.tokens = tokens

    async def _issue(self, user: User, family_id: UUID, settings: Settings) -> Issued:
        now = datetime.now(UTC)
        raw = new_refresh_token()
        await self.tokens.add(
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

    async def login(
        self,
        email: str,
        password: str,
        *,
        settings: Settings,
        require_admin: bool = False,
    ) -> Issued:
        user = await self.users.get_by_email(email)
        if user is None:
            verify_password(password, DUMMY_HASH)  # equalize timing with the known-user path
            raise Unauthorized("invalid credentials")
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise Unauthorized("invalid credentials")
        if require_admin and user.role != Role.admin:  # only after the password is proven
            raise Forbidden("admin access required")
        return await self._issue(user, uuid7(), settings)

    async def refresh(
        self,
        raw_token: str,
        *,
        settings: Settings,
        require_admin: bool = False,
    ) -> Issued:
        row = await self.tokens.get_by_hash_for_update(hash_refresh_token(raw_token))
        if row is None:
            raise Unauthorized("invalid refresh token")
        if row.revoked_at is not None:
            # reuse of a rotated token: assume theft, kill the family. Commit first because
            # get_session rolls back when we raise.
            await self.tokens.revoke_family(row.family_id, at=datetime.now(UTC))
            await self.tokens.commit()
            raise Unauthorized("invalid refresh token")
        if row.expires_at <= datetime.now(UTC):
            raise Unauthorized("invalid refresh token")

        user = await self.users.get(row.user_id, fresh=True)
        if user is None or not user.is_active or (require_admin and user.role != Role.admin):
            await self.tokens.revoke_family(row.family_id, at=datetime.now(UTC))
            await self.tokens.commit()
            raise Unauthorized("invalid refresh token")

        row.revoked_at = datetime.now(UTC)
        await self.tokens.save(row)
        return await self._issue(user, row.family_id, settings)

    async def logout(self, raw_token: str) -> None:
        family_id = await self.tokens.get_family_id(hash_refresh_token(raw_token))
        if family_id is not None:
            await self.tokens.revoke_family(family_id, at=datetime.now(UTC))
            await self.tokens.commit()

    async def purge_expired(self, now: datetime | None = None) -> int:
        deleted = await self.tokens.purge_expired(now or datetime.now(UTC))
        await self.tokens.commit()
        return deleted


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
