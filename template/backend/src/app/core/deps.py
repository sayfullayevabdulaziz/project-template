from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.users.models import Role, User

bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> User:
    if creds is None:
        raise Unauthorized("Not authenticated")
    claims = decode_access_token(creds.credentials, settings.jwt_secret.get_secret_value())
    user = await session.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise Unauthorized("Invalid token")
    return user  # role comes from the row, not the claim: demotion applies at once


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != Role.admin:
        raise Forbidden("Admin role required")
    return user
