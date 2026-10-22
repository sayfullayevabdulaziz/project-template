from typing import Protocol

from app.core.pagination import ListParams
from app.core.repository import BaseRepository, Repo
from app.items.models import Item


class ItemRepo(Repo[Item], Protocol):
    async def list_page(
        self, params: ListParams, *, published_only: bool = False
    ) -> tuple[list[Item], int]: ...


class ItemRepository(BaseRepository[Item]):
    model = Item
    search_column = "name"

    async def list_page(
        self, params: ListParams, *, published_only: bool = False
    ) -> tuple[list[Item], int]:
        # .expression: ty rejects InstrumentedAttribute[bool] in a ColumnElement list
        where = [Item.is_published.expression] if published_only else []
        return await self._list_page(params, *where)
