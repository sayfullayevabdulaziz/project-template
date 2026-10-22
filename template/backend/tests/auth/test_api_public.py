from collections.abc import Awaitable, Callable

import httpx

from app.users.models import User

MakeUser = Callable[..., Awaitable[User]]
PASSWORD = "correct horse battery"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"


async def login(c: httpx.AsyncClient, email: str = "user@example.com", password: str = PASSWORD):
    return await c.post(LOGIN, json={"email": email, "password": password})


async def test_login_returns_token_pair(anon_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user()
    r = await login(anon_client)
    assert r.status_code == 200
    body = r.json()
    assert body["expires_in"] == 900
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert r.headers["cache-control"] == "no-store"


async def test_login_bad_password_401(anon_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user()
    r = await login(anon_client, password="wrong password")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert r.headers["content-type"].startswith("application/problem+json")


async def test_login_inactive_401(anon_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user(is_active=False)
    assert (await login(anon_client)).status_code == 401


async def test_refresh_rotates_and_old_token_reuse_401_and_revokes_family(
    anon_client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user()
    first = (await login(anon_client)).json()["refresh_token"]
    r = await anon_client.post(REFRESH, json={"refresh_token": first})
    assert r.status_code == 200
    second = r.json()["refresh_token"]
    assert second != first
    assert (await anon_client.post(REFRESH, json={"refresh_token": first})).status_code == 401
    assert (await anon_client.post(REFRESH, json={"refresh_token": second})).status_code == 401


async def test_logout_204_then_refresh_401(anon_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user()
    raw = (await login(anon_client)).json()["refresh_token"]
    r = await anon_client.post(LOGOUT, json={"refresh_token": raw})
    assert r.status_code == 204
    assert r.content == b""
    assert (await anon_client.post(REFRESH, json={"refresh_token": raw})).status_code == 401


async def test_refresh_garbage_401(anon_client: httpx.AsyncClient):
    r = await anon_client.post(REFRESH, json={"refresh_token": "garbage"})
    assert r.status_code == 401


async def test_refresh_empty_body_422(anon_client: httpx.AsyncClient):
    assert (await anon_client.post(REFRESH, json={})).status_code == 422


async def test_login_rate_limited_after_5_attempts(
    anon_client: httpx.AsyncClient, make_user: MakeUser
):
    await make_user()
    for _ in range(5):
        assert (await login(anon_client, password="wrong password")).status_code == 401
    r = await login(anon_client)  # valid password, still blocked
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) > 0


async def test_login_rate_limit_is_per_email(anon_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user()
    for _ in range(5):
        await login(anon_client, password="wrong password")
    assert (await login(anon_client)).status_code == 429
    assert (await login(anon_client, "other@example.com")).status_code == 401


async def test_login_password_over_128_is_422(anon_client: httpx.AsyncClient):
    assert (await login(anon_client, password="x" * 129)).status_code == 422
