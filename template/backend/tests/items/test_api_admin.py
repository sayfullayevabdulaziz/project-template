import httpx

BASE = "/api/admin/items"
FIELDS = {"id", "name", "description", "is_published", "created_by_id", "created_at", "updated_at"}


async def create(c: httpx.AsyncClient, **body) -> httpx.Response:
    return await c.post(BASE, json={"name": "thing", **body})


async def test_crud_flow(admin_client: httpx.AsyncClient):
    r = await create(admin_client, description="d")
    assert r.status_code == 201
    item = r.json()
    assert item["is_published"] is False
    url = f"{BASE}/{item['id']}"
    assert (await admin_client.get(url)).json()["name"] == "thing"
    r = await admin_client.patch(url, json={"name": "renamed", "is_published": True})
    assert r.status_code == 200
    assert (r.json()["name"], r.json()["description"], r.json()["is_published"]) == (
        "renamed",
        "d",
        True,
    )
    listed = (await admin_client.get(BASE)).json()
    assert [i["id"] for i in listed["items"]] == [item["id"]]
    assert listed["total"] == 1
    assert (await admin_client.delete(url)).status_code == 204
    assert (await admin_client.get(url)).status_code == 404


async def test_patch_description_null_clears(admin_client: httpx.AsyncClient):
    item = (await create(admin_client, description="d")).json()
    r = await admin_client.patch(f"{BASE}/{item['id']}", json={"description": None})
    assert r.json()["description"] is None


async def test_list_sees_unpublished_and_filters_q(admin_client: httpx.AsyncClient):
    await create(admin_client, name="Alpha")
    await create(admin_client, name="Beta", is_published=True)
    body = (await admin_client.get(BASE, params={"q": "alp"})).json()
    assert [i["name"] for i in body["items"]] == ["Alpha"]
    assert (await admin_client.get(BASE)).json()["total"] == 2


async def test_create_name_empty_422(admin_client: httpx.AsyncClient):
    assert (await create(admin_client, name="")).status_code == 422


async def test_name_length_limits(admin_client: httpx.AsyncClient):
    assert (await create(admin_client, name="x" * 201)).status_code == 422
    assert (await create(admin_client, name="x" * 200)).status_code == 201


async def test_description_2001_422(admin_client: httpx.AsyncClient):
    assert (await create(admin_client, description="x" * 2001)).status_code == 422
    assert (await create(admin_client, description="x" * 2000)).status_code == 201


async def test_delete_unknown_404(admin_client: httpx.AsyncClient):
    r = await admin_client.delete(f"{BASE}/019f0000-0000-7000-8000-000000000000")
    assert r.status_code == 404


async def test_item_id_malformed_422(admin_client: httpx.AsyncClient):
    assert (await admin_client.get(f"{BASE}/not-a-uuid")).status_code == 422
    assert (await admin_client.patch(f"{BASE}/not-a-uuid", json={})).status_code == 422
    assert (await admin_client.delete(f"{BASE}/not-a-uuid")).status_code == 422


async def test_response_has_admin_fields(admin_client: httpx.AsyncClient):
    me = (await admin_client.get("/api/admin/users/me")).json()
    body = (await create(admin_client)).json()
    assert set(body) == FIELDS
    assert body["created_by_id"] == me["id"]


async def test_non_admin_403_and_anon_401(
    user_client: httpx.AsyncClient, anon_client: httpx.AsyncClient
):
    assert (await user_client.get(BASE)).status_code == 403
    assert (await anon_client.get(BASE)).status_code == 401
