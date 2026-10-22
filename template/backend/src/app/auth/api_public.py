from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis

from app.auth import service
from app.auth.schemas import LoginRequest
from app.auth.schemas_public import RefreshRequest, TokenPair
from app.core.config import Settings
from app.core.db import SessionDep
from app.core.deps import get_settings_dep
from app.core.rate_limit import LOGIN_LIMIT, client_ip, get_redis, hit

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={
        401: {"description": "Invalid credentials or token"},
        429: {"description": "Rate limited"},
    },
)

Session = SessionDep
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def _pair(issued: service.Issued, response: Response) -> TokenPair:
    response.headers["Cache-Control"] = "no-store"
    return TokenPair(access_token=issued.access_token, refresh_token=issued.refresh_token)


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session,
    settings: SettingsDep,
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenPair:
    await hit(redis, f"login:{client_ip(request)}:{body.email}", *LOGIN_LIMIT)
    return _pair(
        await service.login(session, body.email, body.password, settings=settings), response
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest, response: Response, session: Session, settings: SettingsDep
) -> TokenPair:
    return _pair(await service.refresh(session, body.refresh_token, settings=settings), response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, session: Session) -> None:
    await service.logout(session, body.refresh_token)
