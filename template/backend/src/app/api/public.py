from fastapi import APIRouter, Depends

from app.api.tagging import tag_surface

router = APIRouter(prefix="/api/v1", dependencies=[Depends(tag_surface("public"))])
