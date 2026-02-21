"""KYA Trust Scoring — Unified agent trust scoring system.

Aggregates multiple trust signals into a single trust score:
  1. KYA Level (identity verification depth)
  2. Transaction History (volume, frequency, success rate)
  3. Compliance Status (sanctions, KYC, violations)
  4. Reputation (ratings from counterparties)
  5. Behavioral Consistency (goal drift, anomaly detection)

Trust scores directly map to spending capabilities:
  0.0-0.3  → UNTRUSTED  ($10/tx,   $25/day)
  0.3-0.5  → LOW        ($50/tx,   $100/day)
  0.5-0.7  → MEDIUM     ($500/tx,  $1k/day)
  0.7-0.9  → HIGH       ($5k/tx,   $10k/day)
  0.9-1.0  → SOVEREIGN  ($50k/tx,  $100k/day)

Usage:
    from sardis_v2_core.kya_trust_scoring import TrustScorer, TrustScore

    scorer = TrustScorer()
    score = await scorer.calculate_trust(
        agent_id="agent_123",
        kya_level=KYALevel.VERIFIED,
        history=transaction_history,
    )
    print(f"Trust: {score.overall} ({score.tier})")
    print(f"Spending limit: ${score.max_per_tx}")
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sardis.core.trust_scoring")


# ============ Enums ============


class TrustTier(str, Enum):
    """Trust tier determines spending capabilities."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SOVEREIGN = "sovereign"


class KYALevel(str, Enum):
    """KYA verification level (mirrors sardis_compliance.kya.KYALevel)."""
    NONE = "none"
    BASIC = "basic"
    VERIFIED = "verified"
    ATTESTED = "attested"


# ============ Configuration ============


TRUST_TIER_THRESHOLDS = {
    TrustTier.UNTRUSTED: 0.0,
    TrustTier.LOW: 0.3,
    TrustTier.MEDIUM: 0.5,
    TrustTier.HIGH: 0.7,
    TrustTier.SOVEREIGN: 0.9,
}

TRUST_TIER_LIMITS = {
    TrustTier.UNTRUSTED: {"max_per_tx": Decimal("10"), "max_per_day": Decimal("25")},
    TrustTier.LOW: {"max_per_tx": Decimal("50"), "max_per_day": Decimal("100")},
    TrustTier.MEDIUM: {"max_per_tx": Decimal("500"), "max_per_day": Decimal("1000")},
    TrustTier.HIGH: {"max_per_tx": Decimal("5000"), "max_per_day": Decimal("10000")},
    TrustTier.SOVEREIGN: {"max_per_tx": Decimal("50000"), "max_per_day": Decimal("100000")},
}

KYA_LEVEL_SCORES = {
    KYALevel.NONE: 0.0,
    KYALevel.BASIC: 0.3,
    KYALevel.VERIFIED: 0.7,
    KYALevel.ATTESTED: 1.0,
}

# Weight configuration for trust components
DEFAULT_WEIGHTS = {
    "kya_level": 0.30,
    "transaction_history": 0.25,
    "compliance_status": 0.20,
    "reputation": 0.15,
    "behavioral_consistency": 0.10,
}


# ============ Data Models ============


@dataclass
class TrustSignal:
    """A single trust signal with score and metadata."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TrustScore:
    """Aggregated trust score with breakdown."""
    agent_id: str
    overall: float  # 0.0 to 1.0
    tier: TrustTier
    max_per_tx: Decimal
    max_per_day: Decimal
    signals: List[TrustSignal] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "overall": round(self.overall, 4),
            "tier": self.tier.value,
            "max_per_tx": str(self.max_per_tx),
            "max_per_day": str(self.max_per_day),
            "signals": [
                {
                    "name": s.name,
                    "score": round(s.score, 4),
                    "weight": s.weight,
                    "details": s.details,
                }
                for s in self.signals
            ],
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class TransactionRecord:
    """Summary of an agent's transaction history."""
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    disputed_count: int = 0
    total_volume: Decimal = Decimal("0")
    avg_amount: Decimal = Decimal("0")
    unique_merchants: int = 0
    days_active: int = 0
    last_transaction_at: Optional[datetime] = None


@dataclass
class ComplianceRecord:
    """Agent's compliance status summary."""
    kyc_verified: bool = False
    sanctions_clear: bool = True
    violation_count: int = 0
    last_violation_at: Optional[datetime] = None
    aml_flagged: bool = False
    pep_flagged: bool = False


@dataclass
class ReputationRecord:
    """Agent's reputation from counterparty ratings."""
    total_ratings: int = 0
    average_rating: float = 0.0  # 1.0 to 5.0
    positive_ratings: int = 0
    negative_ratings: int = 0
    escrows_completed: int = 0
    escrows_disputed: int = 0


@dataclass
class BehavioralRecord:
    """Agent's behavioral consistency metrics."""
    goal_drift_score: float = 0.0  # 0.0 = no drift, 1.0 = max drift
    anomaly_count: int = 0
    circuit_breaker_trips: int = 0
    spending_pattern_consistency: float = 1.0  # 1.0 = perfectly consistent


# ============ Trust Scorer ============


class TrustScorer:
    """Calculates unified trust scores for agents.

    Combines multiple trust signals with configurable weights to produce
    a single trust score that determines spending capabilities.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        cache_ttl_seconds: int = 300,
    ):
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        self._cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, TrustScore] = {}

        # Validate weights sum to ~1.0
        total = sum(self._weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Trust weights must sum to 1.0, got {total}")

    async def calculate_trust(
        self,
        agent_id: str,
        kya_level: KYALevel = KYALevel.NONE,
        history: Optional[TransactionRecord] = None,
        compliance: Optional[ComplianceRecord] = None,
        reputation: Optional[ReputationRecord] = None,
        behavioral: Optional[BehavioralRecord] = None,
        use_cache: bool = True,
    ) -> TrustScore:
        """Calculate unified trust score for an agent.

        Args:
            agent_id: Agent identifier
            kya_level: Current KYA verification level
            history: Transaction history summary
            compliance: Compliance status
            reputation: Counterparty reputation
            behavioral: Behavioral consistency metrics
            use_cache: Whether to use cached scores

        Returns:
            TrustScore with overall score, tier, and signal breakdown
        """
        # Check cache
        if use_cache and agent_id in self._cache:
            cached = self._cache[agent_id]
            if not cached.is_expired:
                return cached

        signals: List[TrustSignal] = []

        # 1. KYA Level Score
        kya_score = self._score_kya_level(kya_level)
        signals.append(kya_score)

        # 2. Transaction History Score
        history_score = self._score_transaction_history(history or TransactionRecord())
        signals.append(history_score)

        # 3. Compliance Status Score
        compliance_score = self._score_compliance(compliance or ComplianceRecord())
        signals.append(compliance_score)

        # 4. Reputation Score
        reputation_score = self._score_reputation(reputation or ReputationRecord())
        signals.append(reputation_score)

        # 5. Behavioral Consistency Score
        behavioral_score = self._score_behavioral(behavioral or BehavioralRecord())
        signals.append(behavioral_score)

        # Calculate weighted overall score
        overall = sum(s.score * s.weight for s in signals)
        overall = max(0.0, min(1.0, overall))

        # Determine trust tier
        tier = self._get_tier(overall)
        limits = TRUST_TIER_LIMITS[tier]

        score = TrustScore(
            agent_id=agent_id,
            overall=overall,
            tier=tier,
            max_per_tx=limits["max_per_tx"],
            max_per_day=limits["max_per_day"],
            signals=signals,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self._cache_ttl),
        )

        # Cache the score
        self._cache[agent_id] = score

        logger.info(
            "Trust score calculated",
            extra={
                "agent_id": agent_id,
                "overall": round(overall, 4),
                "tier": tier.value,
            },
        )

        return score

    def invalidate_cache(self, agent_id: Optional[str] = None) -> None:
        """Invalidate cached trust scores."""
        if agent_id:
            self._cache.pop(agent_id, None)
        else:
            self._cache.clear()

    def _score_kya_level(self, level: KYALevel) -> TrustSignal:
        """Score based on KYA verification level."""
        score = KYA_LEVEL_SCORES.get(level, 0.0)
        return TrustSignal(
            name="kya_level",
            score=score,
            weight=self._weights["kya_level"],
            details={"level": level.value},
        )

    def _score_transaction_history(self, history: TransactionRecord) -> TrustSignal:
        """Score based on transaction history.

        Higher scores for:
        - More successful transactions
        - Higher success rate
        - More unique merchants (diversity)
        - Longer active history
        """
        if history.total_count == 0:
            return TrustSignal(
                name="transaction_history",
                score=0.0,
                weight=self._weights["transaction_history"],
                details={"reason": "no_history"},
            )

        # Success rate (0-1)
        success_rate = (
            history.success_count / history.total_count
            if history.total_count > 0
            else 0.0
        )

        # Volume score - logarithmic scaling (0-1)
        volume_score = min(1.0, math.log10(float(history.total_volume) + 1) / 6.0)

        # Diversity score - unique merchants (0-1)
        diversity_score = min(1.0, history.unique_merchants / 20.0)

        # Longevity score - days active (0-1)
        longevity_score = min(1.0, history.days_active / 90.0)

        # Weighted combination
        score = (
            success_rate * 0.40
            + volume_score * 0.25
            + diversity_score * 0.20
            + longevity_score * 0.15
        )

        # Penalty for disputes
        if history.disputed_count > 0:
            dispute_ratio = history.disputed_count / history.total_count
            score *= 1.0 - (dispute_ratio * 0.5)

        return TrustSignal(
            name="transaction_history",
            score=max(0.0, min(1.0, score)),
            weight=self._weights["transaction_history"],
            details={
                "total_transactions": history.total_count,
                "success_rate": round(success_rate, 4),
                "volume_score": round(volume_score, 4),
                "diversity_score": round(diversity_score, 4),
                "longevity_score": round(longevity_score, 4),
            },
        )

    def _score_compliance(self, compliance: ComplianceRecord) -> TrustSignal:
        """Score based on compliance status.

        Binary penalties for critical flags, graduated for violations.
        """
        score = 1.0

        # Hard penalties
        if compliance.aml_flagged:
            score = 0.0
        elif compliance.pep_flagged:
            score *= 0.3
        elif not compliance.sanctions_clear:
            score = 0.0

        # Graduated penalty for violations
        if compliance.violation_count > 0:
            penalty = min(0.8, compliance.violation_count * 0.15)
            score *= 1.0 - penalty

        # Bonus for KYC verification
        if compliance.kyc_verified:
            score = min(1.0, score * 1.2)

        # Recency penalty for recent violations
        if compliance.last_violation_at:
            days_since = (datetime.now(timezone.utc) - compliance.last_violation_at).days
            if days_since < 7:
                score *= 0.5
            elif days_since < 30:
                score *= 0.7

        return TrustSignal(
            name="compliance_status",
            score=max(0.0, min(1.0, score)),
            weight=self._weights["compliance_status"],
            details={
                "kyc_verified": compliance.kyc_verified,
                "sanctions_clear": compliance.sanctions_clear,
                "violation_count": compliance.violation_count,
                "aml_flagged": compliance.aml_flagged,
            },
        )

    def _score_reputation(self, reputation: ReputationRecord) -> TrustSignal:
        """Score based on counterparty reputation.

        Higher for more positive ratings and successful escrows.
        """
        if reputation.total_ratings == 0:
            # No reputation = neutral (not penalized, not rewarded)
            return TrustSignal(
                name="reputation",
                score=0.5,
                weight=self._weights["reputation"],
                details={"reason": "no_ratings"},
            )

        # Normalize rating from 1-5 to 0-1
        rating_score = (reputation.average_rating - 1.0) / 4.0

        # Escrow completion rate
        total_escrows = reputation.escrows_completed + reputation.escrows_disputed
        escrow_score = (
            reputation.escrows_completed / total_escrows
            if total_escrows > 0
            else 0.5
        )

        # Confidence factor - more ratings = more reliable score
        confidence = min(1.0, reputation.total_ratings / 50.0)

        # Blend toward 0.5 when confidence is low
        score = rating_score * confidence + 0.5 * (1.0 - confidence)

        # Adjust with escrow score
        score = score * 0.7 + escrow_score * 0.3

        return TrustSignal(
            name="reputation",
            score=max(0.0, min(1.0, score)),
            weight=self._weights["reputation"],
            details={
                "average_rating": round(reputation.average_rating, 2),
                "total_ratings": reputation.total_ratings,
                "escrow_completion_rate": round(escrow_score, 4),
                "confidence": round(confidence, 4),
            },
        )

    def _score_behavioral(self, behavioral: BehavioralRecord) -> TrustSignal:
        """Score based on behavioral consistency.

        Penalizes goal drift, anomalies, and circuit breaker trips.
        """
        score = behavioral.spending_pattern_consistency

        # Penalty for goal drift (0.0 is best, 1.0 is worst)
        score *= 1.0 - (behavioral.goal_drift_score * 0.4)

        # Penalty for anomalies
        if behavioral.anomaly_count > 0:
            anomaly_penalty = min(0.5, behavioral.anomaly_count * 0.1)
            score *= 1.0 - anomaly_penalty

        # Penalty for circuit breaker trips
        if behavioral.circuit_breaker_trips > 0:
            cb_penalty = min(0.6, behavioral.circuit_breaker_trips * 0.2)
            score *= 1.0 - cb_penalty

        return TrustSignal(
            name="behavioral_consistency",
            score=max(0.0, min(1.0, score)),
            weight=self._weights["behavioral_consistency"],
            details={
                "goal_drift": round(behavioral.goal_drift_score, 4),
                "anomaly_count": behavioral.anomaly_count,
                "circuit_breaker_trips": behavioral.circuit_breaker_trips,
                "pattern_consistency": round(behavioral.spending_pattern_consistency, 4),
            },
        )

    @staticmethod
    def _get_tier(score: float) -> TrustTier:
        """Map overall score to trust tier."""
        if score >= 0.9:
            return TrustTier.SOVEREIGN
        elif score >= 0.7:
            return TrustTier.HIGH
        elif score >= 0.5:
            return TrustTier.MEDIUM
        elif score >= 0.3:
            return TrustTier.LOW
        else:
            return TrustTier.UNTRUSTED
