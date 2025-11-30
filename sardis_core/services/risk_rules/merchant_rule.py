"""
Merchant reputation risk rule.

Evaluates risk based on merchant trust and history.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from .base import RiskRule, RuleResult, PaymentContext, RiskAction


@dataclass
class MerchantReputation:
    """Reputation data for a merchant."""
    merchant_id: str
    trust_score: float = 50.0  # 0-100
    total_transactions: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    dispute_rate: float = 0.0  # Percentage of disputed transactions
    refund_rate: float = 0.0   # Percentage of refunded transactions
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified: bool = False
    categories: list[str] = field(default_factory=list)


@dataclass
class MerchantConfig:
    """Configuration for merchant reputation rule."""
    # Trust score thresholds
    low_trust_threshold: float = 30.0
    high_risk_threshold: float = 20.0
    
    # New merchant settings
    new_merchant_days: int = 30
    new_merchant_score: float = 15.0
    
    # Dispute/refund thresholds
    high_dispute_rate: float = 0.05  # 5%
    high_refund_rate: float = 0.10   # 10%
    
    # Unknown merchant handling
    unknown_merchant_score: float = 20.0


class MerchantReputationRule(RiskRule):
    """
    Rule to evaluate merchant risk.
    
    Considers merchant trust score, dispute history,
    and other reputation signals.
    """
    
    name = "merchant_reputation"
    description = "Evaluates merchant trust and history"
    default_weight = 1.0
    
    def __init__(
        self,
        config: Optional[MerchantConfig] = None,
        weight: Optional[float] = None,
        enabled: bool = True
    ):
        super().__init__(weight, enabled)
        self.config = config or MerchantConfig()
        
        # In-memory merchant reputation store
        # In production, this would be a database
        self._merchants: dict[str, MerchantReputation] = {}
    
    def register_merchant(
        self,
        merchant_id: str,
        trust_score: float = 50.0,
        is_verified: bool = False,
        categories: Optional[list[str]] = None
    ) -> MerchantReputation:
        """Register a merchant with initial reputation."""
        rep = MerchantReputation(
            merchant_id=merchant_id,
            trust_score=trust_score,
            is_verified=is_verified,
            categories=categories or [],
        )
        self._merchants[merchant_id] = rep
        return rep
    
    def update_reputation(
        self,
        merchant_id: str,
        transaction_success: bool = True,
        refunded: bool = False,
        disputed: bool = False
    ):
        """Update merchant reputation after a transaction."""
        if merchant_id not in self._merchants:
            self.register_merchant(merchant_id)
        
        rep = self._merchants[merchant_id]
        rep.total_transactions += 1
        
        # Adjust trust score based on outcome
        if transaction_success and not refunded and not disputed:
            rep.trust_score = min(100.0, rep.trust_score + 0.1)
        elif disputed:
            rep.trust_score = max(0.0, rep.trust_score - 5.0)
            rep.dispute_rate = (rep.dispute_rate * (rep.total_transactions - 1) + 1) / rep.total_transactions
        elif refunded:
            rep.refund_rate = (rep.refund_rate * (rep.total_transactions - 1) + 1) / rep.total_transactions
    
    def evaluate(self, context: PaymentContext) -> RuleResult:
        """Evaluate merchant reputation."""
        if not self.enabled:
            return self._create_result(0.0)
        
        score = 0.0
        factors = []
        details = {}
        triggered = False
        action = RiskAction.APPROVE
        
        merchant_id = context.merchant_id
        if not merchant_id:
            # No merchant specified (direct wallet transfer)
            return self._create_result(0.0)
        
        # Get merchant reputation
        rep = self._merchants.get(merchant_id)
        
        if not rep:
            # Unknown merchant
            score += self.config.unknown_merchant_score
            factors.append("unknown_merchant")
            details["merchant_id"] = merchant_id
            triggered = True
            action = RiskAction.REVIEW
            
        else:
            details["merchant_id"] = merchant_id
            details["trust_score"] = rep.trust_score
            details["is_verified"] = rep.is_verified
            
            # Check trust score
            if rep.trust_score < self.config.high_risk_threshold:
                score += 30.0
                factors.append("very_low_trust")
                triggered = True
                action = RiskAction.DENY
                
            elif rep.trust_score < self.config.low_trust_threshold:
                score += 15.0
                factors.append("low_trust")
                triggered = True
            
            # Check if new merchant
            merchant_age = datetime.now(timezone.utc) - rep.registered_at
            if merchant_age < timedelta(days=self.config.new_merchant_days):
                score += self.config.new_merchant_score
                factors.append("new_merchant")
                details["merchant_age_days"] = merchant_age.days
            
            # Check dispute rate
            if rep.dispute_rate >= self.config.high_dispute_rate:
                score += 20.0
                factors.append("high_dispute_rate")
                details["dispute_rate"] = f"{rep.dispute_rate:.1%}"
                triggered = True
            
            # Check refund rate
            if rep.refund_rate >= self.config.high_refund_rate:
                score += 10.0
                factors.append("high_refund_rate")
                details["refund_rate"] = f"{rep.refund_rate:.1%}"
            
            # Verified merchants get bonus
            if rep.is_verified:
                score = max(0, score - 10.0)
                factors.append("verified_merchant")
        
        return self._create_result(
            score=score,
            factors=factors,
            details=details,
            triggered=triggered,
            action=action,
        )

