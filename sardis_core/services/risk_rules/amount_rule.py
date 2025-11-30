"""
Amount anomaly risk rule.

Detects unusual transaction amounts based on history.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .base import RiskRule, RuleResult, PaymentContext, RiskAction


@dataclass
class AmountConfig:
    """Configuration for amount anomaly rule."""
    # Absolute thresholds
    large_transaction_threshold: Decimal = Decimal("100.00")
    very_large_threshold: Decimal = Decimal("500.00")
    
    # Relative to history
    deviation_multiplier: float = 3.0  # Flag if > 3x average
    max_deviation_multiplier: float = 10.0  # Block if > 10x average
    
    # Score contributions
    large_tx_score: float = 15.0
    very_large_tx_score: float = 30.0
    deviation_score: float = 25.0
    
    # Minimum transactions for deviation calculation
    min_history_for_deviation: int = 5


class AmountAnomalyRule(RiskRule):
    """
    Rule to detect unusual transaction amounts.
    
    Flags transactions that are significantly larger than
    the agent's typical behavior or absolute thresholds.
    """
    
    name = "amount_anomaly"
    description = "Detects unusual transaction amounts"
    default_weight = 1.2
    
    def __init__(
        self,
        config: Optional[AmountConfig] = None,
        weight: Optional[float] = None,
        enabled: bool = True
    ):
        super().__init__(weight, enabled)
        self.config = config or AmountConfig()
    
    def evaluate(self, context: PaymentContext) -> RuleResult:
        """Evaluate transaction amount for anomalies."""
        if not self.enabled:
            return self._create_result(0.0)
        
        score = 0.0
        factors = []
        details = {}
        triggered = False
        action = RiskAction.APPROVE
        
        amount = context.amount
        
        # Check absolute thresholds
        if amount >= self.config.very_large_threshold:
            score += self.config.very_large_tx_score
            factors.append("very_large_transaction")
            details["amount"] = str(amount)
            details["threshold"] = str(self.config.very_large_threshold)
            triggered = True
            action = RiskAction.REVIEW
            
        elif amount >= self.config.large_transaction_threshold:
            score += self.config.large_tx_score
            factors.append("large_transaction")
            details["amount"] = str(amount)
            details["threshold"] = str(self.config.large_transaction_threshold)
        
        # Check relative to history (if enough history exists)
        if context.total_transactions >= self.config.min_history_for_deviation:
            avg = context.average_transaction
            if avg > 0:
                deviation = float(amount / avg)
                details["deviation_from_average"] = f"{deviation:.1f}x"
                details["average_transaction"] = str(avg)
                
                if deviation >= self.config.max_deviation_multiplier:
                    score += self.config.deviation_score
                    factors.append("extreme_deviation")
                    triggered = True
                    action = RiskAction.DENY
                    
                elif deviation >= self.config.deviation_multiplier:
                    score += self.config.deviation_score * 0.6
                    factors.append("significant_deviation")
                    triggered = True
        
        # Check if amount is close to a round number (potential structuring)
        self._check_round_amount(amount, score, factors, details)
        
        # Check for just-under-threshold amounts (structuring)
        self._check_structuring(amount, score, factors, details)
        
        return self._create_result(
            score=score,
            factors=factors,
            details=details,
            triggered=triggered,
            action=action,
        )
    
    def _check_round_amount(
        self,
        amount: Decimal,
        score: float,
        factors: list,
        details: dict
    ):
        """Check if amount is suspiciously round."""
        # Round amounts (exactly divisible by 100) can indicate automation
        amount_float = float(amount)
        if amount_float >= 100 and amount_float % 100 == 0:
            factors.append("round_amount")
            details["round_amount"] = True
    
    def _check_structuring(
        self,
        amount: Decimal,
        score: float,
        factors: list,
        details: dict
    ):
        """Check for potential structuring (just under reporting thresholds)."""
        # Common reporting thresholds
        thresholds = [
            Decimal("10000.00"),  # US CTR threshold
            Decimal("3000.00"),   # Common wire threshold
        ]
        
        for threshold in thresholds:
            lower = threshold - Decimal("500.00")
            if lower < amount < threshold:
                factors.append("near_reporting_threshold")
                details["near_threshold"] = str(threshold)
                break

