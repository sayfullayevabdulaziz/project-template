from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import Conflict, RateLimited, Unauthorized, register_error_handlers


def make_client() -> AsyncClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/conflict")
    def conflict() -> None:
        raise Conflict("taken")

    @app.get("/unauthorized")
    def unauthorized() -> None:
        raise Unauthorized("bad token")

    @app.get("/limited")
    def limited() -> None:
        raise RateLimited("slow down", retry_after=60)

    @app.get("/items/{item_id}")
    def item(item_id: int) -> int:
        return item_id

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_domain_error_is_problem_json() -> None:
    r = await make_client().get("/conflict")
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert set(body) == {"type", "title", "status", "detail"}
    assert body == {"type": "about:blank", "title": "Conflict", "status": 409, "detail": "taken"}


async def test_unauthorized_has_www_authenticate() -> None:
    r = await make_client().get("/unauthorized")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


async def test_rate_limited_has_retry_after() -> None:
    r = await make_client().get("/limited")
    assert r.status_code == 429
    assert r.headers["retry-after"] == "60"


async def test_validation_error_keeps_default_422_shape() -> None:
    r = await make_client().get("/items/abc")
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/json")
    detail = r.json()["detail"]
    assert isinstance(detail, list)
    assert "loc" in detail[0]
