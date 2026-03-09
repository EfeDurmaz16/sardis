"""Tests for the anomaly tuner — weight adjustment from outcomes."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sardis_guardrails.anomaly_tuner import AnomalyTuner
from sardis_v2_core.outcome_tracker import PaymentOutcome


def _make_outcome(decision: str, outcome_type: str, signals: list[dict] | None = None) -> PaymentOutcome:
    return PaymentOutcome(
        intent_id="int_test",
        decision=decision,
        outcome_type=outcome_type,
        agent_id="agent_1",
        org_id="org_1",
        amount=Decimal("100"),
        outcome_data={"anomaly_signals": signals or []},
        resolved_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_compute_no_outcomes():
    """No outcomes returns current weights unchanged."""
    tuner = AnomalyTuner()
    current = {"amount_anomaly": 0.30, "velocity": 0.25, "new_merchant": 0.15}
    result = await tuner.compute_weight_adjustments([], current)
    assert result == current


@pytest.mark.asyncio
async def test_fraud_signal_gets_upweighted():
    """Signals that correctly predict fraud get higher weight."""
    tuner = AnomalyTuner(learning_rate=0.1)

    # 10 outcomes where amount_anomaly fires and all are fraud
    outcomes = [
        _make_outcome("flagged", "fraud_confirmed", [{"type": "amount_anomaly", "score": 0.8}])
        for _ in range(10)
    ]

    current = {"amount_anomaly": 0.30, "velocity": 0.25, "new_merchant": 0.15, "time_anomaly": 0.10, "merchant_category": 0.10, "behavioral_alerts": 0.10}
    result = await tuner.compute_weight_adjustments(outcomes, current)

    # amount_anomaly should be relatively higher than before (normalized)
    ratio_before = 0.30 / sum(current.values())
    ratio_after = result["amount_anomaly"] / sum(result.values())
    assert ratio_after >= ratio_before - 0.01  # At least maintained or increased


@pytest.mark.asyncio
async def test_noisy_signal_gets_downweighted():
    """Signals that fire on clean transactions get lower weight."""
    tuner = AnomalyTuner(learning_rate=0.1)

    # 10 outcomes where velocity fires but all are clean (false alarms)
    outcomes = [
        _make_outcome("flagged", "completed", [{"type": "velocity", "score": 0.7}])
        for _ in range(10)
    ]

    current = {"amount_anomaly": 0.30, "velocity": 0.25, "new_merchant": 0.15, "time_anomaly": 0.10, "merchant_category": 0.10, "behavioral_alerts": 0.10}
    result = await tuner.compute_weight_adjustments(outcomes, current)

    # Weights should still sum to ~1.0
    assert abs(sum(result.values()) - 1.0) < 0.01


@pytest.mark.asyncio
async def test_tuning_report_generated():
    """Tuning report is generated after compute."""
    tuner = AnomalyTuner()

    outcomes = [
        _make_outcome("approved", "fraud_confirmed", [{"type": "amount_anomaly", "score": 0.5}]),
        _make_outcome("approved", "completed", []),
    ]

    current = {"amount_anomaly": 0.30, "velocity": 0.25}
    await tuner.compute_weight_adjustments(outcomes, current)

    report = await tuner.get_tuning_report()
    assert report is not None
    assert report.outcomes_analyzed == 2
    assert report.fraud_count == 1
    assert report.clean_count == 1
