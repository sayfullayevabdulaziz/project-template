from collections.abc import Awaitable, Callable
from uuid import uuid7

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import ListParams
from app.core.repository import BaseRepository
from app.items.models import Item
from app.users.models import User

MakeUser = Callable[..., Awaitable[User]]


class _Items(BaseRepository[Item]):
    model = Item
    search_column = "name"


async def test_get_returns_none_for_missing(session: AsyncSession) -> None:
    assert await _Items(session).get(uuid7()) is None


async def test_add_fills_server_defaults(session: AsyncSession, make_user: MakeUser) -> None:
    u = await make_user()
    item = await _Items(session).add(Item(name="a", created_by_id=u.id))
    assert item.created_at is not None
    assert item.is_published is False


async def test_get_fresh_reloads_row(session: AsyncSession, make_user: MakeUser) -> None:
    u = await make_user()
    repo = _Items(session)
    item = await repo.add(Item(name="a", created_by_id=u.id))
    # synchronize_session=False: the ORM must not patch the loaded instance for us
    await session.execute(
        update(Item)
        .where(Item.id == item.id)
        .values(name="b")
        .execution_options(synchronize_session=False)
    )
    stale = await repo.get(item.id)
    assert stale is not None
    assert stale.name == "a"  # identity map hands back the loaded object
    fresh = await repo.get(item.id, fresh=True)
    assert fresh is not None
    assert fresh.name == "b"


async def test_save_flushes_and_refreshes_updated_at(
    session: AsyncSession, make_user: MakeUser
) -> None:
    u = await make_user()
    repo = _Items(session)
    item = await repo.add(Item(name="a", created_by_id=u.id))
    item.name = "z"
    await repo.save(item)
    reloaded = await repo.get(item.id, fresh=True)
    assert reloaded is not None
    assert reloaded.name == "z"


async def test_delete_removes_row(session: AsyncSession, make_user: MakeUser) -> None:
    u = await make_user()
    repo = _Items(session)
    item = await repo.add(Item(name="a", created_by_id=u.id))
    await repo.delete(item)
    assert await repo.get(item.id) is None


async def test_list_page_search_sort_count(session: AsyncSession, make_user: MakeUser) -> None:
    u = await make_user()
    repo = _Items(session)
    for name in ("100%", "abc", "abd"):
        await repo.add(Item(name=name, created_by_id=u.id))

    rows, total = await repo._list_page(ListParams(20, 0, "name", "%"))
    assert ([r.name for r in rows], total) == (["100%"], 1)

    rows, total = await repo._list_page(ListParams(20, 0, "-name", "AB"))
    assert ([r.name for r in rows], total) == (["abd", "abc"], 2)

    rows, total = await repo._list_page(ListParams(20, 50, "name", None))
    assert (rows, total) == ([], 3)
