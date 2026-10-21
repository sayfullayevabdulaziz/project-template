from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis

from app import health
from app.api.surfaces import SURFACES, Surface, generate_unique_id, surface_openapi
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Tests bypass this and set app.state by hand. Broker and telemetry arrive in Tasks 14-15.
    settings: Settings = app.state.settings
    engine = make_engine(settings.database_url)
    app.state.session_factory = make_session_factory(engine)
    app.state.redis = Redis.from_url(settings.redis_url)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()


def _add_docs(app: FastAPI, surface: Surface) -> None:
    openapi_url = f"{surface.prefix}/openapi.json"

    @app.get(openapi_url, include_in_schema=False, tags=[surface.name])
    async def openapi_json() -> dict:
        return surface_openapi(app, surface)

    @app.get(f"{surface.prefix}/docs", include_in_schema=False, tags=[surface.name])
    async def docs() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url=openapi_url, title=f"{app.title} {surface.name}")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Project Template API",
        version="0.1.0",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        generate_unique_id_function=generate_unique_id,
        lifespan=lifespan,
    )
    app.state.settings = settings
    register_error_handlers(app)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    for surface in SURFACES:
        app.include_router(surface.router)
        if settings.env == "dev":
            _add_docs(app, surface)
    app.include_router(health.router)
    return app
