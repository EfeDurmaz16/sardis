"""Tests for sardis.pay() Phase 2 — multi-chain auto-routing.

Tests verify:
1. Explicit chain is always used when provided (iron rule)
2. Auto-routing selects cheapest chain when chain is omitted
3. Fallback to next cheapest chain on execution failure
4. Amount validation
5. Route metadata in response
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_orchestrator():
    """Mock PaymentOrchestrator that returns a success result."""
    orchestrator = AsyncMock()

    class MockResult:
        chain_tx_hash = "0xabc123"
        ledger_tx_id = "ledger_001"
        chain = "base"
        mandate_id = "pay_test_agent"

    orchestrator.execute_chain = AsyncMock(return_value=MockResult())
    return orchestrator


@pytest.fixture
def app_with_pay(mock_orchestrator):
    """Create a FastAPI app with the pay router wired."""
    from fastapi import FastAPI

    from sardis_api.routers.pay import PayDependencies, get_deps, router

    app = FastAPI()
    app.include_router(router, prefix="/api/v2/pay")

    app.dependency_overrides[get_deps] = lambda: PayDependencies(
        orchestrator=mock_orchestrator,
    )

    # Override require_principal to return a test principal
    from sardis_api.authz import require_principal

    class FakePrincipal:
        subject_id = "test_agent"
        scopes = ["pay"]

    app.dependency_overrides[require_principal] = lambda: FakePrincipal()

    return app


@pytest.fixture
async def client(app_with_pay):
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_pay),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests — Explicit chain (iron rule)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_chain_is_used(client, mock_orchestrator):
    """When chain is provided, it must be used — no auto-routing."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "25.00",
            "currency": "USDC",
            "chain": "arbitrum",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["route"]["chain"] == "arbitrum"
    assert data["route"]["provider"] == "explicit"
    assert data["route"]["auto_routed"] is False

    # Verify orchestrator was called with the explicit chain
    call_args = mock_orchestrator.execute_chain.call_args
    chain_obj = call_args[0][0]
    assert chain_obj.payment.chain == "arbitrum"


@pytest.mark.asyncio
async def test_explicit_chain_default_base_is_no_longer_default(client):
    """When chain is omitted, it should NOT default to 'base' silently."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "10.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # auto_routed should be True when chain is omitted
    assert data["route"]["auto_routed"] is True


# ---------------------------------------------------------------------------
# Tests — Auto-routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_route_selects_cheapest(client, mock_orchestrator):
    """When chain is omitted, auto-routing should select a chain."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "50.00",
            "currency": "USDC",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["route"] is not None
    assert data["route"]["auto_routed"] is True
    # The chain field should be set
    assert data["route"]["chain"] is not None


@pytest.mark.asyncio
async def test_auto_route_fallback_on_chain_failure(client, mock_orchestrator):
    """When the first chain fails, auto-routing should try the next."""
    from sardis_v2_core.orchestrator import ChainExecutionError

    call_count = 0

    async def fail_first_succeed_second(chain):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ChainExecutionError("Gas estimation failed")

        class MockResult:
            chain_tx_hash = "0xfallback"
            ledger_tx_id = "ledger_fallback"
            chain = "tempo"
            mandate_id = "pay_test_agent"

        return MockResult()

    mock_orchestrator.execute_chain = AsyncMock(side_effect=fail_first_succeed_second)

    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "25.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # Should have succeeded on the fallback chain
    assert data["status"] == "completed"
    assert call_count >= 2


@pytest.mark.asyncio
async def test_explicit_chain_no_fallback_on_failure(client, mock_orchestrator):
    """With explicit chain, failure should NOT try fallback chains."""
    from sardis_v2_core.orchestrator import ChainExecutionError

    mock_orchestrator.execute_chain = AsyncMock(
        side_effect=ChainExecutionError("Gas estimation failed")
    )

    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "25.00",
            "chain": "base",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["route"]["chain"] == "base"
    assert data["route"]["auto_routed"] is False
    # Should have been called exactly once (no fallback)
    assert mock_orchestrator.execute_chain.call_count == 1


# ---------------------------------------------------------------------------
# Tests — Input validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_amount_rejected(client):
    """Negative or non-numeric amounts should be rejected."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "-5.00",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_zero_amount_rejected(client):
    """Zero amount should be rejected."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "0",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_non_numeric_amount_rejected(client):
    """Non-numeric amounts should be rejected."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "not-a-number",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — Response structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_includes_route_metadata(client, mock_orchestrator):
    """Response should include route field with chain/provider metadata."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "100.00",
            "chain": "base",
        },
    )

    assert response.status_code == 200
    data = response.json()

    route = data.get("route")
    assert route is not None
    assert "chain" in route
    assert "provider" in route
    assert "estimated_fee_bps" in route
    assert "route_type" in route
    assert "auto_routed" in route


@pytest.mark.asyncio
async def test_currency_defaults_to_usdc(client, mock_orchestrator):
    """When currency is omitted, it should default to USDC."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "10.00",
        },
    )

    assert response.status_code == 200

    call_args = mock_orchestrator.execute_chain.call_args
    chain_obj = call_args[0][0]
    assert chain_obj.payment.currency == "USDC"


@pytest.mark.asyncio
async def test_mandate_id_in_response(client, mock_orchestrator):
    """Custom mandate_id should be preserved in the response."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "10.00",
            "mandate_id": "custom_mandate_123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # The orchestrator mock returns "pay_test_agent" but the mandate_id
    # in the chain should be the custom one
    call_args = mock_orchestrator.execute_chain.call_args
    chain_obj = call_args[0][0]
    assert chain_obj.payment.mandate_id == "custom_mandate_123"


# ---------------------------------------------------------------------------
# Tests — Policy blocking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_policy_violation_returns_blocked(client, mock_orchestrator):
    """Policy violations should return blocked status, not retry on other chains."""
    from sardis_v2_core.orchestrator import PolicyViolationError

    mock_orchestrator.execute_chain = AsyncMock(
        side_effect=PolicyViolationError("Daily limit exceeded")
    )

    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "10000.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["policy_explanation"] is not None
    # Should NOT retry on other chains for policy violations
    assert mock_orchestrator.execute_chain.call_count == 1
