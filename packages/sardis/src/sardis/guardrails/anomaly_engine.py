"""Anomaly scoring engine that combines multiple risk signals into a unified risk score.

Aggregates behavioral alerts and transaction context signals into a single risk
assessment and determines the appropriate control-plane action.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from .behavioral_monitor import AlertSeverity, BehavioralAlert


class RiskAction(Enum):
    """Action to take based on risk score."""

    ALLOW = "allow"                          # score < 0.3
    FLAG = "flag"                            # 0.3 <= score < 0.6
    REQUIRE_APPROVAL = "require_approval"    # 0.6 <= score < 0.8
    FREEZE_AGENT = "freeze_agent"            # 0.8 <= score < 0.95
    KILL_SWITCH = "kill_switch"              # score >= 0.95


@dataclass
class RiskSignal:
    """Individual risk signal contributing to the overall score."""

    signal_type: str   # e.g. "amount_anomaly", "velocity", "new_merchant", "time_anomaly"
    weight: float      # 0.0-1.0
    score: float       # 0.0-1.0
    description: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """Combined risk assessment from multiple signals."""

    agent_id: str
    overall_score: float   # 0.0-1.0
    action: RiskAction
    signals: list[RiskSignal]
    timestamp: datetime
    transaction_amount: Decimal | None = None
    transaction_merchant: str | None = None


class AnomalyEngine:
    """Combines multiple anomaly signals into a risk score and determines action.

    Weights are normalised so that they always sum to 1.0 even if a caller
    supplies a subset of signals.

    Example::

        engine = AnomalyEngine()
        assessment = engine.assess_risk(
            agent_id="agent-123",
            amount=Decimal("5000.00"),
            merchant_id="merchant-xyz",
            baseline_mean=200.0,
            baseline_std=50.0,
            recent_tx_count_1h=15,
            is_new_merchant=True,
            hour_of_day=3,
            typical_hours={9, 10, 11, 14, 15, 16},
        )
        print(assessment.action)
    """

    # Default signal weights (must sum to 1.0)
    WEIGHTS: dict[str, float] = {
        "amount_anomaly": 0.30,
        "velocity": 0.25,
        "new_merchant": 0.15,
        "time_anomaly": 0.10,
        "merchant_category": 0.10,
        "behavioral_alerts": 0.10,
    }

    # Velocity thresholds (transactions per hour)
    _VELOCITY_LOW = 5     # score starts rising
    _VELOCITY_HIGH = 20   # score caps at 1.0

    # Severity → numeric contribution for behavioral alerts
    _SEVERITY_SCORE: dict[AlertSeverity, float] = {
        AlertSeverity.LOW: 0.2,
        AlertSeverity.MEDIUM: 0.5,
        AlertSeverity.HIGH: 0.8,
        AlertSeverity.CRITICAL: 1.0,
    }

    # High-risk merchant categories
    _HIGH_RISK_CATEGORIES: frozenset[str] = frozenset(
        {
            "gambling",
            "crypto_exchange",
            "money_transfer",
            "adult_content",
            "weapons",
            "drugs",
            "shell_company",
        }
    )

    def assess_risk(
        self,
        agent_id: str,
        amount: Decimal,
        merchant_id: str | None = None,
        merchant_category: str | None = None,
        behavioral_alerts: list[BehavioralAlert] | None = None,
        baseline_mean: float | None = None,
        baseline_std: float | None = None,
        recent_tx_count_1h: int = 0,
        is_new_merchant: bool = False,
        hour_of_day: int | None = None,
        typical_hours: set[int] | None = None,
    ) -> RiskAssessment:
        """Assess risk from multiple signals and return a unified assessment.

        Args:
            agent_id: Unique identifier of the agent.
            amount: Transaction amount.
            merchant_id: Optional merchant identifier.
            merchant_category: Optional merchant category code / slug.
            behavioral_alerts: Alerts raised by :class:`BehavioralMonitor`.
            baseline_mean: Agent's historical mean transaction amount.
            baseline_std: Agent's historical transaction amount std deviation.
            recent_tx_count_1h: Number of transactions in the last hour.
            is_new_merchant: True if this is the agent's first tx with the merchant.
            hour_of_day: UTC hour (0-23) of the transaction.
            typical_hours: Set of hours the agent normally transacts in.

        Returns:
            :class:`RiskAssessment` with overall score, action, and signal breakdown.
        """
        signals: list[RiskSignal] = [
            self._score_amount_anomaly(amount, baseline_mean, baseline_std),
            self._score_velocity(recent_tx_count_1h),
            self._score_new_merchant(is_new_merchant),
            self._score_time_anomaly(hour_of_day, typical_hours),
            self._score_merchant_category(merchant_category),
            self._score_behavioral_alerts(behavioral_alerts),
        ]

        # Weighted average
        total_weight = sum(self.WEIGHTS.get(s.signal_type, 0.0) for s in signals)
        if total_weight == 0.0:
            overall_score = 0.0
        else:
            overall_score = sum(
                s.score * self.WEIGHTS.get(s.signal_type, 0.0) for s in signals
            ) / total_weight

        # Clamp to [0, 1]
        overall_score = max(0.0, min(1.0, overall_score))

        return RiskAssessment(
            agent_id=agent_id,
            overall_score=overall_score,
            action=self._determine_action(overall_score),
            signals=signals,
            timestamp=datetime.now(UTC),
            transaction_amount=amount,
            transaction_merchant=merchant_id,
        )

    # ------------------------------------------------------------------
    # Individual signal scorers
    # ------------------------------------------------------------------

    def _score_amount_anomaly(
        self,
        amount: Decimal,
        mean: float | None,
        std: float | None,
    ) -> RiskSignal:
        """Z-score based amount anomaly signal.

        Returns 0.0 when there is insufficient baseline data, scales to 1.0
        as the z-score climbs above 4 standard deviations.
        """
        if mean is None or std is None or std <= 0:
            return RiskSignal(
                signal_type="amount_anomaly",
                weight=self.WEIGHTS["amount_anomaly"],
                score=0.0,
                description="No baseline data available for amount anomaly scoring.",
                metadata={"amount": str(amount)},
            )

        z = abs(float(amount) - mean) / std
        # Logistic-style scale: z=0 → 0, z=2 → ~0.27, z=4 → ~0.88, z=6 → ~1.0
        score = 1.0 - math.exp(-z / 3.0) if z > 0 else 0.0
        score = max(0.0, min(1.0, score))

        return RiskSignal(
            signal_type="amount_anomaly",
            weight=self.WEIGHTS["amount_anomaly"],
            score=score,
            description=(
                f"Amount {amount} is {z:.2f} standard deviations from baseline mean "
                f"{mean:.2f} (std={std:.2f})."
            ),
            metadata={"amount": str(amount), "mean": mean, "std": std, "z_score": z},
        )

    def _score_velocity(self, recent_tx_count: int) -> RiskSignal:
        """Rate-of-transactions signal over the last hour.

        Score is 0 below the low threshold, linearly rises to 1.0 at the high
        threshold, and stays at 1.0 above it.
        """
        low, high = self._VELOCITY_LOW, self._VELOCITY_HIGH

        if recent_tx_count <= low:
            score = 0.0
        elif recent_tx_count >= high:
            score = 1.0
        else:
            score = (recent_tx_count - low) / (high - low)

        return RiskSignal(
            signal_type="velocity",
            weight=self.WEIGHTS["velocity"],
            score=score,
            description=(
                f"{recent_tx_count} transactions in the last hour "
                f"(low={low}, high={high})."
            ),
            metadata={"recent_tx_count_1h": recent_tx_count},
        )

    def _score_new_merchant(self, is_new: bool) -> RiskSignal:
        """First-seen merchant risk signal."""
        score = 0.5 if is_new else 0.0
        return RiskSignal(
            signal_type="new_merchant",
            weight=self.WEIGHTS["new_merchant"],
            score=score,
            description="First transaction with this merchant." if is_new else "Known merchant.",
            metadata={"is_new_merchant": is_new},
        )

    def _score_time_anomaly(
        self,
        hour: int | None,
        typical: set[int] | None,
    ) -> RiskSignal:
        """Transaction-at-unusual-time signal.

        If the current hour is outside the agent's typical hours the score is
        0.7; if we have no data the score is 0.0.
        """
        if hour is None or not typical:
            return RiskSignal(
                signal_type="time_anomaly",
                weight=self.WEIGHTS["time_anomaly"],
                score=0.0,
                description="No time-of-day baseline available.",
                metadata={},
            )

        is_unusual = hour not in typical
        score = 0.7 if is_unusual else 0.0
        return RiskSignal(
            signal_type="time_anomaly",
            weight=self.WEIGHTS["time_anomaly"],
            score=score,
            description=(
                f"Transaction at hour {hour} is "
                f"{'outside' if is_unusual else 'within'} typical hours {sorted(typical)}."
            ),
            metadata={
                "hour_of_day": hour,
                "typical_hours": sorted(typical),
                "is_unusual": is_unusual,
            },
        )

    def _score_merchant_category(self, category: str | None) -> RiskSignal:
        """High-risk merchant category signal."""
        if category is None:
            return RiskSignal(
                signal_type="merchant_category",
                weight=self.WEIGHTS["merchant_category"],
                score=0.0,
                description="No merchant category provided.",
                metadata={},
            )

        normalised = category.lower().replace(" ", "_").replace("-", "_")
        is_high_risk = normalised in self._HIGH_RISK_CATEGORIES
        score = 0.9 if is_high_risk else 0.0
        return RiskSignal(
            signal_type="merchant_category",
            weight=self.WEIGHTS["merchant_category"],
            score=score,
            description=(
                f"Merchant category '{category}' is "
                f"{'high-risk' if is_high_risk else 'not high-risk'}."
            ),
            metadata={"category": category, "is_high_risk": is_high_risk},
        )

    def _score_behavioral_alerts(
        self,
        alerts: list[BehavioralAlert] | None,
    ) -> RiskSignal:
        """Aggregate behavioral monitor alerts into a single signal.

        Takes the maximum severity score across all alerts so that a single
        CRITICAL alert produces a full-score signal.
        """
        if not alerts:
            return RiskSignal(
                signal_type="behavioral_alerts",
                weight=self.WEIGHTS["behavioral_alerts"],
                score=0.0,
                description="No behavioral alerts.",
                metadata={"alert_count": 0},
            )

        max_score = max(
            self._SEVERITY_SCORE.get(alert.severity, 0.0) for alert in alerts
        )
        severity_counts: dict[str, int] = {}
        for alert in alerts:
            key = alert.severity.value
            severity_counts[key] = severity_counts.get(key, 0) + 1

        return RiskSignal(
            signal_type="behavioral_alerts",
            weight=self.WEIGHTS["behavioral_alerts"],
            score=max_score,
            description=(
                f"{len(alerts)} behavioral alert(s); "
                f"highest severity: {max(alerts, key=lambda a: self._SEVERITY_SCORE.get(a.severity, 0.0)).severity.value}."
            ),
            metadata={
                "alert_count": len(alerts),
                "severity_counts": severity_counts,
                "max_score": max_score,
            },
        )

    def _determine_action(self, score: float) -> RiskAction:
        """Map overall risk score to a control-plane action.

        Thresholds::

            score < 0.30  → ALLOW
            score < 0.60  → FLAG
            score < 0.80  → REQUIRE_APPROVAL
            score < 0.95  → FREEZE_AGENT
            score >= 0.95 → KILL_SWITCH
        """
        if score < 0.30:
            return RiskAction.ALLOW
        if score < 0.60:
            return RiskAction.FLAG
        if score < 0.80:
            return RiskAction.REQUIRE_APPROVAL
        if score < 0.95:
            return RiskAction.FREEZE_AGENT
        return RiskAction.KILL_SWITCH


# Singleton instance for global access (mirrors kill_switch pattern)
_global_anomaly_engine: AnomalyEngine | None = None


def get_anomaly_engine() -> AnomalyEngine:
    """Get the global AnomalyEngine singleton instance."""
    global _global_anomaly_engine
    if _global_anomaly_engine is None:
        _global_anomaly_engine = AnomalyEngine()
    return _global_anomaly_engine
