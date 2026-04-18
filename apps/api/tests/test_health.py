import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_ping(client):
    resp = await client.get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"pong": True}
