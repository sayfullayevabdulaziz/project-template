from collections.abc import Awaitable, Callable
from uuid import uuid4

import httpx

from app.users.models import Role, User

MakeUser = Callable[..., Awaitable[User]]
BASE = "/api/admin/users"


async def my_id(c: httpx.AsyncClient) -> str:
    return (await c.get(f"{BASE}/me")).json()["id"]


async def test_admin_me_has_role_active_created_at(admin_client: httpx.AsyncClient):
    body = (await admin_client.get(f"{BASE}/me")).json()
    assert body["role"] == "admin"
    assert body["is_active"] is True
    assert body["created_at"]


async def test_list_users_pagination_total(admin_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("a@example.com")
    await make_user("b@example.com")
    body = (await admin_client.get(BASE, params={"limit": 1})).json()
    assert len(body["items"]) == 1
    assert body["total"] == 3


async def test_list_sort_and_q(admin_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("alpha@example.com")
    await make_user("beta@example.com")
    r = await admin_client.get(BASE, params={"sort": "email"})
    emails = [u["email"] for u in r.json()["items"]]
    assert emails == sorted(emails)
    r = await admin_client.get(BASE, params={"q": "BETA"})
    assert [u["email"] for u in r.json()["items"]] == ["beta@example.com"]


async def test_list_invalid_sort_422(admin_client: httpx.AsyncClient):
    assert (await admin_client.get(BASE, params={"sort": "password_hash"})).status_code == 422


async def test_list_limit_101_422(admin_client: httpx.AsyncClient):
    assert (await admin_client.get(BASE, params={"limit": 101})).status_code == 422


async def test_non_admin_403_and_anon_401(
    user_client: httpx.AsyncClient, anon_client: httpx.AsyncClient
):
    assert (await user_client.get(BASE)).status_code == 403
    assert (await anon_client.get(BASE)).status_code == 401


async def test_patch_promotes_user(admin_client: httpx.AsyncClient, make_user: MakeUser):
    user = await make_user("u@example.com")
    r = await admin_client.patch(f"{BASE}/{user.id}", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


async def test_patch_self_demote_409(admin_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("other-admin@example.com", role=Role.admin)
    r = await admin_client.patch(f"{BASE}/{await my_id(admin_client)}", json={"role": "user"})
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")


async def test_patch_self_deactivate_409(admin_client: httpx.AsyncClient, make_user: MakeUser):
    await make_user("other-admin@example.com", role=Role.admin)
    r = await admin_client.patch(f"{BASE}/{await my_id(admin_client)}", json={"is_active": False})
    assert r.status_code == 409


# The last-admin rule is covered at service level only (tests/users/test_service.py).
async def test_patch_sole_admin_self_409(admin_client: httpx.AsyncClient):
    r = await admin_client.patch(f"{BASE}/{await my_id(admin_client)}", json={"role": "user"})
    assert r.status_code == 409
    assert "yourself" in r.json()["detail"]


async def test_patch_unknown_user_404(admin_client: httpx.AsyncClient):
    r = await admin_client.patch(f"{BASE}/{uuid4()}", json={"is_active": False})
    assert r.status_code == 404


async def test_patch_malformed_uuid_422(admin_client: httpx.AsyncClient):
    assert (await admin_client.patch(f"{BASE}/nope", json={})).status_code == 422


async def test_patch_invalid_role_422(admin_client: httpx.AsyncClient, make_user: MakeUser):
    user = await make_user("u@example.com")
    assert (await admin_client.patch(f"{BASE}/{user.id}", json={"role": "root"})).status_code == 422
