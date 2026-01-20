"""Unit tests for compliance engine and checks."""
from __future__ import annotations

import time
import pytest
from unittest.mock import patch, MagicMock

from sardis_compliance.checks import (
    ComplianceResult,
    ComplianceProvider,
    SimpleRuleProvider,
    ComplianceEngine,
)
from sardis_v2_core.mandates import PaymentMandate, VCProof


def create_test_mandate(
    token: str = "USDC",
    amount: int = 10000,  # $100.00
    chain: str = "base_sepolia",
) -> PaymentMandate:
    """Create a test PaymentMandate."""
    proof = VCProof(
        verification_method="did:key:test#key-1",
        created="2025-12-08T00:00:00Z",
        proof_value="test_signature",
    )
    
    return PaymentMandate(
        mandate_id=f"test_mandate_{int(time.time())}",
        mandate_type="payment",
        issuer="test_agent",
        subject="test_wallet",
        expires_at=int(time.time()) + 300,
        nonce="test_nonce",
        proof=proof,
        domain="sardis.network",
        purpose="checkout",
        chain=chain,
        token=token,
        amount_minor=amount,
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test_audit_hash",
    )


class TestComplianceResult:
    """Tests for ComplianceResult dataclass."""

    def test_allowed_result(self):
        """Test creating an allowed compliance result."""
        result = ComplianceResult(
            allowed=True,
            provider="rules",
            rule_id="baseline",
        )
        
        assert result.allowed is True
        assert result.reason is None
        assert result.provider == "rules"
        assert result.rule_id == "baseline"
        assert result.reviewed_at is not None

    def test_denied_result(self):
        """Test creating a denied compliance result."""
        result = ComplianceResult(
            allowed=False,
            reason="token_not_permitted",
            provider="rules",
            rule_id="token_allowlist",
        )
        
        assert result.allowed is False
        assert result.reason == "token_not_permitted"
        assert result.provider == "rules"

    def test_result_has_timestamp(self):
        """Test compliance result has reviewed_at timestamp."""
        result = ComplianceResult(allowed=True)
        
        assert result.reviewed_at is not None


class TestSimpleRuleProvider:
    """Tests for SimpleRuleProvider."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        from sardis_v2_core import SardisSettings
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            return SardisSettings(environment="dev")

    @pytest.fixture
    def provider(self, settings):
        """Create a SimpleRuleProvider."""
        return SimpleRuleProvider(settings)

    def test_allowed_token_usdc(self, provider):
        """Test USDC is allowed."""
        mandate = create_test_mandate(token="USDC", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True
        assert result.provider == "rules"
        assert result.rule_id == "baseline"

    def test_allowed_token_usdt(self, provider):
        """Test USDT is allowed."""
        mandate = create_test_mandate(token="USDT", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True

    def test_allowed_token_pyusd(self, provider):
        """Test PYUSD is allowed."""
        mandate = create_test_mandate(token="PYUSD", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True

    def test_allowed_token_eurc(self, provider):
        """Test EURC is allowed."""
        mandate = create_test_mandate(token="EURC", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True

    def test_disallowed_token(self, provider):
        """Test non-permitted token is rejected."""
        mandate = create_test_mandate(token="DAI", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is False
        assert result.reason == "token_not_permitted"
        assert result.rule_id == "token_allowlist"

    def test_disallowed_token_unknown(self, provider):
        """Test unknown token is rejected."""
        mandate = create_test_mandate(token="UNKNOWN_TOKEN", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is False
        assert result.reason == "token_not_permitted"

    def test_amount_within_limit(self, provider):
        """Test amount within limit is allowed."""
        mandate = create_test_mandate(token="USDC", amount=100000000)  # $1,000,000
        result = provider.evaluate(mandate)
        
        assert result.allowed is True

    def test_amount_over_limit(self, provider):
        """Test amount over $10M limit is rejected."""
        mandate = create_test_mandate(token="USDC", amount=1_000_000_01)  # > $10M
        result = provider.evaluate(mandate)
        
        assert result.allowed is False
        assert result.reason == "amount_over_limit"
        assert result.rule_id == "max_amount"

    def test_exact_limit_amount(self, provider):
        """Test exact limit amount is allowed."""
        # 1_000_000_00 = $10,000,000 (in cents)
        mandate = create_test_mandate(token="USDC", amount=1_000_000_00)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True


class TestComplianceEngine:
    """Tests for ComplianceEngine."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        from sardis_v2_core import SardisSettings
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            return SardisSettings(environment="dev")

    @pytest.fixture
    def engine(self, settings):
        """Create a ComplianceEngine with default provider."""
        return ComplianceEngine(settings)

    def test_engine_uses_default_provider(self, engine):
        """Test engine uses SimpleRuleProvider by default."""
        assert engine._provider is not None
        assert isinstance(engine._provider, SimpleRuleProvider)

    def test_preflight_allowed(self, engine):
        """Test preflight check for allowed payment."""
        mandate = create_test_mandate(token="USDC", amount=10000)
        result = engine.preflight(mandate)
        
        assert result.allowed is True

    def test_preflight_denied_token(self, engine):
        """Test preflight check rejects bad token."""
        mandate = create_test_mandate(token="BAD_TOKEN", amount=10000)
        result = engine.preflight(mandate)
        
        assert result.allowed is False
        assert result.reason == "token_not_permitted"

    def test_preflight_denied_amount(self, engine):
        """Test preflight check rejects excessive amount."""
        mandate = create_test_mandate(token="USDC", amount=1_000_000_01)
        result = engine.preflight(mandate)
        
        assert result.allowed is False
        assert result.reason == "amount_over_limit"


class TestCustomComplianceProvider:
    """Tests for custom compliance providers."""

    def test_custom_provider_interface(self):
        """Test custom provider implements the protocol."""
        
        class CustomProvider:
            def evaluate(self, mandate: PaymentMandate) -> ComplianceResult:
                # Custom logic: block transactions to specific address
                if mandate.destination == "0xBLOCKED":
                    return ComplianceResult(
                        allowed=False,
                        reason="blocked_address",
                        provider="custom",
                        rule_id="blocked_addresses",
                    )
                return ComplianceResult(allowed=True, provider="custom")
        
        provider = CustomProvider()
        
        # Test blocked address
        blocked_mandate = PaymentMandate(
            mandate_id="test",
            mandate_type="payment",
            issuer="agent",
            subject="wallet",
            expires_at=int(time.time()) + 300,
            nonce="nonce",
            proof=VCProof(
                verification_method="did:key:test",
                created="2025-12-08T00:00:00Z",
                proof_value="sig",
            ),
            domain="sardis.network",
            purpose="checkout",
            chain="base",
            token="USDC",
            amount_minor=1000,
            destination="0xBLOCKED",
            audit_hash="hash",
        )
        
        result = provider.evaluate(blocked_mandate)
        assert result.allowed is False
        assert result.reason == "blocked_address"
        
        # Test allowed address
        allowed_mandate = create_test_mandate()
        result = provider.evaluate(allowed_mandate)
        assert result.allowed is True

    def test_engine_with_custom_provider(self):
        """Test ComplianceEngine with custom provider."""
        from sardis_v2_core import SardisSettings
        
        class AlwaysAllowProvider:
            def evaluate(self, mandate: PaymentMandate) -> ComplianceResult:
                return ComplianceResult(
                    allowed=True,
                    provider="always_allow",
                    rule_id="permissive",
                )
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            settings = SardisSettings(environment="dev")
        
        engine = ComplianceEngine(settings, provider=AlwaysAllowProvider())
        
        # Even "bad" token should be allowed
        mandate = create_test_mandate(token="ANY_TOKEN", amount=999999999)
        result = engine.preflight(mandate)
        
        assert result.allowed is True
        assert result.provider == "always_allow"


class TestComplianceEdgeCases:
    """Tests for edge cases in compliance checking."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        from sardis_v2_core import SardisSettings
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            return SardisSettings(environment="dev")

    @pytest.fixture
    def provider(self, settings):
        """Create a SimpleRuleProvider."""
        return SimpleRuleProvider(settings)

    def test_zero_amount(self, provider):
        """Test zero amount transaction."""
        mandate = create_test_mandate(token="USDC", amount=0)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True

    def test_one_cent_amount(self, provider):
        """Test one cent transaction."""
        mandate = create_test_mandate(token="USDC", amount=1)
        result = provider.evaluate(mandate)
        
        assert result.allowed is True

    def test_case_sensitive_token(self, provider):
        """Test token matching is case-sensitive."""
        # Lowercase should fail
        mandate = create_test_mandate(token="usdc", amount=1000)
        result = provider.evaluate(mandate)
        
        assert result.allowed is False
        assert result.reason == "token_not_permitted"

    def test_multiple_evaluations(self, provider):
        """Test multiple evaluations don't interfere."""
        mandate1 = create_test_mandate(token="USDC", amount=1000)
        mandate2 = create_test_mandate(token="BAD", amount=1000)
        mandate3 = create_test_mandate(token="USDT", amount=1000)
        
        result1 = provider.evaluate(mandate1)
        result2 = provider.evaluate(mandate2)
        result3 = provider.evaluate(mandate3)
        
        assert result1.allowed is True
        assert result2.allowed is False
        assert result3.allowed is True


class TestComplianceProviderProtocol:
    """Tests for ComplianceProvider protocol compliance."""

    def test_protocol_requires_evaluate_method(self):
        """Test that ComplianceProvider protocol requires evaluate method."""
        from typing import runtime_checkable, Protocol
        
        # SimpleRuleProvider should satisfy the protocol
        from sardis_v2_core import SardisSettings
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            settings = SardisSettings(environment="dev")
        
        provider = SimpleRuleProvider(settings)
        
        # Should have evaluate method
        assert hasattr(provider, "evaluate")
        assert callable(provider.evaluate)
        
        # Should return ComplianceResult
        mandate = create_test_mandate()
        result = provider.evaluate(mandate)
        assert isinstance(result, ComplianceResult)







