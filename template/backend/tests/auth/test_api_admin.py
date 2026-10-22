from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import iter_route_contexts

from app.core.config import Settings
from app.core.deps import require_admin
from app.main import create_app
from app.users.models import Role, User

MakeUser = Callable[..., Awaitable[User]]
PASSWORD = "correct horse battery"
LOGIN = "/api/admin/auth/login"
REFRESH = "/api/admin/auth/refresh"
LOGOUT = "/api/admin/auth/logout"


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    # https so the Secure cookie is replayed
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as c:
        yield c


async def login(c: httpx.AsyncClient, email: str = "admin@example.com", password: str = PASSWORD):
    return await c.post(LOGIN, json={"email": email, "password": password})


def cookie_attrs(r: httpx.Response) -> list[str]:
    return [p.strip().lower() for p in r.headers["set-cookie"].split(";")]


async def test_admin_login_sets_cookie_with_exact_attributes(
    client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user("admin@example.com", role=Role.admin)
    r = await login(client)
    assert r.status_code == 200
    attrs = cookie_attrs(r)
    assert attrs[0].startswith("refresh_token=")
    assert {
        "httponly",
        "secure",
        "samesite=strict",
        "path=/api/admin/auth",
        "max-age=2592000",
    } <= set(attrs)
    body = r.json()
    assert "refresh_token" not in body
    assert body["access_token"]
    assert r.headers["cache-control"] == "no-store"


async def test_cookie_not_secure_when_setting_false(
    app: FastAPI, client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user("admin@example.com", role=Role.admin)
    insecure = create_app(
        Settings.model_validate({**app.state.settings.model_dump(), "cookie_secure": False})
    )
    insecure.state.session_factory = app.state.session_factory
    insecure.state.redis = app.state.redis
    insecure.dependency_overrides = app.dependency_overrides
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=insecure), base_url="http://test"
    ) as c:
        r = await login(c)
    assert r.status_code == 200
    assert "secure" not in cookie_attrs(r)


async def test_admin_login_non_admin_403(client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("plain@example.com")
    r = await login(client, "plain@example.com")
    assert r.status_code == 403
    assert "set-cookie" not in r.headers


async def test_admin_login_bad_password_401(client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("admin@example.com", role=Role.admin)
    assert (await login(client, password="wrong password")).status_code == 401


async def test_admin_refresh_rotates_cookie_and_returns_new_access(
    client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user("admin@example.com", role=Role.admin)
    await login(client)
    old = client.cookies["refresh_token"]
    r = await client.post(REFRESH)
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert "refresh_token" not in r.json()
    assert r.headers["cache-control"] == "no-store"
    assert client.cookies["refresh_token"] != old


async def test_admin_refresh_reuse_revokes_family(client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("admin@example.com", role=Role.admin)
    await login(client)
    first = client.cookies["refresh_token"]
    assert (await client.post(REFRESH)).status_code == 200
    replay = await client.post(REFRESH, headers={"Cookie": f"refresh_token={first}"})
    assert replay.status_code == 401
    assert (await client.post(REFRESH)).status_code == 401  # live cookie died with the family


async def test_admin_refresh_without_cookie_401(client: httpx.AsyncClient):
    r = await client.post(REFRESH)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


async def test_admin_logout_works_without_admin_access_token(
    client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user("admin@example.com", role=Role.admin)
    await login(client)
    raw = client.cookies["refresh_token"]
    r = await client.post(LOGOUT)  # no Authorization header at all
    assert r.status_code == 204
    attrs = cookie_attrs(r)
    assert "max-age=0" in attrs or any(a.startswith("expires=") for a in attrs)
    assert "path=/api/admin/auth" in attrs
    assert "refresh_token" not in client.cookies
    r2 = await client.post(REFRESH, headers={"Cookie": f"refresh_token={raw}"})
    assert r2.status_code == 401


async def test_admin_login_rate_limited(client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("admin@example.com", role=Role.admin)
    for _ in range(5):
        assert (await login(client, password="wrong password")).status_code == 401
    r = await login(client)
    assert r.status_code == 429
    assert "retry-after" in r.headers


async def test_cross_transport_same_service(
    client: httpx.AsyncClient, anon_client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user("admin@example.com", role=Role.admin)
    pub = await anon_client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD}
    )
    raw = pub.json()["refresh_token"]
    out = await anon_client.post("/api/v1/auth/logout", json={"refresh_token": raw})
    assert out.status_code == 204
    r = await client.post(REFRESH, headers={"Cookie": f"refresh_token={raw}"})
    assert r.status_code == 401


def test_every_admin_route_but_auth_requires_admin(app: FastAPI):
    exempt = {"auth-login", "auth-refresh", "auth-logout"}
    seen = set()
    for ctx in iter_route_contexts(app.routes):
        if not (ctx.path or "").startswith("/api/admin/") or not ctx.include_in_schema:
            continue
        if ctx.unique_id in exempt:
            seen.add(ctx.unique_id)
        else:
            assert require_admin in _all_calls(ctx.dependant), ctx.path
    assert seen == exempt


def _all_calls(dependant: Dependant) -> set:
    calls = {dependant.call}
    for sub in dependant.dependencies:
        calls |= _all_calls(sub)
    return calls
