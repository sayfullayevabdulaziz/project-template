from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.auth.models import RefreshToken
from app.core.errors import Conflict, NotFound
from app.core.security import verify_password
from app.users.models import Role, User
from app.users.service import UserService
from tests.fakes import FakeRefreshTokenRepository, FakeUserRepository

PASSWORD = "correct horse battery"


def make_service() -> tuple[UserService, FakeUserRepository, FakeRefreshTokenRepository]:
    users, tokens = FakeUserRepository(), FakeRefreshTokenRepository()
    return UserService(users, tokens), users, tokens


async def seed(
    users: FakeUserRepository, email: str, *, role: Role = Role.user, is_active: bool = True
) -> User:
    return await users.add(User(email=email, password_hash="h", role=role, is_active=is_active))


async def test_register_lowercases_email() -> None:
    svc, _, _ = make_service()
    user = await svc.register("Alice@X.com", PASSWORD)
    assert user.email == "alice@x.com"
    assert user.role == Role.user
    assert (await svc.get_by_email("ALICE@x.COM")) is user


async def test_register_duplicate_case_insensitive_conflicts() -> None:
    svc, _, _ = make_service()
    await svc.register("Alice@X.com", PASSWORD)
    with pytest.raises(Conflict, match="Email already registered"):
        await svc.register("alice@x.com", PASSWORD)
    assert await svc.get_by_email("alice@x.com") is not None


class RacedUserRepository(FakeUserRepository):
    async def get_by_email(self, email: str) -> User | None:
        return None  # the pre-check passes

    async def add_unique(self, user: User) -> User | None:
        return None  # the savepoint reports a duplicate


async def test_register_lost_race_raises_conflict() -> None:
    svc = UserService(RacedUserRepository(), FakeRefreshTokenRepository())
    with pytest.raises(Conflict, match="Email already registered"):
        await svc.register("alice@x.com", PASSWORD)


async def test_register_hashes_password() -> None:
    svc, _, _ = make_service()
    user = await svc.register("a@x.com", PASSWORD)
    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)


async def test_get_missing_raises_not_found() -> None:
    svc, _, _ = make_service()
    with pytest.raises(NotFound, match="User not found"):
        await svc.get(uuid4())


async def test_admin_can_promote_user() -> None:
    svc, users, _ = make_service()
    admin = await seed(users, "admin@x.com", role=Role.admin)
    user = await seed(users, "u@x.com")
    updated = await svc.admin_update(admin, user.id, Role.admin, None)
    assert updated.role == Role.admin


async def test_admin_cannot_demote_self() -> None:
    svc, users, _ = make_service()
    admin = await seed(users, "a@x.com", role=Role.admin)
    await seed(users, "b@x.com", role=Role.admin)
    with pytest.raises(Conflict, match="cannot demote or deactivate yourself"):
        await svc.admin_update(admin, admin.id, Role.user, None)


async def test_admin_cannot_deactivate_self() -> None:
    svc, users, _ = make_service()
    admin = await seed(users, "a@x.com", role=Role.admin)
    await seed(users, "b@x.com", role=Role.admin)
    with pytest.raises(Conflict, match="cannot demote or deactivate yourself"):
        await svc.admin_update(admin, admin.id, None, False)


async def test_last_active_admin_cannot_be_demoted_by_other() -> None:
    svc, users, _ = make_service()
    only_active = await seed(users, "a@x.com", role=Role.admin)
    inactive_actor = await seed(users, "b@x.com", role=Role.admin, is_active=False)
    with pytest.raises(Conflict, match="cannot remove the last active admin"):
        await svc.admin_update(inactive_actor, only_active.id, Role.user, None)
    with pytest.raises(Conflict, match="cannot remove the last active admin"):
        await svc.admin_update(inactive_actor, only_active.id, None, False)


async def test_demoting_one_of_two_admins_is_allowed() -> None:
    svc, users, _ = make_service()
    a = await seed(users, "a@x.com", role=Role.admin)
    b = await seed(users, "b@x.com", role=Role.admin)
    updated = await svc.admin_update(a, b.id, Role.user, None)
    assert updated.role == Role.user


async def test_inactive_admin_can_be_demoted_without_other_admins() -> None:
    svc, users, _ = make_service()
    actor = await seed(users, "a@x.com", role=Role.admin, is_active=False)
    target = await seed(users, "b@x.com", role=Role.admin, is_active=False)
    updated = await svc.admin_update(actor, target.id, Role.user, None)
    assert updated.role == Role.user


async def test_deactivate_revokes_refresh_tokens() -> None:
    svc, users, tokens = make_service()
    admin = await seed(users, "a@x.com", role=Role.admin)
    user = await seed(users, "u@x.com")
    token = await tokens.add(
        RefreshToken(
            user_id=user.id,
            token_hash="h" * 64,
            family_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    updated = await svc.admin_update(admin, user.id, None, False)
    assert updated.is_active is False
    assert token.revoked_at is not None


async def test_admin_update_missing_user_not_found() -> None:
    svc, users, _ = make_service()
    admin = await seed(users, "a@x.com", role=Role.admin)
    with pytest.raises(NotFound, match="User not found"):
        await svc.admin_update(admin, uuid4(), Role.admin, None)


async def test_promote_to_admin_keeps_password_hash() -> None:
    svc, _, _ = make_service()
    user = await svc.register("u@x.com", PASSWORD)
    promoted = await svc.promote_to_admin(user)
    assert promoted.role == Role.admin
    assert verify_password(PASSWORD, promoted.password_hash)
