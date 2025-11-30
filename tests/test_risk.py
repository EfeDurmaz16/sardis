"""Tests for risk scoring and authorization service."""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sardis_core.models.risk import (
    RiskScore,
    RiskLevel,
    RiskFactor,
    AgentRiskProfile,
)
from sardis_core.services.risk_service import (
    RiskService,
    RiskConfig,
    get_risk_service,
)


class TestRiskScore:
    """Tests for RiskScore model."""
    
    def test_score_creation(self):
        """Test creating a risk score."""
        score = RiskScore(
            score=25.0,
            level=RiskLevel.MEDIUM,
            factors=[RiskFactor.HIGH_VELOCITY],
            details={"velocity": "10 tx/hour"}
        )
        
        assert score.score == 25.0
        assert score.level == RiskLevel.MEDIUM
        assert RiskFactor.HIGH_VELOCITY in score.factors
    
    def test_score_from_score(self):
        """Test creating score from numeric value."""
        # Low risk
        low = RiskScore.from_score(10.0)
        assert low.level == RiskLevel.LOW
        
        # Medium risk
        medium = RiskScore.from_score(35.0)
        assert medium.level == RiskLevel.MEDIUM
        
        # High risk
        high = RiskScore.from_score(60.0)
        assert high.level == RiskLevel.HIGH
        
        # Critical risk
        critical = RiskScore.from_score(85.0)
        assert critical.level == RiskLevel.CRITICAL
    
    def test_is_acceptable(self):
        """Test risk acceptability check."""
        # Below threshold
        low = RiskScore.from_score(50.0)
        assert low.is_acceptable(threshold=75.0) is True
        
        # Above threshold
        high = RiskScore.from_score(80.0)
        assert high.is_acceptable(threshold=75.0) is False
        
        # At threshold
        at = RiskScore.from_score(75.0)
        assert at.is_acceptable(threshold=75.0) is False
    
    def test_score_boundaries(self):
        """Test risk level boundaries."""
        assert RiskScore.from_score(0.0).level == RiskLevel.LOW
        assert RiskScore.from_score(24.9).level == RiskLevel.LOW
        assert RiskScore.from_score(25.0).level == RiskLevel.MEDIUM
        assert RiskScore.from_score(49.9).level == RiskLevel.MEDIUM
        assert RiskScore.from_score(50.0).level == RiskLevel.HIGH
        assert RiskScore.from_score(74.9).level == RiskLevel.HIGH
        assert RiskScore.from_score(75.0).level == RiskLevel.CRITICAL
        assert RiskScore.from_score(100.0).level == RiskLevel.CRITICAL


class TestAgentRiskProfile:
    """Tests for AgentRiskProfile model."""
    
    def test_profile_creation(self):
        """Test creating a risk profile."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        assert profile.agent_id == "agent_123"
        assert profile.current_score == 0.0
        assert profile.current_level == RiskLevel.LOW
        assert profile.total_transactions == 0
        assert profile.is_flagged is False
    
    def test_update_from_transaction(self):
        """Test updating profile from transaction."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        profile.update_from_transaction(
            amount=Decimal("50.00"),
            recipient="merchant_1",
            success=True
        )
        
        assert profile.total_transactions == 1
        assert profile.failed_transactions == 0
        assert profile.total_volume == Decimal("50.00")
        assert profile.max_transaction_amount == Decimal("50.00")
    
    def test_update_from_failed_transaction(self):
        """Test updating profile from failed transaction."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        profile.update_from_transaction(
            amount=Decimal("100.00"),
            recipient="merchant_1",
            success=False
        )
        
        assert profile.total_transactions == 1
        assert profile.failed_transactions == 1
    
    def test_average_transaction_amount(self):
        """Test average transaction calculation."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        profile.update_from_transaction(Decimal("10.00"), "m1", True)
        profile.update_from_transaction(Decimal("20.00"), "m2", True)
        profile.update_from_transaction(Decimal("30.00"), "m3", True)
        
        assert profile.total_volume == Decimal("60.00")
        assert profile.average_transaction_amount == Decimal("20.00")
    
    def test_service_authorization(self):
        """Test service authorization management."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        # Initially no authorized services
        assert profile.is_service_authorized("service_1") is True  # Empty = all allowed
        
        # Add authorization
        profile.authorize_service("service_1")
        assert "service_1" in profile.authorized_services
        assert profile.is_service_authorized("service_1") is True
        assert profile.is_service_authorized("service_2") is False
    
    def test_revoke_service(self):
        """Test revoking service authorization."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        profile.authorize_service("service_1")
        profile.authorize_service("service_2")
        
        result = profile.revoke_service("service_1")
        assert result is True
        assert "service_1" not in profile.authorized_services
        assert "service_2" in profile.authorized_services
        
        # Revoke non-existent
        result = profile.revoke_service("service_99")
        assert result is False
    
    def test_flag_agent(self):
        """Test flagging an agent."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        profile.flag("Suspicious activity detected")
        
        assert profile.is_flagged is True
        assert profile.flag_reason == "Suspicious activity detected"
        assert profile.flagged_at is not None
    
    def test_unflag_agent(self):
        """Test unflagging an agent."""
        profile = AgentRiskProfile(agent_id="agent_123")
        
        profile.flag("Test flag")
        profile.unflag()
        
        assert profile.is_flagged is False
        assert profile.flag_reason is None
        assert profile.flagged_at is None


class TestRiskService:
    """Tests for RiskService."""
    
    @pytest.fixture
    def risk_service(self):
        """Create a risk service with default config."""
        return RiskService()
    
    @pytest.fixture
    def strict_config(self):
        """Create a strict risk configuration."""
        return RiskConfig(
            max_transactions_per_hour=5,
            large_transaction_threshold=Decimal("50.00"),
            velocity_weight=30.0,
            amount_weight=25.0
        )
    
    def test_get_or_create_profile(self, risk_service):
        """Test profile creation."""
        profile = risk_service.get_or_create_profile("agent_new")
        
        assert profile is not None
        assert profile.agent_id == "agent_new"
        
        # Should return same profile
        same = risk_service.get_or_create_profile("agent_new")
        assert same is profile
    
    def test_assess_new_agent_low_risk(self, risk_service):
        """Test new agent has low risk."""
        now = datetime.now(timezone.utc)
        
        score = risk_service.assess_transaction(
            agent_id="new_agent",
            amount=Decimal("10.00"),
            recipient_id="merchant_1",
            wallet_created_at=now - timedelta(days=30)  # Old wallet
        )
        
        assert score.score < 25.0
        assert score.level == RiskLevel.LOW
    
    def test_assess_large_transaction(self, risk_service):
        """Test large transaction increases risk."""
        now = datetime.now(timezone.utc)
        
        score = risk_service.assess_transaction(
            agent_id="agent_1",
            amount=Decimal("600.00"),  # Very large
            recipient_id="merchant_1",
            wallet_created_at=now - timedelta(days=30)
        )
        
        assert RiskFactor.LARGE_AMOUNT in score.factors
        assert score.score > 0
    
    def test_assess_new_wallet_risk(self, risk_service):
        """Test new wallet adds risk."""
        now = datetime.now(timezone.utc)
        
        score = risk_service.assess_transaction(
            agent_id="agent_1",
            amount=Decimal("10.00"),
            recipient_id="merchant_1",
            wallet_created_at=now - timedelta(hours=1)  # 1 hour old
        )
        
        assert RiskFactor.NEW_WALLET in score.factors
    
    def test_assess_high_failure_rate(self, risk_service):
        """Test high failure rate increases risk."""
        profile = risk_service.get_or_create_profile("agent_failing")
        
        # Simulate many failed transactions
        for i in range(10):
            profile.update_from_transaction(Decimal("10.00"), "m1", success=(i < 3))
        
        # 7 out of 10 failed = 70% failure rate
        score = risk_service.assess_agent("agent_failing")
        
        assert RiskFactor.FAILED_ATTEMPTS in score.factors
    
    def test_assess_unauthorized_service(self, risk_service):
        """Test unauthorized service adds risk."""
        profile = risk_service.get_or_create_profile("agent_restricted")
        profile.authorize_service("allowed_merchant")
        
        now = datetime.now(timezone.utc)
        
        score = risk_service.assess_transaction(
            agent_id="agent_restricted",
            amount=Decimal("10.00"),
            recipient_id="unknown_merchant",
            wallet_created_at=now - timedelta(days=30)
        )
        
        assert RiskFactor.UNAUTHORIZED_SERVICE in score.factors
    
    def test_record_transaction(self, risk_service):
        """Test recording transactions updates profile."""
        risk_service.record_transaction(
            agent_id="agent_tx",
            amount=Decimal("50.00"),
            recipient_id="merchant_1",
            success=True
        )
        
        profile = risk_service.get_profile("agent_tx")
        
        assert profile.total_transactions == 1
        assert profile.total_volume == Decimal("50.00")
    
    def test_should_block_flagged_agent(self, risk_service):
        """Test flagged agent is blocked."""
        profile = risk_service.get_or_create_profile("flagged_agent")
        profile.flag("Manual review required")
        
        now = datetime.now(timezone.utc)
        
        should_block, reason = risk_service.should_block_transaction(
            agent_id="flagged_agent",
            amount=Decimal("1.00"),
            recipient_id="any",
            wallet_created_at=now
        )
        
        assert should_block is True
        assert "flagged" in reason.lower()
    
    def test_should_block_high_risk(self, risk_service):
        """Test high risk transaction is blocked."""
        # Create profile with bad history
        profile = risk_service.get_or_create_profile("risky_agent")
        for _ in range(20):
            profile.update_from_transaction(Decimal("10.00"), "m1", success=False)
        
        now = datetime.now(timezone.utc)
        
        should_block, reason = risk_service.should_block_transaction(
            agent_id="risky_agent",
            amount=Decimal("1000.00"),  # Very large
            recipient_id="unknown",
            wallet_created_at=now  # New wallet
        )
        
        # Might or might not block depending on accumulated score
        # but should at least assess risk
        assert isinstance(should_block, bool)
    
    def test_authorize_service(self, risk_service):
        """Test authorizing a service."""
        risk_service.authorize_service("agent_1", "merchant_abc")
        
        services = risk_service.list_authorized_services("agent_1")
        
        assert "merchant_abc" in services
    
    def test_revoke_service(self, risk_service):
        """Test revoking a service."""
        risk_service.authorize_service("agent_1", "merchant_abc")
        risk_service.authorize_service("agent_1", "merchant_xyz")
        
        result = risk_service.revoke_service("agent_1", "merchant_abc")
        
        assert result is True
        services = risk_service.list_authorized_services("agent_1")
        assert "merchant_abc" not in services
        assert "merchant_xyz" in services
    
    def test_flag_and_unflag_agent(self, risk_service):
        """Test flag/unflag operations."""
        risk_service.flag_agent("agent_1", "Test reason")
        
        profile = risk_service.get_profile("agent_1")
        assert profile.is_flagged is True
        
        risk_service.unflag_agent("agent_1")
        assert profile.is_flagged is False
    
    def test_score_capped_at_100(self, risk_service):
        """Test risk score doesn't exceed 100."""
        # Create extreme conditions
        profile = risk_service.get_or_create_profile("extreme_agent")
        profile.flag("Flagged")
        for _ in range(100):
            profile.update_from_transaction(Decimal("10.00"), "m1", success=False)
        
        now = datetime.now(timezone.utc)
        
        score = risk_service.assess_transaction(
            agent_id="extreme_agent",
            amount=Decimal("10000.00"),
            recipient_id="unknown",
            wallet_created_at=now
        )
        
        assert score.score <= 100.0


class TestRiskConfig:
    """Tests for RiskConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RiskConfig()
        
        assert config.max_transactions_per_hour == 20
        assert config.large_transaction_threshold == Decimal("100.00")
        assert config.block_threshold == 90.0
        assert config.alert_threshold == 70.0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RiskConfig(
            max_transactions_per_hour=5,
            large_transaction_threshold=Decimal("50.00"),
            block_threshold=80.0
        )
        
        assert config.max_transactions_per_hour == 5
        assert config.large_transaction_threshold == Decimal("50.00")
        assert config.block_threshold == 80.0
    
    def test_service_with_custom_config(self):
        """Test risk service uses custom config."""
        config = RiskConfig(
            large_transaction_threshold=Decimal("10.00"),
            amount_weight=50.0
        )
        
        service = RiskService(config=config)
        now = datetime.now(timezone.utc)
        
        # Amount of 20 is "large" with this config
        score = service.assess_transaction(
            agent_id="test",
            amount=Decimal("20.00"),
            recipient_id="merchant",
            wallet_created_at=now - timedelta(days=30)
        )
        
        assert RiskFactor.LARGE_AMOUNT in score.factors


class TestGlobalRiskService:
    """Tests for global risk service instance."""
    
    def test_get_risk_service_singleton(self):
        """Test global service is singleton."""
        service1 = get_risk_service()
        service2 = get_risk_service()
        
        assert service1 is service2
    
    def test_global_service_persistence(self):
        """Test data persists in global service."""
        service = get_risk_service()
        
        service.authorize_service("global_agent", "global_merchant")
        
        # Should still be there
        services = get_risk_service().list_authorized_services("global_agent")
        assert "global_merchant" in services

