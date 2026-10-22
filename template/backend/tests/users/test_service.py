from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken
from app.core.errors import Conflict, NotFound
from app.core.pagination import ListParams
from app.core.security import verify_password
from app.users import service
from app.users.models import Role, User

MakeUser = Callable[..., Awaitable[User]]
PASSWORD = "correct horse battery"


async def test_register_lowercases_email(session: AsyncSession) -> None:
    user = await service.register(session, "Alice@X.com", PASSWORD)
    assert user.email == "alice@x.com"
    assert user.role == Role.user
    assert (await service.get_by_email(session, "ALICE@x.COM")) is user


async def test_register_duplicate_case_insensitive_conflicts(session: AsyncSession) -> None:
    await service.register(session, "Alice@X.com", PASSWORD)
    with pytest.raises(Conflict):
        await service.register(session, "alice@x.com", PASSWORD)
    # the session must still be usable after the conflict
    assert await service.get_by_email(session, "alice@x.com") is not None


async def test_register_hashes_password(session: AsyncSession) -> None:
    user = await service.register(session, "a@x.com", PASSWORD)
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)


async def test_get_missing_raises_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFound):
        await service.get(session, uuid4())


async def test_admin_can_promote_user(session: AsyncSession, make_user: MakeUser) -> None:
    admin = await make_user("admin@x.com", role=Role.admin)
    user = await make_user("u@x.com")
    updated = await service.admin_update(session, admin, user.id, Role.admin, None)
    assert updated.role == Role.admin


async def test_admin_cannot_demote_self(session: AsyncSession, make_user: MakeUser) -> None:
    admin = await make_user("a@x.com", role=Role.admin)
    await make_user("b@x.com", role=Role.admin)
    with pytest.raises(Conflict, match="yourself"):
        await service.admin_update(session, admin, admin.id, Role.user, None)


async def test_admin_cannot_deactivate_self(session: AsyncSession, make_user: MakeUser) -> None:
    admin = await make_user("a@x.com", role=Role.admin)
    await make_user("b@x.com", role=Role.admin)
    with pytest.raises(Conflict, match="yourself"):
        await service.admin_update(session, admin, admin.id, None, False)


async def test_last_active_admin_cannot_be_demoted_by_other(
    session: AsyncSession, make_user: MakeUser
) -> None:
    only_active = await make_user("a@x.com", role=Role.admin)
    inactive_actor = await make_user("b@x.com", role=Role.admin, is_active=False)
    with pytest.raises(Conflict, match="last active admin"):
        await service.admin_update(session, inactive_actor, only_active.id, Role.user, None)
    with pytest.raises(Conflict, match="last active admin"):
        await service.admin_update(session, inactive_actor, only_active.id, None, False)


async def test_demoting_one_of_two_admins_is_allowed(
    session: AsyncSession, make_user: MakeUser
) -> None:
    a = await make_user("a@x.com", role=Role.admin)
    b = await make_user("b@x.com", role=Role.admin)
    updated = await service.admin_update(session, a, b.id, Role.user, None)
    assert updated.role == Role.user


async def test_inactive_admin_can_be_demoted_without_other_admins(
    session: AsyncSession, make_user: MakeUser
) -> None:
    actor = await make_user("a@x.com", role=Role.admin, is_active=False)
    target = await make_user("b@x.com", role=Role.admin, is_active=False)
    updated = await service.admin_update(session, actor, target.id, Role.user, None)
    assert updated.role == Role.user


async def test_deactivate_revokes_refresh_tokens(
    session: AsyncSession, make_user: MakeUser
) -> None:
    admin = await make_user("a@x.com", role=Role.admin)
    user = await make_user("u@x.com")
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash="h" * 64,
            family_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.flush()
    updated = await service.admin_update(session, admin, user.id, None, False)
    assert updated.is_active is False
    token = (
        await session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id))
    ).one()
    await session.refresh(token)
    assert token.revoked_at is not None


async def test_admin_update_missing_user_not_found(
    session: AsyncSession, make_user: MakeUser
) -> None:
    admin = await make_user("a@x.com", role=Role.admin)
    with pytest.raises(NotFound):
        await service.admin_update(session, admin, uuid4(), Role.admin, None)


async def test_list_sorted_and_filtered(session: AsyncSession, make_user: MakeUser) -> None:
    for email in ("b@x.com", "a@x.com", "c@y.com"):
        await make_user(email)

    def params(*, offset: int = 0, sort: str = "-email", q: str | None = None) -> ListParams:
        return ListParams(limit=20, offset=offset, sort=sort, q=q)

    users, total = await service.list_users(session, params())
    assert [u.email for u in users] == ["c@y.com", "b@x.com", "a@x.com"]
    assert total == 3

    users, total = await service.list_users(session, params(q="@X.COM", sort="email"))
    assert [u.email for u in users] == ["a@x.com", "b@x.com"]
    assert total == 2

    assert await service.list_users(session, params(q="%")) == ([], 0)
    assert await service.list_users(session, params(q="_")) == ([], 0)

    users, total = await service.list_users(session, params(offset=10))
    assert (users, total) == ([], 3)
