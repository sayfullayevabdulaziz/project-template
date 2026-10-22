from uuid import UUID, uuid7

from app.core.pagination import ListParams
from app.items.models import Item
from app.users.models import Role, User
from tests.fakes import FakeRepository


async def test_fake_add_fills_defaults() -> None:
    item = await FakeRepository[Item]().add(Item(name="a", created_by_id=uuid7()))
    assert isinstance(item.id, UUID)
    assert item.is_published is False
    assert item.created_at is not None
    assert item.updated_at is not None

    user = await FakeRepository[User]().add(User(email="A@x.com", password_hash="h"))
    assert isinstance(user.id, UUID)
    assert user.role == Role.user
    assert user.is_active is True
    assert user.email == "a@x.com"
    assert user.created_at is not None
    assert user.updated_at is not None


async def test_fake_get_delete_commit() -> None:
    repo = FakeRepository[Item]()
    item = await repo.add(Item(name="a", created_by_id=uuid7()))
    assert await repo.get(item.id) is item
    await repo.delete(item)
    assert await repo.get(item.id) is None
    await repo.commit()
    await repo.commit()
    assert repo.commits == 2


async def test_fake_list_page_limits_and_counts() -> None:
    repo = FakeRepository[Item]()
    items = [await repo.add(Item(name=str(i), created_by_id=uuid7())) for i in range(5)]
    rows, total = repo._list_page(ListParams(2, 2, "-created_at", None), repo.rows.values())
    assert (rows, total) == (items[2:4], 5)
