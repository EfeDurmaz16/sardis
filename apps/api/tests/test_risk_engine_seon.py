"""End-to-end: the REAL SEON adapter wired into the RiskEngine.

``apps/api/tests/test_fraud_signal_providers.py`` proves the SEON adapter
normalizes ``data.fraud_score`` / ``data.state`` in isolation; the unit tests in
``packages/sardis/tests/guardrails/test_risk_engine.py`` prove the engine's
combine/threshold logic with generic feed doubles.  This file stitches the two
together across the package boundary: the concrete
:class:`SeonFraudSignalAdapter` (its httpx session mocked, no network) is handed
to a :class:`RiskEngine`, and we assert the binding Guard decision.

SEON is the primary *agent-fraud* signal feed — device / email / IP / phone
intelligence scored on whatever subset Sardis can supply for an agent payment.
This is the cross-customer signal Sardis cannot self-generate; the in-house
RiskEngine still owns the ALLOW / FLAG / REQUIRE_APPROVAL / BLOCK decision.

Proves, with NO live keys:

* a HIGH SEON ``fraud_score`` lifts the combined risk so the engine escalates —
  FLAG at the elevated band, REQUIRE_APPROVAL when it blends a warm internal
  model across the approval line, BLOCK at a near-certain SEON DECLINE — even
  when the in-house behavioral model is calm (SEON owns the signal, Sardis owns
  the decision);
* a calm SEON score does not move a calm decision off ALLOW (no false
  escalation);
* a SEON transport error on a high-value money path fails CLOSED (the engine
  escalates to REQUIRE_APPROVAL), never a silent ALLOW;
* money on the wire to SEON is a decimal string, never a float literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from sardis.guardrails.anomaly_engine import RiskAction, RiskAssessment
from sardis.guardrails.risk_engine import GuardAction, RiskEngine

from server.providers.fraud import SeonClient, SeonConfig, SeonFraudSignalAdapter
from server.providers.ports import RecommendedAction
from server.providers.registry import ProviderRegistry

# ── mock SEON HTTP (same shape as test_fraud_signal_providers) ────────────


class _FakeResponse:
    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise = raise_exc

    def raise_for_status(self):
        if self._raise:
            raise self._raise

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, response):
        self._response = response
        self.calls = []

    async def post(self, path, *, json=None, headers=None):
        self.calls.append(("POST", path, {"json": json}))
        return self._response


def _seon_adapter(data_payload=None, *, state="APPROVE", raise_exc=None):
    """A real SEON adapter whose httpx session is replaced with a fake.

    Returns ``(adapter, session)`` so a test can assert on the request shape.
    """
    client = SeonClient(SeonConfig(api_key="k"))
    payload = (
        {"error": "boom"}
        if raise_exc
        else {"success": True, "data": {"state": state, **(data_payload or {})}}
    )
    resp = _FakeResponse(payload, raise_exc=raise_exc)
    session = _FakeSession(resp)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return SeonFraudSignalAdapter(client), session


# ── a stub AnomalyEngine that returns a fixed internal score ──────────────


@dataclass
class _CalmAnomaly:
    """Internal behavioral model says 'calm' (0.05 → 5/100, ALLOW)."""

    def assess_risk(self, **kwargs) -> RiskAssessment:
        return RiskAssessment(
            agent_id=kwargs.get("agent_id", "a"),
            overall_score=0.05,
            action=RiskAction.ALLOW,
            signals=[],
            timestamp=datetime.now(UTC),
            transaction_amount=kwargs.get("amount"),
        )


@dataclass
class _WarmAnomaly:
    """Internal model returns a fixed 0-1 score (warm but below approval alone)."""

    score_01: float

    def assess_risk(self, **kwargs) -> RiskAssessment:
        action = (
            RiskAction.ALLOW
            if self.score_01 < 0.30
            else RiskAction.FLAG
            if self.score_01 < 0.60
            else RiskAction.REQUIRE_APPROVAL
        )
        return RiskAssessment(
            agent_id=kwargs.get("agent_id", "a"),
            overall_score=self.score_01,
            action=action,
            signals=[],
            timestamp=datetime.now(UTC),
            transaction_amount=kwargs.get("amount"),
        )


def _engine_with(adapter) -> RiskEngine:
    return RiskEngine(anomaly_engine=_CalmAnomaly(), fraud_feeds=[adapter])


# ── high SEON score lifts the combined decision ──────────────────────────


class TestSeonLiftsCombinedRisk:
    @pytest.mark.asyncio
    async def test_elevated_seon_score_lifts_off_allow(self):
        # SEON REVIEW / fraud_score 72; internal calm (5).
        # blend = 0.6*5 + 0.4*72 = 31.8 → FLAG band [30,60).  The lift comes
        # entirely from the real SEON adapter's external score, not a fake.
        adapter, _ = _seon_adapter(
            {"id": "seon_e", "fraud_score": 72, "applied_rules": [{"name": "velocity"}]},
            state="REVIEW",
        )
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("50"),
            signal_context={"agent_id": "a"},
        )
        assert d.external_score == 72.0
        assert any(f.provider == "seon" for f in d.feeds)
        assert d.feeds[0].recommended_action == RecommendedAction.REVIEW.value
        assert d.action == GuardAction.FLAG

    @pytest.mark.asyncio
    async def test_warm_internal_plus_seon_requires_approval(self):
        # Internal 0.55 → 55 (FLAG on its own); the elevated SEON score (78)
        # blends it across the approval line: 0.6*55 + 0.4*78 = 64.2, which is
        # in [60,85) → REQUIRE_APPROVAL.  The SEON lift is what crosses it.
        adapter, _ = _seon_adapter({"id": "seon_h", "fraud_score": 78}, state="REVIEW")
        eng = RiskEngine(anomaly_engine=_WarmAnomaly(0.55), fraud_feeds=[adapter])
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("100"),
            signal_context={"agent_id": "a"},
        )
        assert d.external_score == 78.0
        assert d.action == GuardAction.REQUIRE_APPROVAL
        assert d.requires_approval

    @pytest.mark.asyncio
    async def test_seon_decline_blocks_via_floor(self):
        # A near-certain SEON DECLINE (>= BLOCK_THRESHOLD 85) must floor the
        # combined decision at BLOCK even though the internal model is calm —
        # a confident external decline cannot be washed out.
        adapter, _ = _seon_adapter(
            {"id": "seon_x", "fraud_score": 93, "applied_rules": [{"name": "device_dup"}]},
            state="DECLINE",
        )
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("250"),
            signal_context={"agent_id": "a", "email": "rogue@x.test"},
        )
        assert d.external_score == 93.0
        assert d.feeds[0].recommended_action == RecommendedAction.DECLINE.value
        assert d.action == GuardAction.BLOCK
        assert d.is_blocking

    @pytest.mark.asyncio
    async def test_calm_seon_keeps_allow(self):
        # SEON APPROVE / low score + calm internal → ALLOW (no false escalation).
        adapter, _ = _seon_adapter({"id": "seon_n", "fraud_score": 8}, state="APPROVE")
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("10"),
            signal_context={"agent_id": "a"},
        )
        assert d.external_score == 8.0
        assert d.action == GuardAction.ALLOW

    @pytest.mark.asyncio
    async def test_amount_reaches_seon_as_decimal_string(self):
        # The engine seeds signal_context with the amount; it must hit SEON as a
        # decimal string (no float on a money wire).
        adapter, session = _seon_adapter({"id": "seon_a", "fraud_score": 5})
        eng = _engine_with(adapter)
        await eng.assess(agent_id="a", amount=Decimal("250.50"))
        body = session.calls[0][2]["json"]
        assert body["transaction_amount"] == "250.50"
        assert isinstance(body["transaction_amount"], str)


# ── SEON error on a high-value path fails CLOSED ──────────────────────────


class TestSeonErrorFailsClosed:
    @pytest.mark.asyncio
    async def test_seon_transport_error_high_value_escalates(self):
        # The real adapter raises ProviderError on transport failure; on a
        # high-value tx the engine must escalate (REQUIRE_APPROVAL), never ALLOW.
        adapter, _ = _seon_adapter(raise_exc=httpx.HTTPError("boom"))
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("5000"),
            signal_context={"agent_id": "a"},
        )
        assert any(f.ok is False and f.provider == "seon" for f in d.feeds)
        assert d.action == GuardAction.REQUIRE_APPROVAL


# ── no keys → sandbox mock feed, engine still ALLOWs a clean tx ───────────


class TestNoKeysUsesMockFeed:
    @pytest.mark.asyncio
    async def test_no_seon_key_sandbox_feed_yields_allow(self):
        # With no SEON/Stripe key the registry hands back the SIMULATED feed.
        ports, owned = {}, []
        ProviderRegistry._build_fraud_signal(env={}, is_production=False, ports=ports, owned=owned)
        reg = ProviderRegistry(is_production=False, ports=ports, owned_clients=owned)
        feed = reg.fraud_signal()
        assert feed.sandbox is True

        eng = RiskEngine(anomaly_engine=_CalmAnomaly(), fraud_feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.external_score == 0.0
        assert d.feeds[0].recommended_action == RecommendedAction.NOT_ASSESSED.value
        assert d.action == GuardAction.ALLOW
