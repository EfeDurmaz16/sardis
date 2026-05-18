"""Tests for sardis.pay() Phase 3 — cross-currency FX with auto-swap.

Tests verify:
1. Same-currency payments pass through without FX (no swap)
2. Cross-currency USDC->EURC triggers FX quote and returns fx field
3. Fiat currency codes (USD, EUR) are mapped to stablecoin tokens
4. Slippage exceeded returns error with fresh quote
5. Unsupported currency pair returns 422
6. Unsupported currency code returns 422
7. FX rate and provider are present in response
8. Mandate uses target token (EURC) not original currency (EUR)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Stub mandates — the real ones require many VC/proof fields.
# pay.py constructs them with simplified kwargs; we mock the classes
# so they store all kwargs as attributes.
# ---------------------------------------------------------------------------


class StubMandate:
    """Generic stub that accepts any kwargs and stores them as attrs."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class StubMandateChain:
    """Stub MandateChain."""

    def __init__(self, intent=None, cart=None, payment=None):
        self.intent = intent
        self.cart = cart
        self.payment = payment


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_orchestrator():
    """Mock PaymentOrchestrator that returns a success result."""
    orchestrator = AsyncMock()

    class MockResult:
        chain_tx_hash = "0xfx_abc123"
        ledger_tx_id = "ledger_fx_001"
        chain = "base"
        mandate_id = "pay_test_agent"

    orchestrator.execute_chain = AsyncMock(return_value=MockResult())
    return orchestrator


class MockRouteResult:
    """Mock LiquidityRouter.find_best_route() result."""

    def __init__(
        self,
        provider: str = "tempo_dex",
        chain: str = "base",
        rate: Decimal = Decimal("0.9215"),
        fee_bps: int = 0,
        output: Decimal = Decimal("92.15"),
    ):
        self.provider = provider
        self.chain = chain
        self.estimated_rate = rate
        self.estimated_fee_bps = fee_bps
        self.estimated_output = output
        self.route_type = "swap"


class FakeCache:
    """Minimal async cache implementing the idempotency helper contract."""

    def __init__(self):
        self.values: dict[str, str] = {}
        self.locks: set[str] = set()

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.values[key] = value

    async def acquire_lock(self, key: str, ttl_seconds: int) -> str | None:
        if key in self.locks:
            return None
        self.locks.add(key)
        return f"owner:{key}"

    async def release_lock(self, key: str, owner: str) -> None:
        self.locks.discard(key)


@pytest.fixture
def mock_liquidity_router():
    """Mock LiquidityRouter that returns a USDC->EURC quote."""

    async def mock_find_best_route(
        from_token: str,
        to_token: str,
        amount: Decimal,
        from_chain: str | None = None,
        to_chain: str | None = None,
    ) -> MockRouteResult:
        # Same-token route (auto-routing)
        if from_token == to_token:
            return MockRouteResult(
                provider="indicative",
                chain=from_chain or "base",
                rate=Decimal("1.0"),
                fee_bps=0,
                output=amount,
            )
        # USDC -> EURC
        if from_token == "USDC" and to_token == "EURC":
            output = (amount * Decimal("0.9215")).quantize(Decimal("0.000001"))
            return MockRouteResult(
                provider="tempo_dex",
                chain=from_chain or "base",
                rate=Decimal("0.9215"),
                fee_bps=0,
                output=output,
            )
        # EURC -> USDC
        if from_token == "EURC" and to_token == "USDC":
            output = (amount * Decimal("1.0852")).quantize(Decimal("0.000001"))
            return MockRouteResult(
                provider="uniswap_v3",
                chain=from_chain or "base",
                rate=Decimal("1.0852"),
                fee_bps=5,
                output=output,
            )
        # USDC -> USDT
        if from_token == "USDC" and to_token == "USDT":
            return MockRouteResult(
                provider="uniswap_v3",
                chain=from_chain or "base",
                rate=Decimal("1.0000"),
                fee_bps=1,
                output=amount,
            )
        raise ValueError(f"Unsupported pair: {from_token}/{to_token}")

    router_mock = MagicMock()
    router_mock.find_best_route = AsyncMock(side_effect=mock_find_best_route)
    return router_mock


@pytest.fixture
def _patch_mandates():
    """Patch mandate classes so pay.py can construct them with simplified kwargs."""
    with patch("sardis_api.routers.pay.IntentMandate", StubMandate), \
         patch("sardis_api.routers.pay.CartMandate", StubMandate), \
         patch("sardis_api.routers.pay.PaymentMandate", StubMandate), \
         patch("sardis_api.routers.pay.MandateChain", StubMandateChain):
        yield


@pytest.fixture
def app_with_pay(mock_orchestrator, mock_liquidity_router, _patch_mandates):
    """Create a FastAPI app with the pay router and mocked FX infra."""
    from fastapi import FastAPI

    from sardis_api.routers.pay import PayDependencies, get_deps, router

    app = FastAPI()
    app.state.cache_service = FakeCache()
    app.include_router(router, prefix="/api/v2/pay")

    app.dependency_overrides[get_deps] = lambda: PayDependencies(
        orchestrator=mock_orchestrator,
    )

    # Override require_principal
    from sardis_api.authz import require_principal

    class FakePrincipal:
        organization_id = "org_test"
        subject_id = "test_agent"
        scopes = ["pay"]

        @property
        def user_id(self):
            return self.subject_id

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
# Tests — Same-currency (no FX passthrough)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_currency_no_fx(client, mock_orchestrator):
    """When currency matches sender token (USDC), no FX should occur."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "100.00",
            "currency": "USDC",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["fx"] is None


@pytest.mark.asyncio
async def test_same_currency_usd_maps_to_usdc_no_fx(client, mock_orchestrator):
    """USD maps to USDC which is same as sender token, so no FX."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "50.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["fx"] is None


@pytest.mark.asyncio
async def test_pay_idempotency_replays_same_payload_without_reexecution(
    client, mock_orchestrator
):
    """A repeated client idempotency key should return the cached response."""
    payload = {
        "to": "0xmerchant",
        "amount": "100.00",
        "currency": "USDC",
    }
    headers = {"Idempotency-Key": "pay_replay_same_payload"}

    first = await client.post("/api/v2/pay", json=payload, headers=headers)
    second = await client.post("/api/v2/pay", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert mock_orchestrator.execute_chain.await_count == 1


@pytest.mark.asyncio
async def test_pay_idempotency_rejects_same_key_with_different_payload(
    client, mock_orchestrator
):
    """A reused key with a different payment payload is a replay/tamper signal."""
    headers = {"Idempotency-Key": "pay_replay_changed_payload"}

    first = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "100.00",
            "currency": "USDC",
        },
        headers=headers,
    )
    replay = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "101.00",
            "currency": "USDC",
        },
        headers=headers,
    )

    assert first.status_code == 200
    assert replay.status_code == 409
    assert replay.json()["detail"] == "idempotency_key_reuse_different_payload"
    assert mock_orchestrator.execute_chain.await_count == 1


# ---------------------------------------------------------------------------
# Tests — Cross-currency USDC->EURC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_currency_eur_triggers_fx(
    client, mock_orchestrator, mock_liquidity_router
):
    """currency=EUR should trigger USDC->EURC swap with FX info in response."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "merchant@eu",
                "amount": "100.00",
                "currency": "EUR",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    # FX field should be present
    fx = data.get("fx")
    assert fx is not None
    assert fx["from_currency"] == "USDC"
    assert fx["to_currency"] == "EURC"
    assert fx["rate"] == "0.9215"
    assert fx["provider"] == "tempo_dex"
    assert fx["slippage_bps"] == 100  # 1% tolerance
    assert fx["input_amount"] == "100.00"
    assert fx["output_amount"] == "92.150000"


@pytest.mark.asyncio
async def test_cross_currency_eurc_triggers_fx(
    client, mock_orchestrator, mock_liquidity_router
):
    """Explicit EURC should also work as cross-currency from USDC sender."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "merchant@eu",
                "amount": "100.00",
                "currency": "EURC",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    fx = data.get("fx")
    assert fx is not None
    assert fx["from_currency"] == "USDC"
    assert fx["to_currency"] == "EURC"


@pytest.mark.asyncio
async def test_cross_currency_mandate_uses_target_token(
    client, mock_orchestrator, mock_liquidity_router
):
    """The orchestrator mandate should use target token (EURC), not EUR."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "merchant@eu",
                "amount": "100.00",
                "currency": "EUR",
            },
        )

    assert response.status_code == 200

    # Verify the orchestrator received EURC as the token
    call_args = mock_orchestrator.execute_chain.call_args
    chain_obj = call_args[0][0]
    assert chain_obj.payment.currency == "EURC"
    assert chain_obj.payment.token == "EURC"


@pytest.mark.asyncio
async def test_cross_currency_route_type_is_fx_swap(
    client, mock_orchestrator, mock_liquidity_router
):
    """Cross-currency route_type should be 'fx_swap'."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "merchant@eu",
                "amount": "100.00",
                "currency": "EUR",
                "chain": "base",
            },
        )

    assert response.status_code == 200
    data = response.json()
    route = data.get("route")
    assert route is not None
    assert route["route_type"] == "fx_swap"


# ---------------------------------------------------------------------------
# Tests — Slippage exceeded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slippage_exceeded_returns_error_with_fresh_quote(
    client, mock_orchestrator,
):
    """When slippage exceeds tolerance, return failed with fresh quote."""
    call_count = 0

    async def bad_then_good_rate(
        from_token, to_token, amount, from_chain=None, to_chain=None,
    ):
        nonlocal call_count
        call_count += 1
        # Same-token routing calls
        if from_token == to_token:
            return MockRouteResult(
                provider="indicative",
                chain=from_chain or "base",
                rate=Decimal("1.0"),
                fee_bps=0,
                output=amount,
            )
        # FX quotes
        output = (amount * Decimal("0.9215")).quantize(Decimal("0.000001"))
        return MockRouteResult(
            provider="tempo_dex",
            rate=Decimal("0.9215"),
            output=output,
        )

    bad_router = MagicMock()
    bad_router.find_best_route = AsyncMock(side_effect=bad_then_good_rate)

    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=bad_router,
    ):
        # Patch _check_slippage to simulate slippage exceeded
        with patch(
            "sardis_api.routers.pay._check_slippage",
            return_value="Slippage 250 bps exceeds tolerance 100 bps. Request a fresh quote.",
        ):
            response = await client.post(
                "/api/v2/pay",
                json={
                    "to": "merchant@eu",
                    "amount": "100.00",
                    "currency": "EUR",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "Slippage" in data["message"]
    assert "Fresh rate" in data["message"]
    # FX info should still be present
    assert data["fx"] is not None


# ---------------------------------------------------------------------------
# Tests — Unsupported currency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsupported_currency_returns_422(client):
    """Completely unknown currency should return 422."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "100.00",
            "currency": "GBP",
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert "Unsupported currency" in data["detail"]


@pytest.mark.asyncio
async def test_unsupported_currency_jpy_returns_422(client):
    """JPY is not in CURRENCY_TO_TOKEN, should return 422."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "10000",
            "currency": "JPY",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — FX rate in response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fx_rate_reflects_actual_quote(
    client, mock_orchestrator, mock_liquidity_router
):
    """FX rate in response should match the quote from LiquidityRouter."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "merchant@eu",
                "amount": "250.00",
                "currency": "EUR",
            },
        )

    assert response.status_code == 200
    data = response.json()
    fx = data["fx"]

    # Rate should be 0.9215 (from mock)
    assert Decimal(fx["rate"]) == Decimal("0.9215")
    # Output should be 250 * 0.9215 = 230.375000
    expected_output = (Decimal("250.00") * Decimal("0.9215")).quantize(
        Decimal("0.000001")
    )
    assert Decimal(fx["output_amount"]) == expected_output


@pytest.mark.asyncio
async def test_fx_provider_in_response(
    client, mock_orchestrator, mock_liquidity_router
):
    """Provider should be included in FX response."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "merchant@eu",
                "amount": "100.00",
                "currency": "EUR",
            },
        )

    assert response.status_code == 200
    fx = response.json()["fx"]
    assert fx["provider"] in ("tempo_dex", "uniswap_v3", "indicative", "cdp_swap")


# ---------------------------------------------------------------------------
# Tests — USDC->USDT pair
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_currency_usdt(
    client, mock_orchestrator, mock_liquidity_router
):
    """USDT should trigger USDC->USDT swap."""
    with patch(
        "sardis_chain.liquidity_router.LiquidityRouter",
        return_value=mock_liquidity_router,
    ):
        response = await client.post(
            "/api/v2/pay",
            json={
                "to": "0xmerchant",
                "amount": "100.00",
                "currency": "USDT",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    fx = data.get("fx")
    assert fx is not None
    assert fx["from_currency"] == "USDC"
    assert fx["to_currency"] == "USDT"
    assert fx["provider"] == "uniswap_v3"


# ---------------------------------------------------------------------------
# Tests — Phase 2 backward compatibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase2_explicit_chain_still_works(client, mock_orchestrator):
    """Explicit chain with same currency should work as before."""
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
    assert data["fx"] is None
    assert data["route"]["chain"] == "arbitrum"
    assert data["route"]["auto_routed"] is False


@pytest.mark.asyncio
async def test_phase2_auto_route_still_works(client, mock_orchestrator):
    """Auto-routing with same currency should work as before."""
    response = await client.post(
        "/api/v2/pay",
        json={
            "to": "0xmerchant",
            "amount": "50.00",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["fx"] is None
    assert data["route"]["auto_routed"] is True
