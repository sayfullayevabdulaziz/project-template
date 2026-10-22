from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import iter_route_contexts

from app.core.db import get_session


def _session_deps(dep: Dependant) -> list[Dependant]:
    found = [dep] if dep.call is get_session else []
    for sub in dep.dependencies:
        found.extend(_session_deps(sub))
    return found


def test_get_session_is_function_scoped_on_every_api_route(app: FastAPI):
    # Request scope would commit after the response is sent: the client could read stale state.
    per_surface: dict[str, int] = {"/api/admin/": 0, "/api/v1/": 0}
    for ctx in iter_route_contexts(app.routes):
        path = ctx.path or ""
        for prefix in per_surface:
            if path.startswith(prefix):
                deps = _session_deps(ctx.dependant)
                per_surface[prefix] += len(deps)
                assert all(d.scope == "function" for d in deps), path
    assert all(n >= 8 for n in per_surface.values()), per_surface
