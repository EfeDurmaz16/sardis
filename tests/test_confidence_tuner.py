"""Tests for the confidence threshold tuner."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from sardis_v2_core.confidence_tuner import ConfidenceTuner
from sardis_v2_core.confidence_router import ConfidenceThresholds
from sardis_v2_core.outcome_tracker import PaymentOutcome


def _make_outcome(decision: str, outcome_type: str) -> PaymentOutcome:
    return PaymentOutcome(
        intent_id="int_test",
        decision=decision,
        outcome_type=outcome_type,
        agent_id="agent_1",
        org_id="org_1",
        amount=Decimal("100"),
        resolved_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_thresholds_within_range():
    """When error rates are acceptable, thresholds stay unchanged."""
    tuner = ConfidenceTuner()
    current = ConfidenceThresholds(auto_approve=0.95, manager=0.85, multi_sig=0.70)

    outcomes = [
        _make_outcome("approved", "completed") for _ in range(100)
    ]

    rec = await tuner.evaluate_thresholds(outcomes, current)
    assert rec.recommended_auto_approve == current.auto_approve
    assert "acceptable range" in rec.reason


@pytest.mark.asyncio
async def test_high_false_negative_tightens_thresholds():
    """High false negative rate should tighten (raise) thresholds."""
    tuner = ConfidenceTuner()
    current = ConfidenceThresholds(auto_approve=0.95, manager=0.85, multi_sig=0.70)

    # 90 approved, 10 turn out to be fraud = ~11% FN rate
    outcomes = [_make_outcome("approved", "completed") for _ in range(90)]
    outcomes += [_make_outcome("approved", "fraud_confirmed") for _ in range(10)]

    rec = await tuner.evaluate_thresholds(outcomes, current)
    assert rec.recommended_auto_approve >= current.auto_approve
    assert rec.false_negative_rate > 0.02
    assert "tightening" in rec.reason.lower()


@pytest.mark.asyncio
async def test_high_false_positive_loosens_thresholds():
    """High false positive rate should loosen (lower) thresholds."""
    tuner = ConfidenceTuner()
    current = ConfidenceThresholds(auto_approve=0.95, manager=0.85, multi_sig=0.70)

    # 50 flagged/denied, 40 turn out clean = 80% FP rate
    outcomes = [_make_outcome("flagged", "completed") for _ in range(40)]
    outcomes += [_make_outcome("flagged", "fraud_confirmed") for _ in range(10)]
    outcomes += [_make_outcome("approved", "completed") for _ in range(50)]

    rec = await tuner.evaluate_thresholds(outcomes, current)
    assert rec.false_positive_rate > 0.20
    assert "loosening" in rec.reason.lower()


@pytest.mark.asyncio
async def test_generates_report():
    """Tuner generates a report after evaluation."""
    tuner = ConfidenceTuner()
    current = ConfidenceThresholds()
    outcomes = [_make_outcome("approved", "completed") for _ in range(10)]

    await tuner.evaluate_thresholds(outcomes, current)
    report = await tuner.generate_report()

    assert report is not None
    assert report.outcomes_analyzed == 10
    assert report.recommendation is not None
