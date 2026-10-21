from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute, iter_route_contexts


@dataclass(frozen=True)
class Surface:
    name: str
    prefix: str
    router: APIRouter


def tag_surface(name: str):
    """Stub dependency factory; Task 15 replaces it with the real surface tagging."""

    def _tag() -> None:
        return None

    return _tag


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


# Imported last: the surface routers need tag_surface defined above.
from app.api.admin import router as admin_router  # noqa: E402
from app.api.public import router as public_router  # noqa: E402

SURFACES: list[Surface] = [
    Surface("admin", "/api/admin", admin_router),
    Surface("public", "/api/v1", public_router),
]
