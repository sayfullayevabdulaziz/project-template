from dataclasses import replace
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.pagination import ListParams
from app.core.repository import BaseRepository, Repo
from app.users.models import Role, User


class UserRepo(Repo[User], Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_for_update(self, id: UUID) -> User | None: ...
    async def count_active_admins(self, *, exclude_id: UUID) -> int: ...
    async def add_unique(self, user: User) -> User | None: ...
    async def list_page(self, params: ListParams) -> tuple[list[User], int]: ...


class UserRepository(BaseRepository[User]):
    model = User
    search_column = "email"

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email.lower()))

    async def get_for_update(self, id: UUID) -> User | None:
        return await self.session.scalar(
            select(User)
            .where(User.id == id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def count_active_admins(self, *, exclude_id: UUID) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.role == Role.admin, User.is_active, User.id != exclude_id)
            )
            or 0
        )

    async def add_unique(self, user: User) -> User | None:
        try:
            # savepoint: a lost race must not poison the caller's transaction
            async with self.session.begin_nested():
                self.session.add(user)
                await self.session.flush()
        except IntegrityError:
            return None
        return user

    async def list_page(self, params: ListParams) -> tuple[list[User], int]:
        return await self._list_page(replace(params, q=params.q.lower() if params.q else None))
