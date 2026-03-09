"""Tests for the outcome tracker — decision recording, outcome resolution, risk profiles."""

from decimal import Decimal

import pytest
from sardis_v2_core.outcome_tracker import OutcomeTracker


@pytest.mark.asyncio
async def test_record_decision():
    """Record a payment decision and retrieve it."""
    tracker = OutcomeTracker()
    outcome_id = await tracker.record_decision(
        intent_id="int_123",
        decision="approved",
        reason="pipeline_passed",
        agent_id="agent_1",
        org_id="org_1",
        merchant_id="merchant_abc",
        amount=Decimal("100.00"),
    )

    assert outcome_id.startswith("out_")
    outcome = await tracker.get_outcome(outcome_id)
    assert outcome is not None
    assert outcome.decision == "approved"
    assert outcome.agent_id == "agent_1"


@pytest.mark.asyncio
async def test_record_outcome_resolution():
    """Record a real-world outcome for a decision."""
    tracker = OutcomeTracker()
    outcome_id = await tracker.record_decision(
        intent_id="int_456",
        decision="approved",
        agent_id="agent_1",
        org_id="org_1",
        amount=Decimal("50.00"),
    )

    await tracker.record_outcome(outcome_id, "completed", {"notes": "all good"})

    outcome = await tracker.get_outcome(outcome_id)
    assert outcome.outcome_type == "completed"
    assert outcome.resolved_at is not None
    assert outcome.outcome_data["notes"] == "all good"


@pytest.mark.asyncio
async def test_agent_risk_profile_updates():
    """Agent risk profile updates on decisions."""
    tracker = OutcomeTracker()

    # Record several decisions
    for _ in range(3):
        await tracker.record_decision(
            intent_id="int_a", decision="approved", agent_id="agent_1", org_id="org_1",
            amount=Decimal("10"),
        )
    await tracker.record_decision(
        intent_id="int_d", decision="denied", reason="limit", agent_id="agent_1", org_id="org_1",
        amount=Decimal("10"),
    )

    profile = await tracker.get_agent_profile("agent_1")
    assert profile is not None
    assert profile.total_decisions == 4
    assert profile.total_approved == 3
    assert profile.total_denied == 1


@pytest.mark.asyncio
async def test_false_negative_tracking():
    """Track false negatives (approved but turned out fraud)."""
    tracker = OutcomeTracker()
    oid = await tracker.record_decision(
        intent_id="int_fn", decision="approved", agent_id="agent_1", org_id="org_1",
        amount=Decimal("100"),
    )

    await tracker.record_outcome(oid, "fraud_confirmed")

    profile = await tracker.get_agent_profile("agent_1")
    assert profile.false_negative_count == 1


@pytest.mark.asyncio
async def test_false_positive_tracking():
    """Track false positives (denied but was actually clean)."""
    tracker = OutcomeTracker()
    oid = await tracker.record_decision(
        intent_id="int_fp", decision="denied", reason="suspicious", agent_id="agent_1", org_id="org_1",
        amount=Decimal("50"),
    )

    await tracker.record_outcome(oid, "false_positive")

    profile = await tracker.get_agent_profile("agent_1")
    assert profile.false_positive_count == 1


@pytest.mark.asyncio
async def test_merchant_risk_profile():
    """Merchant risk profile updates from outcomes."""
    tracker = OutcomeTracker()

    # Record 10 normal transactions
    for i in range(10):
        await tracker.record_decision(
            intent_id=f"int_m{i}", decision="approved", agent_id="agent_1", org_id="org_1",
            merchant_id="merchant_A", amount=Decimal("10"),
        )

    profile = await tracker.get_merchant_profile("merchant_A")
    assert profile is not None
    assert profile.total_transactions == 10
    # Risk tier is only recomputed on outcome resolution, not decisions alone
    assert profile.risk_tier == "unknown"


@pytest.mark.asyncio
async def test_merchant_dispute_updates_risk_tier():
    """Disputes update merchant risk tier."""
    tracker = OutcomeTracker()

    oids = []
    for i in range(10):
        oid = await tracker.record_decision(
            intent_id=f"int_d{i}", decision="approved", agent_id="agent_1", org_id="org_1",
            merchant_id="merchant_B", amount=Decimal("10"),
        )
        oids.append(oid)

    # Dispute 1 of 10 = 10% dispute rate → high risk
    await tracker.record_outcome(oids[0], "disputed")

    profile = await tracker.get_merchant_profile("merchant_B")
    assert profile.dispute_count == 1
    assert profile.dispute_rate > 0
    assert profile.risk_tier == "high"  # 10% > 5% threshold


@pytest.mark.asyncio
async def test_compute_agent_stats():
    """Compute aggregated stats for an agent."""
    tracker = OutcomeTracker()
    oid = await tracker.record_decision(
        intent_id="int_stats", decision="approved", agent_id="agent_stats", org_id="org_1",
        amount=Decimal("100"),
    )
    await tracker.record_outcome(oid, "completed")

    stats = await tracker.compute_agent_stats("agent_stats")
    assert stats["total_outcomes"] == 1
    assert stats["resolved_outcomes"] == 1
    assert stats["approved_count"] == 1
    assert stats["total_amount"] == "100"


@pytest.mark.asyncio
async def test_record_outcome_nonexistent_raises():
    """Recording outcome for nonexistent ID raises ValueError."""
    tracker = OutcomeTracker()
    with pytest.raises(ValueError, match="not found"):
        await tracker.record_outcome("nonexistent", "completed")
