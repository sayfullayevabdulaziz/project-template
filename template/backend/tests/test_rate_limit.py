from collections.abc import Callable

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.core.errors import RateLimited
from app.core.rate_limit import LOGIN_LIMIT, REGISTER_LIMIT, client_ip, get_redis, hit

START = 900_000.0  # on a boundary of both the 900 s and 3600 s windows


def at(t: float) -> Callable[[], float]:
    return lambda: t


async def test_allows_exactly_limit_then_429(redis_client: Redis) -> None:
    now = at(START + 10)
    for _ in range(5):
        await hit(redis_client, "login:a", 5, 900, now=now)
    with pytest.raises(RateLimited) as exc:
        await hit(redis_client, "login:a", 5, 900, now=now)
    assert exc.value.headers["Retry-After"] == "890"


async def test_window_rollover_resets(redis_client: Redis) -> None:
    for _ in range(5):
        await hit(redis_client, "login:a", 5, 900, now=at(START + 10))
    await hit(redis_client, "login:a", 5, 900, now=at(START + 910))


async def test_keys_are_independent(redis_client: Redis) -> None:
    for _ in range(5):
        await hit(redis_client, "login:a", 5, 900, now=at(START + 10))
    await hit(redis_client, "login:b", 5, 900, now=at(START + 10))


def test_constants() -> None:
    assert LOGIN_LIMIT == (5, 900)
    assert REGISTER_LIMIT == (10, 3600)


async def test_key_expires(redis_client: Redis) -> None:
    await hit(redis_client, "expiry", 5, 900, now=at(START + 10))
    ttl = await redis_client.ttl(f"rl:expiry:{int((START + 10) // 900)}")
    assert 0 < ttl <= 900


async def test_client_ip_ignores_x_forwarded_for() -> None:
    app = FastAPI()

    @app.get("/ip")
    def ip(request: Request) -> str:
        return client_ip(request)

    transport = ASGITransport(app=app)
    r = await AsyncClient(transport=transport, base_url="http://test").get(
        "/ip", headers={"X-Forwarded-For": "203.0.113.9"}
    )
    assert r.json() == "127.0.0.1"


async def test_get_redis_reads_app_state(redis_client: Redis) -> None:
    app = FastAPI()
    app.state.redis = redis_client

    @app.get("/redis")
    def route(request: Request) -> bool:
        return get_redis(request) is redis_client

    transport = ASGITransport(app=app)
    r = await AsyncClient(transport=transport, base_url="http://test").get("/redis")
    assert r.json() is True
