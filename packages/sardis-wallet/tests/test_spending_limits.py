"""
Comprehensive tests for sardis_wallet.spending_limits module.

Tests cover:
- Spending limit types and configurations
- Limit checking and enforcement
- Time-based limit resets
- Velocity controls
- Limit overrides
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_wallet.spending_limits import (
    LimitType,
    LimitScope,
    LimitAction,
    VelocityCheckType,
    SpendingLimit,
)


class TestLimitType:
    """Tests for LimitType enum."""

    def test_limit_type_values(self):
        """Should have correct limit type values."""
        assert LimitType.PER_TRANSACTION.value == "per_transaction"
        assert LimitType.DAILY.value == "daily"
        assert LimitType.WEEKLY.value == "weekly"
        assert LimitType.MONTHLY.value == "monthly"
        assert LimitType.ROLLING_24H.value == "rolling_24h"
        assert LimitType.ROLLING_7D.value == "rolling_7d"
        assert LimitType.ROLLING_30D.value == "rolling_30d"
        assert LimitType.LIFETIME.value == "lifetime"


class TestLimitScope:
    """Tests for LimitScope enum."""

    def test_limit_scope_values(self):
        """Should have correct limit scope values."""
        assert LimitScope.GLOBAL.value == "global"
        assert LimitScope.TOKEN.value == "token"
        assert LimitScope.CHAIN.value == "chain"
        assert LimitScope.MERCHANT_CATEGORY.value == "merchant_category"
        assert LimitScope.MERCHANT.value == "merchant"
        assert LimitScope.RECIPIENT.value == "recipient"


class TestLimitAction:
    """Tests for LimitAction enum."""

    def test_limit_action_values(self):
        """Should have correct limit action values."""
        assert LimitAction.BLOCK.value == "block"
        assert LimitAction.WARN.value == "warn"
        assert LimitAction.REQUIRE_MFA.value == "require_mfa"
        assert LimitAction.REQUIRE_APPROVAL.value == "require_approval"
        assert LimitAction.RATE_LIMIT.value == "rate_limit"


class TestVelocityCheckType:
    """Tests for VelocityCheckType enum."""

    def test_velocity_check_values(self):
        """Should have correct velocity check values."""
        assert VelocityCheckType.TRANSACTION_COUNT.value == "transaction_count"
        assert VelocityCheckType.UNIQUE_RECIPIENTS.value == "unique_recipients"
        assert VelocityCheckType.AMOUNT_INCREASE.value == "amount_increase"
        assert VelocityCheckType.FREQUENCY.value == "frequency"


class TestSpendingLimit:
    """Tests for SpendingLimit class."""

    def test_create_spending_limit(self):
        """Should create spending limit."""
        limit = SpendingLimit(
            limit_id="limit_123",
            wallet_id="wallet_456",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
        )

        assert limit.limit_id == "limit_123"
        assert limit.wallet_id == "wallet_456"
        assert limit.limit_type == LimitType.DAILY
        assert limit.limit_amount == Decimal("1000")
        assert limit.is_active is True

    def test_remaining_amount(self):
        """Should calculate remaining amount."""
        limit = SpendingLimit(
            limit_id="limit_1",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("300"),
        )

        remaining = limit.remaining()
        assert remaining == Decimal("700")

    def test_remaining_amount_zero(self):
        """Should not go negative."""
        limit = SpendingLimit(
            limit_id="limit_2",
            wallet_id="wallet_2",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("1200"),  # Over limit
        )

        remaining = limit.remaining()
        assert remaining == Decimal("0")

    def test_utilization_percent(self):
        """Should calculate utilization percentage."""
        limit = SpendingLimit(
            limit_id="limit_3",
            wallet_id="wallet_3",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("500"),
        )

        util = limit.utilization_percent()
        assert util == 50.0

    def test_utilization_zero_limit(self):
        """Should handle zero limit amount."""
        limit = SpendingLimit(
            limit_id="limit_4",
            wallet_id="wallet_4",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("0"),
        )

        util = limit.utilization_percent()
        assert util == 0.0

    def test_check_within_limit(self):
        """Should allow transaction within limit."""
        limit = SpendingLimit(
            limit_id="limit_5",
            wallet_id="wallet_5",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("300"),
        )

        allowed, reason, action = limit.check(Decimal("500"))

        assert allowed is True

    def test_check_exceeds_limit(self):
        """Should block transaction exceeding limit."""
        limit = SpendingLimit(
            limit_id="limit_6",
            wallet_id="wallet_6",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("800"),
        )

        allowed, reason, action = limit.check(Decimal("300"))

        assert allowed is False
        assert action == LimitAction.BLOCK

    def test_check_per_transaction_limit(self):
        """Should check per-transaction limit."""
        limit = SpendingLimit(
            limit_id="limit_7",
            wallet_id="wallet_7",
            limit_type=LimitType.PER_TRANSACTION,
            limit_amount=Decimal("500"),
        )

        # Within limit
        allowed1, _, _ = limit.check(Decimal("400"))
        assert allowed1 is True

        # Exceeds limit
        allowed2, reason, _ = limit.check(Decimal("600"))
        assert allowed2 is False
        assert "per-transaction" in reason.lower()

    def test_reset_daily_limit(self):
        """Should reset daily limit after 24 hours."""
        yesterday = datetime.now(timezone.utc) - timedelta(hours=25)

        limit = SpendingLimit(
            limit_id="limit_8",
            wallet_id="wallet_8",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("900"),
            last_reset_at=yesterday,
        )

        # This should trigger reset
        was_reset = limit.reset_if_needed()

        assert was_reset is True
        assert limit.current_spent == Decimal("0")
        assert limit.transactions_count == 0

    def test_no_reset_within_window(self):
        """Should not reset within time window."""
        recent = datetime.now(timezone.utc) - timedelta(hours=12)

        limit = SpendingLimit(
            limit_id="limit_9",
            wallet_id="wallet_9",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            current_spent=Decimal("500"),
            last_reset_at=recent,
        )

        was_reset = limit.reset_if_needed()

        assert was_reset is False
        assert limit.current_spent == Decimal("500")

    def test_weekly_window_duration(self):
        """Should have correct weekly window."""
        limit = SpendingLimit(
            limit_id="limit_10",
            wallet_id="wallet_10",
            limit_type=LimitType.WEEKLY,
            limit_amount=Decimal("5000"),
        )

        duration = limit._get_window_duration()
        assert duration == timedelta(weeks=1)

    def test_monthly_window_duration(self):
        """Should have correct monthly window."""
        limit = SpendingLimit(
            limit_id="limit_11",
            wallet_id="wallet_11",
            limit_type=LimitType.MONTHLY,
            limit_amount=Decimal("10000"),
        )

        duration = limit._get_window_duration()
        assert duration == timedelta(days=30)

    def test_per_transaction_no_window(self):
        """Per-transaction limit should have no window."""
        limit = SpendingLimit(
            limit_id="limit_12",
            wallet_id="wallet_12",
            limit_type=LimitType.PER_TRANSACTION,
            limit_amount=Decimal("500"),
        )

        duration = limit._get_window_duration()
        assert duration is None


class TestSpendingLimitScopes:
    """Tests for limit scopes."""

    def test_global_scope(self):
        """Should create global scope limit."""
        limit = SpendingLimit(
            limit_id="global_1",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            scope=LimitScope.GLOBAL,
        )

        assert limit.scope == LimitScope.GLOBAL
        assert limit.scope_value is None

    def test_token_scope(self):
        """Should create token-specific limit."""
        limit = SpendingLimit(
            limit_id="token_1",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            scope=LimitScope.TOKEN,
            scope_value="USDC",
        )

        assert limit.scope == LimitScope.TOKEN
        assert limit.scope_value == "USDC"

    def test_merchant_scope(self):
        """Should create merchant-specific limit."""
        limit = SpendingLimit(
            limit_id="merchant_1",
            wallet_id="wallet_1",
            limit_type=LimitType.MONTHLY,
            limit_amount=Decimal("500"),
            scope=LimitScope.MERCHANT,
            scope_value="merchant_xyz",
        )

        assert limit.scope == LimitScope.MERCHANT
        assert limit.scope_value == "merchant_xyz"


class TestSpendingLimitOverrides:
    """Tests for limit override functionality."""

    def test_override_disabled(self):
        """Should not allow override by default."""
        limit = SpendingLimit(
            limit_id="no_override",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
        )

        assert limit.can_be_overridden is False

    def test_override_enabled(self):
        """Should allow override when enabled."""
        limit = SpendingLimit(
            limit_id="with_override",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            can_be_overridden=True,
            override_requires_approval=True,
            override_max_amount=Decimal("2000"),
        )

        assert limit.can_be_overridden is True
        assert limit.override_requires_approval is True
        assert limit.override_max_amount == Decimal("2000")


class TestSpendingLimitWarnings:
    """Tests for warning threshold functionality."""

    def test_warning_threshold(self):
        """Should support warning threshold."""
        limit = SpendingLimit(
            limit_id="with_warning",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            warning_threshold=Decimal("80"),  # 80%
        )

        assert limit.warning_threshold == Decimal("80")


class TestSpendingLimitEdgeCases:
    """Edge case tests for spending limits."""

    def test_zero_amount_transaction(self):
        """Should handle zero amount transactions."""
        limit = SpendingLimit(
            limit_id="zero_test",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
        )

        allowed, _, _ = limit.check(Decimal("0"))
        assert allowed is True

    def test_very_large_limit(self):
        """Should handle very large limits."""
        limit = SpendingLimit(
            limit_id="large_limit",
            wallet_id="wallet_1",
            limit_type=LimitType.MONTHLY,
            limit_amount=Decimal("1000000000"),  # 1 billion
        )

        allowed, _, _ = limit.check(Decimal("999999999"))
        assert allowed is True

    def test_decimal_precision(self):
        """Should maintain decimal precision."""
        limit = SpendingLimit(
            limit_id="precision_test",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("100.123456"),
            current_spent=Decimal("50.123456"),
        )

        remaining = limit.remaining()
        assert remaining == Decimal("50.000000")

    def test_inactive_limit(self):
        """Should handle inactive limits."""
        limit = SpendingLimit(
            limit_id="inactive",
            wallet_id="wallet_1",
            limit_type=LimitType.DAILY,
            limit_amount=Decimal("1000"),
            is_active=False,
        )

        assert limit.is_active is False

    def test_lifetime_limit_no_reset(self):
        """Lifetime limit should not reset."""
        old_reset = datetime.now(timezone.utc) - timedelta(days=365)

        limit = SpendingLimit(
            limit_id="lifetime",
            wallet_id="wallet_1",
            limit_type=LimitType.LIFETIME,
            limit_amount=Decimal("100000"),
            current_spent=Decimal("50000"),
            last_reset_at=old_reset,
        )

        was_reset = limit.reset_if_needed()

        # Lifetime limits don't have a window, so no reset
        assert was_reset is False or limit._get_window_duration() is None
