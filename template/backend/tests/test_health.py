from redis.asyncio import Redis


async def test_live_ok(anon_client):
    r = await anon_client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_ready_ok_when_db_and_redis_up(anon_client):
    r = await anon_client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_ready_503_when_redis_down(app, anon_client):
    app.state.redis = Redis.from_url("redis://127.0.0.1:1")
    r = await anon_client.get("/health/ready")
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")
    assert "redis" in r.json()["detail"]
