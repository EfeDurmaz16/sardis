"""Tests for GDPR data export endpoints."""

from __future__ import annotations

import pytest

import sardis_api.routers.data_export as _mod


def _reset_stores():
    """Clear in-memory state between tests."""
    _mod._export_store.clear()
    _mod._rate_limit_store.clear()


@pytest.fixture(autouse=True)
def clean_stores():
    _reset_stores()
    yield
    _reset_stores()


@pytest.mark.asyncio
async def test_create_export_returns_export_id(client):
    resp = await client.post("/api/v2/account/export")
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["export_id"].startswith("exp_")
    assert body["status"] == "ready"
    assert body["expires_at"] is not None
    assert body["download_url"] == f"/api/v2/account/export/{body['export_id']}"


@pytest.mark.asyncio
async def test_create_export_rate_limit(client):
    # First request should succeed
    first = await client.post("/api/v2/account/export")
    assert first.status_code == 202

    # Second request within 24 h should be rejected
    second = await client.post("/api/v2/account/export")
    assert second.status_code == 429
    body = second.json()
    assert "export already requested" in body["detail"].lower()


@pytest.mark.asyncio
async def test_get_export_returns_data(client):
    create_resp = await client.post("/api/v2/account/export")
    assert create_resp.status_code == 202
    export_id = create_resp.json()["export_id"]

    get_resp = await client.get(f"/api/v2/account/export/{export_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["export_id"] == export_id
    assert body["status"] == "ready"
    assert "data" in body
    assert "user" in body["data"]
    assert body["data"]["export_format_version"] == "1.0"


@pytest.mark.asyncio
async def test_get_export_not_found(client):
    resp = await client.get("/api/v2/account/export/exp_doesnotexist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_exports(client):
    # No exports yet
    list_resp = await client.get("/api/v2/account/exports")
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    # Create one
    create_resp = await client.post("/api/v2/account/export")
    assert create_resp.status_code == 202
    export_id = create_resp.json()["export_id"]

    # List should now contain it
    list_resp2 = await client.get("/api/v2/account/exports")
    assert list_resp2.status_code == 200
    items = list_resp2.json()
    assert len(items) == 1
    assert items[0]["export_id"] == export_id
    assert items[0]["status"] == "ready"


@pytest.mark.asyncio
async def test_auth_required(app):
    """Unauthenticated requests must be rejected."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as unauthed_client:
        resp = await unauthed_client.post("/api/v2/account/export")
        assert resp.status_code in (401, 403)
