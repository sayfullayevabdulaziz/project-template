from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, func, select, update

from app.auth.models import RefreshToken
from app.core.repository import BaseRepository, Repo


class RefreshTokenRepo(Repo[RefreshToken], Protocol):
    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None: ...
    async def get_family_id(self, token_hash: str) -> UUID | None: ...
    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None: ...
    async def revoke_all_for_user(self, user_id: UUID) -> None: ...
    async def purge_expired(self, now: datetime) -> int: ...


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        return await self.session.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def get_family_id(self, token_hash: str) -> UUID | None:
        return await self.session.scalar(
            select(RefreshToken.family_id).where(RefreshToken.token_hash == token_hash)
        )

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )

    # does not commit: the caller owns the transaction
    async def purge_expired(self, now: datetime) -> int:
        result = await self.session.scalars(
            delete(RefreshToken).where(RefreshToken.expires_at < now).returning(RefreshToken.id)
        )
        return len(result.all())
