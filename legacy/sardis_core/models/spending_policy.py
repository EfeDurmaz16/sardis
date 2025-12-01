"""
Spending policy models for granular spending controls.

Provides:
- Time-based limits (daily, weekly, monthly)
- Merchant allowlists and denylists
- Category-based spending scopes
- Trust levels with tiered limits
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class TrustLevel(str, Enum):
    """Trust levels for agents with different limit tiers."""
    LOW = "low"        # New agents, restricted limits
    MEDIUM = "medium"  # Verified agents, standard limits
    HIGH = "high"      # Established agents, elevated limits
    UNLIMITED = "unlimited"  # Enterprise/trusted, no soft limits


class SpendingScope(str, Enum):
    """Categories of spending that can be controlled."""
    ALL = "all"                    # All spending
    RETAIL = "retail"              # Physical goods
    DIGITAL = "digital"            # Digital products/subscriptions
    SERVICES = "services"          # Service providers
    COMPUTE = "compute"            # GPU/compute resources
    DATA = "data"                  # Data/API access
    AGENT_TO_AGENT = "agent_to_agent"  # Payments to other agents


@dataclass
class TimeWindowLimit:
    """Spending limit for a specific time window."""
    
    window_type: str  # "daily", "weekly", "monthly"
    limit_amount: Decimal
    currency: str = "USDC"
    
    # Tracking
    current_spent: Decimal = field(default_factory=lambda: Decimal("0"))
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def reset_if_expired(self) -> bool:
        """Reset the window if it has expired. Returns True if reset occurred."""
        now = datetime.now(timezone.utc)
        
        if self.window_type == "daily":
            window_duration = timedelta(days=1)
        elif self.window_type == "weekly":
            window_duration = timedelta(weeks=1)
        elif self.window_type == "monthly":
            window_duration = timedelta(days=30)
        else:
            return False
        
        if now >= self.window_start + window_duration:
            self.current_spent = Decimal("0")
            self.window_start = now
            return True
        return False
    
    def remaining(self) -> Decimal:
        """Get remaining amount in this window."""
        self.reset_if_expired()
        return max(Decimal("0"), self.limit_amount - self.current_spent)
    
    def can_spend(self, amount: Decimal) -> tuple[bool, str]:
        """Check if amount can be spent within this limit."""
        self.reset_if_expired()
        if self.current_spent + amount > self.limit_amount:
            return False, f"{self.window_type.title()} limit exceeded: {self.current_spent + amount} > {self.limit_amount}"
        return True, "OK"
    
    def record_spend(self, amount: Decimal) -> None:
        """Record a spend against this limit."""
        self.reset_if_expired()
        self.current_spent += amount


@dataclass
class MerchantRule:
    """Rule for allowing or denying specific merchants."""
    
    rule_id: str = field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:12]}")
    
    # Rule type
    rule_type: str = "allow"  # "allow" or "deny"
    
    # Target (can use wildcards)
    merchant_id: Optional[str] = None  # Specific merchant
    category: Optional[str] = None      # All merchants in category
    
    # Optional limits for allow rules
    max_per_tx: Optional[Decimal] = None
    daily_limit: Optional[Decimal] = None
    
    # Metadata
    reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    def is_active(self) -> bool:
        """Check if this rule is still active."""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
    
    def matches_merchant(self, merchant_id: str, merchant_category: Optional[str] = None) -> bool:
        """Check if this rule matches a merchant."""
        if not self.is_active():
            return False
        
        if self.merchant_id and self.merchant_id == merchant_id:
            return True
        
        if self.category and merchant_category and self.category == merchant_category:
            return True
        
        return False


@dataclass
class SpendingPolicy:
    """
    Complete spending policy for an agent.
    
    Combines multiple types of limits and rules:
    - Time-based limits (daily, weekly, monthly)
    - Per-transaction limits
    - Total spending caps
    - Merchant allowlists/denylists
    - Category restrictions
    - Trust-based tiers
    """
    
    policy_id: str = field(default_factory=lambda: f"policy_{uuid.uuid4().hex[:16]}")
    agent_id: str = ""
    
    # Trust level determines base limits
    trust_level: TrustLevel = TrustLevel.LOW
    
    # Per-transaction limit
    limit_per_tx: Decimal = field(default_factory=lambda: Decimal("100.00"))
    
    # Total lifetime spending limit
    limit_total: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    spent_total: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Time-based limits
    daily_limit: Optional[TimeWindowLimit] = None
    weekly_limit: Optional[TimeWindowLimit] = None
    monthly_limit: Optional[TimeWindowLimit] = None
    
    # Merchant rules (ordered by priority - first match wins)
    merchant_rules: list[MerchantRule] = field(default_factory=list)
    
    # Allowed spending scopes
    allowed_scopes: list[SpendingScope] = field(default_factory=lambda: [SpendingScope.ALL])
    
    # Whether to require pre-authorization for all payments
    require_preauth: bool = False
    
    # Maximum hold duration (in hours)
    max_hold_hours: int = 168  # 7 days
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def validate_payment(
        self,
        amount: Decimal,
        fee: Decimal,
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        scope: SpendingScope = SpendingScope.ALL
    ) -> tuple[bool, str]:
        """
        Validate a payment against all policy rules.
        
        Returns (allowed, reason).
        """
        total_cost = amount + fee
        
        # Check scope
        if SpendingScope.ALL not in self.allowed_scopes and scope not in self.allowed_scopes:
            return False, f"Spending scope {scope.value} not allowed"
        
        # Check per-transaction limit
        if amount > self.limit_per_tx:
            return False, f"Amount {amount} exceeds per-transaction limit {self.limit_per_tx}"
        
        # Check total limit
        if self.spent_total + amount > self.limit_total:
            return False, f"Amount {amount} would exceed total limit {self.limit_total}"
        
        # Check time-based limits
        if self.daily_limit:
            ok, reason = self.daily_limit.can_spend(amount)
            if not ok:
                return False, reason
        
        if self.weekly_limit:
            ok, reason = self.weekly_limit.can_spend(amount)
            if not ok:
                return False, reason
        
        if self.monthly_limit:
            ok, reason = self.monthly_limit.can_spend(amount)
            if not ok:
                return False, reason
        
        # Check merchant rules
        if merchant_id:
            merchant_ok, merchant_reason = self._check_merchant_rules(
                merchant_id, merchant_category, amount
            )
            if not merchant_ok:
                return False, merchant_reason
        
        return True, "OK"
    
    def _check_merchant_rules(
        self,
        merchant_id: str,
        merchant_category: Optional[str],
        amount: Decimal
    ) -> tuple[bool, str]:
        """Check merchant-specific rules."""
        
        # Check deny rules first
        for rule in self.merchant_rules:
            if rule.rule_type == "deny" and rule.matches_merchant(merchant_id, merchant_category):
                return False, f"Merchant {merchant_id} is blocked: {rule.reason or 'Policy restriction'}"
        
        # If there are explicit allow rules, check them
        allow_rules = [r for r in self.merchant_rules if r.rule_type == "allow"]
        if allow_rules:
            matching_allow = None
            for rule in allow_rules:
                if rule.matches_merchant(merchant_id, merchant_category):
                    matching_allow = rule
                    break
            
            if not matching_allow:
                return False, f"Merchant {merchant_id} not in allowlist"
            
            # Check allow rule limits
            if matching_allow.max_per_tx and amount > matching_allow.max_per_tx:
                return False, f"Amount exceeds merchant-specific limit {matching_allow.max_per_tx}"
        
        return True, "OK"
    
    def record_spend(self, amount: Decimal) -> None:
        """Record a successful spend."""
        self.spent_total += amount
        
        if self.daily_limit:
            self.daily_limit.record_spend(amount)
        if self.weekly_limit:
            self.weekly_limit.record_spend(amount)
        if self.monthly_limit:
            self.monthly_limit.record_spend(amount)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def remaining_daily(self) -> Optional[Decimal]:
        """Get remaining daily limit."""
        if self.daily_limit:
            return self.daily_limit.remaining()
        return None
    
    def remaining_total(self) -> Decimal:
        """Get remaining total limit."""
        return max(Decimal("0"), self.limit_total - self.spent_total)
    
    def add_merchant_allow(
        self,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        max_per_tx: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> MerchantRule:
        """Add a merchant to the allowlist."""
        rule = MerchantRule(
            rule_type="allow",
            merchant_id=merchant_id,
            category=category,
            max_per_tx=max_per_tx,
            reason=reason,
        )
        self.merchant_rules.append(rule)
        self.updated_at = datetime.now(timezone.utc)
        return rule
    
    def add_merchant_deny(
        self,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> MerchantRule:
        """Add a merchant to the denylist."""
        rule = MerchantRule(
            rule_type="deny",
            merchant_id=merchant_id,
            category=category,
            reason=reason,
            expires_at=expires_at,
        )
        # Deny rules go first
        self.merchant_rules.insert(0, rule)
        self.updated_at = datetime.now(timezone.utc)
        return rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a merchant rule."""
        for i, rule in enumerate(self.merchant_rules):
            if rule.rule_id == rule_id:
                del self.merchant_rules[i]
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False


# Default policies by trust level
def create_default_policy(agent_id: str, trust_level: TrustLevel = TrustLevel.LOW) -> SpendingPolicy:
    """Create a default spending policy based on trust level."""
    
    limits = {
        TrustLevel.LOW: {
            "per_tx": Decimal("50.00"),
            "daily": Decimal("100.00"),
            "weekly": Decimal("500.00"),
            "monthly": Decimal("1000.00"),
            "total": Decimal("5000.00"),
        },
        TrustLevel.MEDIUM: {
            "per_tx": Decimal("500.00"),
            "daily": Decimal("1000.00"),
            "weekly": Decimal("5000.00"),
            "monthly": Decimal("10000.00"),
            "total": Decimal("50000.00"),
        },
        TrustLevel.HIGH: {
            "per_tx": Decimal("5000.00"),
            "daily": Decimal("10000.00"),
            "weekly": Decimal("50000.00"),
            "monthly": Decimal("100000.00"),
            "total": Decimal("500000.00"),
        },
        TrustLevel.UNLIMITED: {
            "per_tx": Decimal("999999999.00"),
            "daily": None,
            "weekly": None,
            "monthly": None,
            "total": Decimal("999999999.00"),
        },
    }
    
    tier = limits[trust_level]
    
    policy = SpendingPolicy(
        agent_id=agent_id,
        trust_level=trust_level,
        limit_per_tx=tier["per_tx"],
        limit_total=tier["total"],
    )
    
    if tier["daily"]:
        policy.daily_limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=tier["daily"],
        )
    
    if tier["weekly"]:
        policy.weekly_limit = TimeWindowLimit(
            window_type="weekly",
            limit_amount=tier["weekly"],
        )
    
    if tier["monthly"]:
        policy.monthly_limit = TimeWindowLimit(
            window_type="monthly",
            limit_amount=tier["monthly"],
        )
    
    return policy

