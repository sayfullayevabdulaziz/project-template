from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.db import SessionDep
from app.core.deps import CurrentUser
from app.core.pagination import ListParams, list_params
from app.items import service
from app.items.schemas_admin import ItemAdmin, ItemAdminPage, ItemCreate, ItemUpdate

router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    },
)

Session = SessionDep
Params = Annotated[
    ListParams, Depends(list_params(frozenset({"name", "created_at", "updated_at"})))
]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Item not found"}}


@router.get("", name="list")  # function is list_items: `list` would shadow the builtin
async def list_items(session: Session, params: Params) -> ItemAdminPage:
    rows, total = await service.list_items(session, params)
    return ItemAdminPage(items=[ItemAdmin.model_validate(i) for i in rows], total=total)


@router.get("/{item_id}", responses=NOT_FOUND)
async def get(item_id: UUID, session: Session) -> ItemAdmin:
    return ItemAdmin.model_validate(await service.get(session, item_id))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(body: ItemCreate, session: Session, actor: CurrentUser) -> ItemAdmin:
    item = await service.create(
        session,
        actor,
        name=body.name,
        description=body.description,
        is_published=body.is_published,
    )
    return ItemAdmin.model_validate(item)


@router.patch("/{item_id}", responses=NOT_FOUND)
async def update(item_id: UUID, body: ItemUpdate, session: Session) -> ItemAdmin:
    item = await service.update(session, item_id, body.model_dump(exclude_unset=True))
    return ItemAdmin.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
async def delete(item_id: UUID, session: Session) -> Response:
    await service.delete(session, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
