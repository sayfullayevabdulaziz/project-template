from fastapi import APIRouter, Depends

from app.api.tagging import tag_surface
from app.auth import api_admin as auth
from app.core.deps import require_admin

router = APIRouter(prefix="/api/admin", dependencies=[Depends(tag_surface("admin"))])
router.include_router(auth.router)  # login/refresh/logout carry no bearer auth by design
protected = APIRouter(dependencies=[Depends(require_admin)])
# Users and items routers (Tasks 12-13) must be added to `protected` before this include.
router.include_router(protected)
