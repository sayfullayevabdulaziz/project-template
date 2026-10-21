from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.db import SessionDep
from app.core.deps import get_current_user
from app.core.pagination import ListParams, list_params
from app.items import service
from app.items.schemas import ItemPublic, ItemPublicPage

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(get_current_user)],
    responses={401: {"description": "Not authenticated"}},
)

Session = SessionDep
Params = Annotated[
    ListParams, Depends(list_params(frozenset({"name", "created_at", "updated_at"})))
]


@router.get("", name="list")
async def list_items(session: Session, params: Params) -> ItemPublicPage:
    rows, total = await service.list_items(session, params, published_only=True)
    return ItemPublicPage(items=[ItemPublic.model_validate(i) for i in rows], total=total)


@router.get("/{item_id}", responses={404: {"description": "Item not found"}})
async def get(item_id: UUID, session: Session) -> ItemPublic:
    return ItemPublic.model_validate(await service.get(session, item_id, published_only=True))
