from collections.abc import Awaitable, Callable

import httpx
import pytest

from app.users.models import User

MakeUser = Callable[..., Awaitable[User]]
REGISTER = "/api/v1/users/register"
ME = "/api/v1/users/me"
PASSWORD = "correct horse battery"


async def register(c: httpx.AsyncClient, email: str = "new@example.com", password: str = PASSWORD):
    return await c.post(REGISTER, json={"email": email, "password": password})


async def test_register_201_returns_only_id_and_email(anon_client: httpx.AsyncClient):
    r = await register(anon_client)
    assert r.status_code == 201
    assert set(r.json()) == {"id", "email"}
    assert r.json()["email"] == "new@example.com"


async def test_register_duplicate_409_problem_json(anon_client: httpx.AsyncClient):
    await register(anon_client)
    r = await register(anon_client)
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")


async def test_register_email_case_insensitive_409(anon_client: httpx.AsyncClient):
    await register(anon_client, "new@example.com")
    assert (await register(anon_client, "NEW@Example.com")).status_code == 409


@pytest.mark.parametrize("length", [12, 128])
async def test_register_boundary_password_lengths_ok(anon_client: httpx.AsyncClient, length: int):
    assert (await register(anon_client, password="a" * length)).status_code == 201


async def test_register_short_password_422(anon_client: httpx.AsyncClient):
    assert (await register(anon_client, password="a" * 11)).status_code == 422


async def test_register_129_chars_422(anon_client: httpx.AsyncClient):
    assert (await register(anon_client, password="a" * 129)).status_code == 422


async def test_register_invalid_email_422(anon_client: httpx.AsyncClient):
    assert (await register(anon_client, "not-an-email")).status_code == 422


async def test_register_rate_limited_after_10_per_hour(anon_client: httpx.AsyncClient):
    for i in range(10):
        assert (await register(anon_client, f"u{i}@example.com")).status_code == 201
    r = await register(anon_client, "u10@example.com")
    assert r.status_code == 429
    assert "retry-after" in r.headers


async def test_me_requires_auth_401(anon_client: httpx.AsyncClient):
    assert (await anon_client.get(ME)).status_code == 401


async def test_me_returns_current_user(user_client: httpx.AsyncClient):
    r = await user_client.get(ME)
    assert r.status_code == 200
    assert set(r.json()) == {"id", "email"}
    assert r.json()["email"] == "plain@example.com"
