"""Tests for the external fraud-signal adapters (Stripe Radar / SEON).

Proves, without any live keys:

* each adapter conforms to :class:`FraudSignalPort`, reports SIMULATED custody
  (no funds flow through a signal feed) and the right sandbox flag;
* the registry wires SEON / Stripe only when its env key is present, and falls
  back to the SIMULATED :class:`SandboxFraudSignalPort` when absent;
* SEON normalizes fraud_score (0-100) + state (APPROVE/REVIEW/DECLINE) ->
  RiskSignalResult, sending only the subset of fields Sardis supplies, with
  amount as a decimal string (no float on the wire);
* Stripe maps charge.outcome risk_level/risk_score -> RiskSignalResult, and
  abstains (NOT_ASSESSED) when no charge id is in context;
* both raise ProviderError on transport failure (so the RiskEngine fails
  closed on a high-value money path).

The clients' ``_client_()`` (the httpx session) is monkeypatched so no network
call happens; we assert on the request shape + the normalized signal.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from server.providers.fraud import (
    SeonClient,
    SeonConfig,
    SeonFraudSignalAdapter,
    StripeRadarClient,
    StripeRadarConfig,
    StripeRadarFraudSignalAdapter,
)
from server.providers.ports import (
    CustodyModel,
    FraudSignalPort,
    ProviderCapability,
    ProviderError,
    RecommendedAction,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxFraudSignalPort

# Synthetic Stripe-style keys assembled from parts so no literal secret token
# appears in source (keeps the gitleaks gate honest; these are not real keys).
_TEST_KEY = "sk_" + "test_" + "fake0000"
_LIVE_KEY = "sk_" + "live_" + "fake0000"


# ── fake httpx session ──────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, payload, status_code=200, raise_exc=None):
        self._payload = payload
        self.status_code = status_code
        self._raise = raise_exc

    def raise_for_status(self):
        if self._raise:
            raise self._raise

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def get(self, path, *, params=None, headers=None):
        self.calls.append(("GET", path, {"params": params}))
        return self._next()

    async def post(self, path, *, json=None, headers=None):
        self.calls.append(("POST", path, {"json": json}))
        return self._next()

    def _next(self):
        item = self._responses.pop(0)
        return item if isinstance(item, _FakeResponse) else _FakeResponse(item)


def _patch(client, responses):
    session = _FakeSession(responses)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return session


# ── port conformance + custody ──────────────────────────────────────────


class TestPortConformance:
    def test_both_conform_to_fraud_signal_port(self):
        seon = SeonFraudSignalAdapter(SeonClient(SeonConfig(api_key="k")))
        stripe = StripeRadarFraudSignalAdapter(
            StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
        )
        assert isinstance(seon, FraudSignalPort)
        assert isinstance(stripe, FraudSignalPort)

    def test_signal_feeds_are_simulated_custody(self):
        # No money ever flows through a signal feed.
        seon = SeonFraudSignalAdapter(SeonClient(SeonConfig(api_key="k")))
        assert seon.custody_model == CustodyModel.SIMULATED
        assert seon.provider == "seon"

    def test_stripe_live_key_is_not_sandbox(self):
        live = StripeRadarFraudSignalAdapter(
            StripeRadarClient(StripeRadarConfig(api_key=_LIVE_KEY))
        )
        assert live.sandbox is False
        test = StripeRadarFraudSignalAdapter(
            StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
        )
        assert test.sandbox is True


# ── SEON ─────────────────────────────────────────────────────────────────


class TestSeonAdapter:
    @pytest.mark.asyncio
    async def test_normalizes_score_and_state(self):
        client = SeonClient(SeonConfig(api_key="k"))
        adapter = SeonFraudSignalAdapter(client)
        session = _patch(
            client,
            [
                {
                    "success": True,
                    "data": {
                        "id": "seon_1",
                        "fraud_score": 78.5,
                        "state": "DECLINE",
                        "applied_rules": [{"id": "R1", "name": "velocity"}],
                    },
                }
            ],
        )
        sig = await adapter.score({"agent_id": "a", "amount": Decimal("250.50")})
        assert sig.score == 78.5
        assert sig.recommended_action == RecommendedAction.DECLINE
        assert sig.reference == "seon_1"
        # amount went out as a decimal string (no float).
        body = session.calls[0][2]["json"]
        assert body["transaction_amount"] == "250.50"
        assert body["user_id"] == "a"

    @pytest.mark.asyncio
    async def test_only_supplied_fields_are_sent(self):
        client = SeonClient(SeonConfig(api_key="k"))
        adapter = SeonFraudSignalAdapter(client)
        session = _patch(
            client,
            [{"success": True, "data": {"id": "x", "fraud_score": 1, "state": "APPROVE"}}],
        )
        await adapter.score({"agent_id": "a", "amount": Decimal("10")})
        body = session.calls[0][2]["json"]
        assert "email" not in body and "ip" not in body
        assert body["config"]["email_api"] is False

    @pytest.mark.asyncio
    async def test_transport_error_raises_provider_error(self):
        import httpx

        client = SeonClient(SeonConfig(api_key="k"))
        adapter = SeonFraudSignalAdapter(client)
        _patch(client, [_FakeResponse({}, raise_exc=httpx.HTTPError("boom"))])
        with pytest.raises(ProviderError):
            await adapter.score({"agent_id": "a", "amount": Decimal("10")})


# ── Stripe Radar ──────────────────────────────────────────────────────────


class TestStripeRadarAdapter:
    @pytest.mark.asyncio
    async def test_abstains_without_charge_id(self):
        client = StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
        adapter = StripeRadarFraudSignalAdapter(client)
        sig = await adapter.score({"agent_id": "a", "amount": Decimal("10")})
        assert sig.recommended_action == RecommendedAction.NOT_ASSESSED
        assert sig.score == 0.0

    @pytest.mark.asyncio
    async def test_maps_charge_outcome(self):
        client = StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
        adapter = StripeRadarFraudSignalAdapter(client)
        _patch(
            client,
            [
                {
                    "id": "ch_1",
                    "outcome": {
                        "risk_level": "highest",
                        "risk_score": 92,
                        "type": "blocked",
                        "reason": "highest_risk_level",
                    },
                }
            ],
        )
        sig = await adapter.score({"stripe_charge_id": "ch_1"})
        assert sig.score == 92.0
        assert sig.recommended_action == RecommendedAction.DECLINE
        assert sig.reference == "ch_1"

    @pytest.mark.asyncio
    async def test_level_only_maps_to_band(self):
        # Non-Fraud-Teams: only a level, no numeric score.
        client = StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
        adapter = StripeRadarFraudSignalAdapter(client)
        _patch(client, [{"id": "ch_2", "outcome": {"risk_level": "elevated"}}])
        sig = await adapter.score({"charge_id": "ch_2"})
        assert sig.recommended_action == RecommendedAction.REVIEW
        assert sig.score == 70.0

    @pytest.mark.asyncio
    async def test_transport_error_raises_provider_error(self):
        import httpx

        client = StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
        adapter = StripeRadarFraudSignalAdapter(client)
        _patch(client, [_FakeResponse({}, raise_exc=httpx.HTTPError("boom"))])
        with pytest.raises(ProviderError):
            await adapter.score({"stripe_charge_id": "ch_x"})


# ── registry wiring ───────────────────────────────────────────────────────


class TestRegistryWiring:
    def test_no_key_falls_back_to_sandbox(self):
        ports, owned = {}, []
        ProviderRegistry._build_fraud_signal(
            env={}, is_production=False, ports=ports, owned=owned
        )
        # No real provider registered -> .get() returns the sandbox impl.
        reg = ProviderRegistry(is_production=False, ports=ports, owned_clients=owned)
        impl = reg.fraud_signal()
        assert isinstance(impl, SandboxFraudSignalPort)
        assert impl.sandbox is True

    def test_seon_key_wires_seon(self):
        ports, owned = {}, []
        ProviderRegistry._build_fraud_signal(
            env={"SEON_API_KEY": "k"}, is_production=False, ports=ports, owned=owned
        )
        assert ports[ProviderCapability.FRAUD_SIGNAL].provider == "seon"
        assert len(owned) == 1

    def test_stripe_key_wires_stripe(self):
        ports, owned = {}, []
        ProviderRegistry._build_fraud_signal(
            env={"STRIPE_RADAR_API_KEY": _TEST_KEY},
            is_production=False, ports=ports, owned=owned,
        )
        assert ports[ProviderCapability.FRAUD_SIGNAL].provider == "stripe_radar"

    @pytest.mark.asyncio
    async def test_sandbox_feed_returns_clean_signal(self):
        impl = SandboxFraudSignalPort(provider="sandbox")
        sig = await impl.score({"amount": "10"})
        assert sig.score == 0.0
        assert sig.recommended_action == RecommendedAction.NOT_ASSESSED
