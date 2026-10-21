from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.pagination import ListParams, apply_sort, escape_like
from app.items.models import Item
from app.items.schemas import ItemCreate, ItemUpdate
from app.users.models import User


async def create(session: AsyncSession, actor: User, data: ItemCreate) -> Item:
    item = Item(**data.model_dump(), created_by_id=actor.id)
    session.add(item)
    await session.flush()
    await session.refresh(item)  # load server-default timestamps
    return item


async def get(session: AsyncSession, item_id: UUID, *, published_only: bool = False) -> Item:
    item = await session.get(Item, item_id)
    if item is None or (published_only and not item.is_published):
        raise NotFound("Item not found")
    return item


async def list_items(
    session: AsyncSession, params: ListParams, *, published_only: bool = False
) -> tuple[list[Item], int]:
    where = []
    if published_only:
        where.append(Item.is_published)
    if params.q:
        where.append(Item.name.ilike(f"%{escape_like(params.q)}%", escape="\\"))
    total = await session.scalar(select(func.count()).select_from(Item).where(*where))
    stmt = apply_sort(select(Item).where(*where), Item, params.sort)
    rows = await session.scalars(stmt.limit(params.limit).offset(params.offset))
    return list(rows), total or 0


async def update(session: AsyncSession, item_id: UUID, data: ItemUpdate) -> Item:
    item = await get(session, item_id)
    for field in data.model_fields_set:
        value = getattr(data, field)
        if value is not None or field == "description":
            setattr(item, field, value)
    await session.flush()
    await session.refresh(item)  # onupdate updated_at is server-side
    return item


async def delete(session: AsyncSession, item_id: UUID) -> None:
    await session.delete(await get(session, item_id))
    await session.flush()
