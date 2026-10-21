from uuid import uuid7

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import iter_route_contexts

from app.api.surfaces import SURFACES, surface_openapi

SURFACE = {s.name: s for s in SURFACES}
AUTH_EXEMPT = {"auth-login", "auth-refresh", "auth-logout"}
ADMIN_SCHEMAS = {
    "ItemAdmin",
    "UserAdmin",
    "AdminTokenResponse",
    "ItemAdminPage",
    "UserAdminPage",
    "UserAdminUpdate",
}
CONTRACT = {
    "admin": {
        "auth-login",
        "auth-refresh",
        "auth-logout",
        "users-me",
        "users-list",
        "users-update",
        "items-list",
        "items-get",
        "items-create",
        "items-update",
        "items-delete",
    },
    "public": {
        "auth-login",
        "auth-refresh",
        "auth-logout",
        "users-register",
        "users-me",
        "items-list",
        "items-get",
    },
}


def protected_admin_requests(app: FastAPI) -> list[tuple[str, str]]:
    # path params are dummy uuids and bodies are {}: auth must reject before validation runs
    out = []
    for ctx in iter_route_contexts(app.routes):
        if not (ctx.path or "").startswith("/api/admin/") or ctx.unique_id in AUTH_EXEMPT:
            continue
        path = (
            (ctx.path or "").replace("{user_id}", str(uuid7())).replace("{item_id}", str(uuid7()))
        )
        out.extend((m, path) for m in sorted(ctx.methods or ()))
    return out


async def test_admin_routes_anonymous_401(app: FastAPI, anon_client: httpx.AsyncClient):
    checked = protected_admin_requests(app)
    assert len(checked) >= 8
    for method, path in checked:
        r = await anon_client.request(method, path, json={})
        assert r.status_code == 401, (method, path)


async def test_admin_routes_role_user_403(app: FastAPI, user_client: httpx.AsyncClient):
    checked = protected_admin_requests(app)
    assert len(checked) >= 8
    for method, path in checked:
        r = await user_client.request(method, path, json={})
        assert r.status_code == 403, (method, path)


def test_public_json_has_no_admin_path(app: FastAPI):
    public = surface_openapi(app, SURFACE["public"])["paths"]
    assert public
    assert all("/admin" not in p and p.startswith("/api/v1") for p in public)
    admin = surface_openapi(app, SURFACE["admin"])["paths"]
    assert admin
    assert all(p.startswith("/api/admin") for p in admin)


def test_public_spec_has_no_admin_schemas(app: FastAPI):
    spec = surface_openapi(app, SURFACE["public"])
    assert not ADMIN_SCHEMAS & set(spec["components"]["schemas"])


@pytest.mark.parametrize("name", ["admin", "public"])
def test_operation_ids_match_contract(app: FastAPI, name: str):
    paths = surface_openapi(app, SURFACE[name])["paths"]
    ids = {op["operationId"] for item in paths.values() for op in item.values()}
    assert ids == CONTRACT[name]


@pytest.mark.parametrize("name", ["admin", "public"])
def test_schema_names_clean(app: FastAPI, name: str):
    names = surface_openapi(app, SURFACE[name])["components"]["schemas"]
    assert not [n for n in names if n.endswith(("-Input", "-Output"))]


def test_every_route_has_exactly_one_tag_and_name_set(app: FastAPI):
    seen = 0
    for ctx in iter_route_contexts(app.routes):
        if (
            not (ctx.path or "").startswith(("/api/admin/", "/api/v1/"))
            or not ctx.include_in_schema
        ):
            continue
        seen += 1
        assert len(ctx.tags) == 1, ctx.path
        assert ctx.name, ctx.path
        assert ctx.unique_id == f"{ctx.tags[0]}-{ctx.name}", ctx.path
    assert seen >= 15
