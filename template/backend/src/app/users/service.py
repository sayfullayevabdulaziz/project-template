from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.auth.repository import RefreshTokenRepo, RefreshTokenRepository
from app.core.db import SessionDep
from app.core.errors import Conflict, NotFound
from app.core.pagination import ListParams
from app.core.security import hash_password
from app.users.models import Role, User
from app.users.repository import UserRepo, UserRepository


class UserService:
    def __init__(self, users: UserRepo, tokens: RefreshTokenRepo) -> None:
        self.users = users
        self.tokens = tokens

    async def get(self, user_id: UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFound("User not found")
        return user

    async def get_by_email(self, email: str) -> User | None:
        return await self.users.get_by_email(email)

    async def register(self, email: str, password: str, role: Role = Role.user) -> User:
        email = email.lower()
        if await self.users.get_by_email(email) is not None:
            raise Conflict("Email already registered")
        user = User(email=email, password_hash=hash_password(password), role=role)
        # a None here means a lost race on the unique email
        if await self.users.add_unique(user) is None:
            raise Conflict("Email already registered")
        return user

    async def list_users(self, params: ListParams) -> tuple[list[User], int]:
        return await self.users.list_page(params)

    async def admin_update(
        self, actor: User, user_id: UUID, role: Role | None, is_active: bool | None
    ) -> User:
        target = await self.users.get_for_update(user_id)
        if target is None:
            raise NotFound("User not found")

        demotes = target.role == Role.admin and role == Role.user
        deactivates = target.is_active and is_active is False
        if target.role == Role.admin and target.is_active and (demotes or deactivates):
            if target.id == actor.id:
                raise Conflict("cannot demote or deactivate yourself")
            if not await self.users.count_active_admins(exclude_id=target.id):
                raise Conflict("cannot remove the last active admin")

        if role is not None:
            target.role = role
        if is_active is not None:
            target.is_active = is_active
        if deactivates:
            await self.tokens.revoke_all_for_user(target.id)
        return await self.users.save(target)

    async def promote_to_admin(self, user: User) -> User:
        user.role = Role.admin
        return await self.users.save(user)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserRepository(session), RefreshTokenRepository(session))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
