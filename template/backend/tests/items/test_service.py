from uuid import uuid7

import pytest

from app.core.errors import NotFound
from app.core.pagination import ListParams
from app.items.service import ItemService
from app.users.models import User
from tests.fakes import FakeItemRepository

actor = User(id=uuid7(), email="a@x.com", password_hash="h")


def make_service() -> ItemService:
    return ItemService(FakeItemRepository())


async def test_create_sets_creator_and_defaults_unpublished():
    item = await make_service().create(actor, name="a")
    assert item.created_by_id == actor.id
    assert item.is_published is False
    assert item.description is None
    assert item.created_at is not None


async def test_update_partial_keeps_other_fields():
    svc = make_service()
    item = await svc.create(actor, name="a", description="d")
    updated = await svc.update(item.id, {"is_published": True})
    assert (updated.name, updated.description, updated.is_published) == ("a", "d", True)


async def test_update_can_set_description_null():
    svc = make_service()
    item = await svc.create(actor, name="a", description="d")
    updated = await svc.update(item.id, {"description": None})
    assert updated.description is None
    assert updated.name == "a"


async def test_update_ignores_null_name():
    svc = make_service()
    item = await svc.create(actor, name="a")
    updated = await svc.update(item.id, {"name": None})
    assert updated.name == "a"


async def test_delete_hard_deletes():
    repo = FakeItemRepository()
    svc = ItemService(repo)
    item = await svc.create(actor, name="a")
    await svc.delete(item.id)
    assert await repo.get(item.id) is None
    with pytest.raises(NotFound):
        await svc.get(item.id)
    with pytest.raises(NotFound):
        await svc.delete(uuid7())


async def test_get_published_only_hides_unpublished():
    svc = make_service()
    item = await svc.create(actor, name="a")
    assert (await svc.get(item.id)).id == item.id
    with pytest.raises(NotFound):
        await svc.get(item.id, published_only=True)


async def test_list_published_only_passes_filter():
    svc = make_service()
    pub = await svc.create(actor, name="pub", is_published=True)
    await svc.create(actor, name="draft")
    p = ListParams(limit=20, offset=0, sort="-created_at", q=None)
    rows, total = await svc.list_items(p, published_only=True)
    assert rows == [pub]
    assert total == 1
