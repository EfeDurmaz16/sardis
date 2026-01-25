"""
Enhanced risk scoring module.

Provides comprehensive risk assessment with:
- Multi-factor risk scoring
- Configurable risk weights
- Risk category aggregation
- Transaction velocity analysis
- Geographic risk assessment
- Behavioral pattern analysis
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class RiskCategory(str, Enum):
    """Categories of risk factors."""
    TRANSACTION = "transaction"  # Amount, frequency, patterns
    COUNTERPARTY = "counterparty"  # Who they transact with
    GEOGRAPHIC = "geographic"  # Location-based risks
    BEHAVIORAL = "behavioral"  # Unusual patterns
    REGULATORY = "regulatory"  # KYC/AML requirements
    SANCTIONS = "sanctions"  # Sanctions screening results
    PEP = "pep"  # Politically Exposed Persons


class RiskLevel(str, Enum):
    """Overall risk level classification."""
    MINIMAL = "minimal"  # Score 0-20
    LOW = "low"  # Score 21-40
    MEDIUM = "medium"  # Score 41-60
    HIGH = "high"  # Score 61-80
    CRITICAL = "critical"  # Score 81-100


class RiskAction(str, Enum):
    """Recommended actions based on risk level."""
    APPROVE = "approve"  # Auto-approve
    REVIEW = "review"  # Manual review required
    ENHANCED_DUE_DILIGENCE = "edd"  # Enhanced due diligence
    BLOCK = "block"  # Block transaction
    ESCALATE = "escalate"  # Escalate to compliance officer


@dataclass
class RiskFactor:
    """A single risk factor contributing to overall score."""
    category: RiskCategory
    name: str
    score: float  # 0-100
    weight: float = 1.0  # Multiplier for importance
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score."""
        return min(100, self.score * self.weight)


@dataclass
class RiskAssessment:
    """Complete risk assessment result."""
    subject_id: str
    overall_score: float  # 0-100
    risk_level: RiskLevel
    recommended_action: RiskAction
    factors: List[RiskFactor] = field(default_factory=list)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def by_category(self) -> Dict[RiskCategory, List[RiskFactor]]:
        """Group factors by category."""
        result: Dict[RiskCategory, List[RiskFactor]] = {}
        for factor in self.factors:
            if factor.category not in result:
                result[factor.category] = []
            result[factor.category].append(factor)
        return result

    @property
    def highest_risk_factors(self) -> List[RiskFactor]:
        """Get factors with highest weighted scores."""
        return sorted(self.factors, key=lambda f: f.weighted_score, reverse=True)[:5]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject_id": self.subject_id,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level.value,
            "recommended_action": self.recommended_action.value,
            "factors": [
                {
                    "category": f.category.value,
                    "name": f.name,
                    "score": f.score,
                    "weight": f.weight,
                    "weighted_score": f.weighted_score,
                    "description": f.description,
                }
                for f in self.factors
            ],
            "assessed_at": self.assessed_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class RiskConfig:
    """Configuration for risk scoring."""
    # Category weights (how important each category is)
    category_weights: Dict[RiskCategory, float] = field(default_factory=lambda: {
        RiskCategory.SANCTIONS: 2.0,  # Highest priority
        RiskCategory.PEP: 1.5,
        RiskCategory.REGULATORY: 1.3,
        RiskCategory.GEOGRAPHIC: 1.2,
        RiskCategory.COUNTERPARTY: 1.1,
        RiskCategory.TRANSACTION: 1.0,
        RiskCategory.BEHAVIORAL: 1.0,
    })

    # Thresholds for risk levels
    level_thresholds: Dict[RiskLevel, float] = field(default_factory=lambda: {
        RiskLevel.MINIMAL: 20,
        RiskLevel.LOW: 40,
        RiskLevel.MEDIUM: 60,
        RiskLevel.HIGH: 80,
        RiskLevel.CRITICAL: 100,
    })

    # Thresholds for actions
    action_thresholds: Dict[RiskAction, float] = field(default_factory=lambda: {
        RiskAction.APPROVE: 30,
        RiskAction.REVIEW: 50,
        RiskAction.ENHANCED_DUE_DILIGENCE: 70,
        RiskAction.BLOCK: 85,
        RiskAction.ESCALATE: 95,
    })

    # Transaction limits
    high_value_threshold: Decimal = Decimal("10000")  # $10,000
    velocity_window_hours: int = 24
    max_transactions_per_window: int = 50
    max_amount_per_window: Decimal = Decimal("100000")  # $100,000

    # Geographic risk
    high_risk_countries: Set[str] = field(default_factory=lambda: {
        "KP", "IR", "SY", "CU", "VE", "MM", "BY", "RU",  # Sanctioned countries
        "AF", "YE", "SO", "LY", "SD", "SS", "CF",  # High-risk jurisdictions
    })
    medium_risk_countries: Set[str] = field(default_factory=lambda: {
        "PK", "NG", "BD", "KH", "LA", "VN", "PH",  # Elevated risk
    })


class TransactionVelocityMonitor:
    """
    Monitors transaction velocity for AML compliance.

    Tracks transaction frequency and volume over time windows
    to detect structuring and unusual patterns.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self._config = config or RiskConfig()
        self._transactions: Dict[str, List[tuple[datetime, Decimal]]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_transaction(
        self,
        subject_id: str,
        amount: Decimal,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record a transaction for velocity tracking."""
        timestamp = timestamp or datetime.now(timezone.utc)

        with self._lock:
            self._transactions[subject_id].append((timestamp, amount))
            # Cleanup old transactions
            self._cleanup_old_transactions(subject_id)

    def _cleanup_old_transactions(self, subject_id: str) -> None:
        """Remove transactions outside the monitoring window."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._config.velocity_window_hours * 2)
        self._transactions[subject_id] = [
            (ts, amt) for ts, amt in self._transactions[subject_id]
            if ts > cutoff
        ]

    def get_velocity_metrics(
        self,
        subject_id: str,
        window_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get velocity metrics for a subject."""
        window = window_hours or self._config.velocity_window_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window)

        with self._lock:
            recent = [
                (ts, amt) for ts, amt in self._transactions.get(subject_id, [])
                if ts > cutoff
            ]

        if not recent:
            return {
                "transaction_count": 0,
                "total_amount": Decimal("0"),
                "average_amount": Decimal("0"),
                "max_amount": Decimal("0"),
                "velocity_score": 0.0,
            }

        amounts = [amt for _, amt in recent]
        total = sum(amounts, Decimal("0"))
        avg = total / len(amounts) if amounts else Decimal("0")
        max_amt = max(amounts) if amounts else Decimal("0")

        # Calculate velocity score (0-100)
        count_ratio = len(recent) / self._config.max_transactions_per_window
        amount_ratio = float(total) / float(self._config.max_amount_per_window)
        velocity_score = min(100, (count_ratio + amount_ratio) * 50)

        return {
            "transaction_count": len(recent),
            "total_amount": total,
            "average_amount": avg,
            "max_amount": max_amt,
            "velocity_score": velocity_score,
            "window_hours": window,
        }

    def assess_velocity_risk(self, subject_id: str) -> RiskFactor:
        """Assess velocity-based risk for a subject."""
        metrics = self.get_velocity_metrics(subject_id)

        score = metrics["velocity_score"]
        description = f"{metrics['transaction_count']} transactions totaling ${metrics['total_amount']:.2f} in {metrics['window_hours']}h"

        # Check for structuring patterns
        if metrics["transaction_count"] >= 10:
            amounts = [amt for _, amt in self._transactions.get(subject_id, [])]
            if self._detect_structuring(amounts):
                score = min(100, score + 30)
                description += " - Potential structuring detected"

        return RiskFactor(
            category=RiskCategory.TRANSACTION,
            name="velocity",
            score=score,
            description=description,
            evidence=metrics,
        )

    def _detect_structuring(self, amounts: List[Decimal]) -> bool:
        """Detect potential structuring (breaking up transactions)."""
        if len(amounts) < 5:
            return False

        # Check for multiple transactions just under $10,000
        suspicious_count = sum(
            1 for amt in amounts
            if Decimal("9000") <= amt < Decimal("10000")
        )

        # If 3+ transactions are just under the CTR threshold, flag as suspicious
        return suspicious_count >= 3


class GeographicRiskAssessor:
    """
    Assesses geographic risk based on jurisdiction.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self._config = config or RiskConfig()

    def assess_country_risk(self, country_code: str) -> RiskFactor:
        """Assess risk for a country."""
        country_code = country_code.upper()

        if country_code in self._config.high_risk_countries:
            return RiskFactor(
                category=RiskCategory.GEOGRAPHIC,
                name="country_risk",
                score=90,
                weight=1.5,
                description=f"High-risk jurisdiction: {country_code}",
                evidence={"country": country_code, "risk_tier": "high"},
            )
        elif country_code in self._config.medium_risk_countries:
            return RiskFactor(
                category=RiskCategory.GEOGRAPHIC,
                name="country_risk",
                score=50,
                description=f"Elevated risk jurisdiction: {country_code}",
                evidence={"country": country_code, "risk_tier": "medium"},
            )
        else:
            return RiskFactor(
                category=RiskCategory.GEOGRAPHIC,
                name="country_risk",
                score=10,
                description=f"Standard jurisdiction: {country_code}",
                evidence={"country": country_code, "risk_tier": "low"},
            )

    def assess_transaction_geography(
        self,
        source_country: str,
        destination_country: str,
    ) -> RiskFactor:
        """Assess geographic risk for a transaction between two countries."""
        source_factor = self.assess_country_risk(source_country)
        dest_factor = self.assess_country_risk(destination_country)

        # Cross-border transactions have inherent additional risk
        cross_border_penalty = 10 if source_country != destination_country else 0

        combined_score = min(100, max(source_factor.score, dest_factor.score) + cross_border_penalty)

        return RiskFactor(
            category=RiskCategory.GEOGRAPHIC,
            name="transaction_geography",
            score=combined_score,
            description=f"Transaction from {source_country} to {destination_country}",
            evidence={
                "source_country": source_country,
                "destination_country": destination_country,
                "cross_border": source_country != destination_country,
            },
        )


class RiskScorer:
    """
    Main risk scoring engine.

    Aggregates multiple risk factors into a comprehensive assessment.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self._config = config or RiskConfig()
        self._velocity_monitor = TransactionVelocityMonitor(config)
        self._geo_assessor = GeographicRiskAssessor(config)

    def assess_transaction_risk(
        self,
        subject_id: str,
        amount: Decimal,
        source_country: str = "US",
        destination_country: str = "US",
        counterparty_id: Optional[str] = None,
        pep_result: Optional[Dict[str, Any]] = None,
        sanctions_result: Optional[Dict[str, Any]] = None,
        additional_factors: Optional[List[RiskFactor]] = None,
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment for a transaction.

        Args:
            subject_id: ID of the transacting entity
            amount: Transaction amount
            source_country: ISO country code for source
            destination_country: ISO country code for destination
            counterparty_id: ID of counterparty if known
            pep_result: PEP screening result if available
            sanctions_result: Sanctions screening result if available
            additional_factors: Any additional risk factors to include

        Returns:
            Complete RiskAssessment with all factors and recommendations
        """
        factors: List[RiskFactor] = []

        # 1. Transaction amount risk
        amount_factor = self._assess_amount_risk(amount)
        factors.append(amount_factor)

        # 2. Velocity risk
        velocity_factor = self._velocity_monitor.assess_velocity_risk(subject_id)
        factors.append(velocity_factor)

        # Record this transaction for future velocity calculations
        self._velocity_monitor.record_transaction(subject_id, amount)

        # 3. Geographic risk
        geo_factor = self._geo_assessor.assess_transaction_geography(
            source_country, destination_country
        )
        factors.append(geo_factor)

        # 4. PEP risk (if provided)
        if pep_result:
            pep_factor = self._assess_pep_risk(pep_result)
            factors.append(pep_factor)

        # 5. Sanctions risk (if provided)
        if sanctions_result:
            sanctions_factor = self._assess_sanctions_risk(sanctions_result)
            factors.append(sanctions_factor)

        # 6. Additional factors
        if additional_factors:
            factors.extend(additional_factors)

        # Calculate overall score
        overall_score = self._calculate_overall_score(factors)
        risk_level = self._determine_risk_level(overall_score)
        recommended_action = self._determine_action(overall_score, factors)

        return RiskAssessment(
            subject_id=subject_id,
            overall_score=overall_score,
            risk_level=risk_level,
            recommended_action=recommended_action,
            factors=factors,
            metadata={
                "amount": str(amount),
                "source_country": source_country,
                "destination_country": destination_country,
            },
        )

    def assess_entity_risk(
        self,
        subject_id: str,
        entity_type: str = "individual",
        country: str = "US",
        pep_result: Optional[Dict[str, Any]] = None,
        sanctions_result: Optional[Dict[str, Any]] = None,
        kyc_status: Optional[str] = None,
        additional_factors: Optional[List[RiskFactor]] = None,
    ) -> RiskAssessment:
        """
        Assess risk for an entity (customer/counterparty).

        Args:
            subject_id: Entity ID
            entity_type: Type of entity (individual, business, etc.)
            country: Entity's country
            pep_result: PEP screening result
            sanctions_result: Sanctions screening result
            kyc_status: Current KYC verification status
            additional_factors: Additional risk factors

        Returns:
            Complete RiskAssessment
        """
        factors: List[RiskFactor] = []

        # 1. Geographic risk
        geo_factor = self._geo_assessor.assess_country_risk(country)
        factors.append(geo_factor)

        # 2. PEP risk
        if pep_result:
            pep_factor = self._assess_pep_risk(pep_result)
            factors.append(pep_factor)

        # 3. Sanctions risk
        if sanctions_result:
            sanctions_factor = self._assess_sanctions_risk(sanctions_result)
            factors.append(sanctions_factor)

        # 4. KYC status risk
        if kyc_status:
            kyc_factor = self._assess_kyc_risk(kyc_status)
            factors.append(kyc_factor)

        # 5. Entity type risk
        entity_factor = self._assess_entity_type_risk(entity_type)
        factors.append(entity_factor)

        # 6. Historical velocity
        velocity_factor = self._velocity_monitor.assess_velocity_risk(subject_id)
        factors.append(velocity_factor)

        # 7. Additional factors
        if additional_factors:
            factors.extend(additional_factors)

        overall_score = self._calculate_overall_score(factors)
        risk_level = self._determine_risk_level(overall_score)
        recommended_action = self._determine_action(overall_score, factors)

        return RiskAssessment(
            subject_id=subject_id,
            overall_score=overall_score,
            risk_level=risk_level,
            recommended_action=recommended_action,
            factors=factors,
            metadata={
                "entity_type": entity_type,
                "country": country,
            },
        )

    def _assess_amount_risk(self, amount: Decimal) -> RiskFactor:
        """Assess risk based on transaction amount."""
        threshold = self._config.high_value_threshold

        if amount >= threshold * 10:
            score = 80
            description = f"Very high value transaction: ${amount:.2f}"
        elif amount >= threshold:
            score = 50
            description = f"High value transaction: ${amount:.2f}"
        elif amount >= threshold / 2:
            score = 25
            description = f"Moderate value transaction: ${amount:.2f}"
        else:
            score = 10
            description = f"Standard transaction: ${amount:.2f}"

        return RiskFactor(
            category=RiskCategory.TRANSACTION,
            name="amount",
            score=score,
            description=description,
            evidence={"amount": str(amount), "threshold": str(threshold)},
        )

    def _assess_pep_risk(self, pep_result: Dict[str, Any]) -> RiskFactor:
        """Assess risk based on PEP screening result."""
        if not pep_result.get("is_pep", False):
            return RiskFactor(
                category=RiskCategory.PEP,
                name="pep_status",
                score=0,
                description="Not a PEP",
            )

        highest_risk = pep_result.get("highest_risk", "low")
        risk_scores = {
            "very_high": 95,
            "high": 80,
            "medium": 50,
            "low": 25,
        }

        score = risk_scores.get(highest_risk, 50)

        return RiskFactor(
            category=RiskCategory.PEP,
            name="pep_status",
            score=score,
            weight=self._config.category_weights.get(RiskCategory.PEP, 1.5),
            description=f"PEP identified - Risk level: {highest_risk}",
            evidence=pep_result,
        )

    def _assess_sanctions_risk(self, sanctions_result: Dict[str, Any]) -> RiskFactor:
        """Assess risk based on sanctions screening result."""
        if sanctions_result.get("is_sanctioned", False):
            return RiskFactor(
                category=RiskCategory.SANCTIONS,
                name="sanctions_status",
                score=100,
                weight=self._config.category_weights.get(RiskCategory.SANCTIONS, 2.0),
                description="SANCTIONED - Transaction must be blocked",
                evidence=sanctions_result,
            )

        risk_level = sanctions_result.get("risk_level", "low")
        risk_scores = {
            "blocked": 100,
            "severe": 90,
            "high": 70,
            "medium": 40,
            "low": 10,
        }

        score = risk_scores.get(risk_level, 10)

        return RiskFactor(
            category=RiskCategory.SANCTIONS,
            name="sanctions_status",
            score=score,
            weight=self._config.category_weights.get(RiskCategory.SANCTIONS, 2.0),
            description=f"Sanctions screening - Risk level: {risk_level}",
            evidence=sanctions_result,
        )

    def _assess_kyc_risk(self, kyc_status: str) -> RiskFactor:
        """Assess risk based on KYC verification status."""
        status_scores = {
            "approved": 0,
            "verified": 0,
            "pending": 40,
            "expired": 60,
            "declined": 90,
            "not_started": 70,
        }

        score = status_scores.get(kyc_status.lower(), 50)

        return RiskFactor(
            category=RiskCategory.REGULATORY,
            name="kyc_status",
            score=score,
            description=f"KYC status: {kyc_status}",
            evidence={"status": kyc_status},
        )

    def _assess_entity_type_risk(self, entity_type: str) -> RiskFactor:
        """Assess risk based on entity type."""
        type_scores = {
            "individual": 20,
            "business": 30,
            "trust": 50,
            "foundation": 50,
            "npo": 60,  # Non-profit - higher scrutiny
            "shell_company": 90,
            "unknown": 70,
        }

        score = type_scores.get(entity_type.lower(), 40)

        return RiskFactor(
            category=RiskCategory.COUNTERPARTY,
            name="entity_type",
            score=score,
            description=f"Entity type: {entity_type}",
            evidence={"type": entity_type},
        )

    def _calculate_overall_score(self, factors: List[RiskFactor]) -> float:
        """Calculate overall risk score from all factors."""
        if not factors:
            return 0.0

        # Weighted average with category weights applied
        total_weighted_score = sum(f.weighted_score for f in factors)
        total_weight = sum(f.weight for f in factors)

        if total_weight == 0:
            return 0.0

        base_score = total_weighted_score / total_weight

        # Apply any critical factor overrides
        for factor in factors:
            if factor.category == RiskCategory.SANCTIONS and factor.score >= 100:
                return 100.0  # Sanctions hit always results in max risk

        return min(100.0, base_score)

    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level from score."""
        thresholds = self._config.level_thresholds

        if score <= thresholds[RiskLevel.MINIMAL]:
            return RiskLevel.MINIMAL
        elif score <= thresholds[RiskLevel.LOW]:
            return RiskLevel.LOW
        elif score <= thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        elif score <= thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _determine_action(
        self,
        score: float,
        factors: List[RiskFactor],
    ) -> RiskAction:
        """Determine recommended action based on score and factors."""
        # Check for hard blocks first
        for factor in factors:
            if factor.category == RiskCategory.SANCTIONS and factor.score >= 100:
                return RiskAction.BLOCK

        thresholds = self._config.action_thresholds

        if score >= thresholds[RiskAction.ESCALATE]:
            return RiskAction.ESCALATE
        elif score >= thresholds[RiskAction.BLOCK]:
            return RiskAction.BLOCK
        elif score >= thresholds[RiskAction.ENHANCED_DUE_DILIGENCE]:
            return RiskAction.ENHANCED_DUE_DILIGENCE
        elif score >= thresholds[RiskAction.REVIEW]:
            return RiskAction.REVIEW
        else:
            return RiskAction.APPROVE

    def get_velocity_monitor(self) -> TransactionVelocityMonitor:
        """Get the velocity monitor for direct access."""
        return self._velocity_monitor


def create_risk_scorer(config: Optional[RiskConfig] = None) -> RiskScorer:
    """Factory function to create a RiskScorer instance."""
    return RiskScorer(config=config)
