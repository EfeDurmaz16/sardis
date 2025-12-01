"""
Base class for risk rules.

Provides the interface that all risk rules must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Any


class RiskAction(str, Enum):
    """Actions to take based on risk assessment."""
    APPROVE = "approve"      # Allow the transaction
    DENY = "deny"           # Block the transaction
    REVIEW = "review"       # Flag for manual review
    STEP_UP = "step_up"     # Require additional verification


@dataclass
class PaymentContext:
    """
    Context about a payment for risk evaluation.
    
    Contains all the information a rule might need to assess risk.
    """
    
    # Agent info
    agent_id: str
    wallet_id: str
    wallet_created_at: Optional[datetime] = None
    
    # Transaction details
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    
    # Recipient info
    recipient_id: Optional[str] = None
    merchant_id: Optional[str] = None
    merchant_category: Optional[str] = None
    
    # Historical data
    total_transactions: int = 0
    failed_transactions: int = 0
    transactions_last_hour: int = 0
    transactions_last_day: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    average_transaction: Decimal = field(default_factory=lambda: Decimal("0"))
    max_transaction: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Recent transactions
    recent_transaction_amounts: list[Decimal] = field(default_factory=list)
    recent_recipients: list[str] = field(default_factory=list)
    
    # Session/request data
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """
    Result from a single risk rule evaluation.
    """
    
    rule_name: str
    score: float  # 0-100 contribution to overall score
    weight: float = 1.0  # Relative importance of this rule
    
    # Factors that contributed to the score
    factors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    
    # Whether this rule triggered a flag
    triggered: bool = False
    
    # Recommended action from this rule
    recommended_action: RiskAction = RiskAction.APPROVE
    
    def weighted_score(self) -> float:
        """Get score weighted by importance."""
        return self.score * self.weight


class RiskRule(ABC):
    """
    Abstract base class for risk rules.
    
    Each rule focuses on a specific aspect of risk assessment.
    Rules are composable and their results are combined by the risk engine.
    """
    
    # Rule identification
    name: str = "base_rule"
    description: str = "Base risk rule"
    
    # How much this rule contributes to overall score
    default_weight: float = 1.0
    
    # Whether this rule is enabled
    enabled: bool = True
    
    def __init__(self, weight: Optional[float] = None, enabled: bool = True):
        """
        Initialize the rule.
        
        Args:
            weight: Override default weight
            enabled: Whether the rule is active
        """
        self.weight = weight if weight is not None else self.default_weight
        self.enabled = enabled
    
    @abstractmethod
    def evaluate(self, context: PaymentContext) -> RuleResult:
        """
        Evaluate the payment context and return a risk result.
        
        Args:
            context: Payment context with all relevant data
            
        Returns:
            RuleResult with score and details
        """
        pass
    
    def _create_result(
        self,
        score: float,
        factors: Optional[list[str]] = None,
        details: Optional[dict] = None,
        triggered: bool = False,
        action: RiskAction = RiskAction.APPROVE
    ) -> RuleResult:
        """Helper to create a rule result."""
        return RuleResult(
            rule_name=self.name,
            score=min(100.0, max(0.0, score)),  # Clamp to 0-100
            weight=self.weight,
            factors=factors or [],
            details=details or {},
            triggered=triggered,
            recommended_action=action,
        )

