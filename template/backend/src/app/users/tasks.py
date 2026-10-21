from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.broker import broker
from app.core.db import TASK_SESSION
from app.users.models import User

log = structlog.get_logger()


@broker.task(retry_on_error=True, max_retries=3)
async def send_welcome_email(user_id: str, session: AsyncSession = TASK_SESSION) -> None:
    # Stub: no real email. Read-only, so safe to retry or run twice; a missing user is a no-op.
    if await session.get(User, UUID(user_id)) is None:
        return
    log.info("send_welcome_email", user_id=user_id)
