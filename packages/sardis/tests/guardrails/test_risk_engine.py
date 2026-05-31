"""Unit tests for the RiskEngine Guard decision layer.

Verifies: the internal behavioral score drives each action (ALLOW / FLAG /
REQUIRE_APPROVAL / BLOCK); an external feed lifts the combined score; a
high-confidence external decline floors the action; and an external feed error
on a high-value transaction fails CLOSED (escalates), never silently allows.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from sardis.guardrails.anomaly_engine import AnomalyEngine
from sardis.guardrails.risk_engine import GuardAction, RiskEngine

# ── test doubles for the FraudSignalPort ────────────────────────────────


@dataclass
class _FakeSignal:
    provider: str
    score: float
    recommended_action: str = "allow"
    reasons: tuple[str, ...] = ()
    sandbox: bool = True


@dataclass
class _FakeFeed:
    provider: str
    signal: _FakeSignal | None = None
    raises: bool = False

    async def score(self, context: dict) -> _FakeSignal:
        if self.raises:
            raise RuntimeError("feed down")
        return self.signal or _FakeSignal(provider=self.provider, score=0.0)


# ── a stub AnomalyEngine that returns a fixed internal 0-1 score ─────────


@dataclass
class _StubAnomaly:
    score_01: float

    def assess_risk(self, **kwargs):
        # Mirror the real engine's return shape closely enough for RiskEngine.
        from datetime import UTC, datetime

        from sardis.guardrails.anomaly_engine import RiskAction, RiskAssessment

        action = (
            RiskAction.ALLOW if self.score_01 < 0.30
            else RiskAction.FLAG if self.score_01 < 0.60
            else RiskAction.REQUIRE_APPROVAL if self.score_01 < 0.80
            else RiskAction.KILL_SWITCH
        )
        return RiskAssessment(
            agent_id=kwargs.get("agent_id", "a"),
            overall_score=self.score_01,
            action=action,
            signals=[],
            timestamp=datetime.now(UTC),
            transaction_amount=kwargs.get("amount"),
        )


def _engine(internal_01: float, feeds=None) -> RiskEngine:
    return RiskEngine(anomaly_engine=_StubAnomaly(internal_01), fraud_feeds=feeds or [])


class TestInternalScoreDrivesAction:
    @pytest.mark.asyncio
    async def test_low_score_allows(self):
        eng = _engine(0.05)
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.action == GuardAction.ALLOW
        assert not d.is_blocking

    @pytest.mark.asyncio
    async def test_mid_score_flags(self):
        # internal 0.40 → 40/100 → FLAG band [30, 60)
        eng = _engine(0.40)
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.action == GuardAction.FLAG

    @pytest.mark.asyncio
    async def test_high_score_requires_approval(self):
        # internal 0.70 → 70/100 → REQUIRE_APPROVAL band [60, 85)
        eng = _engine(0.70)
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.action == GuardAction.REQUIRE_APPROVAL
        assert d.requires_approval

    @pytest.mark.asyncio
    async def test_critical_score_blocks(self):
        # internal 0.95 → 95/100 → BLOCK band [85, 100]
        eng = _engine(0.95)
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.action == GuardAction.BLOCK
        assert d.is_blocking


class TestExternalFeeds:
    @pytest.mark.asyncio
    async def test_external_feed_lifts_combined_score(self):
        # Calm internal (0.10 → 10) but a feed scoring 80 → blend 0.6*10+0.4*80=38 → FLAG
        feed = _FakeFeed("seon", _FakeSignal("seon", score=80.0, recommended_action="review"))
        eng = _engine(0.10, feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.external_score == 80.0
        assert d.action == GuardAction.FLAG

    @pytest.mark.asyncio
    async def test_high_confidence_external_decline_floors_block(self):
        # Calm internal but a near-certain external decline (>= block threshold)
        # must not be diluted below the block line.
        feed = _FakeFeed("seon", _FakeSignal("seon", score=95.0, recommended_action="decline"))
        eng = _engine(0.05, feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.action == GuardAction.BLOCK

    @pytest.mark.asyncio
    async def test_max_external_across_feeds(self):
        feeds = [
            _FakeFeed("stripe_radar", _FakeSignal("stripe_radar", score=10.0)),
            _FakeFeed("seon", _FakeSignal("seon", score=90.0, recommended_action="decline")),
        ]
        eng = _engine(0.05, feeds=feeds)
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.external_score == 90.0


class TestFailClosed:
    @pytest.mark.asyncio
    async def test_feed_error_high_value_escalates(self):
        # Calm internal + a feed that raises on a HIGH-VALUE tx → fail-closed to
        # REQUIRE_APPROVAL (never a silent ALLOW).
        feed = _FakeFeed("seon", raises=True)
        eng = _engine(0.05, feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("5000"))
        assert d.action == GuardAction.REQUIRE_APPROVAL
        assert any(f.ok is False for f in d.feeds)

    @pytest.mark.asyncio
    async def test_feed_error_low_value_degrades_not_blocks(self):
        # On a LOW-VALUE tx a feed error degrades to internal-only scoring
        # (no escalation) — internal is calm so it ALLOWs.
        feed = _FakeFeed("seon", raises=True)
        eng = _engine(0.05, feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert d.action == GuardAction.ALLOW
        assert any(f.ok is False for f in d.feeds)

    @pytest.mark.asyncio
    async def test_feed_error_high_value_does_not_downgrade_block(self):
        # If internal already demands BLOCK, a high-value feed error keeps BLOCK.
        feed = _FakeFeed("seon", raises=True)
        eng = _engine(0.99, feeds=[feed])
        d = await eng.assess(agent_id="a", amount=Decimal("5000"))
        assert d.action == GuardAction.BLOCK


class TestReusesAnomalyEngine:
    @pytest.mark.asyncio
    async def test_default_uses_real_anomaly_engine(self):
        # No stub: RiskEngine must reuse the real AnomalyEngine and produce a
        # bounded 0-100 internal score for a clean transaction.
        eng = RiskEngine()
        d = await eng.assess(agent_id="a", amount=Decimal("10"))
        assert 0.0 <= d.internal_score <= 100.0
        assert d.action == GuardAction.ALLOW

    def test_constructs_with_explicit_anomaly_engine(self):
        ae = AnomalyEngine()
        eng = RiskEngine(anomaly_engine=ae)
        assert eng._anomaly is ae
