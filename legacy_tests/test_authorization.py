"""Tests for the AuthorizationService with spending policies."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sardis_core.services.authorization_service import (
    AuthorizationService,
    AuthorizationResult,
    get_authorization_service,
)
from sardis_core.models.spending_policy import (
    SpendingPolicy,
    TrustLevel,
    SpendingScope,
    MerchantRule,
    TimeWindowLimit,
    create_default_policy,
)


class TestSpendingPolicy:
    """Test suite for SpendingPolicy model."""
    
    def test_create_default_policy_low_trust(self):
        """Test creating default policy for low trust level."""
        policy = create_default_policy("agent_1", TrustLevel.LOW)
        
        assert policy.agent_id == "agent_1"
        assert policy.trust_level == TrustLevel.LOW
        assert policy.limit_per_tx == Decimal("50.00")
        assert policy.limit_total == Decimal("5000.00")
        assert policy.daily_limit is not None
        assert policy.daily_limit.limit_amount == Decimal("100.00")
    
    def test_create_default_policy_high_trust(self):
        """Test creating default policy for high trust level."""
        policy = create_default_policy("agent_1", TrustLevel.HIGH)
        
        assert policy.limit_per_tx == Decimal("5000.00")
        assert policy.limit_total == Decimal("500000.00")
        assert policy.daily_limit.limit_amount == Decimal("10000.00")
    
    def test_create_default_policy_unlimited(self):
        """Test creating default policy for unlimited trust level."""
        policy = create_default_policy("agent_1", TrustLevel.UNLIMITED)
        
        assert policy.limit_per_tx == Decimal("999999999.00")
        assert policy.daily_limit is None  # No daily limit for unlimited
    
    def test_validate_payment_within_limits(self):
        """Test validating a payment within limits."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        
        allowed, reason = policy.validate_payment(
            amount=Decimal("100.00"),
            fee=Decimal("1.00")
        )
        
        assert allowed is True
        assert reason == "OK"
    
    def test_validate_payment_exceeds_per_tx_limit(self):
        """Test payment exceeding per-transaction limit."""
        policy = create_default_policy("agent_1", TrustLevel.LOW)
        
        allowed, reason = policy.validate_payment(
            amount=Decimal("100.00"),  # Exceeds 50.00 limit
            fee=Decimal("0.00")
        )
        
        assert allowed is False
        assert "per-transaction limit" in reason.lower()
    
    def test_validate_payment_exceeds_total_limit(self):
        """Test payment exceeding total spending limit."""
        policy = create_default_policy("agent_1", TrustLevel.LOW)
        policy.spent_total = Decimal("4990.00")  # Close to 5000 limit
        
        allowed, reason = policy.validate_payment(
            amount=Decimal("20.00"),
            fee=Decimal("0.00")
        )
        
        assert allowed is False
        assert "total limit" in reason.lower()
    
    def test_validate_payment_exceeds_daily_limit(self):
        """Test payment exceeding daily limit."""
        policy = create_default_policy("agent_1", TrustLevel.LOW)
        policy.daily_limit.current_spent = Decimal("95.00")
        
        allowed, reason = policy.validate_payment(
            amount=Decimal("10.00"),  # Would exceed 100.00 daily
            fee=Decimal("0.00")
        )
        
        assert allowed is False
        assert "daily" in reason.lower()
    
    def test_record_spend(self):
        """Test recording a spend updates all counters."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        
        policy.record_spend(Decimal("50.00"))
        
        assert policy.spent_total == Decimal("50.00")
        assert policy.daily_limit.current_spent == Decimal("50.00")
        assert policy.weekly_limit.current_spent == Decimal("50.00")
        assert policy.monthly_limit.current_spent == Decimal("50.00")


class TestMerchantRules:
    """Test suite for merchant allowlist/denylist."""
    
    def test_add_merchant_to_allowlist(self):
        """Test adding a merchant to allowlist."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        
        rule = policy.add_merchant_allow(
            merchant_id="merchant_123",
            max_per_tx=Decimal("200.00"),
            reason="Trusted vendor"
        )
        
        assert rule.rule_type == "allow"
        assert rule.merchant_id == "merchant_123"
        assert len(policy.merchant_rules) == 1
    
    def test_add_merchant_to_denylist(self):
        """Test adding a merchant to denylist."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        
        rule = policy.add_merchant_deny(
            merchant_id="bad_merchant",
            reason="Suspected fraud"
        )
        
        assert rule.rule_type == "deny"
        assert len(policy.merchant_rules) == 1
    
    def test_denylist_blocks_payment(self):
        """Test that denied merchants are blocked."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        policy.add_merchant_deny(merchant_id="bad_merchant", reason="Blocked")
        
        allowed, reason = policy.validate_payment(
            amount=Decimal("10.00"),
            fee=Decimal("0.00"),
            merchant_id="bad_merchant"
        )
        
        assert allowed is False
        assert "blocked" in reason.lower()
    
    def test_allowlist_only_mode(self):
        """Test that only allowlisted merchants work when rules exist."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        policy.add_merchant_allow(merchant_id="good_merchant")
        
        # Allowed merchant works
        allowed, _ = policy.validate_payment(
            amount=Decimal("10.00"),
            fee=Decimal("0.00"),
            merchant_id="good_merchant"
        )
        assert allowed is True
        
        # Unknown merchant blocked
        allowed, reason = policy.validate_payment(
            amount=Decimal("10.00"),
            fee=Decimal("0.00"),
            merchant_id="unknown_merchant"
        )
        assert allowed is False
        assert "allowlist" in reason.lower()
    
    def test_category_based_rule(self):
        """Test category-based merchant rules."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        policy.add_merchant_deny(category="gambling", reason="Policy restriction")
        
        allowed, reason = policy.validate_payment(
            amount=Decimal("10.00"),
            fee=Decimal("0.00"),
            merchant_id="casino_xyz",
            merchant_category="gambling"
        )
        
        assert allowed is False
    
    def test_remove_rule(self):
        """Test removing a merchant rule."""
        policy = create_default_policy("agent_1", TrustLevel.MEDIUM)
        rule = policy.add_merchant_deny(merchant_id="merchant_123")
        
        assert len(policy.merchant_rules) == 1
        
        removed = policy.remove_rule(rule.rule_id)
        
        assert removed is True
        assert len(policy.merchant_rules) == 0


class TestTimeWindowLimit:
    """Test suite for time-based limits."""
    
    def test_daily_limit_reset(self):
        """Test daily limit resets after 24 hours."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("100.00"),
            current_spent=Decimal("50.00"),
            window_start=datetime.now(timezone.utc) - timedelta(hours=25)  # Expired
        )
        
        # Should reset
        reset_occurred = limit.reset_if_expired()
        
        assert reset_occurred is True
        assert limit.current_spent == Decimal("0.00")
    
    def test_daily_limit_no_reset_if_fresh(self):
        """Test daily limit doesn't reset if still within window."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("100.00"),
            current_spent=Decimal("50.00"),
            window_start=datetime.now(timezone.utc) - timedelta(hours=12)
        )
        
        reset_occurred = limit.reset_if_expired()
        
        assert reset_occurred is False
        assert limit.current_spent == Decimal("50.00")
    
    def test_remaining_calculation(self):
        """Test remaining amount calculation."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("100.00"),
            current_spent=Decimal("30.00")
        )
        
        remaining = limit.remaining()
        
        assert remaining == Decimal("70.00")
    
    def test_can_spend_within_limit(self):
        """Test can_spend returns true within limit."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("100.00"),
            current_spent=Decimal("30.00")
        )
        
        can_spend, reason = limit.can_spend(Decimal("50.00"))
        
        assert can_spend is True
    
    def test_can_spend_exceeds_limit(self):
        """Test can_spend returns false when exceeding limit."""
        limit = TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("100.00"),
            current_spent=Decimal("80.00")
        )
        
        can_spend, reason = limit.can_spend(Decimal("30.00"))
        
        assert can_spend is False
        assert "exceeded" in reason.lower()


class TestAuthorizationService:
    """Test suite for AuthorizationService."""
    
    @pytest.fixture
    def auth_service(self):
        """Create a fresh authorization service."""
        return AuthorizationService()
    
    def test_create_policy(self, auth_service):
        """Test creating a spending policy."""
        policy = auth_service.create_policy(
            agent_id="agent_1",
            trust_level=TrustLevel.MEDIUM
        )
        
        assert policy is not None
        assert policy.agent_id == "agent_1"
        assert policy.trust_level == TrustLevel.MEDIUM
    
    def test_create_policy_with_custom_limits(self, auth_service):
        """Test creating policy with custom limits."""
        policy = auth_service.create_policy(
            agent_id="agent_1",
            trust_level=TrustLevel.LOW,
            limit_per_tx=Decimal("200.00"),
            daily_limit=Decimal("500.00")
        )
        
        assert policy.limit_per_tx == Decimal("200.00")
        assert policy.daily_limit.limit_amount == Decimal("500.00")
    
    def test_get_or_create_policy(self, auth_service):
        """Test get_or_create returns existing or creates new."""
        # First call creates
        policy1 = auth_service.get_or_create_policy("agent_1", TrustLevel.MEDIUM)
        
        # Second call returns same
        policy2 = auth_service.get_or_create_policy("agent_1", TrustLevel.HIGH)
        
        assert policy1.policy_id == policy2.policy_id
        assert policy1.trust_level == TrustLevel.MEDIUM  # Original trust level
    
    def test_authorize_payment_success(self, auth_service):
        """Test authorizing a valid payment."""
        auth_service.create_policy("agent_1", TrustLevel.MEDIUM)
        
        result = auth_service.authorize_payment(
            agent_id="agent_1",
            amount=Decimal("100.00"),
            fee=Decimal("1.00")
        )
        
        assert result.authorized is True
        assert result.reason == "OK"
    
    def test_authorize_payment_denied(self, auth_service):
        """Test denying a payment that exceeds limits."""
        auth_service.create_policy("agent_1", TrustLevel.LOW)
        
        result = auth_service.authorize_payment(
            agent_id="agent_1",
            amount=Decimal("100.00"),  # Exceeds LOW tier limit
            fee=Decimal("1.00")
        )
        
        assert result.authorized is False
        assert "limit" in result.reason.lower()
    
    def test_authorize_payment_requires_review(self, auth_service):
        """Test payment requiring review when preauth is mandatory."""
        policy = auth_service.create_policy("agent_1", TrustLevel.MEDIUM)
        auth_service.update_policy("agent_1", require_preauth=True)
        
        result = auth_service.authorize_payment(
            agent_id="agent_1",
            amount=Decimal("10.00")
        )
        
        assert result.authorized is False
        assert result.requires_review is True
    
    def test_record_spend(self, auth_service):
        """Test recording a spend updates policy."""
        auth_service.create_policy("agent_1", TrustLevel.MEDIUM)
        
        auth_service.record_spend("agent_1", Decimal("50.00"))
        
        policy = auth_service.get_policy("agent_1")
        assert policy.spent_total == Decimal("50.00")
    
    def test_add_to_allowlist(self, auth_service):
        """Test adding merchant to allowlist."""
        auth_service.create_policy("agent_1", TrustLevel.MEDIUM)
        
        rule = auth_service.add_to_allowlist(
            agent_id="agent_1",
            merchant_id="trusted_merchant"
        )
        
        assert rule is not None
        assert rule.rule_type == "allow"
    
    def test_add_to_denylist(self, auth_service):
        """Test adding merchant to denylist."""
        auth_service.create_policy("agent_1", TrustLevel.MEDIUM)
        
        rule = auth_service.add_to_denylist(
            agent_id="agent_1",
            merchant_id="bad_merchant",
            reason="Suspected fraud"
        )
        
        assert rule is not None
        assert rule.rule_type == "deny"
    
    def test_upgrade_trust_level(self, auth_service):
        """Test upgrading an agent's trust level."""
        auth_service.create_policy("agent_1", TrustLevel.LOW)
        
        policy = auth_service.upgrade_trust_level("agent_1", TrustLevel.MEDIUM)
        
        assert policy.trust_level == TrustLevel.MEDIUM
        assert policy.limit_per_tx >= Decimal("500.00")  # MEDIUM limits
    
    def test_downgrade_trust_level(self, auth_service):
        """Test downgrading an agent's trust level."""
        auth_service.create_policy("agent_1", TrustLevel.HIGH)
        
        policy = auth_service.downgrade_trust_level("agent_1", TrustLevel.LOW)
        
        assert policy.trust_level == TrustLevel.LOW
        assert policy.limit_per_tx == Decimal("50.00")  # LOW limits
    
    def test_get_spending_summary(self, auth_service):
        """Test getting spending summary."""
        auth_service.create_policy("agent_1", TrustLevel.MEDIUM)
        auth_service.record_spend("agent_1", Decimal("100.00"))
        
        summary = auth_service.get_spending_summary("agent_1")
        
        assert summary is not None
        assert summary["trust_level"] == "medium"
        assert summary["spent"]["total"] == "100.00"


class TestSpendingScopes:
    """Test suite for spending scope restrictions."""
    
    def test_scope_all_allows_everything(self):
        """Test ALL scope allows any spending."""
        policy = SpendingPolicy(
            agent_id="agent_1",
            limit_per_tx=Decimal("1000.00"),
            limit_total=Decimal("10000.00"),
            allowed_scopes=[SpendingScope.ALL]
        )
        
        allowed, _ = policy.validate_payment(
            amount=Decimal("50.00"),
            fee=Decimal("0.00"),
            scope=SpendingScope.COMPUTE
        )
        
        assert allowed is True
    
    def test_restricted_scope_blocks_other(self):
        """Test restricted scopes block unauthorized spending."""
        policy = SpendingPolicy(
            agent_id="agent_1",
            limit_per_tx=Decimal("1000.00"),
            limit_total=Decimal("10000.00"),
            allowed_scopes=[SpendingScope.COMPUTE, SpendingScope.DATA]
        )
        
        # Allowed scope works
        allowed, _ = policy.validate_payment(
            amount=Decimal("50.00"),
            fee=Decimal("0.00"),
            scope=SpendingScope.COMPUTE
        )
        assert allowed is True
        
        # Unauthorized scope blocked
        allowed, reason = policy.validate_payment(
            amount=Decimal("50.00"),
            fee=Decimal("0.00"),
            scope=SpendingScope.RETAIL
        )
        assert allowed is False
        assert "scope" in reason.lower()

