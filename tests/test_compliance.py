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

    @pytest.mark.asyncio
    async def test_preflight_allowed(self, engine):
        """Test preflight check for allowed payment."""
        mandate = create_test_mandate(token="USDC", amount=10000)
        result = await engine.preflight(mandate)
        
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_preflight_denied_token(self, engine):
        """Test preflight check rejects bad token."""
        mandate = create_test_mandate(token="BAD_TOKEN", amount=10000)
        result = await engine.preflight(mandate)
        
        assert result.allowed is False
        assert result.reason == "token_not_permitted"

    @pytest.mark.asyncio
    async def test_preflight_denied_amount(self, engine):
        """Test preflight check rejects excessive amount."""
        mandate = create_test_mandate(token="USDC", amount=1_000_000_01)
        result = await engine.preflight(mandate)
        
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

    @pytest.mark.asyncio
    async def test_engine_with_custom_provider(self):
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
        result = await engine.preflight(mandate)
        
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


class TestNLPolicyProvider:
    """Tests for NLPolicyProvider with natural language policies."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        from sardis_v2_core import SardisSettings

        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            return SardisSettings(environment="dev")

    @pytest.fixture
    def provider(self, settings):
        """Create an NLPolicyProvider."""
        from sardis_compliance.checks import NLPolicyProvider
        return NLPolicyProvider(settings)

    def test_nl_provider_has_fallback(self, provider):
        """Test NL provider uses SimpleRuleProvider as fallback."""
        assert provider._fallback is not None
        assert isinstance(provider._fallback, SimpleRuleProvider)

    def test_no_policy_uses_fallback(self, provider):
        """Test mandate without policy uses fallback rules."""
        mandate = create_test_mandate(token="USDC", amount=10000)
        result = provider.evaluate(mandate)

        assert result.allowed is True
        assert result.provider == "nl_policy"
        assert result.rule_id == "no_policy_default"

    def test_set_and_get_policy(self, provider):
        """Test setting and getting policies for agents."""
        from decimal import Decimal
        from sardis_v2_core.spending_policy import SpendingPolicy, TrustLevel

        policy = SpendingPolicy(
            agent_id="test_agent",
            trust_level=TrustLevel.MEDIUM,
            limit_per_tx=Decimal("100.00"),
            limit_total=Decimal("1000.00"),
        )

        provider.set_policy_for_agent("test_agent", policy)
        retrieved = provider.get_policy_for_agent("test_agent")

        assert retrieved is not None
        assert retrieved.agent_id == "test_agent"
        assert retrieved.limit_per_tx == Decimal("100.00")

    def test_policy_enforces_per_tx_limit(self, provider):
        """Test that NL policy enforces per-transaction limits."""
        from decimal import Decimal
        from sardis_v2_core.spending_policy import SpendingPolicy, TrustLevel

        # Create policy with $50 per-tx limit
        policy = SpendingPolicy(
            agent_id="test_wallet",
            trust_level=TrustLevel.LOW,
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("1000.00"),
        )
        provider.set_policy_for_agent("test_wallet", policy)

        # Test amount within limit ($40 in USDC 6-decimal minor units)
        mandate_ok = create_test_mandate(token="USDC", amount=40_000_000)
        result_ok = provider.evaluate(mandate_ok)
        assert result_ok.allowed is True

        # Test amount over limit ($75 in USDC 6-decimal minor units)
        mandate_over = create_test_mandate(token="USDC", amount=75_000_000)
        result_over = provider.evaluate(mandate_over)
        assert result_over.allowed is False
        assert result_over.reason == "per_transaction_limit"


class TestComplianceAuditStore:
    """Tests for ComplianceAuditStore audit trail."""

    @pytest.fixture
    def store(self):
        """Create a fresh audit store."""
        from sardis_compliance.checks import ComplianceAuditStore
        return ComplianceAuditStore()

    @pytest.fixture
    def entry(self):
        """Create a test audit entry."""
        from sardis_compliance.checks import ComplianceAuditEntry
        return ComplianceAuditEntry(
            mandate_id="test_mandate_123",
            subject="test_wallet",
            allowed=True,
            reason=None,
            rule_id="baseline",
            provider="rules",
        )

    def test_append_entry(self, store, entry):
        """Test appending an audit entry."""
        audit_id = store.append(entry)

        assert audit_id is not None
        assert audit_id == entry.audit_id
        assert store.count() == 1

    def test_append_multiple_entries(self, store):
        """Test appending multiple entries."""
        from sardis_compliance.checks import ComplianceAuditEntry

        for i in range(5):
            entry = ComplianceAuditEntry(
                mandate_id=f"mandate_{i}",
                subject="wallet",
                allowed=True,
            )
            store.append(entry)

        assert store.count() == 5

    def test_get_by_mandate(self, store, entry):
        """Test retrieving entries by mandate ID."""
        store.append(entry)

        entries = store.get_by_mandate("test_mandate_123")
        assert len(entries) == 1
        assert entries[0].mandate_id == "test_mandate_123"

    def test_get_recent(self, store):
        """Test getting recent entries."""
        from sardis_compliance.checks import ComplianceAuditEntry

        for i in range(10):
            entry = ComplianceAuditEntry(
                mandate_id=f"mandate_{i}",
                subject="wallet",
                allowed=True,
            )
            store.append(entry)

        recent = store.get_recent(5)
        assert len(recent) == 5
        # Should be most recent
        assert recent[-1].mandate_id == "mandate_9"

    def test_export_all(self, store, entry):
        """Test exporting all entries as dictionaries."""
        store.append(entry)

        exported = store.export_all()
        assert len(exported) == 1
        assert exported[0]["mandate_id"] == "test_mandate_123"
        assert exported[0]["allowed"] is True

    def test_audit_entry_to_dict(self, entry):
        """Test converting audit entry to dictionary."""
        data = entry.to_dict()

        assert "audit_id" in data
        assert "mandate_id" in data
        assert data["mandate_id"] == "test_mandate_123"
        assert data["allowed"] is True
        assert "evaluated_at" in data


class TestComplianceEngineAuditTrail:
    """Tests for ComplianceEngine audit trail integration."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        from sardis_v2_core import SardisSettings

        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            return SardisSettings(environment="dev")

    @pytest.fixture
    def engine(self, settings):
        """Create a ComplianceEngine."""
        from sardis_compliance.checks import ComplianceAuditStore
        store = ComplianceAuditStore()
        return ComplianceEngine(settings, audit_store=store)

    @pytest.mark.asyncio
    async def test_preflight_creates_audit_entry(self, engine):
        """Test that preflight creates an audit entry."""
        mandate = create_test_mandate()
        result = await engine.preflight(mandate)

        assert result.audit_id is not None

        # Check audit store
        audits = await engine.get_audit_history(mandate.mandate_id)
        assert len(audits) == 1
        assert audits[0].mandate_id == mandate.mandate_id

    @pytest.mark.asyncio
    async def test_preflight_records_denial(self, engine):
        """Test that denied mandates are recorded in audit."""
        mandate = create_test_mandate(token="BAD_TOKEN")
        result = await engine.preflight(mandate)

        assert result.allowed is False

        audits = await engine.get_audit_history(mandate.mandate_id)
        assert len(audits) == 1
        assert audits[0].allowed is False
        assert audits[0].reason == "token_not_permitted"

    @pytest.mark.asyncio
    async def test_recent_audits(self, engine):
        """Test getting recent audit entries."""
        # Create several mandates
        for i in range(5):
            mandate = create_test_mandate()
            await engine.preflight(mandate)

        recent = await engine.get_recent_audits(3)
        assert len(recent) == 3





