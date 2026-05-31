"""Tests that swap/exchange/verification endpoints require authentication.

These are money-moving endpoints — unauthenticated requests must return 401,
not 200/422/502.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from server.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def authed_client(app):
    """Client with valid test API key."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "sk_test_demo123"},  # nosecret: test-only dummy key
    ) as ac:
        yield ac


@pytest.fixture
async def anon_client(app):
    """Client with NO auth headers — must be rejected by authn-gated endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Unauthenticated requests must return 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_swap_execute_requires_auth(anon_client):
    """POST /api/v2/swap/execute with no auth → 401."""
    resp = await anon_client.post(
        "/api/v2/swap/execute",
        json={"quote_id": "test-quote-id"},
    )
    assert resp.status_code == 401, (
        f"Expected 401 but got {resp.status_code}. "
        "swap/execute is moving real money and must require authentication."
    )


@pytest.mark.asyncio
async def test_swap_quote_requires_auth(anon_client):
    """POST /api/v2/swap/quote with no auth → 401."""
    resp = await anon_client.post(
        "/api/v2/swap/quote",
        json={
            "from_token": "USDC",
            "to_token": "EURC",
            "amount": "100",
            "chain": "base",
        },
    )
    assert resp.status_code == 401, (
        f"Expected 401 but got {resp.status_code}. "
        "swap/quote reveals pricing data and must require authentication."
    )


@pytest.mark.asyncio
async def test_exchange_trade_requires_auth(anon_client):
    """POST /api/v2/exchange/trade with no auth → 401."""
    resp = await anon_client.post(
        "/api/v2/exchange/trade",
        json={"quote_id": "test-quote-id"},
    )
    assert resp.status_code == 401, (
        f"Expected 401 but got {resp.status_code}. "
        "exchange/trade executes real trades and must require authentication."
    )


@pytest.mark.asyncio
async def test_exchange_quote_requires_auth(anon_client):
    """POST /api/v2/exchange/quote with no auth → 401."""
    resp = await anon_client.post(
        "/api/v2/exchange/quote",
        json={
            "from_currency": "USDC",
            "to_currency": "EURC",
            "amount": "100",
        },
    )
    assert resp.status_code == 401, (
        f"Expected 401 but got {resp.status_code}. "
        "exchange/quote must require authentication."
    )


@pytest.mark.asyncio
async def test_exchange_settlements_requires_auth(anon_client):
    """GET /api/v2/exchange/settlements with no auth → 401."""
    resp = await anon_client.get("/api/v2/exchange/settlements")
    assert resp.status_code == 401, (
        f"Expected 401 but got {resp.status_code}. "
        "exchange/settlements exposes financial data and must require authentication."
    )


@pytest.mark.asyncio
async def test_verifications_requires_auth(anon_client):
    """GET /api/v2/verifications/{address} with no auth → 401."""
    resp = await anon_client.get("/api/v2/verifications/0xdeadbeef")
    assert resp.status_code == 401, (
        f"Expected 401 but got {resp.status_code}. "
        "verifications/{address} must require authentication."
    )


# ---------------------------------------------------------------------------
# Authenticated requests must NOT return 401/403 (auth layer passes through)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_swap_execute_accepts_valid_auth(authed_client):
    """POST /api/v2/swap/execute with valid auth must not return 401/403."""
    resp = await authed_client.post(
        "/api/v2/swap/execute",
        json={"quote_id": "test-quote-id"},
    )
    # We expect 5xx (no real CDP configured) or 422, but NOT 401/403
    assert resp.status_code not in (401, 403), (
        f"Authenticated request was rejected with {resp.status_code}. "
        "A valid API key should pass the auth layer."
    )


@pytest.mark.asyncio
async def test_exchange_trade_accepts_valid_auth(authed_client):
    """POST /api/v2/exchange/trade with valid auth must not return 401/403."""
    resp = await authed_client.post(
        "/api/v2/exchange/trade",
        json={"quote_id": "test-quote-id"},
    )
    assert resp.status_code not in (401, 403), (
        f"Authenticated request was rejected with {resp.status_code}."
    )
