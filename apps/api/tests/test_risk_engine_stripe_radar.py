"""End-to-end: the REAL Stripe Radar adapter wired into the RiskEngine.

The unit tests in ``packages/sardis/tests/guardrails/test_risk_engine.py`` prove
the engine's combine/threshold logic with generic feed doubles, and
``apps/api/tests/test_fraud_signal_providers.py`` proves the Radar adapter
normalizes ``charge.outcome`` in isolation.  This file stitches the two together
across the package boundary: the concrete :class:`StripeRadarFraudSignalAdapter`
(its httpx session mocked, no network) is handed to a :class:`RiskEngine`, and
we assert the binding Guard decision.

Proves, with NO live keys:

* a HIGH Radar ``risk_score`` (``charge.outcome.risk_score``) lifts the combined
  risk so the engine escalates — REQUIRE_APPROVAL at the elevated band, BLOCK at
  a near-certain Radar decline — even when the in-house behavioral model is calm
  (Stripe owns the signal, Sardis owns the decision);
* a calm Radar score does not move a calm decision off ALLOW;
* with NO Stripe/SEON key the registry hands back the SIMULATED sandbox feed,
  which the engine folds in as a clean (NOT_ASSESSED, score 0) signal → ALLOW;
* a Radar transport error on a high-value money path fails CLOSED (the engine
  escalates to REQUIRE_APPROVAL), never a silent ALLOW.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from sardis.guardrails.anomaly_engine import RiskAction, RiskAssessment
from sardis.guardrails.risk_engine import GuardAction, RiskEngine

from server.providers.fraud import (
    StripeRadarClient,
    StripeRadarConfig,
    StripeRadarFraudSignalAdapter,
)
from server.providers.ports import RecommendedAction
from server.providers.registry import ProviderRegistry

# Synthetic key assembled from parts so no literal secret appears in source.
_TEST_KEY = "sk_" + "test_" + "fake0000"


# ── mock Radar HTTP (same shape as test_fraud_signal_providers) ──────────


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

    async def get(self, path, *, params=None, headers=None):
        return self._response


def _radar_adapter(outcome_payload=None, *, raise_exc=None) -> StripeRadarFraudSignalAdapter:
    """A real Radar adapter whose httpx session is replaced with a fake."""
    client = StripeRadarClient(StripeRadarConfig(api_key=_TEST_KEY))
    resp = _FakeResponse(outcome_payload or {}, raise_exc=raise_exc)
    session = _FakeSession(resp)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return StripeRadarFraudSignalAdapter(client)


# ── a stub AnomalyEngine that returns a fixed calm internal score ─────────


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


# ── high Radar score lifts the combined decision ──────────────────────────


class TestRadarLiftsCombinedRisk:
    @pytest.mark.asyncio
    async def test_elevated_radar_score_lifts_off_allow(self):
        # Radar 'elevated' / score 72 on charge.outcome; internal calm (5).
        # blend = 0.6*5 + 0.4*72 = 31.8 → FLAG band [30,60).  The lift comes
        # entirely from the real Radar adapter's external score, not a fake.
        adapter = _radar_adapter(
            {"id": "ch_e", "outcome": {"risk_level": "elevated", "risk_score": 72}}
        )
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("50"),
            signal_context={"stripe_charge_id": "ch_e"},
        )
        assert d.external_score == 72.0
        assert any(f.provider == "stripe_radar" for f in d.feeds)
        assert d.feeds[0].recommended_action == RecommendedAction.REVIEW.value
        assert d.action == GuardAction.FLAG

    @pytest.mark.asyncio
    async def test_warm_internal_plus_radar_requires_approval(self):
        # Internal 0.55 → 55 (FLAG on its own); the elevated Radar score (78)
        # blends it across the approval line: 0.6*55 + 0.4*78 = 64.2, which is
        # in [60,85) → REQUIRE_APPROVAL.  The Radar lift is what crosses it.
        adapter = _radar_adapter(
            {"id": "ch_h", "outcome": {"risk_level": "elevated", "risk_score": 78}}
        )
        eng = RiskEngine(anomaly_engine=_WarmAnomaly(0.55), fraud_feeds=[adapter])
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("100"),
            signal_context={"charge_id": "ch_h"},
        )
        assert d.external_score == 78.0
        assert d.action == GuardAction.REQUIRE_APPROVAL
        assert d.requires_approval

    @pytest.mark.asyncio
    async def test_radar_highest_blocks_via_floor(self):
        # Radar 'highest' with a near-certain score (>= BLOCK_THRESHOLD 85) must
        # floor the combined decision at BLOCK even though the internal model is
        # calm — a confident external decline cannot be washed out.
        adapter = _radar_adapter(
            {
                "id": "ch_x",
                "outcome": {
                    "risk_level": "highest",
                    "risk_score": 93,
                    "type": "blocked",
                    "reason": "highest_risk_level",
                },
            }
        )
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("250"),
            signal_context={"stripe_charge_id": "ch_x"},
        )
        assert d.external_score == 93.0
        assert d.feeds[0].recommended_action == RecommendedAction.DECLINE.value
        assert d.action == GuardAction.BLOCK
        assert d.is_blocking

    @pytest.mark.asyncio
    async def test_calm_radar_keeps_allow(self):
        # Radar 'normal' / low score + calm internal → ALLOW (no false escalation).
        adapter = _radar_adapter(
            {"id": "ch_n", "outcome": {"risk_level": "normal", "risk_score": 12}}
        )
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("10"),
            signal_context={"stripe_charge_id": "ch_n"},
        )
        assert d.external_score == 12.0
        assert d.action == GuardAction.ALLOW


# ── no keys → sandbox mock feed, engine still ALLOWs a clean tx ───────────


class TestNoKeysUsesMockFeed:
    @pytest.mark.asyncio
    async def test_no_key_sandbox_feed_yields_allow(self):
        # With no Stripe/SEON key the registry hands back the SIMULATED feed.
        ports, owned = {}, []
        ProviderRegistry._build_fraud_signal(env={}, is_production=False, ports=ports, owned=owned)
        reg = ProviderRegistry(is_production=False, ports=ports, owned_clients=owned)
        feed = reg.fraud_signal()
        assert feed.sandbox is True

        eng = RiskEngine(anomaly_engine=_CalmAnomaly(), fraud_feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        # Mock feed is a clean (NOT_ASSESSED, 0) signal → calm internal stands.
        assert d.external_score == 0.0
        assert d.feeds[0].recommended_action == RecommendedAction.NOT_ASSESSED.value
        assert d.action == GuardAction.ALLOW


# ── Radar error on a high-value path fails CLOSED ─────────────────────────


class TestRadarErrorFailsClosed:
    @pytest.mark.asyncio
    async def test_radar_transport_error_high_value_escalates(self):
        # The real adapter raises ProviderError on transport failure; on a
        # high-value tx the engine must escalate (REQUIRE_APPROVAL), never ALLOW.
        adapter = _radar_adapter(raise_exc=httpx.HTTPError("boom"))
        eng = _engine_with(adapter)
        d = await eng.assess(
            agent_id="a",
            amount=Decimal("5000"),
            signal_context={"stripe_charge_id": "ch_err"},
        )
        assert any(f.ok is False and f.provider == "stripe_radar" for f in d.feeds)
        assert d.action == GuardAction.REQUIRE_APPROVAL
