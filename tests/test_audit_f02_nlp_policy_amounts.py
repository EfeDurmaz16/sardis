"""Test F02: NLPolicyProvider uses normalize_token_amount instead of hardcoded /100."""
import time
from decimal import Decimal
from sardis_compliance.checks import NLPolicyProvider, ComplianceResult
from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate, VCProof


def _proof():
    return VCProof(
        verification_method="did:key:test",
        created=str(int(time.time())),
        proof_value="dGVzdA==",
    )


def _mandate(subject, amount_minor, token, chain="base", destination="0xdest"):
    return PaymentMandate(
        mandate_id=f"mandate_{subject}_{token}",
        mandate_type="payment",
        issuer=subject,
        subject=subject,
        expires_at=int(time.time()) + 3600,
        nonce="test-nonce",
        proof=_proof(),
        domain="example.com",
        purpose="checkout",
        destination=destination,
        amount_minor=amount_minor,
        token=token,
        chain=chain,
        audit_hash="test-hash",
    )


class MockSpendingPolicy:
    """Mock spending policy for testing."""

    def __init__(self, policy_id: str = "test_policy"):
        self.policy_id = policy_id
        self.last_amount = None
        self.last_merchant = None

    def validate_payment(self, amount: Decimal, fee: Decimal, merchant_id: str) -> tuple[bool, str]:
        self.last_amount = amount
        self.last_merchant = merchant_id
        return True, ""


def test_nlp_policy_normalizes_usdc_correctly():
    """USDC has 6 decimals, so 1000000 minor units = 1.0 USDC."""
    settings = SardisSettings()
    provider = NLPolicyProvider(settings)

    policy = MockSpendingPolicy()
    agent_id = "agent_123"
    provider.set_policy_for_agent(agent_id, policy)

    mandate = _mandate(agent_id, 1_000_000, "USDC")
    result = provider.evaluate(mandate)

    assert result.allowed is True
    assert policy.last_amount == Decimal("1.0")


def test_nlp_policy_normalizes_usdt_correctly():
    """USDT has 6 decimals, same as USDC."""
    settings = SardisSettings()
    provider = NLPolicyProvider(settings)

    policy = MockSpendingPolicy()
    agent_id = "agent_456"
    provider.set_policy_for_agent(agent_id, policy)

    mandate = _mandate(agent_id, 2_500_000, "USDT", chain="ethereum")
    result = provider.evaluate(mandate)

    assert result.allowed is True
    assert policy.last_amount == Decimal("2.5")


def test_nlp_policy_normalizes_pyusd_correctly():
    """PYUSD has 6 decimals."""
    settings = SardisSettings()
    provider = NLPolicyProvider(settings)

    policy = MockSpendingPolicy()
    agent_id = "agent_789"
    provider.set_policy_for_agent(agent_id, policy)

    mandate = _mandate(agent_id, 100_000, "PYUSD", chain="ethereum")
    result = provider.evaluate(mandate)

    assert result.allowed is True
    assert policy.last_amount == Decimal("0.1")


def test_nlp_policy_normalizes_eurc_correctly():
    """EURC has 6 decimals."""
    settings = SardisSettings()
    provider = NLPolicyProvider(settings)

    policy = MockSpendingPolicy()
    agent_id = "agent_eurc"
    provider.set_policy_for_agent(agent_id, policy)

    mandate = _mandate(agent_id, 5_000_000, "EURC", chain="polygon")
    result = provider.evaluate(mandate)

    assert result.allowed is True
    assert policy.last_amount == Decimal("5.0")


def test_nlp_policy_handles_invalid_token():
    """Invalid token should fail gracefully."""
    settings = SardisSettings()
    provider = NLPolicyProvider(settings)

    policy = MockSpendingPolicy()
    agent_id = "agent_bad"
    provider.set_policy_for_agent(agent_id, policy)

    mandate = _mandate(agent_id, 1_000_000, "INVALID_TOKEN")
    result = provider.evaluate(mandate)

    # Should fail-closed on invalid token (SimpleRuleProvider rejects unknown tokens)
    assert result.allowed is False
    assert result.reason is not None
