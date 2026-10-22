from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.pagination import ListParams, list_params
from app.items.schemas_public import ItemPublic, ItemPublicPage
from app.items.service import ItemServiceDep

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_user)],
    responses={401: {"description": "Not authenticated"}},
)

Params = Annotated[
    ListParams, Depends(list_params(frozenset({"name", "created_at", "updated_at"})))
]


@router.get("", name="list")
async def list_items(items: ItemServiceDep, params: Params) -> ItemPublicPage:
    rows, total = await items.list_items(params, published_only=True)
    return ItemPublicPage(items=[ItemPublic.model_validate(i) for i in rows], total=total)


@router.get("/{item_id}", responses={404: {"description": "Item not found"}})
async def get(item_id: UUID, items: ItemServiceDep) -> ItemPublic:
    return ItemPublic.model_validate(await items.get(item_id, published_only=True))
