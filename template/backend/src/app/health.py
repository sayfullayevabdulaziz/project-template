from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session

router = APIRouter(prefix="/health", tags=["health"], include_in_schema=False)


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
async def ready(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, str] | JSONResponse:
    checks = (
        ("database", session.execute(text("SELECT 1"))),
        ("redis", request.app.state.redis.ping()),
    )
    for name, check in checks:
        try:
            await check
        except Exception:
            return JSONResponse(
                {
                    "type": "about:blank",
                    "title": "Service Unavailable",
                    "status": 503,
                    "detail": f"{name} unavailable",
                },
                status_code=503,
                media_type="application/problem+json",
            )
    return {"status": "ok"}
