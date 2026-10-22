from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from redis.asyncio import Redis

from app.auth.schemas import LoginRequest
from app.auth.schemas_admin import AdminTokenResponse
from app.auth.service import AuthServiceDep, Issued
from app.core.config import Settings
from app.core.deps import get_settings_dep
from app.core.errors import Unauthorized
from app.core.rate_limit import LOGIN_LIMIT, client_ip, get_redis, hit

COOKIE = "refresh_token"
COOKIE_PATH = "/api/admin/auth"

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={
        401: {"description": "Invalid credentials or refresh cookie"},
        403: {"description": "Not an admin"},
        429: {"description": "Rate limited"},
    },
)

SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


def _set_refresh_cookie(response: Response, raw: str, settings: Settings) -> None:
    response.set_cookie(
        COOKIE,
        raw,
        max_age=2_592_000,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _respond(issued: Issued, response: Response, settings: Settings) -> AdminTokenResponse:
    _set_refresh_cookie(response, issued.refresh_token, settings)
    response.headers["Cache-Control"] = "no-store"
    return AdminTokenResponse(access_token=issued.access_token)


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth: AuthServiceDep,
    settings: SettingsDep,
    redis: Annotated[Redis, Depends(get_redis)],
) -> AdminTokenResponse:
    await hit(redis, f"login:{client_ip(request)}:{body.email}", *LOGIN_LIMIT)
    issued = await auth.login(body.email, body.password, settings=settings, require_admin=True)
    return _respond(issued, response, settings)


@router.post("/refresh")
async def refresh(
    response: Response,
    auth: AuthServiceDep,
    settings: SettingsDep,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> AdminTokenResponse:
    if not refresh_token:
        raise Unauthorized("missing refresh token")
    issued = await auth.refresh(refresh_token, settings=settings, require_admin=True)
    return _respond(issued, response, settings)


# No require_admin: a demoted admin must still be able to end their session.
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    auth: AuthServiceDep,
    settings: SettingsDep,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    if refresh_token:
        await auth.logout(refresh_token)
    response.delete_cookie(
        COOKIE,
        path=COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
