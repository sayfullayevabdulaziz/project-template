from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID, uuid7

from sqlalchemy.sql.schema import ColumnDefault

from app.core.db import Base
from app.core.pagination import ListParams
from app.items.models import Item


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
