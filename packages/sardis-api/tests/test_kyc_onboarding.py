"""Tests for self-serve KYC initiation and status endpoints."""
from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _unset_idenfy_key(monkeypatch) -> None:
    """Remove the iDenfy API key from the environment."""
    monkeypatch.delenv("SARDIS_IDENFY_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# POST /api/v2/kyc/initiate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initiate_returns_503_without_idenfy_key(client, monkeypatch):
    """POST /kyc/initiate returns 503 when SARDIS_IDENFY_API_KEY is not set."""
    monkeypatch.delenv("SARDIS_IDENFY_API_KEY", raising=False)

    resp = await client.post("/api/v2/kyc/initiate")
    assert resp.status_code == 503
    body = resp.json()
    assert "SARDIS_IDENFY_API_KEY" in body.get("detail", "")


@pytest.mark.asyncio
async def test_initiate_returns_redirect_when_key_configured(client, monkeypatch):
    """POST /kyc/initiate returns redirect_url and session_token when key is set."""
    monkeypatch.setenv("SARDIS_IDENFY_API_KEY", "test_key_abc123")

    resp = await client.post("/api/v2/kyc/initiate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["redirect_url"] is not None
    assert "idenfy.com" in body["redirect_url"]
    assert body["session_token"] is not None
    assert body["provider"] == "idenfy"
    assert body["message"] != ""


@pytest.mark.asyncio
async def test_initiate_requires_auth(app):
    """POST /kyc/initiate without credentials returns 401 or 403."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as unauthenticated_client:
        resp = await unauthenticated_client.post("/api/v2/kyc/initiate")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/v2/kyc/status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_returns_not_started_by_default(client):
    """GET /kyc/status returns not_started when no verification exists."""
    resp = await client.get("/api/v2/kyc/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "not_started"


@pytest.mark.asyncio
async def test_status_requires_auth(app):
    """GET /kyc/status without credentials returns 401 or 403."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as unauthenticated_client:
        resp = await unauthenticated_client.get("/api/v2/kyc/status")
    assert resp.status_code in (401, 403)
