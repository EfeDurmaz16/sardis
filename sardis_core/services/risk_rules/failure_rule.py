"""
Failure pattern risk rule.

Detects suspicious patterns in failed transactions.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .base import RiskRule, RuleResult, PaymentContext, RiskAction


@dataclass
class FailureConfig:
    """Configuration for failure pattern rule."""
    # Threshold for flagging
    high_failure_rate: float = 0.20  # 20%
    critical_failure_rate: float = 0.40  # 40%
    
    # Minimum transactions for rate calculation
    min_transactions: int = 5
    
    # Consecutive failure handling
    max_consecutive_failures: int = 3
    
    # Score contributions
    high_failure_score: float = 25.0
    critical_failure_score: float = 50.0
    consecutive_failure_score: float = 15.0


class FailurePatternRule(RiskRule):
    """
    Rule to detect suspicious failure patterns.
    
    Flags agents with high failure rates or repeated
    failed attempts, which could indicate fraud probing.
    """
    
    name = "failure_pattern"
    description = "Detects suspicious patterns in failed transactions"
    default_weight = 1.3
    
    def __init__(
        self,
        config: Optional[FailureConfig] = None,
        weight: Optional[float] = None,
        enabled: bool = True
    ):
        super().__init__(weight, enabled)
        self.config = config or FailureConfig()
        
        # Track consecutive failures per agent
        self._consecutive_failures: dict[str, int] = {}
    
    def record_outcome(self, agent_id: str, success: bool):
        """Record transaction outcome for consecutive failure tracking."""
        if success:
            self._consecutive_failures[agent_id] = 0
        else:
            current = self._consecutive_failures.get(agent_id, 0)
            self._consecutive_failures[agent_id] = current + 1
    
    def evaluate(self, context: PaymentContext) -> RuleResult:
        """Evaluate failure patterns."""
        if not self.enabled:
            return self._create_result(0.0)
        
        score = 0.0
        factors = []
        details = {}
        triggered = False
        action = RiskAction.APPROVE
        
        # Calculate failure rate if enough history
        if context.total_transactions >= self.config.min_transactions:
            failure_rate = context.failed_transactions / context.total_transactions
            details["failure_rate"] = f"{failure_rate:.1%}"
            details["failed_count"] = context.failed_transactions
            details["total_count"] = context.total_transactions
            
            if failure_rate >= self.config.critical_failure_rate:
                score += self.config.critical_failure_score
                factors.append("critical_failure_rate")
                triggered = True
                action = RiskAction.DENY
                
            elif failure_rate >= self.config.high_failure_rate:
                score += self.config.high_failure_score
                factors.append("high_failure_rate")
                triggered = True
                action = RiskAction.REVIEW
        
        # Check consecutive failures
        consecutive = self._consecutive_failures.get(context.agent_id, 0)
        if consecutive > 0:
            details["consecutive_failures"] = consecutive
            
            if consecutive >= self.config.max_consecutive_failures:
                score += self.config.consecutive_failure_score
                factors.append("consecutive_failures")
                triggered = True
                
                if consecutive >= self.config.max_consecutive_failures * 2:
                    action = RiskAction.DENY
        
        # Check for probing patterns
        # (many small failed transactions followed by a large attempt)
        if context.failed_transactions >= 3 and context.total_transactions < 10:
            # New agent with several failures already
            if context.amount > context.average_transaction * Decimal("2"):
                score += 15.0
                factors.append("potential_probing")
                details["probing_pattern"] = True
        
        return self._create_result(
            score=score,
            factors=factors,
            details=details,
            triggered=triggered,
            action=action,
        )

