"""Advanced spending policy logic migrated from V1."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class TrustLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNLIMITED = "unlimited"


class SpendingScope(str, Enum):
    ALL = "all"
    RETAIL = "retail"
    DIGITAL = "digital"
    SERVICES = "services"
    COMPUTE = "compute"
    DATA = "data"
    AGENT_TO_AGENT = "agent_to_agent"


@dataclass(slots=True)
class TimeWindowLimit:
    window_type: str
    limit_amount: Decimal
    currency: str = "USDC"
    current_spent: Decimal = field(default_factory=lambda: Decimal("0"))
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reset_if_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.window_type == "daily":
            duration = timedelta(days=1)
        elif self.window_type == "weekly":
            duration = timedelta(weeks=1)
        elif self.window_type == "monthly":
            duration = timedelta(days=30)
        else:
            return False
        if now >= self.window_start + duration:
            self.current_spent = Decimal("0")
            self.window_start = now
            return True
        return False

    def remaining(self) -> Decimal:
        self.reset_if_expired()
        return max(Decimal("0"), self.limit_amount - self.current_spent)

    def can_spend(self, amount: Decimal) -> tuple[bool, str]:
        self.reset_if_expired()
        if self.current_spent + amount > self.limit_amount:
            return False, "time_window_limit"
        return True, "OK"

    def record_spend(self, amount: Decimal) -> None:
        self.reset_if_expired()
        self.current_spent += amount


@dataclass(slots=True)
class MerchantRule:
    rule_id: str = field(default_factory=lambda: f"rule_{uuid.uuid4().hex[:12]}")
    rule_type: str = "allow"
    merchant_id: Optional[str] = None
    category: Optional[str] = None
    max_per_tx: Optional[Decimal] = None
    daily_limit: Optional[Decimal] = None
    reason: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def is_active(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def matches_merchant(self, merchant_id: str, merchant_category: Optional[str] = None) -> bool:
        if not self.is_active():
            return False
        if self.merchant_id and self.merchant_id == merchant_id:
            return True
        if self.category and merchant_category and self.category == merchant_category:
            return True
        return False


@dataclass(slots=True)
class SpendingPolicy:
    policy_id: str = field(default_factory=lambda: f"policy_{uuid.uuid4().hex[:16]}")
    agent_id: str = ""
    trust_level: TrustLevel = TrustLevel.LOW
    limit_per_tx: Decimal = field(default_factory=lambda: Decimal("100.00"))
    limit_total: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    spent_total: Decimal = field(default_factory=lambda: Decimal("0"))
    daily_limit: Optional[TimeWindowLimit] = None
    weekly_limit: Optional[TimeWindowLimit] = None
    monthly_limit: Optional[TimeWindowLimit] = None
    merchant_rules: list[MerchantRule] = field(default_factory=list)
    allowed_scopes: list[SpendingScope] = field(default_factory=lambda: [SpendingScope.ALL])
    require_preauth: bool = False
    max_hold_hours: int = 168
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate_payment(
        self,
        amount: Decimal,
        fee: Decimal,
        *,
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        scope: SpendingScope = SpendingScope.ALL,
    ) -> tuple[bool, str]:
        total_cost = amount + fee
        if SpendingScope.ALL not in self.allowed_scopes and scope not in self.allowed_scopes:
            return False, "scope_not_allowed"
        if amount > self.limit_per_tx:
            return False, "per_transaction_limit"
        if self.spent_total + amount > self.limit_total:
            return False, "total_limit_exceeded"
        for window_limit in filter(None, [self.daily_limit, self.weekly_limit, self.monthly_limit]):
            ok, reason = window_limit.can_spend(amount)
            if not ok:
                return ok, reason
        if merchant_id:
            merchant_ok, merchant_reason = self._check_merchant_rules(merchant_id, merchant_category, amount)
            if not merchant_ok:
                return False, merchant_reason
        return True, "OK"

    def _check_merchant_rules(
        self,
        merchant_id: str,
        merchant_category: Optional[str],
        amount: Decimal,
    ) -> tuple[bool, str]:
        for rule in self.merchant_rules:
            if rule.rule_type == "deny" and rule.matches_merchant(merchant_id, merchant_category):
                return False, "merchant_denied"
        allow_rules = [rule for rule in self.merchant_rules if rule.rule_type == "allow"]
        if allow_rules:
            match = next((rule for rule in allow_rules if rule.matches_merchant(merchant_id, merchant_category)), None)
            if not match:
                return False, "merchant_not_allowlisted"
            if match.max_per_tx and amount > match.max_per_tx:
                return False, "merchant_cap_exceeded"
        return True, "OK"

    def record_spend(self, amount: Decimal) -> None:
        self.spent_total += amount
        for window_limit in filter(None, [self.daily_limit, self.weekly_limit, self.monthly_limit]):
            window_limit.record_spend(amount)
        self.updated_at = datetime.now(timezone.utc)

    def remaining_total(self) -> Decimal:
        return max(Decimal("0"), self.limit_total - self.spent_total)

    def add_merchant_allow(
        self,
        *,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        max_per_tx: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> MerchantRule:
        rule = MerchantRule(rule_type="allow", merchant_id=merchant_id, category=category, max_per_tx=max_per_tx, reason=reason)
        self.merchant_rules.append(rule)
        self.updated_at = datetime.now(timezone.utc)
        return rule

    def add_merchant_deny(
        self,
        *,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> MerchantRule:
        rule = MerchantRule(rule_type="deny", merchant_id=merchant_id, category=category, reason=reason, expires_at=expires_at)
        self.merchant_rules.insert(0, rule)
        self.updated_at = datetime.now(timezone.utc)
        return rule


DEFAULT_LIMITS = {
    TrustLevel.LOW: {"per_tx": Decimal("50.00"), "daily": Decimal("100.00"), "weekly": Decimal("500.00"), "monthly": Decimal("1000.00"), "total": Decimal("5000.00")},
    TrustLevel.MEDIUM: {"per_tx": Decimal("500.00"), "daily": Decimal("1000.00"), "weekly": Decimal("5000.00"), "monthly": Decimal("10000.00"), "total": Decimal("50000.00")},
    TrustLevel.HIGH: {"per_tx": Decimal("5000.00"), "daily": Decimal("10000.00"), "weekly": Decimal("50000.00"), "monthly": Decimal("100000.00"), "total": Decimal("500000.00")},
    TrustLevel.UNLIMITED: {"per_tx": Decimal("999999999.00"), "daily": None, "weekly": None, "monthly": None, "total": Decimal("999999999.00")},
}


def create_default_policy(agent_id: str, trust_level: TrustLevel = TrustLevel.LOW) -> SpendingPolicy:
    tier = DEFAULT_LIMITS[trust_level]
    policy = SpendingPolicy(agent_id=agent_id, trust_level=trust_level, limit_per_tx=tier["per_tx"], limit_total=tier["total"])
    if tier["daily"]:
        policy.daily_limit = TimeWindowLimit(window_type="daily", limit_amount=tier["daily"])
    if tier["weekly"]:
        policy.weekly_limit = TimeWindowLimit(window_type="weekly", limit_amount=tier["weekly"])
    if tier["monthly"]:
        policy.monthly_limit = TimeWindowLimit(window_type="monthly", limit_amount=tier["monthly"])
    return policy
