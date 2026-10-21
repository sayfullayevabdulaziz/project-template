from fastapi import APIRouter, Depends

from app.api.tagging import tag_surface
from app.auth import api_public as auth
from app.items import api_public as items
from app.users import api_public as users

router = APIRouter(prefix="/api/v1", dependencies=[Depends(tag_surface("public"))])
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(items.router)
