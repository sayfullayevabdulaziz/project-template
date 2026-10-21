from fastapi import APIRouter, Depends

from app.api.tagging import tag_surface
from app.core.deps import require_admin

router = APIRouter(prefix="/api/admin", dependencies=[Depends(tag_surface("admin"))])
# Module routers (auth login/refresh/logout without auth; users, items below) arrive in Tasks 11-13.
protected = APIRouter(dependencies=[Depends(require_admin)])
router.include_router(protected)
