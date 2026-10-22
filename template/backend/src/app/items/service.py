from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends

from app.core.db import SessionDep
from app.core.errors import NotFound
from app.core.pagination import ListParams
from app.items.models import Item
from app.items.repository import ItemRepo, ItemRepository
from app.users.models import User


class ItemService:
    def __init__(self, items: ItemRepo) -> None:
        self.items = items

    # Plain arguments, not a surface schema: each surface decides which fields its callers may set.
    async def create(
        self,
        actor: User,
        *,
        name: str,
        description: str | None = None,
        is_published: bool = False,
    ) -> Item:
        return await self.items.add(
            Item(
                name=name,
                description=description,
                is_published=is_published,
                created_by_id=actor.id,
            )
        )

    async def get(self, item_id: UUID, *, published_only: bool = False) -> Item:
        item = await self.items.get(item_id)
        if item is None or (published_only and not item.is_published):
            raise NotFound("Item not found")
        return item

    async def list_items(
        self, params: ListParams, *, published_only: bool = False
    ) -> tuple[list[Item], int]:
        return await self.items.list_page(params, published_only=published_only)

    async def update(self, item_id: UUID, changes: dict[str, Any]) -> Item:
        item = await self.get(item_id)
        for field, value in changes.items():
            if value is not None or field == "description":
                setattr(item, field, value)
        return await self.items.save(item)

    async def delete(self, item_id: UUID) -> None:
        await self.items.delete(await self.get(item_id))


def get_item_service(session: SessionDep) -> ItemService:
    return ItemService(ItemRepository(session))


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
