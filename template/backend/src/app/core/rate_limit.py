import math
import time
from collections.abc import Callable

from fastapi import Request
from redis.asyncio import Redis

from app.core.errors import RateLimited

LOGIN_LIMIT = (5, 900)  # per IP+email, 15 min
REGISTER_LIMIT = (10, 3600)  # per IP, 1 h


async def hit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
    *,
    now: Callable[[], float] = time.time,
) -> None:
    t = now()
    bucket = int(t // window_seconds)
    rkey = f"rl:{key}:{bucket}"
    count = await redis.incrby(rkey, 1)  # == INCR; `incr` is an alias ty cannot resolve async
    if count == 1:
        await redis.expire(rkey, window_seconds)
    if count > limit:
        window_end = (bucket + 1) * window_seconds
        # generic detail: the key can hold the email, which must not reach the response
        raise RateLimited(
            "Too many requests, try again later.", retry_after=math.ceil(window_end - t)
        )


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
