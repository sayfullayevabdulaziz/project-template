from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import CurrentUser
from app.core.pagination import ListParams, list_params
from app.items.schemas_admin import ItemAdmin, ItemAdminPage, ItemCreate, ItemUpdate
from app.items.service import ItemServiceDep

router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    },
)

Params = Annotated[
    ListParams, Depends(list_params(frozenset({"name", "created_at", "updated_at"})))
]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Item not found"}}


@router.get("", name="list")  # function is list_items: `list` would shadow the builtin
async def list_items(items: ItemServiceDep, params: Params) -> ItemAdminPage:
    rows, total = await items.list_items(params)
    return ItemAdminPage(items=[ItemAdmin.model_validate(i) for i in rows], total=total)


@router.get("/{item_id}", responses=NOT_FOUND)
async def get(item_id: UUID, items: ItemServiceDep) -> ItemAdmin:
    return ItemAdmin.model_validate(await items.get(item_id))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(body: ItemCreate, items: ItemServiceDep, actor: CurrentUser) -> ItemAdmin:
    item = await items.create(
        actor,
        name=body.name,
        description=body.description,
        is_published=body.is_published,
    )
    return ItemAdmin.model_validate(item)


@router.patch("/{item_id}", responses=NOT_FOUND)
async def update(item_id: UUID, body: ItemUpdate, items: ItemServiceDep) -> ItemAdmin:
    item = await items.update(item_id, body.model_dump(exclude_unset=True))
    return ItemAdmin.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
async def delete(item_id: UUID, items: ItemServiceDep) -> Response:
    await items.delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
