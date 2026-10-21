from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.core.broker import broker
from app.core.db import TASK_SESSION


@broker.task(schedule=[{"cron": "0 3 * * *"}])
async def purge_expired_refresh_tokens(
    session: AsyncSession = TASK_SESSION,
) -> int:
    return await service.purge_expired(session)
