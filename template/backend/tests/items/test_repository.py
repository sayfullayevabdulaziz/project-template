from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import ListParams
from app.items.models import Item
from app.items.repository import ItemRepository
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


async def test_list_published_only_flag(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    await seed(session, actor, "pub")
    await seed(session, actor, "draft", published=False)
    rows, total = await ItemRepository(session).list_page(params())
    assert (len(rows), total) == (2, 2)
    rows, total = await ItemRepository(session).list_page(params(), published_only=True)
    assert [r.name for r in rows] == ["pub"]
    assert total == 1


async def test_list_q_escapes_wildcards(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    await seed(session, actor, "100%", "abc")
    rows, total = await ItemRepository(session).list_page(params(q="%"))
    assert [r.name for r in rows] == ["100%"]
    assert total == 1
    rows, total = await ItemRepository(session).list_page(params(q="_"))
    assert (rows, total) == ([], 0)
    rows, _ = await ItemRepository(session).list_page(params(q="ABC"))
    assert [r.name for r in rows] == ["abc"]


async def test_list_sort_name_and_default_created_desc(session: AsyncSession, make_user: MakeUser):
    actor = await make_user()
    await seed(session, actor, "b", "c", "a")
    default, _ = await ItemRepository(session).list_page(params())
    assert [r.name for r in default] == ["a", "c", "b"]
    by_name, _ = await ItemRepository(session).list_page(params(sort="name"))
    assert [r.name for r in by_name] == ["a", "b", "c"]


async def test_offset_past_total_returns_empty_with_total(
    session: AsyncSession, make_user: MakeUser
):
    actor = await make_user()
    await seed(session, actor, "a", "b")
    rows, total = await ItemRepository(session).list_page(params(offset=50))
    assert (rows, total) == ([], 2)


@pytest.mark.parametrize("sort", ["name", "-name", "created_at", "-created_at"])
async def test_ties_page_deterministically(session: AsyncSession, make_user: MakeUser, sort: str):
    actor = await make_user()
    same = datetime(2026, 1, 1, tzinfo=UTC)
    session.add_all(Item(name="same", created_by_id=actor.id, created_at=same) for _ in range(10))
    await session.flush()
    ids: list = []
    for offset in range(10):
        page = ListParams(limit=1, offset=offset, sort=sort, q=None)
        rows, total = await ItemRepository(session).list_page(page)
        assert total == 10
        ids += [r.id for r in rows]
    assert len(set(ids)) == 10
