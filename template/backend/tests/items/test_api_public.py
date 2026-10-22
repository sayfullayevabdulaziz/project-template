import httpx

ADMIN = "/api/admin/items"
BASE = "/api/v1/items"


async def make_item(admin: httpx.AsyncClient, name: str, *, published: bool) -> dict:
    r = await admin.post(ADMIN, json={"name": name, "description": "d", "is_published": published})
    assert r.status_code == 201
    return r.json()


async def test_list_returns_only_published(
    admin_client: httpx.AsyncClient, user_client: httpx.AsyncClient
):
    await make_item(admin_client, "pub", published=True)
    await make_item(admin_client, "draft", published=False)
    body = (await user_client.get(BASE)).json()
    assert [i["name"] for i in body["items"]] == ["pub"]


async def test_list_item_keys_exactly_id_name_description(
    admin_client: httpx.AsyncClient, user_client: httpx.AsyncClient
):
    await make_item(admin_client, "pub", published=True)
    item = (await user_client.get(BASE)).json()["items"][0]
    assert set(item) == {"id", "name", "description"}
    detail = (await user_client.get(f"{BASE}/{item['id']}")).json()
    assert set(detail) == {"id", "name", "description"}


async def test_detail_unpublished_404(
    admin_client: httpx.AsyncClient, user_client: httpx.AsyncClient
):
    draft = await make_item(admin_client, "draft", published=False)
    assert (await user_client.get(f"{BASE}/{draft['id']}")).status_code == 404
    assert (
        await user_client.get(f"{BASE}/019f0000-0000-7000-8000-000000000000")
    ).status_code == 404
    assert (await user_client.get(f"{BASE}/not-a-uuid")).status_code == 422


async def test_unpublishing_hides_from_list_and_detail(
    admin_client: httpx.AsyncClient, user_client: httpx.AsyncClient
):
    item = await make_item(admin_client, "pub", published=True)
    assert (await user_client.get(f"{BASE}/{item['id']}")).status_code == 200
    await admin_client.patch(f"{ADMIN}/{item['id']}", json={"is_published": False})
    assert (await user_client.get(f"{BASE}/{item['id']}")).status_code == 404
    assert (await user_client.get(BASE)).json() == {"items": [], "total": 0}


async def test_public_requires_auth_401(
    anon_client: httpx.AsyncClient, admin_client: httpx.AsyncClient
):
    item = await make_item(admin_client, "pub", published=True)
    assert (await anon_client.get(BASE)).status_code == 401
    assert (await anon_client.get(f"{BASE}/{item['id']}")).status_code == 401


async def test_public_pagination_total_counts_only_published(
    admin_client: httpx.AsyncClient, user_client: httpx.AsyncClient
):
    for i in range(3):
        await make_item(admin_client, f"pub{i}", published=True)
    await make_item(admin_client, "draft", published=False)
    body = (await user_client.get(BASE, params={"limit": 2})).json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
