"""Unit tests for spending policies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from sardis_v2_core.spending_policy import (
    SpendingPolicy,
    TimeWindowLimit,
    MerchantRule,
    TrustLevel,
    SpendingScope,
    create_default_policy,
    DEFAULT_LIMITS,
)


class TestTimeWindowLimit:
    """Tests for TimeWindowLimit model."""

    def test_time_window_creation(self):
        """Test creating a TimeWindowLimit."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
            currency="USDC",
        )
        
        assert limit.window_type == "daily"
        assert limit.limit_amount == Decimal("1000.00")
        assert limit.current_spent == Decimal("0")

    def test_time_window_remaining(self):
        """Test remaining calculation."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
            current_spent=Decimal("300.00"),
        )
        
        remaining = limit.remaining()
        assert remaining == Decimal("700.00")

    def test_time_window_can_spend_success(self):
        """Test can_spend returns True when within limit."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
            current_spent=Decimal("300.00"),
        )
        
        can_spend, reason = limit.can_spend(Decimal("500.00"))
        
        assert can_spend is True
        assert reason == "OK"

    def test_time_window_can_spend_exceeds_limit(self):
        """Test can_spend returns False when exceeding limit."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
            current_spent=Decimal("800.00"),
        )
        
        can_spend, reason = limit.can_spend(Decimal("300.00"))
        
        assert can_spend is False
        assert reason == "time_window_limit"

    def test_time_window_record_spend(self):
        """Test recording spend."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
        )
        
        limit.record_spend(Decimal("250.00"))
        limit.record_spend(Decimal("150.00"))
        
        assert limit.current_spent == Decimal("400.00")

    def test_time_window_reset_daily(self):
        """Test daily window reset when expired."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=2)
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
            current_spent=Decimal("800.00"),
            window_start=yesterday,
        )
        
        # Calling remaining() triggers reset check
        limit.remaining()
        
        assert limit.current_spent == Decimal("0")

    def test_time_window_reset_weekly(self):
        """Test weekly window reset when expired."""
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=2)
        limit = TimeWindowLimit(
            window_type="weekly",
            limit_amount=Decimal("5000.00"),
            current_spent=Decimal("4000.00"),
            window_start=two_weeks_ago,
        )
        
        reset_occurred = limit.reset_if_expired()
        
        assert reset_occurred is True
        assert limit.current_spent == Decimal("0")

    def test_time_window_no_reset_when_valid(self):
        """Test window does not reset when still valid."""
        limit = TimeWindowLimit(
            window_type="weekly",
            limit_amount=Decimal("5000.00"),
            current_spent=Decimal("2000.00"),
            window_start=datetime.now(timezone.utc),
        )
        
        reset_occurred = limit.reset_if_expired()
        
        assert reset_occurred is False
        assert limit.current_spent == Decimal("2000.00")


class TestMerchantRule:
    """Tests for MerchantRule model."""

    def test_merchant_rule_creation(self):
        """Test creating a MerchantRule."""
        rule = MerchantRule(
            rule_type="allow",
            merchant_id="merchant_123",
            max_per_tx=Decimal("500.00"),
            reason="Trusted merchant",
        )
        
        assert rule.rule_type == "allow"
        assert rule.merchant_id == "merchant_123"
        assert rule.is_active() is True

    def test_merchant_rule_is_active_expired(self):
        """Test is_active returns False for expired rule."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        rule = MerchantRule(
            rule_type="deny",
            merchant_id="merchant_456",
            expires_at=past,
        )
        
        assert rule.is_active() is False

    def test_merchant_rule_matches_by_id(self):
        """Test matches_merchant by merchant_id."""
        rule = MerchantRule(
            rule_type="allow",
            merchant_id="merchant_123",
        )
        
        assert rule.matches_merchant("merchant_123") is True
        assert rule.matches_merchant("merchant_456") is False

    def test_merchant_rule_matches_by_category(self):
        """Test matches_merchant by category."""
        rule = MerchantRule(
            rule_type="allow",
            category="electronics",
        )
        
        assert rule.matches_merchant("merchant_123", "electronics") is True
        assert rule.matches_merchant("merchant_123", "groceries") is False
        assert rule.matches_merchant("merchant_123") is False

    def test_merchant_rule_expired_does_not_match(self):
        """Test expired rule does not match."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        rule = MerchantRule(
            rule_type="allow",
            merchant_id="merchant_123",
            expires_at=past,
        )
        
        assert rule.matches_merchant("merchant_123") is False


class TestSpendingPolicy:
    """Tests for SpendingPolicy model."""

    def test_spending_policy_creation(self):
        """Test creating a SpendingPolicy."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            trust_level=TrustLevel.MEDIUM,
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("10000.00"),
        )
        
        assert policy.agent_id == "agent_001"
        assert policy.trust_level == TrustLevel.MEDIUM
        assert policy.limit_per_tx == Decimal("500.00")
        assert policy.policy_id.startswith("policy_")

    def test_validate_payment_success(self):
        """Test validate_payment returns True for valid payment."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("10000.00"),
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("1.00"),
        )
        
        assert is_valid is True
        assert reason == "OK"

    def test_validate_payment_per_tx_limit(self):
        """Test validate_payment fails on per-transaction limit."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("10000.00"),
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
        )
        
        assert is_valid is False
        assert reason == "per_transaction_limit"

    def test_validate_payment_total_limit(self):
        """Test validate_payment fails on total limit."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("200.00"),
            spent_total=Decimal("150.00"),
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
        )
        
        assert is_valid is False
        assert reason == "total_limit_exceeded"

    def test_validate_payment_scope_not_allowed(self):
        """Test validate_payment fails on disallowed scope."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            allowed_scopes=[SpendingScope.RETAIL],
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            scope=SpendingScope.AGENT_TO_AGENT,
        )
        
        assert is_valid is False
        assert reason == "scope_not_allowed"

    def test_validate_payment_scope_all_allows_everything(self):
        """Test validate_payment with ALL scope allows everything."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            allowed_scopes=[SpendingScope.ALL],
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            scope=SpendingScope.COMPUTE,
        )
        
        assert is_valid is True
        assert reason == "OK"

    def test_validate_payment_daily_limit(self):
        """Test validate_payment fails on daily limit."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("10000.00"),
            daily_limit=TimeWindowLimit(
                window_type="daily",
                limit_amount=Decimal("100.00"),
                current_spent=Decimal("80.00"),
            ),
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("50.00"),
            fee=Decimal("0.00"),
        )
        
        assert is_valid is False
        assert reason == "time_window_limit"


class TestSpendingPolicyMerchantRules:
    """Tests for merchant rule enforcement in SpendingPolicy."""

    def test_merchant_denied(self):
        """Test payment fails when merchant is denied."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("10000.00"),
        )
        policy.add_merchant_deny(
            merchant_id="bad_merchant",
            reason="Fraudulent",
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            merchant_id="bad_merchant",
        )
        
        assert is_valid is False
        assert reason == "merchant_denied"

    def test_merchant_category_denied(self):
        """Test payment fails when merchant category is denied."""
        policy = SpendingPolicy(
            agent_id="agent_001",
        )
        policy.add_merchant_deny(category="gambling")
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            merchant_id="casino_001",
            merchant_category="gambling",
        )
        
        assert is_valid is False
        assert reason == "merchant_denied"

    def test_merchant_not_allowlisted(self):
        """Test payment fails when merchant not in allowlist."""
        policy = SpendingPolicy(
            agent_id="agent_001",
        )
        policy.add_merchant_allow(merchant_id="trusted_merchant")
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            merchant_id="unknown_merchant",
        )
        
        assert is_valid is False
        assert reason == "merchant_not_allowlisted"

    def test_merchant_cap_exceeded(self):
        """Test payment fails when exceeding merchant cap."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_per_tx=Decimal("1000.00"),
        )
        policy.add_merchant_allow(
            merchant_id="limited_merchant",
            max_per_tx=Decimal("50.00"),
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            merchant_id="limited_merchant",
        )
        
        assert is_valid is False
        assert reason == "merchant_cap_exceeded"

    def test_merchant_allowlist_success(self):
        """Test payment succeeds when merchant is allowlisted."""
        policy = SpendingPolicy(
            agent_id="agent_001",
        )
        policy.add_merchant_allow(
            merchant_id="trusted_merchant",
            max_per_tx=Decimal("500.00"),
        )
        
        is_valid, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            merchant_id="trusted_merchant",
        )
        
        assert is_valid is True
        assert reason == "OK"


class TestSpendingPolicyHelpers:
    """Tests for SpendingPolicy helper methods."""

    def test_record_spend(self):
        """Test record_spend updates all limits."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            daily_limit=TimeWindowLimit(window_type="daily", limit_amount=Decimal("1000.00")),
            weekly_limit=TimeWindowLimit(window_type="weekly", limit_amount=Decimal("5000.00")),
        )
        
        policy.record_spend(Decimal("100.00"))
        
        assert policy.spent_total == Decimal("100.00")
        assert policy.daily_limit.current_spent == Decimal("100.00")
        assert policy.weekly_limit.current_spent == Decimal("100.00")

    def test_remaining_total(self):
        """Test remaining_total calculation."""
        policy = SpendingPolicy(
            agent_id="agent_001",
            limit_total=Decimal("1000.00"),
            spent_total=Decimal("350.00"),
        )
        
        remaining = policy.remaining_total()
        assert remaining == Decimal("650.00")

    def test_add_merchant_allow(self):
        """Test adding merchant allow rule."""
        policy = SpendingPolicy(agent_id="agent_001")
        
        rule = policy.add_merchant_allow(
            merchant_id="good_merchant",
            max_per_tx=Decimal("200.00"),
            reason="Verified partner",
        )
        
        assert len(policy.merchant_rules) == 1
        assert rule.rule_type == "allow"
        assert rule.merchant_id == "good_merchant"

    def test_add_merchant_deny(self):
        """Test adding merchant deny rule (added at front)."""
        policy = SpendingPolicy(agent_id="agent_001")
        policy.add_merchant_allow(merchant_id="merchant_1")
        
        rule = policy.add_merchant_deny(
            merchant_id="bad_merchant",
            reason="Suspicious activity",
        )
        
        assert len(policy.merchant_rules) == 2
        assert policy.merchant_rules[0] == rule  # Deny rules added at front
        assert rule.rule_type == "deny"


class TestCreateDefaultPolicy:
    """Tests for create_default_policy factory function."""

    def test_create_low_trust_policy(self):
        """Test creating LOW trust policy."""
        policy = create_default_policy("agent_001", TrustLevel.LOW)
        
        assert policy.agent_id == "agent_001"
        assert policy.trust_level == TrustLevel.LOW
        assert policy.limit_per_tx == Decimal("50.00")
        assert policy.daily_limit is not None
        assert policy.daily_limit.limit_amount == Decimal("100.00")

    def test_create_medium_trust_policy(self):
        """Test creating MEDIUM trust policy."""
        policy = create_default_policy("agent_001", TrustLevel.MEDIUM)
        
        assert policy.trust_level == TrustLevel.MEDIUM
        assert policy.limit_per_tx == Decimal("500.00")
        assert policy.limit_total == Decimal("50000.00")

    def test_create_high_trust_policy(self):
        """Test creating HIGH trust policy."""
        policy = create_default_policy("agent_001", TrustLevel.HIGH)
        
        assert policy.trust_level == TrustLevel.HIGH
        assert policy.limit_per_tx == Decimal("5000.00")

    def test_create_unlimited_trust_policy(self):
        """Test creating UNLIMITED trust policy."""
        policy = create_default_policy("agent_001", TrustLevel.UNLIMITED)
        
        assert policy.trust_level == TrustLevel.UNLIMITED
        assert policy.limit_per_tx == Decimal("999999999.00")
        assert policy.daily_limit is None
        assert policy.weekly_limit is None
        assert policy.monthly_limit is None

    def test_default_limits_structure(self):
        """Test DEFAULT_LIMITS dictionary structure."""
        for trust_level in TrustLevel:
            assert trust_level in DEFAULT_LIMITS
            limits = DEFAULT_LIMITS[trust_level]
            assert "per_tx" in limits
            assert "total" in limits

