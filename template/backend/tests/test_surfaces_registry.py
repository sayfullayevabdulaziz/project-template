from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.api.surfaces import SURFACES, Surface, generate_unique_id, surface_openapi
from app.core.config import Settings
from app.main import create_app


def test_registry_contains_admin_and_public_with_prefixes():
    assert {s.name: s.prefix for s in SURFACES} == {"admin": "/api/admin", "public": "/api/v1"}


def test_surface_openapi_only_contains_prefix_paths():
    app = FastAPI(title="Scratch", generate_unique_id_function=generate_unique_id)
    router = APIRouter(tags=["t"])

    @router.get("/api/v1/x")
    async def x() -> dict[str, int]:
        return {}

    @router.get("/api/admin/y")
    async def y() -> dict[str, int]:
        return {}

    app.include_router(router)
    public = Surface("public", "/api/v1", APIRouter())
    admin = Surface("admin", "/api/admin", APIRouter())
    assert list(surface_openapi(app, public)["paths"]) == ["/api/v1/x"]
    assert list(surface_openapi(app, admin)["paths"]) == ["/api/admin/y"]
    assert surface_openapi(app, public)["info"]["title"] == "Scratch public"


def test_unique_id_function():
    route = APIRoute("/items", lambda: None, tags=["items"], name="list")
    assert generate_unique_id(route) == "items-list"


def _settings(env: str) -> Settings:
    return Settings.model_validate(
        {
            "env": env,
            "database_url": "postgresql+asyncpg://x/x",
            "redis_url": "redis://x",
            "jwt_secret": "x" * 40,
        }
    )


def test_openapi_url_is_none():
    assert create_app(_settings("test")).openapi_url is None


async def test_default_openapi_not_served(anon_client):
    assert (await anon_client.get("/openapi.json")).status_code == 404


async def test_docs_served_only_in_dev():
    import httpx

    async def status(env: str, path: str) -> int:
        transport = httpx.ASGITransport(app=create_app(_settings(env)))
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            return (await c.get(path)).status_code

    assert await status("dev", "/api/v1/openapi.json") == 200
    assert await status("dev", "/api/admin/docs") == 200
    for env in ("test", "prod"):
        assert await status(env, "/api/v1/openapi.json") == 404
        assert await status(env, "/api/admin/docs") == 404
