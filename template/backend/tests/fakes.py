from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy.sql.schema import ColumnDefault

from app.auth.models import RefreshToken
from app.core.db import Base
from app.core.pagination import ListParams
from app.items.models import Item
from app.users.models import Role, User


class FakeRepository[M: Base]:
    def __init__(self) -> None:
        self.rows: dict[UUID, M] = {}
        self.commits = 0

    async def get(self, id: UUID, *, fresh: bool = False) -> M | None:
        return self.rows.get(id)

    async def add(self, obj: M) -> M:
        # Mirrors what the database fills in on flush.
        if getattr(obj, "id", None) is None:
            setattr(obj, "id", uuid7())  # noqa: B010  # M is only bound to Base, which has no id
        for column in type(obj).__table__.columns:
            default = column.default
            if (
                getattr(obj, column.key) is None
                and isinstance(default, ColumnDefault)
                and default.is_scalar
            ):
                setattr(obj, column.key, default.arg)
        now = datetime.now(UTC)
        for stamp in ("created_at", "updated_at"):
            if hasattr(obj, stamp) and getattr(obj, stamp) is None:
                setattr(obj, stamp, now)
        self.rows[getattr(obj, "id")] = obj  # noqa: B009
        return obj

    async def save(self, obj: M) -> M:
        if hasattr(obj, "updated_at"):
            setattr(obj, "updated_at", datetime.now(UTC))  # noqa: B010
        return obj

    async def delete(self, obj: M) -> None:
        del self.rows[getattr(obj, "id")]  # noqa: B009

    async def commit(self) -> None:
        self.commits += 1

    def _list_page(self, params: ListParams, rows: Iterable[M]) -> tuple[list[M], int]:
        # shortcut: no search/sort in fakes; covered by Postgres repository tests
        everything = list(rows)
        return everything[params.offset : params.offset + params.limit], len(everything)


class FakeItemRepository(FakeRepository[Item]):
    async def list_page(
        self, params: ListParams, *, published_only: bool = False
    ) -> tuple[list[Item], int]:
        return self._list_page(
            params, (i for i in self.rows.values() if i.is_published or not published_only)
        )


class FakeUserRepository(FakeRepository[User]):
    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.rows.values() if u.email == email.lower()), None)

    async def get_for_update(self, id: UUID) -> User | None:
        return await self.get(id)

    async def count_active_admins(self, *, exclude_id: UUID) -> int:
        return sum(
            u.role == Role.admin and u.is_active and u.id != exclude_id for u in self.rows.values()
        )

    async def add_unique(self, user: User) -> User | None:
        if await self.get_by_email(user.email) is not None:
            return None
        return await self.add(user)

    async def list_page(self, params: ListParams) -> tuple[list[User], int]:
        return self._list_page(params, self.rows.values())


class FakeRefreshTokenRepository(FakeRepository[RefreshToken]):
    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self.rows.values() if t.token_hash == token_hash), None)

    async def get_family_id(self, token_hash: str) -> UUID | None:
        row = await self.get_by_hash_for_update(token_hash)
        return row.family_id if row else None

    async def revoke_family(self, family_id: UUID, *, at: datetime) -> None:
        for t in self.rows.values():
            if t.family_id == family_id and t.revoked_at is None:
                t.revoked_at = at

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        for t in self.rows.values():
            if t.user_id == user_id and t.revoked_at is None:
                t.revoked_at = datetime.now(UTC)

    async def purge_expired(self, now: datetime) -> int:
        expired = [i for i, t in self.rows.items() if t.expires_at < now]
        for i in expired:
            del self.rows[i]
        return len(expired)
