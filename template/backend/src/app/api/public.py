from fastapi import APIRouter, Depends

from app.api.tagging import tag_surface
from app.auth import api_public as auth

router = APIRouter(prefix="/api/v1", dependencies=[Depends(tag_surface("public"))])
router.include_router(auth.router)
