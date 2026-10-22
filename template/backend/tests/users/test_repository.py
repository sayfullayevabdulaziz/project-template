from collections.abc import Awaitable, Callable
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import ListParams
from app.users.models import Role, User
from app.users.repository import UserRepository

MakeUser = Callable[..., Awaitable[User]]


async def test_list_sorted_and_filtered(session: AsyncSession, make_user: MakeUser) -> None:
    repo = UserRepository(session)
    for email in ("b@x.com", "a@x.com", "c@y.com"):
        await make_user(email)

    def params(*, offset: int = 0, sort: str = "-email", q: str | None = None) -> ListParams:
        return ListParams(limit=20, offset=offset, sort=sort, q=q)

    users, total = await repo.list_page(params())
    assert [u.email for u in users] == ["c@y.com", "b@x.com", "a@x.com"]
    assert total == 3

    users, total = await repo.list_page(params(q="@X.COM", sort="email"))
    assert [u.email for u in users] == ["a@x.com", "b@x.com"]
    assert total == 2

    assert await repo.list_page(params(q="%")) == ([], 0)
    assert await repo.list_page(params(q="_")) == ([], 0)

    users, total = await repo.list_page(params(offset=10))
    assert (users, total) == ([], 3)


async def test_get_by_email_case_insensitive(session: AsyncSession, make_user: MakeUser) -> None:
    alice = await make_user("alice@x.com")
    assert await UserRepository(session).get_by_email("ALICE@x.COM") is alice


async def test_add_unique_duplicate_returns_none_and_session_usable(
    session: AsyncSession, make_user: MakeUser
) -> None:
    repo = UserRepository(session)
    await make_user("alice@x.com")
    assert await repo.add_unique(User(email="Alice@X.com", password_hash="h")) is None
    assert await repo.get_by_email("alice@x.com") is not None


async def test_count_active_admins_excludes_and_skips_inactive(
    session: AsyncSession, make_user: MakeUser
) -> None:
    repo = UserRepository(session)
    active = await make_user("a@x.com", role=Role.admin)
    await make_user("b@x.com", role=Role.admin, is_active=False)
    await make_user("c@x.com")
    assert await repo.count_active_admins(exclude_id=uuid4()) == 1
    assert await repo.count_active_admins(exclude_id=active.id) == 0
