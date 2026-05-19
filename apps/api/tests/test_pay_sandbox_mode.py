"""Tests for server.pay() sandbox/simulated mode.

When chain_mode != "live", the /pay endpoint returns a simulated successful
payment without hitting the orchestrator or requiring funded wallets.

Tests verify:
1. Simulated mode returns completed status with simulated=True
2. Amount and currency validation still runs in simulated mode
3. Explicit chain is reflected in simulated response
4. Auto-routed (no chain) defaults to "base" in simulated response
5. Mandate ID is passed through in simulated response
6. Live mode (chain_mode="live") falls through to the orchestrator
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stub mandates — same pattern as test_pay_phase2_routing.py
# ---------------------------------------------------------------------------


class StubMandate:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class StubMandateChain:
    def __init__(self, intent=None, cart=None, payment=None):
        self.intent = intent
        self.cart = cart
        self.payment = payment


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakePrincipal:
    subject_id = "test_agent"
    user_id = "test_agent"
    organization_id = "test_org"
    scopes = ["pay"]
    kind = "api_key"
    user = None
    api_key = None


@pytest.fixture
def mock_orchestrator():
    orchestrator = AsyncMock()

    class MockResult:
        chain_tx_hash = "0xreal_abc123"
        ledger_tx_id = "ledger_real_001"
        chain = "base"
        mandate_id = "pay_test_agent"

    orchestrator.execute_chain = AsyncMock(return_value=MockResult())
    return orchestrator


@pytest.fixture
def app_sandbox(mock_orchestrator):
    """App with chain_mode='simulated' (sandbox mode)."""
    from unittest.mock import patch

    with patch("server.routes.money_movement.pay.IntentMandate", StubMandate), \
         patch("server.routes.money_movement.pay.CartMandate", StubMandate), \
         patch("server.routes.money_movement.pay.PaymentMandate", StubMandate), \
         patch("server.routes.money_movement.pay.MandateChain", StubMandateChain):

        from fastapi import FastAPI

        from server.authz import require_principal
        from server.routes.money_movement.pay import PayDependencies, get_deps, router

        app = FastAPI()
        app.include_router(router, prefix="/api/v2/pay")

        app.dependency_overrides[get_deps] = lambda: PayDependencies(
            orchestrator=mock_orchestrator,
            chain_mode="simulated",
        )
        app.dependency_overrides[require_principal] = lambda: FakePrincipal()

        yield app


@pytest.fixture
def app_live(mock_orchestrator):
    """App with chain_mode='live' (live mode)."""
    from unittest.mock import patch

    with patch("server.routes.money_movement.pay.IntentMandate", StubMandate), \
         patch("server.routes.money_movement.pay.CartMandate", StubMandate), \
         patch("server.routes.money_movement.pay.PaymentMandate", StubMandate), \
         patch("server.routes.money_movement.pay.MandateChain", StubMandateChain):

        from fastapi import FastAPI

        from server.authz import require_principal
        from server.routes.money_movement.pay import PayDependencies, get_deps, router

        app = FastAPI()
        app.include_router(router, prefix="/api/v2/pay")

        app.dependency_overrides[get_deps] = lambda: PayDependencies(
            orchestrator=mock_orchestrator,
            chain_mode="live",
        )
        app.dependency_overrides[require_principal] = lambda: FakePrincipal()

        yield app


@pytest.fixture
async def sandbox_client(app_sandbox):
    async with AsyncClient(
        transport=ASGITransport(app=app_sandbox),
        base_url="http://test",
    ) as c:
        yield c


@pytest.fixture
async def live_client(app_live):
    async with AsyncClient(
        transport=ASGITransport(app=app_live),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests — Sandbox mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sandbox_returns_simulated_completed(sandbox_client, mock_orchestrator):
    """Sandbox mode returns a simulated completed payment."""
    response = await sandbox_client.post(
        "/api/v2/pay",
        json={"to": "0xmerchant", "amount": "25.00", "currency": "USDC"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["simulated"] is True
    assert data["tx_hash"].startswith("0xsim_")
    assert data["ledger_tx_id"].startswith("sim_ledger_")
    assert data["chain"] == "base"  # default when no chain specified
    assert data["route"]["provider"] == "simulated"
    assert data["route"]["route_type"] == "simulated"
    assert data["route"]["auto_routed"] is True
    assert "Simulated payment" in data["message"]

    # Orchestrator must NOT have been called
    mock_orchestrator.execute_chain.assert_not_called()


@pytest.mark.asyncio
async def test_sandbox_explicit_chain(sandbox_client):
    """Sandbox mode reflects the explicit chain in the response."""
    response = await sandbox_client.post(
        "/api/v2/pay",
        json={"to": "0xmerchant", "amount": "10.00", "chain": "arbitrum"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["simulated"] is True
    assert data["chain"] == "arbitrum"
    assert data["route"]["chain"] == "arbitrum"
    assert data["route"]["auto_routed"] is False


@pytest.mark.asyncio
async def test_sandbox_mandate_id_passthrough(sandbox_client):
    """Sandbox mode passes through the mandate_id if provided."""
    response = await sandbox_client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "50.00",
            "mandate_id": "mandate_custom_123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mandate_id"] == "mandate_custom_123"


@pytest.mark.asyncio
async def test_sandbox_still_validates_amount(sandbox_client):
    """Sandbox mode still rejects invalid amounts."""
    response = await sandbox_client.post(
        "/api/v2/pay",
        json={"to": "0xmerchant", "amount": "-5.00"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sandbox_still_validates_currency(sandbox_client):
    """Sandbox mode still rejects unsupported currencies."""
    response = await sandbox_client.post(
        "/api/v2/pay",
        json={"to": "0xmerchant", "amount": "10.00", "currency": "FAKE"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sandbox_zero_amount_rejected(sandbox_client):
    """Sandbox mode rejects zero amounts."""
    response = await sandbox_client.post(
        "/api/v2/pay",
        json={"to": "0xmerchant", "amount": "0"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — Live mode (falls through to orchestrator)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_mode_calls_orchestrator(live_client, mock_orchestrator):
    """Live mode calls the orchestrator instead of simulating."""
    response = await live_client.post(
        "/api/v2/pay",
        json={"to": "0xmerchant", "amount": "25.00", "chain": "base"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["simulated"] is False
    assert data["tx_hash"] == "0xreal_abc123"
    mock_orchestrator.execute_chain.assert_called_once()
