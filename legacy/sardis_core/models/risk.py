"""Risk profile and scoring models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskFactor(str, Enum):
    """Types of risk factors that can affect score."""
    HIGH_VELOCITY = "high_velocity"  # Too many transactions in short time
    LARGE_AMOUNT = "large_amount"  # Unusually large transaction
    NEW_WALLET = "new_wallet"  # Newly created wallet
    UNUSUAL_RECIPIENT = "unusual_recipient"  # First time sending to this recipient
    LIMIT_APPROACHING = "limit_approaching"  # Close to spending limits
    PATTERN_ANOMALY = "pattern_anomaly"  # Unusual spending pattern
    FAILED_ATTEMPTS = "failed_attempts"  # Multiple failed transactions
    GEOGRAPHIC_RISK = "geographic_risk"  # High-risk jurisdiction
    UNAUTHORIZED_SERVICE = "unauthorized_service"  # Attempting to pay unauthorized service


@dataclass
class RiskScore:
    """
    Risk assessment for an agent or transaction.
    
    Score ranges from 0 (no risk) to 100 (maximum risk).
    """
    
    score: float = 0.0  # 0-100
    level: RiskLevel = RiskLevel.LOW
    factors: list[RiskFactor] = field(default_factory=list)
    details: dict[str, str] = field(default_factory=dict)
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def from_score(cls, score: float, factors: list[RiskFactor] = None, details: dict = None) -> "RiskScore":
        """Create a RiskScore from a numeric score."""
        level = cls._score_to_level(score)
        return cls(
            score=score,
            level=level,
            factors=factors or [],
            details=details or {}
        )
    
    @staticmethod
    def _score_to_level(score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score < 25:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MEDIUM
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def is_acceptable(self, threshold: float = 75.0) -> bool:
        """Check if risk is below threshold."""
        return self.score < threshold


@dataclass
class AgentRiskProfile:
    """
    Long-term risk profile for an agent.
    
    Tracks historical behavior and risk indicators.
    """
    
    profile_id: str = field(default_factory=lambda: f"risk_{uuid.uuid4().hex[:16]}")
    agent_id: str = ""
    
    # Current risk assessment
    current_score: float = 0.0
    current_level: RiskLevel = RiskLevel.LOW
    
    # Historical metrics
    total_transactions: int = 0
    failed_transactions: int = 0
    total_volume: Decimal = field(default=Decimal("0.00"))
    
    # Velocity tracking (transactions in last hour)
    transactions_last_hour: int = 0
    last_transaction_at: Optional[datetime] = None
    
    # Patterns
    average_transaction_amount: Decimal = field(default=Decimal("0.00"))
    max_transaction_amount: Decimal = field(default=Decimal("0.00"))
    unique_recipients: int = 0
    
    # Authorized services
    authorized_services: list[str] = field(default_factory=list)
    
    # Flags
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    flagged_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_from_transaction(
        self,
        amount: Decimal,
        recipient: str,
        success: bool
    ):
        """Update profile after a transaction."""
        self.total_transactions += 1
        if not success:
            self.failed_transactions += 1
        
        self.total_volume += amount
        self.last_transaction_at = datetime.now(timezone.utc)
        
        # Update averages
        if self.total_transactions > 0:
            self.average_transaction_amount = self.total_volume / self.total_transactions
        
        if amount > self.max_transaction_amount:
            self.max_transaction_amount = amount
        
        self.updated_at = datetime.now(timezone.utc)
    
    def is_service_authorized(self, service_id: str) -> bool:
        """Check if a service is authorized for this agent."""
        if not self.authorized_services:  # Empty means all authorized
            return True
        return service_id in self.authorized_services
    
    def authorize_service(self, service_id: str):
        """Authorize a service for this agent."""
        if service_id not in self.authorized_services:
            self.authorized_services.append(service_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def revoke_service(self, service_id: str) -> bool:
        """Revoke a service authorization."""
        if service_id in self.authorized_services:
            self.authorized_services.remove(service_id)
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def flag(self, reason: str):
        """Flag this agent for review."""
        self.is_flagged = True
        self.flag_reason = reason
        self.flagged_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def unflag(self):
        """Remove flag from this agent."""
        self.is_flagged = False
        self.flag_reason = None
        self.flagged_at = None
        self.updated_at = datetime.now(timezone.utc)

