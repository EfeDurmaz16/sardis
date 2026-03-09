"""Outcome tracking — links payment decisions to real-world outcomes.

Records whether approved transactions completed successfully, were disputed,
or turned out to be fraudulent. Builds agent and merchant risk profiles
from this outcome data.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PaymentOutcome:
    """Links a payment decision to its real-world outcome."""
    outcome_id: str = field(default_factory=lambda: f"out_{uuid.uuid4().hex[:16]}")
    receipt_id: str = ""
    intent_id: str = ""
    decision: str = ""          # 'approved', 'denied', 'flagged'
    decision_reason: str = ""
    outcome_type: str = ""      # 'completed', 'disputed', 'refunded', 'fraud_confirmed', 'false_positive'
    outcome_data: dict[str, Any] = field(default_factory=dict)
    decided_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    agent_id: str = ""
    org_id: str = ""
    merchant_id: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    anomaly_score: float = 0.0
    confidence_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "receipt_id": self.receipt_id,
            "intent_id": self.intent_id,
            "decision": self.decision,
            "decision_reason": self.decision_reason,
            "outcome_type": self.outcome_type,
            "outcome_data": self.outcome_data,
            "decided_at": self.decided_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "agent_id": self.agent_id,
            "org_id": self.org_id,
            "merchant_id": self.merchant_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "anomaly_score": self.anomaly_score,
            "confidence_score": self.confidence_score,
        }


@dataclass
class AgentRiskProfile:
    """Compounding agent risk profile derived from outcomes."""
    agent_id: str = ""
    org_id: str = ""
    total_decisions: int = 0
    total_approved: int = 0
    total_denied: int = 0
    total_flagged: int = 0
    false_positive_count: int = 0
    true_positive_count: int = 0
    false_negative_count: int = 0
    avg_anomaly_score: float = 0.0
    avg_confidence_score: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def false_positive_rate(self) -> float:
        flagged_or_denied = self.total_flagged + self.total_denied
        if flagged_or_denied == 0:
            return 0.0
        return self.false_positive_count / flagged_or_denied

    @property
    def false_negative_rate(self) -> float:
        if self.total_approved == 0:
            return 0.0
        return self.false_negative_count / self.total_approved

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "org_id": self.org_id,
            "total_decisions": self.total_decisions,
            "total_approved": self.total_approved,
            "total_denied": self.total_denied,
            "total_flagged": self.total_flagged,
            "false_positive_count": self.false_positive_count,
            "true_positive_count": self.true_positive_count,
            "false_negative_count": self.false_negative_count,
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "avg_anomaly_score": round(self.avg_anomaly_score, 4),
            "avg_confidence_score": round(self.avg_confidence_score, 4),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class MerchantRiskProfile:
    """Merchant risk profile derived from outcomes."""
    merchant_id: str = ""
    total_transactions: int = 0
    dispute_count: int = 0
    refund_count: int = 0
    fraud_count: int = 0
    dispute_rate: float = 0.0
    risk_tier: str = "unknown"  # 'low', 'medium', 'high', 'blocked'
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_transaction: datetime | None = None
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "total_transactions": self.total_transactions,
            "dispute_count": self.dispute_count,
            "refund_count": self.refund_count,
            "fraud_count": self.fraud_count,
            "dispute_rate": round(self.dispute_rate, 4),
            "risk_tier": self.risk_tier,
            "first_seen": self.first_seen.isoformat(),
            "last_transaction": self.last_transaction.isoformat() if self.last_transaction else None,
            "last_updated": self.last_updated.isoformat(),
        }


class OutcomeTracker:
    """Tracks payment decisions and their real-world outcomes.

    In-memory implementation for dev/test. Production would use PostgreSQL
    backed by the outcome_tracking migration tables.
    """

    def __init__(self) -> None:
        self._outcomes: dict[str, PaymentOutcome] = {}
        self._agent_profiles: dict[str, AgentRiskProfile] = {}
        self._merchant_profiles: dict[str, MerchantRiskProfile] = {}

    async def record_decision(
        self,
        *,
        receipt_id: str = "",
        intent_id: str,
        decision: str,
        reason: str = "",
        agent_id: str,
        org_id: str,
        merchant_id: str = "",
        amount: Decimal = Decimal("0"),
        currency: str = "USDC",
        anomaly_score: float = 0.0,
        confidence_score: float = 0.0,
    ) -> str:
        """Record a payment decision (before outcome is known)."""
        outcome = PaymentOutcome(
            receipt_id=receipt_id,
            intent_id=intent_id,
            decision=decision,
            decision_reason=reason,
            agent_id=agent_id,
            org_id=org_id,
            merchant_id=merchant_id,
            amount=amount,
            currency=currency,
            anomaly_score=anomaly_score,
            confidence_score=confidence_score,
        )
        self._outcomes[outcome.outcome_id] = outcome

        # Update agent profile
        profile = self._get_or_create_agent_profile(agent_id, org_id)
        profile.total_decisions += 1
        if decision == "approved":
            profile.total_approved += 1
        elif decision == "denied":
            profile.total_denied += 1
        elif decision == "flagged":
            profile.total_flagged += 1
        # Running average of scores
        n = profile.total_decisions
        profile.avg_anomaly_score = ((profile.avg_anomaly_score * (n - 1)) + anomaly_score) / n
        profile.avg_confidence_score = ((profile.avg_confidence_score * (n - 1)) + confidence_score) / n
        profile.last_updated = datetime.now(UTC)

        # Update merchant profile
        if merchant_id:
            mp = self._get_or_create_merchant_profile(merchant_id)
            mp.total_transactions += 1
            mp.last_transaction = datetime.now(UTC)
            mp.last_updated = datetime.now(UTC)

        logger.info(
            "Decision recorded: outcome_id=%s decision=%s agent=%s",
            outcome.outcome_id, decision, agent_id,
        )
        return outcome.outcome_id

    async def record_outcome(
        self,
        outcome_id: str,
        outcome_type: str,
        outcome_data: dict[str, Any] | None = None,
    ) -> None:
        """Record the real-world outcome of a previous decision."""
        outcome = self._outcomes.get(outcome_id)
        if not outcome:
            raise ValueError(f"Outcome not found: {outcome_id}")

        outcome.outcome_type = outcome_type
        outcome.outcome_data = outcome_data or {}
        outcome.resolved_at = datetime.now(UTC)

        # Update profiles based on outcome
        profile = self._get_or_create_agent_profile(outcome.agent_id, outcome.org_id)
        if outcome_type in ("disputed", "fraud_confirmed"):
            if outcome.decision == "approved":
                profile.false_negative_count += 1
            elif outcome.decision in ("denied", "flagged"):
                profile.true_positive_count += 1
        elif outcome_type in ("completed", "false_positive"):
            if outcome.decision in ("denied", "flagged"):
                profile.false_positive_count += 1
        profile.last_updated = datetime.now(UTC)

        # Update merchant profile
        if outcome.merchant_id:
            mp = self._get_or_create_merchant_profile(outcome.merchant_id)
            if outcome_type == "disputed":
                mp.dispute_count += 1
            elif outcome_type == "refunded":
                mp.refund_count += 1
            elif outcome_type == "fraud_confirmed":
                mp.fraud_count += 1
            # Recompute dispute rate
            if mp.total_transactions > 0:
                mp.dispute_rate = (mp.dispute_count + mp.fraud_count) / mp.total_transactions
            # Update risk tier
            mp.risk_tier = self._compute_risk_tier(mp)
            mp.last_updated = datetime.now(UTC)

        logger.info(
            "Outcome recorded: outcome_id=%s type=%s agent=%s",
            outcome_id, outcome_type, outcome.agent_id,
        )

    async def get_outcome(self, outcome_id: str) -> PaymentOutcome | None:
        return self._outcomes.get(outcome_id)

    async def get_agent_profile(self, agent_id: str) -> AgentRiskProfile | None:
        return self._agent_profiles.get(agent_id)

    async def get_merchant_profile(self, merchant_id: str) -> MerchantRiskProfile | None:
        return self._merchant_profiles.get(merchant_id)

    async def compute_agent_stats(self, agent_id: str) -> dict[str, Any]:
        """Compute aggregated stats from all outcomes for an agent."""
        outcomes = [o for o in self._outcomes.values() if o.agent_id == agent_id]
        if not outcomes:
            return {"agent_id": agent_id, "total_outcomes": 0}

        resolved = [o for o in outcomes if o.resolved_at is not None]
        return {
            "agent_id": agent_id,
            "total_outcomes": len(outcomes),
            "resolved_outcomes": len(resolved),
            "pending_outcomes": len(outcomes) - len(resolved),
            "approved_count": sum(1 for o in outcomes if o.decision == "approved"),
            "denied_count": sum(1 for o in outcomes if o.decision == "denied"),
            "flagged_count": sum(1 for o in outcomes if o.decision == "flagged"),
            "fraud_count": sum(1 for o in resolved if o.outcome_type == "fraud_confirmed"),
            "dispute_count": sum(1 for o in resolved if o.outcome_type == "disputed"),
            "total_amount": str(sum(o.amount for o in outcomes)),
        }

    def _get_or_create_agent_profile(self, agent_id: str, org_id: str) -> AgentRiskProfile:
        if agent_id not in self._agent_profiles:
            self._agent_profiles[agent_id] = AgentRiskProfile(agent_id=agent_id, org_id=org_id)
        return self._agent_profiles[agent_id]

    def _get_or_create_merchant_profile(self, merchant_id: str) -> MerchantRiskProfile:
        if merchant_id not in self._merchant_profiles:
            self._merchant_profiles[merchant_id] = MerchantRiskProfile(merchant_id=merchant_id)
        return self._merchant_profiles[merchant_id]

    @staticmethod
    def _compute_risk_tier(profile: MerchantRiskProfile) -> str:
        if profile.fraud_count > 0:
            return "high"
        if profile.dispute_rate > 0.05:
            return "high"
        if profile.dispute_rate > 0.02:
            return "medium"
        if profile.total_transactions >= 10:
            return "low"
        return "unknown"
