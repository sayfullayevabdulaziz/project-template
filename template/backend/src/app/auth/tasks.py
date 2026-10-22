from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import RefreshTokenRepository
from app.auth.service import AuthService
from app.core.broker import broker
from app.core.db import TASK_SESSION
from app.users.repository import UserRepository


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def purge_expired_refresh_tokens(
    session: AsyncSession = TASK_SESSION,
) -> int:
    return await AuthService(
        UserRepository(session), RefreshTokenRepository(session)
    ).purge_expired()
