from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid7

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.pagination import ListParams
from app.items import service
from app.items.models import Item
from app.items.schemas import ItemCreate, ItemUpdate
from app.users.models import User

MakeUser = Callable[..., Awaitable[User]]


def params(*, offset: int = 0, sort: str = "-created_at", q: str | None = None) -> ListParams:
    return ListParams(limit=20, offset=offset, sort=sort, q=q)


async def seed(session: AsyncSession, actor: User, *names: str, published: bool = True) -> None:
    # now() is the transaction start time, so stagger created_at to make order deterministic
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i, name in enumerate(names):
        session.add(
            Item(
                name=name,
                is_published=published,
                created_by_id=actor.id,
                created_at=base + timedelta(minutes=i),
            )
        )
    await session.flush()


async def test_create_sets_creator_and_defaults_unpublished(
    session: AsyncSession, make_user: MakeUser
):
    actor = await make_user()
    item = await service.create(session, actor, ItemCreate(name="a"))
    assert item.created_by_id == actor.id
    assert item.is_published is False
    assert item.description is None
    assert item.created_at is not None


async def test_update_partial_keeps_other_fields(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    item = await service.create(session, actor, ItemCreate(name="a", description="d"))
    updated = await service.update(session, item.id, ItemUpdate(is_published=True))
    assert (updated.name, updated.description, updated.is_published) == ("a", "d", True)


async def test_update_can_set_description_null(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    item = await service.create(session, actor, ItemCreate(name="a", description="d"))
    updated = await service.update(session, item.id, ItemUpdate(description=None))
    assert updated.description is None
    assert updated.name == "a"


async def test_delete_hard_deletes(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    item = await service.create(session, actor, ItemCreate(name="a"))
    await service.delete(session, item.id)
    assert await session.get(Item, item.id) is None
    with pytest.raises(NotFound):
        await service.get(session, item.id)
    with pytest.raises(NotFound):
        await service.delete(session, uuid7())


async def test_list_published_only_flag(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    await seed(session, actor, "pub")
    await seed(session, actor, "draft", published=False)
    rows, total = await service.list_items(session, params())
    assert (len(rows), total) == (2, 2)
    rows, total = await service.list_items(session, params(), published_only=True)
    assert [r.name for r in rows] == ["pub"]
    assert total == 1


async def test_get_published_only_hides_unpublished(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    item = await service.create(session, actor, ItemCreate(name="a"))
    assert (await service.get(session, item.id)).id == item.id
    with pytest.raises(NotFound):
        await service.get(session, item.id, published_only=True)


async def test_list_q_escapes_wildcards(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    await seed(session, actor, "100%", "abc")
    rows, total = await service.list_items(session, params(q="%"))
    assert [r.name for r in rows] == ["100%"]
    assert total == 1
    rows, total = await service.list_items(session, params(q="_"))
    assert (rows, total) == ([], 0)
    rows, _ = await service.list_items(session, params(q="ABC"))
    assert [r.name for r in rows] == ["abc"]


async def test_list_sort_name_and_default_created_desc(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    await seed(session, actor, "b", "c", "a")
    default, _ = await service.list_items(session, params())
    assert [r.name for r in default] == ["a", "c", "b"]
    by_name, _ = await service.list_items(session, params(sort="name"))
    assert [r.name for r in by_name] == ["a", "b", "c"]


async def test_offset_past_total_returns_empty_with_total(
    session: AsyncSession, make_user: MakeUser
):
    actor = await make_user()
    await seed(session, actor, "a", "b")
    rows, total = await service.list_items(session, params(offset=50))
    assert (rows, total) == ([], 2)
