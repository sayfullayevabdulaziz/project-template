from datetime import timedelta
from typing import Annotated

import pytest
from fastapi import Depends

from app.core.deps import CurrentUser, require_admin
from app.users.models import Role, User


@pytest.fixture(autouse=True)
def _scratch_routes(app):
    @app.get("/_t/me", tags=["t"])
    async def me(user: CurrentUser) -> dict[str, str]:
        return {"email": user.email}

    @app.get("/_t/admin", tags=["t"])
    async def admin_only(user: Annotated[User, Depends(require_admin)]) -> dict[str, str]:
        return {"email": user.email}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_no_header_401_with_www_authenticate(anon_client):
    r = await anon_client.get("/_t/me")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


async def test_garbage_bearer_401(anon_client):
    r = await anon_client.get("/_t/me", headers=bearer("garbage"))
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


async def test_expired_token_401(anon_client, make_user, make_token):
    user = await make_user()
    token = make_token(user, ttl=timedelta(seconds=-10))
    assert (await anon_client.get("/_t/me", headers=bearer(token))).status_code == 401


async def test_deleted_user_401(anon_client, make_user, make_token, session):
    user = await make_user()
    token = make_token(user)
    await session.delete(user)
    await session.flush()
    assert (await anon_client.get("/_t/me", headers=bearer(token))).status_code == 401


async def test_inactive_user_401(anon_client, make_user, make_token):
    user = await make_user(is_active=False)
    r = await anon_client.get("/_t/me", headers=bearer(make_token(user)))
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


async def test_user_role_on_admin_route_403(user_client):
    assert (await user_client.get("/_t/admin")).status_code == 403


async def test_admin_200(admin_client):
    r = await admin_client.get("/_t/admin")
    assert r.status_code == 200
    assert r.json() == {"email": "admin@example.com"}


async def test_role_read_from_db_not_claim(anon_client, make_user, make_token):
    user = await make_user(role=Role.user)
    token = make_token(user, role="admin")
    assert (await anon_client.get("/_t/admin", headers=bearer(token))).status_code == 403
