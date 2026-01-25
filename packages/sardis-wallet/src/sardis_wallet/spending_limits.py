"""
Enhanced Spending Limits for Sardis Wallets.

Implements granular spending controls with multiple dimensions:
- Per-transaction limits
- Time-based limits (daily, weekly, monthly)
- Category-based limits
- Velocity controls
- Dynamic limit adjustments
- Compliance-based limits
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_v2_core import Wallet, Transaction

logger = logging.getLogger(__name__)


class LimitType(str, Enum):
    """Type of spending limit."""
    PER_TRANSACTION = "per_transaction"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ROLLING_24H = "rolling_24h"
    ROLLING_7D = "rolling_7d"
    ROLLING_30D = "rolling_30d"
    LIFETIME = "lifetime"


class LimitScope(str, Enum):
    """Scope of the limit application."""
    GLOBAL = "global"  # Applies to all transactions
    TOKEN = "token"  # Specific token
    CHAIN = "chain"  # Specific chain
    MERCHANT_CATEGORY = "merchant_category"
    MERCHANT = "merchant"
    RECIPIENT = "recipient"


class LimitAction(str, Enum):
    """Action when limit is hit."""
    BLOCK = "block"
    WARN = "warn"
    REQUIRE_MFA = "require_mfa"
    REQUIRE_APPROVAL = "require_approval"
    RATE_LIMIT = "rate_limit"


class VelocityCheckType(str, Enum):
    """Type of velocity check."""
    TRANSACTION_COUNT = "transaction_count"
    UNIQUE_RECIPIENTS = "unique_recipients"
    AMOUNT_INCREASE = "amount_increase"
    FREQUENCY = "frequency"


@dataclass
class SpendingLimit:
    """A spending limit configuration."""
    limit_id: str
    wallet_id: str
    limit_type: LimitType
    limit_amount: Decimal
    currency: str = "USD"  # Limit currency for normalization
    scope: LimitScope = LimitScope.GLOBAL
    scope_value: Optional[str] = None  # Token name, chain, merchant, etc.
    action: LimitAction = LimitAction.BLOCK
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None

    # Current state
    current_spent: Decimal = field(default_factory=lambda: Decimal("0"))
    last_reset_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    transactions_count: int = 0

    # Soft limit (warning threshold)
    warning_threshold: Optional[Decimal] = None  # Warn at this percentage
    warning_sent_at: Optional[datetime] = None

    # Override settings
    can_be_overridden: bool = False
    override_requires_approval: bool = True
    override_max_amount: Optional[Decimal] = None

    def reset_if_needed(self) -> bool:
        """Reset spending counter if the time window has passed."""
        now = datetime.now(timezone.utc)

        if self.limit_type == LimitType.PER_TRANSACTION:
            return False

        window_duration = self._get_window_duration()
        if window_duration and now >= self.last_reset_at + window_duration:
            self.current_spent = Decimal("0")
            self.transactions_count = 0
            self.last_reset_at = now
            self.warning_sent_at = None
            return True

        return False

    def _get_window_duration(self) -> Optional[timedelta]:
        """Get the duration of the limit window."""
        durations = {
            LimitType.DAILY: timedelta(days=1),
            LimitType.WEEKLY: timedelta(weeks=1),
            LimitType.MONTHLY: timedelta(days=30),
            LimitType.ROLLING_24H: timedelta(hours=24),
            LimitType.ROLLING_7D: timedelta(days=7),
            LimitType.ROLLING_30D: timedelta(days=30),
        }
        return durations.get(self.limit_type)

    def remaining(self) -> Decimal:
        """Get remaining amount in the limit."""
        self.reset_if_needed()
        return max(Decimal("0"), self.limit_amount - self.current_spent)

    def utilization_percent(self) -> float:
        """Get current utilization as percentage."""
        if self.limit_amount <= 0:
            return 0.0
        self.reset_if_needed()
        return float(self.current_spent / self.limit_amount * 100)

    def check(self, amount: Decimal) -> Tuple[bool, str, LimitAction]:
        """
        Check if a transaction amount is within limit.

        Returns:
            Tuple of (allowed, reason, action)
        """
        self.reset_if_needed()

        if self.limit_type == LimitType.PER_TRANSACTION:
            if amount > self.limit_amount:
                return False, f"Exceeds per-transaction limit of {self.limit_amount}", self.action
            return True, "OK", LimitAction.BLOCK

        # Check cumulative limit
        if self.current_spent + amount > self.limit_amount:
            return (
                False,
                f"Would exceed {self.limit_type.value} limit of {self.limit_amount} "
                f"(current: {self.current_spent}, remaining: {self.remaining()})",
                self.action,
            )

        # Check warning threshold
        if self.warning_threshold:
            new_utilization = (self.current_spent + amount) / self.limit_amount * 100
            if new_utilization >= float(self.warning_threshold):
                if not self.warning_sent_at:
                    return True, f"Warning: {new_utilization:.1f}% of limit utilized", LimitAction.WARN

        return True, "OK", LimitAction.BLOCK

    def record_spend(self, amount: Decimal) -> None:
        """Record a spend against this limit."""
        self.reset_if_needed()
        self.current_spent += amount
        self.transactions_count += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "limit_id": self.limit_id,
            "wallet_id": self.wallet_id,
            "limit_type": self.limit_type.value,
            "limit_amount": str(self.limit_amount),
            "currency": self.currency,
            "scope": self.scope.value,
            "scope_value": self.scope_value,
            "action": self.action.value,
            "is_active": self.is_active,
            "current_spent": str(self.current_spent),
            "remaining": str(self.remaining()),
            "utilization_percent": self.utilization_percent(),
            "transactions_count": self.transactions_count,
            "last_reset_at": self.last_reset_at.isoformat(),
        }


@dataclass
class VelocityRule:
    """Velocity control rule for detecting unusual patterns."""
    rule_id: str
    wallet_id: str
    check_type: VelocityCheckType
    threshold: int  # Threshold value
    window_minutes: int = 60
    action: LimitAction = LimitAction.REQUIRE_MFA
    is_active: bool = True

    # Current state
    current_count: int = 0
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unique_values: set = field(default_factory=set)

    def reset_if_needed(self) -> bool:
        """Reset counter if window has passed."""
        now = datetime.now(timezone.utc)
        window = timedelta(minutes=self.window_minutes)

        if now >= self.window_start + window:
            self.current_count = 0
            self.unique_values = set()
            self.window_start = now
            return True
        return False

    def check(self, transaction_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if transaction triggers velocity rule.

        Returns:
            Tuple of (triggered, reason)
        """
        self.reset_if_needed()

        if self.check_type == VelocityCheckType.TRANSACTION_COUNT:
            if self.current_count + 1 > self.threshold:
                return True, f"Too many transactions ({self.current_count + 1}) in {self.window_minutes} minutes"

        elif self.check_type == VelocityCheckType.UNIQUE_RECIPIENTS:
            recipient = transaction_data.get("recipient", "")
            self.unique_values.add(recipient)
            if len(self.unique_values) > self.threshold:
                return True, f"Too many unique recipients ({len(self.unique_values)}) in {self.window_minutes} minutes"

        elif self.check_type == VelocityCheckType.AMOUNT_INCREASE:
            # Check for sudden increase in transaction amounts
            avg_amount = transaction_data.get("avg_amount", Decimal("0"))
            current_amount = transaction_data.get("amount", Decimal("0"))
            if avg_amount > 0:
                increase_factor = current_amount / avg_amount
                if increase_factor > self.threshold:
                    return True, f"Transaction amount {increase_factor:.1f}x higher than average"

        return False, "OK"

    def record(self, transaction_data: Dict[str, Any]) -> None:
        """Record a transaction for velocity tracking."""
        self.reset_if_needed()
        self.current_count += 1

        if self.check_type == VelocityCheckType.UNIQUE_RECIPIENTS:
            recipient = transaction_data.get("recipient", "")
            self.unique_values.add(recipient)


@dataclass
class DynamicLimitAdjustment:
    """Configuration for automatic limit adjustments."""
    adjustment_id: str
    wallet_id: str
    base_limit_id: str

    # Adjustment triggers
    increase_after_days: int = 30  # Days of good behavior before increase
    increase_percentage: float = 10.0  # Percentage to increase
    max_increase_multiplier: float = 3.0  # Maximum multiplier from base

    decrease_on_violation: bool = True
    decrease_percentage: float = 20.0  # Percentage to decrease on violation
    min_decrease_multiplier: float = 0.5  # Minimum multiplier from base

    # Current state
    current_multiplier: float = 1.0
    last_adjustment_at: Optional[datetime] = None
    violation_count: int = 0
    clean_days: int = 0


@dataclass
class ComplianceLimit:
    """Compliance-based spending limits."""
    limit_id: str
    wallet_id: str
    compliance_type: str  # "aml", "ofac", "travel_rule", "kyc_level"
    limit_amount: Decimal
    currency: str = "USD"

    # KYC level thresholds
    kyc_level_required: int = 0  # 0=none, 1=basic, 2=enhanced, 3=full
    current_kyc_level: int = 0

    # Restrictions
    blocked_countries: List[str] = field(default_factory=list)
    blocked_categories: List[str] = field(default_factory=list)

    is_active: bool = True

    def check(
        self,
        amount: Decimal,
        recipient_country: Optional[str] = None,
        merchant_category: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Check compliance limits."""
        # Check KYC level
        if self.current_kyc_level < self.kyc_level_required:
            return False, f"KYC level {self.kyc_level_required} required (current: {self.current_kyc_level})"

        # Check amount
        if amount > self.limit_amount:
            return False, f"Amount exceeds compliance limit of {self.limit_amount}"

        # Check blocked countries
        if recipient_country and recipient_country.upper() in self.blocked_countries:
            return False, f"Transfers to {recipient_country} are restricted"

        # Check blocked categories
        if merchant_category and merchant_category in self.blocked_categories:
            return False, f"Category {merchant_category} is restricted"

        return True, "OK"


@dataclass
class SpendingLimitsConfig:
    """Configuration for spending limits."""
    wallet_id: str

    # Default limits
    default_per_tx: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    default_daily: Decimal = field(default_factory=lambda: Decimal("5000.00"))
    default_weekly: Decimal = field(default_factory=lambda: Decimal("25000.00"))
    default_monthly: Decimal = field(default_factory=lambda: Decimal("100000.00"))

    # Velocity defaults
    max_transactions_per_hour: int = 20
    max_unique_recipients_per_day: int = 10

    # Dynamic adjustment settings
    enable_dynamic_limits: bool = True
    enable_velocity_checks: bool = True
    enable_compliance_limits: bool = True


class SpendingLimitsManager:
    """
    Manages spending limits for wallets.

    Features:
    - Multiple limit types (per-tx, daily, weekly, monthly, rolling)
    - Scope-based limits (token, chain, merchant)
    - Velocity controls
    - Dynamic limit adjustments
    - Compliance integration
    """

    def __init__(self):
        # Storage (in production, use database)
        self._configs: Dict[str, SpendingLimitsConfig] = {}
        self._limits: Dict[str, Dict[str, SpendingLimit]] = {}  # wallet_id -> limit_id -> limit
        self._velocity_rules: Dict[str, Dict[str, VelocityRule]] = {}
        self._compliance_limits: Dict[str, Dict[str, ComplianceLimit]] = {}
        self._dynamic_adjustments: Dict[str, Dict[str, DynamicLimitAdjustment]] = {}

        # Transaction history for velocity checks
        self._transaction_history: Dict[str, List[Dict[str, Any]]] = {}

        # Lock for concurrent access
        self._lock = asyncio.Lock()

    async def setup_default_limits(
        self,
        wallet_id: str,
        config: Optional[SpendingLimitsConfig] = None,
    ) -> SpendingLimitsConfig:
        """
        Set up default spending limits for a wallet.

        Args:
            wallet_id: Wallet identifier
            config: Optional custom configuration

        Returns:
            SpendingLimitsConfig for the wallet
        """
        limits_config = config or SpendingLimitsConfig(wallet_id=wallet_id)
        limits_config.wallet_id = wallet_id
        self._configs[wallet_id] = limits_config

        # Initialize storage
        self._limits[wallet_id] = {}
        self._velocity_rules[wallet_id] = {}
        self._compliance_limits[wallet_id] = {}

        # Create default limits
        default_limits = [
            SpendingLimit(
                limit_id=f"limit_per_tx_{wallet_id[:8]}",
                wallet_id=wallet_id,
                limit_type=LimitType.PER_TRANSACTION,
                limit_amount=limits_config.default_per_tx,
                warning_threshold=Decimal("80"),
            ),
            SpendingLimit(
                limit_id=f"limit_daily_{wallet_id[:8]}",
                wallet_id=wallet_id,
                limit_type=LimitType.DAILY,
                limit_amount=limits_config.default_daily,
                warning_threshold=Decimal("80"),
            ),
            SpendingLimit(
                limit_id=f"limit_weekly_{wallet_id[:8]}",
                wallet_id=wallet_id,
                limit_type=LimitType.WEEKLY,
                limit_amount=limits_config.default_weekly,
                warning_threshold=Decimal("80"),
            ),
            SpendingLimit(
                limit_id=f"limit_monthly_{wallet_id[:8]}",
                wallet_id=wallet_id,
                limit_type=LimitType.MONTHLY,
                limit_amount=limits_config.default_monthly,
                warning_threshold=Decimal("80"),
            ),
        ]

        for limit in default_limits:
            self._limits[wallet_id][limit.limit_id] = limit

        # Create default velocity rules
        if limits_config.enable_velocity_checks:
            velocity_rules = [
                VelocityRule(
                    rule_id=f"velocity_tx_count_{wallet_id[:8]}",
                    wallet_id=wallet_id,
                    check_type=VelocityCheckType.TRANSACTION_COUNT,
                    threshold=limits_config.max_transactions_per_hour,
                    window_minutes=60,
                ),
                VelocityRule(
                    rule_id=f"velocity_recipients_{wallet_id[:8]}",
                    wallet_id=wallet_id,
                    check_type=VelocityCheckType.UNIQUE_RECIPIENTS,
                    threshold=limits_config.max_unique_recipients_per_day,
                    window_minutes=1440,  # 24 hours
                ),
            ]

            for rule in velocity_rules:
                self._velocity_rules[wallet_id][rule.rule_id] = rule

        logger.info(f"Set up default spending limits for wallet {wallet_id}")
        return limits_config

    async def add_limit(
        self,
        wallet_id: str,
        limit_type: LimitType,
        limit_amount: Decimal,
        scope: LimitScope = LimitScope.GLOBAL,
        scope_value: Optional[str] = None,
        action: LimitAction = LimitAction.BLOCK,
        created_by: Optional[str] = None,
    ) -> SpendingLimit:
        """Add a new spending limit."""
        import secrets

        limit_id = f"limit_{secrets.token_hex(8)}"

        limit = SpendingLimit(
            limit_id=limit_id,
            wallet_id=wallet_id,
            limit_type=limit_type,
            limit_amount=limit_amount,
            scope=scope,
            scope_value=scope_value,
            action=action,
            created_by=created_by,
        )

        if wallet_id not in self._limits:
            self._limits[wallet_id] = {}

        self._limits[wallet_id][limit_id] = limit

        logger.info(
            f"Added {limit_type.value} limit of {limit_amount} for wallet {wallet_id}"
        )

        return limit

    async def update_limit(
        self,
        wallet_id: str,
        limit_id: str,
        limit_amount: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        action: Optional[LimitAction] = None,
    ) -> Optional[SpendingLimit]:
        """Update an existing limit."""
        limit = self._limits.get(wallet_id, {}).get(limit_id)
        if not limit:
            return None

        if limit_amount is not None:
            limit.limit_amount = limit_amount
        if is_active is not None:
            limit.is_active = is_active
        if action is not None:
            limit.action = action

        limit.updated_at = datetime.now(timezone.utc)

        logger.info(f"Updated limit {limit_id} for wallet {wallet_id}")
        return limit

    async def check_transaction(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
        chain: str = "base",
        recipient: Optional[str] = None,
        merchant_category: Optional[str] = None,
        merchant_id: Optional[str] = None,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check if a transaction is within all limits.

        Args:
            wallet_id: Wallet identifier
            amount: Transaction amount
            token: Token type
            chain: Chain identifier
            recipient: Recipient address
            merchant_category: Merchant category
            merchant_id: Merchant identifier

        Returns:
            Tuple of (allowed, list of limit check results)
        """
        async with self._lock:
            results = []
            all_allowed = True

            wallet_limits = self._limits.get(wallet_id, {})

            for limit in wallet_limits.values():
                if not limit.is_active:
                    continue

                # Check if limit applies to this transaction
                applies = self._limit_applies(
                    limit,
                    token=token,
                    chain=chain,
                    merchant_category=merchant_category,
                    merchant_id=merchant_id,
                    recipient=recipient,
                )

                if not applies:
                    continue

                allowed, reason, action = limit.check(amount)

                results.append({
                    "limit_id": limit.limit_id,
                    "limit_type": limit.limit_type.value,
                    "allowed": allowed,
                    "reason": reason,
                    "action": action.value,
                    "remaining": str(limit.remaining()),
                    "utilization": limit.utilization_percent(),
                })

                if not allowed:
                    all_allowed = False

            # Check velocity rules
            velocity_results = await self._check_velocity(
                wallet_id,
                amount=amount,
                recipient=recipient,
            )
            results.extend(velocity_results)

            if any(not r.get("allowed", True) for r in velocity_results):
                all_allowed = False

            # Check compliance limits
            compliance_results = await self._check_compliance(
                wallet_id,
                amount=amount,
                merchant_category=merchant_category,
            )
            results.extend(compliance_results)

            if any(not r.get("allowed", True) for r in compliance_results):
                all_allowed = False

            return all_allowed, results

    def _limit_applies(
        self,
        limit: SpendingLimit,
        token: str,
        chain: str,
        merchant_category: Optional[str],
        merchant_id: Optional[str],
        recipient: Optional[str],
    ) -> bool:
        """Check if a limit applies to a transaction."""
        if limit.scope == LimitScope.GLOBAL:
            return True
        if limit.scope == LimitScope.TOKEN and limit.scope_value == token:
            return True
        if limit.scope == LimitScope.CHAIN and limit.scope_value == chain:
            return True
        if limit.scope == LimitScope.MERCHANT_CATEGORY and limit.scope_value == merchant_category:
            return True
        if limit.scope == LimitScope.MERCHANT and limit.scope_value == merchant_id:
            return True
        if limit.scope == LimitScope.RECIPIENT and limit.scope_value == recipient:
            return True
        return False

    async def _check_velocity(
        self,
        wallet_id: str,
        amount: Decimal,
        recipient: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Check velocity rules."""
        results = []
        rules = self._velocity_rules.get(wallet_id, {})

        # Calculate average amount from history
        history = self._transaction_history.get(wallet_id, [])
        avg_amount = Decimal("0")
        if history:
            total = sum(Decimal(str(tx.get("amount", 0))) for tx in history[-10:])
            avg_amount = total / len(history[-10:])

        tx_data = {
            "amount": amount,
            "recipient": recipient,
            "avg_amount": avg_amount,
        }

        for rule in rules.values():
            if not rule.is_active:
                continue

            triggered, reason = rule.check(tx_data)

            results.append({
                "rule_id": rule.rule_id,
                "rule_type": "velocity",
                "check_type": rule.check_type.value,
                "allowed": not triggered,
                "reason": reason,
                "action": rule.action.value if triggered else None,
            })

        return results

    async def _check_compliance(
        self,
        wallet_id: str,
        amount: Decimal,
        merchant_category: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Check compliance limits."""
        results = []
        compliance_limits = self._compliance_limits.get(wallet_id, {})

        for limit in compliance_limits.values():
            if not limit.is_active:
                continue

            allowed, reason = limit.check(
                amount=amount,
                merchant_category=merchant_category,
            )

            results.append({
                "limit_id": limit.limit_id,
                "limit_type": "compliance",
                "compliance_type": limit.compliance_type,
                "allowed": allowed,
                "reason": reason,
            })

        return results

    async def record_transaction(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
        chain: str = "base",
        recipient: Optional[str] = None,
        merchant_category: Optional[str] = None,
        merchant_id: Optional[str] = None,
    ) -> None:
        """Record a transaction against limits."""
        async with self._lock:
            wallet_limits = self._limits.get(wallet_id, {})

            for limit in wallet_limits.values():
                if not limit.is_active:
                    continue

                applies = self._limit_applies(
                    limit,
                    token=token,
                    chain=chain,
                    merchant_category=merchant_category,
                    merchant_id=merchant_id,
                    recipient=recipient,
                )

                if applies:
                    limit.record_spend(amount)

            # Record for velocity tracking
            velocity_rules = self._velocity_rules.get(wallet_id, {})
            tx_data = {
                "amount": amount,
                "recipient": recipient,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            for rule in velocity_rules.values():
                if rule.is_active:
                    rule.record(tx_data)

            # Store in history
            if wallet_id not in self._transaction_history:
                self._transaction_history[wallet_id] = []
            self._transaction_history[wallet_id].append(tx_data)

            # Keep only last 100 transactions
            self._transaction_history[wallet_id] = self._transaction_history[wallet_id][-100:]

    def get_limits(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get all limits for a wallet."""
        limits = self._limits.get(wallet_id, {})
        return [limit.to_dict() for limit in limits.values()]

    def get_limit_summary(self, wallet_id: str) -> Dict[str, Any]:
        """Get a summary of limit utilization."""
        limits = self._limits.get(wallet_id, {})

        summary = {
            "wallet_id": wallet_id,
            "limits": [],
            "total_utilization": 0.0,
            "warnings": [],
        }

        total_util = 0.0
        count = 0

        for limit in limits.values():
            if not limit.is_active:
                continue

            util = limit.utilization_percent()
            total_util += util
            count += 1

            limit_info = {
                "type": limit.limit_type.value,
                "limit": str(limit.limit_amount),
                "spent": str(limit.current_spent),
                "remaining": str(limit.remaining()),
                "utilization": util,
            }
            summary["limits"].append(limit_info)

            if util >= 80:
                summary["warnings"].append(
                    f"{limit.limit_type.value} limit at {util:.1f}% utilization"
                )

        if count > 0:
            summary["total_utilization"] = total_util / count

        return summary


# Singleton instance
_spending_limits_manager: Optional[SpendingLimitsManager] = None


def get_spending_limits_manager() -> SpendingLimitsManager:
    """Get the global spending limits manager instance."""
    global _spending_limits_manager

    if _spending_limits_manager is None:
        _spending_limits_manager = SpendingLimitsManager()

    return _spending_limits_manager


__all__ = [
    "LimitType",
    "LimitScope",
    "LimitAction",
    "VelocityCheckType",
    "SpendingLimit",
    "VelocityRule",
    "DynamicLimitAdjustment",
    "ComplianceLimit",
    "SpendingLimitsConfig",
    "SpendingLimitsManager",
    "get_spending_limits_manager",
]
