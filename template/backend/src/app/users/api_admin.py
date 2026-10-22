from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser
from app.core.pagination import ListParams, list_params
from app.users.schemas_admin import UserAdmin, UserAdminPage, UserAdminUpdate
from app.users.service import UserServiceDep

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    },
)

Params = Annotated[ListParams, Depends(list_params(frozenset({"email", "created_at"})))]


# Declared before /{user_id}: otherwise "me" would be parsed as a user id.
@router.get("/me")
async def me(user: CurrentUser) -> UserAdmin:
    return UserAdmin.model_validate(user)


@router.get("", name="list")  # function is list_users: `list` would shadow the builtin
async def list_users(users: UserServiceDep, params: Params) -> UserAdminPage:
    items, total = await users.list_users(params)
    return UserAdminPage(items=[UserAdmin.model_validate(u) for u in items], total=total)


@router.patch(
    "/{user_id}",
    responses={
        404: {"description": "User not found"},
        409: {"description": "Would remove the last active admin or demote/deactivate yourself"},
    },
)
async def update(
    user_id: UUID, body: UserAdminUpdate, users: UserServiceDep, actor: CurrentUser
) -> UserAdmin:
    user = await users.admin_update(actor, user_id, body.role, body.is_active)
    return UserAdmin.model_validate(user)
