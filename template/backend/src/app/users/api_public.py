from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import CurrentUser
from app.core.rate_limit import REGISTER_LIMIT, client_ip, get_redis, hit
from app.users import service
from app.users.schemas import RegisterRequest, UserPublic
from app.users.tasks import send_welcome_email

router = APIRouter(prefix="/users", tags=["users"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Email already registered"},
        429: {"description": "Rate limited"},
    },
)
async def register(
    body: RegisterRequest,
    request: Request,
    session: Session,
    redis: Annotated[Redis, Depends(get_redis)],
) -> UserPublic:
    await hit(redis, f"register:{client_ip(request)}", *REGISTER_LIMIT)
    user = await service.register(session, body.email, body.password)
    out = UserPublic.model_validate(user)
    # Commit before enqueueing so the worker can see the row.
    await session.commit()
    await send_welcome_email.kiq(str(out.id))
    return out


@router.get("/me", responses={401: {"description": "Not authenticated"}})
async def me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)
