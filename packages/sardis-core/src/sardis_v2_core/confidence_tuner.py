"""Confidence threshold auto-tuner — adjusts ConfidenceRouter thresholds from outcome data.

Analyzes false positive rate (flagged/denied clean transactions) and false negative
rate (approved fraud) to recommend threshold adjustments that minimize total cost.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .confidence_router import ConfidenceThresholds
    from .outcome_tracker import PaymentOutcome

logger = logging.getLogger(__name__)

# Cost model: how expensive each error type is relative to each other
_FP_COST = 1.0    # Cost of a false positive (blocking legitimate transaction)
_FN_COST = 10.0   # Cost of a false negative (allowing fraud) — 10x worse

# Maximum adjustment per cycle
_MAX_ADJUSTMENT = 0.03


@dataclass
class ThresholdRecommendation:
    """Recommended threshold changes."""
    current_auto_approve: float
    current_manager: float
    current_multi_sig: float
    recommended_auto_approve: float
    recommended_manager: float
    recommended_multi_sig: float
    false_positive_rate: float
    false_negative_rate: float
    total_cost: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "current": {
                "auto_approve": self.current_auto_approve,
                "manager": self.current_manager,
                "multi_sig": self.current_multi_sig,
            },
            "recommended": {
                "auto_approve": self.recommended_auto_approve,
                "manager": self.recommended_manager,
                "multi_sig": self.recommended_multi_sig,
            },
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "total_cost": round(self.total_cost, 2),
            "reason": self.reason,
        }


@dataclass
class ConfidenceTuningReport:
    """Report from a confidence tuning cycle."""
    recommendation: ThresholdRecommendation | None = None
    outcomes_analyzed: int = 0
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
            "outcomes_analyzed": self.outcomes_analyzed,
            "computed_at": self.computed_at.isoformat(),
        }


class ConfidenceTuner:
    """Auto-tunes ConfidenceRouter thresholds from outcome data.

    Uses a cost-based model: false negatives (missed fraud) cost 10x
    more than false positives (blocking legitimate transactions).
    """

    def __init__(
        self,
        fp_cost: float = _FP_COST,
        fn_cost: float = _FN_COST,
        max_adjustment: float = _MAX_ADJUSTMENT,
    ) -> None:
        self._fp_cost = fp_cost
        self._fn_cost = fn_cost
        self._max_adjustment = max_adjustment
        self._last_report: ConfidenceTuningReport | None = None

    async def evaluate_thresholds(
        self,
        outcomes: list[PaymentOutcome],
        current: ConfidenceThresholds,
    ) -> ThresholdRecommendation:
        """Evaluate current thresholds and recommend adjustments.

        Args:
            outcomes: Resolved outcomes with confidence scores
            current: Current ConfidenceThresholds

        Returns:
            ThresholdRecommendation with suggested changes
        """
        fraud_types = {"fraud_confirmed", "disputed"}
        clean_types = {"completed", "false_positive"}

        # Compute error rates
        flagged_or_denied = [o for o in outcomes if o.decision in ("flagged", "denied")]
        approved = [o for o in outcomes if o.decision == "approved"]

        fp_count = sum(1 for o in flagged_or_denied if o.outcome_type in clean_types)
        fn_count = sum(1 for o in approved if o.outcome_type in fraud_types)

        fp_rate = fp_count / len(flagged_or_denied) if flagged_or_denied else 0
        fn_rate = fn_count / len(approved) if approved else 0

        total_cost = (fp_count * self._fp_cost) + (fn_count * self._fn_cost)

        # Determine adjustment direction
        new_auto = current.auto_approve
        new_manager = current.manager
        new_multi_sig = current.multi_sig
        reason_parts: list[str] = []

        if fn_rate > 0.02:
            # Too many false negatives — tighten thresholds (raise them)
            adjustment = min(self._max_adjustment, fn_rate * 0.5)
            new_auto = min(0.99, current.auto_approve + adjustment)
            new_manager = min(new_auto - 0.05, current.manager + adjustment * 0.5)
            reason_parts.append(f"FN rate {fn_rate:.2%} too high — tightening thresholds")

        if fp_rate > 0.20:
            # Too many false positives — loosen thresholds (lower them)
            adjustment = min(self._max_adjustment, fp_rate * 0.1)
            new_auto = max(0.80, current.auto_approve - adjustment)
            new_manager = max(0.65, current.manager - adjustment * 0.5)
            new_multi_sig = max(0.50, current.multi_sig - adjustment * 0.3)
            reason_parts.append(f"FP rate {fp_rate:.2%} too high — loosening thresholds")

        if not reason_parts:
            reason_parts.append("Thresholds within acceptable range")

        recommendation = ThresholdRecommendation(
            current_auto_approve=current.auto_approve,
            current_manager=current.manager,
            current_multi_sig=current.multi_sig,
            recommended_auto_approve=round(new_auto, 3),
            recommended_manager=round(new_manager, 3),
            recommended_multi_sig=round(new_multi_sig, 3),
            false_positive_rate=fp_rate,
            false_negative_rate=fn_rate,
            total_cost=total_cost,
            reason="; ".join(reason_parts),
        )

        self._last_report = ConfidenceTuningReport(
            recommendation=recommendation,
            outcomes_analyzed=len(outcomes),
        )

        logger.info(
            "Confidence tuner: analyzed %d outcomes, FP=%.2f%% FN=%.2f%%",
            len(outcomes), fp_rate * 100, fn_rate * 100,
        )
        return recommendation

    async def generate_report(self) -> ConfidenceTuningReport | None:
        """Get the last tuning report."""
        return self._last_report
