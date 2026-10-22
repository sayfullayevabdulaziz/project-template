from typing import ClassVar, Protocol
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Base
from app.core.pagination import ListParams, apply_sort, escape_like


class Repo[M](Protocol):
    async def get(self, id: UUID, *, fresh: bool = False) -> M | None: ...
    async def add(self, obj: M) -> M: ...
    async def save(self, obj: M) -> M: ...
    async def delete(self, obj: M) -> None: ...
    async def commit(self) -> None: ...


class BaseRepository[M: Base]:
    model: type[M]
    search_column: ClassVar[str | None] = None

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # fresh=True re-reads the row, overwriting an already-loaded instance (e.g. after a row lock).
    async def get(self, id: UUID, *, fresh: bool = False) -> M | None:
        return await self.session.get(self.model, id, populate_existing=fresh)

    async def add(self, obj: M) -> M:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)  # load server-default timestamps
        return obj

    async def save(self, obj: M) -> M:
        await self.session.flush()
        await self.session.refresh(obj)  # onupdate updated_at is server-side
        return obj

    async def delete(self, obj: M) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def _list_page(
        self, params: ListParams, *where: ColumnElement[bool]
    ) -> tuple[list[M], int]:
        conditions = list(where)
        if params.q and self.search_column:
            column = getattr(self.model, self.search_column)
            conditions.append(column.ilike(f"%{escape_like(params.q)}%", escape="\\"))
        total = await self.session.scalar(
            select(func.count()).select_from(self.model).where(*conditions)
        )
        stmt = apply_sort(select(self.model).where(*conditions), self.model, params.sort)
        rows = await self.session.scalars(stmt.limit(params.limit).offset(params.offset))
        return list(rows), total or 0
