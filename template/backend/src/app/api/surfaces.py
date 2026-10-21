from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, iter_route_contexts

from app.api.admin import router as admin_router
from app.api.public import router as public_router


@dataclass(frozen=True)
class Surface:
    name: str
    prefix: str
    router: APIRouter


def generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


def surface_openapi(app: FastAPI, surface: Surface) -> dict[str, Any]:
    prefix = surface.prefix + "/"
    return get_openapi(
        title=f"{app.title} {surface.name}",
        version=app.version,
        # FastAPI 0.150 wraps included routers lazily; iter_route_contexts flattens them.
        routes=[r for r in iter_route_contexts(app.routes) if (r.path or "").startswith(prefix)],
        separate_input_output_schemas=False,
    )


SURFACES: list[Surface] = [
    Surface("admin", "/api/admin", admin_router),
    Surface("public", "/api/v1", public_router),
]
