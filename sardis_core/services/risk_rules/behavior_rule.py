"""
Agent behavior fingerprint risk rule.

Detects unusual patterns in agent behavior.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
import statistics

from .base import RiskRule, RuleResult, PaymentContext, RiskAction


@dataclass
class BehaviorProfile:
    """Behavioral profile for an agent."""
    agent_id: str
    
    # Typical transaction patterns
    typical_amount_range: tuple[Decimal, Decimal] = field(
        default_factory=lambda: (Decimal("0"), Decimal("100"))
    )
    typical_recipients: list[str] = field(default_factory=list)
    typical_categories: list[str] = field(default_factory=list)
    
    # Transaction timing patterns
    typical_hour_of_day: list[int] = field(default_factory=list)  # 0-23
    typical_day_of_week: list[int] = field(default_factory=list)  # 0-6
    
    # Amount history for std deviation
    amount_history: list[Decimal] = field(default_factory=list)


@dataclass
class BehaviorConfig:
    """Configuration for behavior fingerprint rule."""
    # How many transactions to keep for profiling
    max_history_size: int = 100
    
    # Minimum transactions to establish a profile
    min_profile_transactions: int = 10
    
    # Standard deviation multiplier for anomaly
    std_dev_multiplier: float = 2.5
    
    # Score contributions
    new_recipient_score: float = 10.0
    unusual_amount_score: float = 20.0
    unusual_category_score: float = 10.0


class BehaviorFingerprintRule(RiskRule):
    """
    Rule to detect unusual agent behavior.
    
    Builds a profile of typical behavior and flags
    transactions that deviate significantly.
    """
    
    name = "behavior_fingerprint"
    description = "Detects unusual agent behavior patterns"
    default_weight = 1.0
    
    def __init__(
        self,
        config: Optional[BehaviorConfig] = None,
        weight: Optional[float] = None,
        enabled: bool = True
    ):
        super().__init__(weight, enabled)
        self.config = config or BehaviorConfig()
        
        # Behavior profiles per agent
        self._profiles: dict[str, BehaviorProfile] = {}
    
    def update_profile(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_id: Optional[str] = None,
        category: Optional[str] = None
    ):
        """Update agent's behavioral profile after a transaction."""
        if agent_id not in self._profiles:
            self._profiles[agent_id] = BehaviorProfile(agent_id=agent_id)
        
        profile = self._profiles[agent_id]
        
        # Update amount history
        profile.amount_history.append(amount)
        if len(profile.amount_history) > self.config.max_history_size:
            profile.amount_history.pop(0)
        
        # Update typical amount range
        if len(profile.amount_history) >= 5:
            amounts = [float(a) for a in profile.amount_history]
            min_amt = Decimal(str(min(amounts)))
            max_amt = Decimal(str(max(amounts)))
            profile.typical_amount_range = (min_amt, max_amt)
        
        # Update typical recipients
        if recipient_id:
            if recipient_id not in profile.typical_recipients:
                profile.typical_recipients.append(recipient_id)
                if len(profile.typical_recipients) > 50:
                    profile.typical_recipients.pop(0)
        
        # Update typical categories
        if category:
            if category not in profile.typical_categories:
                profile.typical_categories.append(category)
    
    def evaluate(self, context: PaymentContext) -> RuleResult:
        """Evaluate against agent's behavioral profile."""
        if not self.enabled:
            return self._create_result(0.0)
        
        score = 0.0
        factors = []
        details = {}
        triggered = False
        action = RiskAction.APPROVE
        
        profile = self._profiles.get(context.agent_id)
        
        if not profile or len(profile.amount_history) < self.config.min_profile_transactions:
            # Not enough history to profile
            details["profile_status"] = "insufficient_history"
            return self._create_result(0.0, details=details)
        
        details["profile_status"] = "active"
        details["history_size"] = len(profile.amount_history)
        
        # Check amount against historical pattern
        amount_score = self._check_amount_anomaly(context.amount, profile)
        if amount_score > 0:
            score += amount_score
            factors.append("unusual_amount")
            triggered = True
        
        # Check recipient novelty
        if context.recipient_id and context.recipient_id not in profile.typical_recipients:
            score += self.config.new_recipient_score
            factors.append("new_recipient")
            details["recipient_is_new"] = True
        
        # Check category
        if context.merchant_category and profile.typical_categories:
            if context.merchant_category not in profile.typical_categories:
                score += self.config.unusual_category_score
                factors.append("unusual_category")
                details["category"] = context.merchant_category
        
        if score >= 30:
            action = RiskAction.REVIEW
        
        return self._create_result(
            score=score,
            factors=factors,
            details=details,
            triggered=triggered,
            action=action,
        )
    
    def _check_amount_anomaly(
        self,
        amount: Decimal,
        profile: BehaviorProfile
    ) -> float:
        """Check if amount is anomalous compared to history."""
        if len(profile.amount_history) < 5:
            return 0.0
        
        amounts = [float(a) for a in profile.amount_history]
        mean = statistics.mean(amounts)
        
        if len(amounts) < 2:
            return 0.0
        
        try:
            std_dev = statistics.stdev(amounts)
        except statistics.StatisticsError:
            return 0.0
        
        if std_dev == 0:
            # All same amount, any deviation is suspicious
            if float(amount) != mean:
                return self.config.unusual_amount_score
            return 0.0
        
        z_score = (float(amount) - mean) / std_dev
        
        if abs(z_score) > self.config.std_dev_multiplier:
            # Proportional score based on how extreme the deviation is
            return min(self.config.unusual_amount_score * (abs(z_score) / 3), 40.0)
        
        return 0.0

