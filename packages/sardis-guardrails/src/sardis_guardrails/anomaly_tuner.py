"""Anomaly engine weight tuner — adjusts signal weights based on outcome data.

Implements Bayesian-inspired weight updates: signals that correctly predict
fraud get upweighted, signals that fire on clean transactions get downweighted.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sardis_v2_core.outcome_tracker import PaymentOutcome

    from .anomaly_engine import AnomalyEngine

logger = logging.getLogger(__name__)

# Learning rate — how aggressively to adjust weights per tuning cycle
_LEARNING_RATE = 0.05
_MIN_WEIGHT = 0.05
_MAX_WEIGHT = 0.50


@dataclass
class WeightAdjustment:
    """Recommended weight change for a single signal."""
    signal_type: str
    current_weight: float
    recommended_weight: float
    delta: float
    reason: str


@dataclass
class TuningReport:
    """Report from a tuning cycle."""
    adjustments: list[WeightAdjustment] = field(default_factory=list)
    outcomes_analyzed: int = 0
    fraud_count: int = 0
    clean_count: int = 0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "adjustments": [
                {
                    "signal_type": a.signal_type,
                    "current_weight": round(a.current_weight, 4),
                    "recommended_weight": round(a.recommended_weight, 4),
                    "delta": round(a.delta, 4),
                    "reason": a.reason,
                }
                for a in self.adjustments
            ],
            "outcomes_analyzed": self.outcomes_analyzed,
            "fraud_count": self.fraud_count,
            "clean_count": self.clean_count,
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "computed_at": self.computed_at.isoformat(),
        }


class AnomalyTuner:
    """Adjusts anomaly engine weights based on outcome data.

    For each signal type:
    - If signal fires and outcome is fraud → increase weight
    - If signal fires and outcome is clean → decrease weight
    - Bayesian update: P(fraud|signal) from historical data
    """

    def __init__(self, learning_rate: float = _LEARNING_RATE) -> None:
        self._learning_rate = learning_rate
        self._last_report: TuningReport | None = None

    async def compute_weight_adjustments(
        self,
        outcomes: list[PaymentOutcome],
        current_weights: dict[str, float],
    ) -> dict[str, float]:
        """Compute recommended weight adjustments from resolved outcomes.

        Args:
            outcomes: List of resolved outcomes with anomaly data
            current_weights: Current engine weights {signal_type: weight}

        Returns:
            Dict of {signal_type: new_weight}
        """
        if not outcomes:
            return dict(current_weights)

        # Count signal firings vs fraud outcomes
        signal_fires: dict[str, int] = dict.fromkeys(current_weights, 0)
        signal_fraud: dict[str, int] = dict.fromkeys(current_weights, 0)
        signal_clean: dict[str, int] = dict.fromkeys(current_weights, 0)

        fraud_types = {"fraud_confirmed", "disputed"}
        clean_types = {"completed", "false_positive"}

        fraud_count = 0
        clean_count = 0

        for outcome in outcomes:
            if outcome.outcome_type in fraud_types:
                fraud_count += 1
            elif outcome.outcome_type in clean_types:
                clean_count += 1

            # Check which signals fired (stored in outcome_data)
            fired_signals = outcome.outcome_data.get("anomaly_signals", [])
            for sig in fired_signals:
                sig_type = sig.get("type", "")
                if sig_type in signal_fires:
                    signal_fires[sig_type] += 1
                    if outcome.outcome_type in fraud_types:
                        signal_fraud[sig_type] += 1
                    elif outcome.outcome_type in clean_types:
                        signal_clean[sig_type] += 1

        # Compute adjustments
        adjustments: list[WeightAdjustment] = []
        new_weights = dict(current_weights)

        for sig_type, current_w in current_weights.items():
            fires = signal_fires[sig_type]
            if fires == 0:
                continue

            precision = signal_fraud[sig_type] / fires  # P(fraud|signal_fired)
            false_alarm = signal_clean[sig_type] / fires

            if precision > 0.5:
                # Signal is useful — increase weight
                delta = self._learning_rate * precision
                reason = f"High precision ({precision:.2f}): signal predicts fraud well"
            elif false_alarm > 0.7:
                # Signal causes too many false alarms — decrease weight
                delta = -self._learning_rate * false_alarm
                reason = f"High false alarm rate ({false_alarm:.2f}): signal too noisy"
            else:
                delta = 0.0
                reason = "No significant adjustment needed"

            new_w = max(_MIN_WEIGHT, min(_MAX_WEIGHT, current_w + delta))
            adjustments.append(WeightAdjustment(
                signal_type=sig_type,
                current_weight=current_w,
                recommended_weight=new_w,
                delta=new_w - current_w,
                reason=reason,
            ))
            new_weights[sig_type] = new_w

        # Normalize weights to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}

        # Build report
        flagged_or_denied = sum(1 for o in outcomes if o.decision in ("flagged", "denied"))
        fp = sum(1 for o in outcomes if o.decision in ("flagged", "denied") and o.outcome_type in clean_types)
        fn = sum(1 for o in outcomes if o.decision == "approved" and o.outcome_type in fraud_types)

        self._last_report = TuningReport(
            adjustments=adjustments,
            outcomes_analyzed=len(outcomes),
            fraud_count=fraud_count,
            clean_count=clean_count,
            false_positive_rate=fp / flagged_or_denied if flagged_or_denied else 0,
            false_negative_rate=fn / (len(outcomes) - flagged_or_denied) if (len(outcomes) - flagged_or_denied) else 0,
        )

        logger.info(
            "Anomaly tuner: analyzed %d outcomes, %d adjustments",
            len(outcomes), len(adjustments),
        )
        return new_weights

    async def apply_adjustments(
        self,
        engine: AnomalyEngine,
        adjustments: dict[str, float],
    ) -> None:
        """Apply weight adjustments to an anomaly engine instance."""
        engine.WEIGHTS = dict(adjustments)
        logger.info("Applied weight adjustments to anomaly engine: %s", adjustments)

    async def get_tuning_report(self) -> TuningReport | None:
        """Get the last tuning report."""
        return self._last_report
