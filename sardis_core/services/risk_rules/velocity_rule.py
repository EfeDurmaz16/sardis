"""
Velocity-based risk rule.

Detects abnormally high transaction frequency.
"""

from dataclasses import dataclass
from typing import Optional

from .base import RiskRule, RuleResult, PaymentContext, RiskAction


@dataclass
class VelocityConfig:
    """Configuration for velocity rule."""
    max_transactions_per_hour: int = 20
    max_transactions_per_day: int = 100
    
    # Score contributions
    hourly_exceed_score: float = 30.0
    daily_exceed_score: float = 20.0
    
    # Thresholds for warnings (percentage of limit)
    warning_threshold: float = 0.8


class VelocityRule(RiskRule):
    """
    Rule to detect abnormally high transaction frequency.
    
    Flags agents that are transacting much faster than normal,
    which could indicate automated fraud or account compromise.
    """
    
    name = "velocity"
    description = "Detects abnormally high transaction frequency"
    default_weight = 1.5  # Higher weight for velocity
    
    def __init__(
        self,
        config: Optional[VelocityConfig] = None,
        weight: Optional[float] = None,
        enabled: bool = True
    ):
        super().__init__(weight, enabled)
        self.config = config or VelocityConfig()
    
    def evaluate(self, context: PaymentContext) -> RuleResult:
        """Evaluate transaction velocity."""
        if not self.enabled:
            return self._create_result(0.0)
        
        score = 0.0
        factors = []
        details = {}
        triggered = False
        action = RiskAction.APPROVE
        
        # Check hourly velocity
        hourly_ratio = context.transactions_last_hour / self.config.max_transactions_per_hour
        if hourly_ratio >= 1.0:
            score += self.config.hourly_exceed_score
            factors.append("high_hourly_velocity")
            details["hourly_transactions"] = context.transactions_last_hour
            details["hourly_limit"] = self.config.max_transactions_per_hour
            triggered = True
            
            if hourly_ratio >= 2.0:
                action = RiskAction.DENY
            elif hourly_ratio >= 1.5:
                action = RiskAction.REVIEW
                
        elif hourly_ratio >= self.config.warning_threshold:
            score += self.config.hourly_exceed_score * 0.3
            factors.append("elevated_hourly_velocity")
            details["hourly_transactions"] = context.transactions_last_hour
        
        # Check daily velocity
        daily_ratio = context.transactions_last_day / self.config.max_transactions_per_day
        if daily_ratio >= 1.0:
            score += self.config.daily_exceed_score
            factors.append("high_daily_velocity")
            details["daily_transactions"] = context.transactions_last_day
            details["daily_limit"] = self.config.max_transactions_per_day
            triggered = True
            
        elif daily_ratio >= self.config.warning_threshold:
            score += self.config.daily_exceed_score * 0.3
            factors.append("elevated_daily_velocity")
            details["daily_transactions"] = context.transactions_last_day
        
        # Check for burst patterns (many transactions in very short time)
        if context.transactions_last_hour >= 10:
            # More than 10 in an hour is suspicious
            burst_score = (context.transactions_last_hour - 10) * 2
            score += min(burst_score, 15.0)
            if burst_score > 0:
                factors.append("burst_pattern")
        
        return self._create_result(
            score=score,
            factors=factors,
            details=details,
            triggered=triggered,
            action=action,
        )

