from fastapi import APIRouter, Depends

from app.api.tagging import tag_surface
from app.auth import api_admin as auth
from app.core.deps import require_admin
from app.items import api_admin as items
from app.users import api_admin as users

router = APIRouter(prefix="/api/admin", dependencies=[Depends(tag_surface("admin"))])
router.include_router(auth.router)  # login/refresh/logout carry no bearer auth by design
protected = APIRouter(dependencies=[Depends(require_admin)])
protected.include_router(users.router)
protected.include_router(items.router)
router.include_router(protected)
