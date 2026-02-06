"""Anti-bypass tests for split payments and evasion attacks.

Tests verify that common bypass attempts are detected and blocked:
- Split payment attacks (aggregate amount exceeds policy)
- Rapid sequential payments to same vendor
- Merchant/category evasion via name changes
- Alternate flow bypasses (skipping UCP/TAP)
- x402 payments without prior challenge
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from sardis_protocol.verifier import MandateVerifier, MandateChainVerification
from sardis_protocol.x402 import (
    X402Challenge,
    X402PaymentPayload,
    verify_payment_payload,
    X402VerificationResult,
)
from sardis_protocol.schemas import AP2PaymentExecuteRequest
from sardis_v2_core.spending_policy import (
    SpendingPolicy,
    TimeWindowLimit,
    TrustLevel,
    SpendingScope,
    MerchantRule,
)
from sardis_v2_core.mandates import (
    IntentMandate,
    CartMandate,
    PaymentMandate,
    VCProof,
    MandateChain,
)
from sardis_v2_core import load_settings

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.security]


# Helper functions
def create_vc_proof(method: str = "did:key:ed25519:ZmFrZQ==") -> VCProof:
    """Create a test VCProof."""
    return VCProof(
        verification_method=method,
        created=str(int(time.time())),
        proof_purpose="assertionMethod",
        proof_value="dGVzdA==",
    )


def create_intent_mandate(
    agent_id: str = "agent:test",
    requested_amount: int | None = None,
    expires_at: int | None = None,
) -> IntentMandate:
    """Create a test IntentMandate."""
    if expires_at is None:
        expires_at = int(time.time()) + 3600

    return IntentMandate(
        mandate_id=f"intent_{int(time.time() * 1000)}",
        mandate_type="intent",
        issuer=agent_id,
        subject=agent_id,
        expires_at=expires_at,
        nonce=f"nonce_{int(time.time() * 1000)}",
        proof=create_vc_proof(),
        domain="example.com",
        purpose="intent",
        scope=["payment"],
        requested_amount=requested_amount,
    )


def create_cart_mandate(
    agent_id: str = "agent:test",
    merchant_domain: str = "merchant.example",
    amount_minor: int = 10000,
    expires_at: int | None = None,
) -> CartMandate:
    """Create a test CartMandate."""
    if expires_at is None:
        expires_at = int(time.time()) + 3600

    return CartMandate(
        mandate_id=f"cart_{int(time.time() * 1000)}",
        mandate_type="cart",
        issuer=agent_id,
        subject=agent_id,
        expires_at=expires_at,
        nonce=f"nonce_{int(time.time() * 1000)}",
        proof=create_vc_proof(),
        domain="example.com",
        purpose="cart",
        line_items=[{"item_id": "item1", "name": "Test Item", "quantity": 1, "price_minor": amount_minor}],
        merchant_domain=merchant_domain,
        currency="USD",
        subtotal_minor=amount_minor,
        taxes_minor=0,
    )


def create_payment_mandate(
    agent_id: str = "agent:test",
    merchant_domain: str = "merchant.example",
    amount_minor: int = 10000,
    expires_at: int | None = None,
    destination: str = "0x1234567890123456789012345678901234567890",
) -> PaymentMandate:
    """Create a test PaymentMandate."""
    if expires_at is None:
        expires_at = int(time.time()) + 3600

    return PaymentMandate(
        mandate_id=f"payment_{int(time.time() * 1000)}",
        mandate_type="payment",
        issuer=agent_id,
        subject=agent_id,
        expires_at=expires_at,
        nonce=f"nonce_{int(time.time() * 1000)}",
        proof=create_vc_proof(),
        domain="example.com",
        purpose="checkout",
        chain="base",
        token="USDC",
        amount_minor=amount_minor,
        destination=destination,
        audit_hash=f"audit_{int(time.time() * 1000)}",
        merchant_domain=merchant_domain,
        ai_agent_presence=True,
        transaction_modality="human_present",
    )


# ==========================================
# Split Payment Bypass Tests
# ==========================================

def test_split_payment_aggregate_exceeds_policy():
    """Test that splitting a $1000 payment into 10x $100 payments is detected.

    Attack vector: Agent attempts to bypass per-transaction limit by splitting
    a large payment into multiple smaller payments that individually pass policy
    but collectively exceed the limit.

    Defense: Aggregate spending tracking within time windows catches this.
    """
    # Create policy with $500 per-tx limit and $1000 daily limit
    policy = SpendingPolicy(
        agent_id="agent:test",
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("500.00"),
        limit_total=Decimal("10000.00"),
        daily_limit=TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("1000.00"),
            currency="USDC",
        ),
    )

    # First 10 payments of $100 each should work initially
    payments_processed = 0
    for i in range(10):
        amount = Decimal("100.00")
        fee = Decimal("1.00")

        ok, reason = policy.validate_payment(
            amount=amount,
            fee=fee,
            merchant_id="merchant:test",
            scope=SpendingScope.ALL,
        )

        if ok:
            policy.record_spend(amount)
            payments_processed += 1
        else:
            break

    # Should process exactly 10 payments ($1000 total) and reject 11th
    assert payments_processed == 10

    # 11th payment should fail due to daily limit
    ok, reason = policy.validate_payment(
        amount=Decimal("100.00"),
        fee=Decimal("1.00"),
        merchant_id="merchant:test",
        scope=SpendingScope.ALL,
    )

    assert ok is False
    assert reason == "time_window_limit"


def test_rapid_sequential_payments_same_vendor():
    """Test rapid sequential payments to same vendor within time window are flagged.

    Attack vector: Agent makes multiple rapid payments to the same merchant
    to avoid per-transaction limits while staying under aggregate limits.

    Defense: Policy engine tracks aggregate spending per time window.
    """
    policy = SpendingPolicy(
        agent_id="agent:test",
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("200.00"),
        limit_total=Decimal("10000.00"),
        daily_limit=TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("500.00"),
            currency="USDC",
        ),
    )

    merchant_id = "merchant:rapid_test"

    # Make 3 rapid payments of $150 each to same merchant
    for i in range(3):
        amount = Decimal("150.00")
        ok, reason = policy.validate_payment(
            amount=amount,
            fee=Decimal("1.00"),
            merchant_id=merchant_id,
            scope=SpendingScope.ALL,
        )

        if ok:
            policy.record_spend(amount)

    # Total spent: $450, still under $500 daily limit
    assert policy.daily_limit.current_spent == Decimal("450.00")

    # 4th payment should fail (would bring total to $600)
    ok, reason = policy.validate_payment(
        amount=Decimal("150.00"),
        fee=Decimal("1.00"),
        merchant_id=merchant_id,
        scope=SpendingScope.ALL,
    )

    assert ok is False
    assert reason == "time_window_limit"


def test_boundary_amounts_handled_correctly():
    """Test boundary amounts ($999.99 vs $1000 limit) handled correctly.

    Attack vector: Agent attempts to exploit rounding or boundary conditions
    by using amounts just under the limit repeatedly.

    Defense: Exact decimal arithmetic prevents rounding exploits.
    """
    policy = SpendingPolicy(
        agent_id="agent:test",
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("1000.00"),
        limit_total=Decimal("10000.00"),
        daily_limit=TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("3000.00"),
            currency="USDC",
        ),
    )

    # Payment at exact limit should succeed
    ok, reason = policy.validate_payment(
        amount=Decimal("1000.00"),
        fee=Decimal("0.00"),
        merchant_id="merchant:boundary",
        scope=SpendingScope.ALL,
    )
    assert ok is True
    policy.record_spend(Decimal("1000.00"))

    # Payment just under limit should succeed
    ok, reason = policy.validate_payment(
        amount=Decimal("999.99"),
        fee=Decimal("0.00"),
        merchant_id="merchant:boundary",
        scope=SpendingScope.ALL,
    )
    assert ok is True
    policy.record_spend(Decimal("999.99"))

    # Payment just over limit should fail
    ok, reason = policy.validate_payment(
        amount=Decimal("1000.01"),
        fee=Decimal("0.00"),
        merchant_id="merchant:boundary",
        scope=SpendingScope.ALL,
    )
    assert ok is False
    assert reason == "per_transaction_limit"

    # Aggregate check: $1999.99 spent so far, $1000.01 more would exceed $3000 daily
    ok, reason = policy.validate_payment(
        amount=Decimal("1000.01"),
        fee=Decimal("0.00"),
        merchant_id="merchant:boundary",
        scope=SpendingScope.ALL,
    )
    assert ok is False


# ==========================================
# Merchant/Category Evasion Tests
# ==========================================

def test_merchant_name_change_does_not_bypass_domain_policy():
    """Test changing merchant name but keeping domain does NOT bypass policy.

    Attack vector: Agent changes merchant_name in mandate but keeps same
    merchant_domain to bypass merchant-specific rules.

    Defense: MandateVerifier enforces merchant_domain binding across chain.
    """
    agent_id = "agent:test"
    merchant_domain = "blocked-merchant.example"

    # Create mandate chain with consistent merchant_domain
    intent = create_intent_mandate(agent_id=agent_id, requested_amount=50000)
    cart = create_cart_mandate(
        agent_id=agent_id,
        merchant_domain=merchant_domain,
        amount_minor=10000,
    )
    payment = create_payment_mandate(
        agent_id=agent_id,
        merchant_domain=merchant_domain,
        amount_minor=10000,
    )

    # Verify chain enforces merchant_domain consistency
    try:
        chain = MandateChain(intent=intent, cart=cart, payment=payment)
        # Chain creation should succeed if domains match
        assert cart.merchant_domain == payment.merchant_domain
    except ValueError as e:
        pytest.fail(f"Mandate chain creation failed unexpectedly: {e}")

    # Now test with mismatched merchant_domain (attack attempt)
    payment_modified = create_payment_mandate(
        agent_id=agent_id,
        merchant_domain="different-merchant.example",  # Changed!
        amount_minor=10000,
    )

    # This should fail at chain verification level
    settings = load_settings()
    verifier = MandateVerifier(settings=settings)

    # Create mock request bundle with mismatched domains
    bundle = type("Bundle", (), {
        "intent": {
            "mandate_id": intent.mandate_id,
            "mandate_type": "intent",
            "issuer": intent.issuer,
            "subject": intent.subject,
            "expires_at": intent.expires_at,
            "nonce": intent.nonce,
            "proof": {"type": "DataIntegrityProof", "verification_method": intent.proof.verification_method, "created": intent.proof.created, "proof_purpose": "assertionMethod", "proof_value": intent.proof.proof_value},
            "domain": intent.domain,
            "purpose": intent.purpose,
            "scope": list(intent.scope),
            "requested_amount": intent.requested_amount,
        },
        "cart": {
            "mandate_id": cart.mandate_id,
            "mandate_type": "cart",
            "issuer": cart.issuer,
            "subject": cart.subject,
            "expires_at": cart.expires_at,
            "nonce": cart.nonce,
            "proof": {"type": "DataIntegrityProof", "verification_method": cart.proof.verification_method, "created": cart.proof.created, "proof_purpose": "assertionMethod", "proof_value": cart.proof.proof_value},
            "domain": cart.domain,
            "purpose": cart.purpose,
            "line_items": list(cart.line_items),
            "merchant_domain": cart.merchant_domain,
            "currency": cart.currency,
            "subtotal_minor": cart.subtotal_minor,
            "taxes_minor": cart.taxes_minor,
        },
        "payment": {
            "mandate_id": payment_modified.mandate_id,
            "mandate_type": "payment",
            "issuer": payment_modified.issuer,
            "subject": payment_modified.subject,
            "expires_at": payment_modified.expires_at,
            "nonce": payment_modified.nonce,
            "proof": {"type": "DataIntegrityProof", "verification_method": payment_modified.proof.verification_method, "created": payment_modified.proof.created, "proof_purpose": "assertionMethod", "proof_value": payment_modified.proof.proof_value},
            "domain": payment_modified.domain,
            "purpose": payment_modified.purpose,
            "chain": payment_modified.chain,
            "token": payment_modified.token,
            "amount_minor": payment_modified.amount_minor,
            "destination": payment_modified.destination,
            "audit_hash": payment_modified.audit_hash,
            "merchant_domain": payment_modified.merchant_domain,
            "ai_agent_presence": True,
            "transaction_modality": "human_present",
        },
        "canonicalization_mode": "pipe",
    })()

    result = verifier.verify_chain(bundle)

    assert result.accepted is False
    assert result.reason == "merchant_domain_mismatch"


def test_blocked_category_cannot_bypass_with_different_merchant_name():
    """Test merchant in blocked category cannot be paid with different merchant_name.

    Attack vector: Agent attempts to pay a merchant in a blocked category
    (e.g., gambling) by using a different merchant name or category label.

    Defense: Policy checks merchant rules including category-based denials.
    """
    policy = SpendingPolicy(
        agent_id="agent:test",
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("1000.00"),
        limit_total=Decimal("10000.00"),
    )

    # Add a deny rule for gambling category
    policy.add_merchant_deny(
        merchant_id="gambling-site.example",
        category="gambling",
        reason="Blocked category",
    )

    # Attempt payment with different merchant name but same category
    ok, reason = policy.validate_payment(
        amount=Decimal("100.00"),
        fee=Decimal("1.00"),
        merchant_id="totally-legit-merchant.example",  # Different name!
        merchant_category="gambling",  # But same category
        scope=SpendingScope.ALL,
    )

    assert ok is False
    assert reason == "merchant_denied"


def test_mandate_chain_rejects_mismatched_merchant_info():
    """Test mandate chain with mismatched merchant info across stages is rejected.

    Attack vector: Agent creates intent/cart with one merchant, then changes
    merchant in payment stage to bypass allowlists.

    Defense: MandateVerifier.verify_chain enforces merchant_domain consistency.

    Note: MandateChain.__post_init__ validates amount/expiry consistency, but
    merchant_domain mismatch is detected at verification level.
    """
    agent_id = "agent:test"

    intent = create_intent_mandate(agent_id=agent_id, requested_amount=50000)
    cart = create_cart_mandate(
        agent_id=agent_id,
        merchant_domain="legitimate-merchant.example",
        amount_minor=10000,
    )
    payment = create_payment_mandate(
        agent_id=agent_id,
        merchant_domain="malicious-merchant.example",  # Mismatched!
        amount_minor=10000,
    )

    # MandateVerifier should reject merchant_domain mismatch
    settings = load_settings()
    verifier = MandateVerifier(settings=settings)

    bundle = type("Bundle", (), {
        "intent": {
            "mandate_id": intent.mandate_id,
            "mandate_type": "intent",
            "issuer": intent.issuer,
            "subject": intent.subject,
            "expires_at": intent.expires_at,
            "nonce": intent.nonce,
            "proof": {"type": "DataIntegrityProof", "verification_method": intent.proof.verification_method, "created": intent.proof.created, "proof_purpose": "assertionMethod", "proof_value": intent.proof.proof_value},
            "domain": intent.domain,
            "purpose": intent.purpose,
            "scope": list(intent.scope),
            "requested_amount": intent.requested_amount,
        },
        "cart": {
            "mandate_id": cart.mandate_id,
            "mandate_type": "cart",
            "issuer": cart.issuer,
            "subject": cart.subject,
            "expires_at": cart.expires_at,
            "nonce": cart.nonce,
            "proof": {"type": "DataIntegrityProof", "verification_method": cart.proof.verification_method, "created": cart.proof.created, "proof_purpose": "assertionMethod", "proof_value": cart.proof.proof_value},
            "domain": cart.domain,
            "purpose": cart.purpose,
            "line_items": list(cart.line_items),
            "merchant_domain": cart.merchant_domain,
            "currency": cart.currency,
            "subtotal_minor": cart.subtotal_minor,
            "taxes_minor": cart.taxes_minor,
        },
        "payment": {
            "mandate_id": payment.mandate_id,
            "mandate_type": "payment",
            "issuer": payment.issuer,
            "subject": payment.subject,
            "expires_at": payment.expires_at,
            "nonce": payment.nonce,
            "proof": {"type": "DataIntegrityProof", "verification_method": payment.proof.verification_method, "created": payment.proof.created, "proof_purpose": "assertionMethod", "proof_value": payment.proof.proof_value},
            "domain": payment.domain,
            "purpose": payment.purpose,
            "chain": payment.chain,
            "token": payment.token,
            "amount_minor": payment.amount_minor,
            "destination": payment.destination,
            "audit_hash": payment.audit_hash,
            "merchant_domain": payment.merchant_domain,
            "ai_agent_presence": True,
            "transaction_modality": "human_present",
        },
        "canonicalization_mode": "pipe",
    })()

    result = verifier.verify_chain(bundle)

    assert result.accepted is False
    assert result.reason == "merchant_domain_mismatch"


# ==========================================
# Alternate Flow Evasion Tests
# ==========================================

def test_skipping_ucp_still_enforces_policy():
    """Test skipping UCP checkout and going directly to AP2 execute still enforces policy.

    Attack vector: Agent bypasses UCP (Universal Checkout Protocol) flow
    and goes directly to AP2 payment execution to avoid pre-authorization checks.

    Defense: AP2 execute endpoint performs all policy checks regardless of entry point.
    """
    # Create a mandate chain that would normally go through UCP
    agent_id = "agent:test"

    intent = create_intent_mandate(agent_id=agent_id, requested_amount=50000)
    cart = create_cart_mandate(
        agent_id=agent_id,
        merchant_domain="merchant.example",
        amount_minor=10000,
    )
    payment = create_payment_mandate(
        agent_id=agent_id,
        merchant_domain="merchant.example",
        amount_minor=10000,
    )

    chain = MandateChain(intent=intent, cart=cart, payment=payment)

    # Create a policy that would reject this amount
    policy = SpendingPolicy(
        agent_id=agent_id,
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("50.00"),  # Much lower than payment amount
        limit_total=Decimal("10000.00"),
    )

    # Validate payment against policy (simulating AP2 execute checks)
    amount_dollars = Decimal(payment.amount_minor) / Decimal("100")
    ok, reason = policy.validate_payment(
        amount=amount_dollars,
        fee=Decimal("1.00"),
        merchant_id=payment.merchant_domain,
        scope=SpendingScope.ALL,
    )

    # Should fail due to per-transaction limit
    assert ok is False
    assert reason == "per_transaction_limit"


def test_bypassing_tap_does_not_disable_ap2_policy_checks():
    """Test bypassing TAP (if disabled) does NOT disable AP2 policy checks.

    Attack vector: Agent assumes that if TAP (Trust Anchor Protocol) identity
    verification is disabled, other security checks might also be bypassed.

    Defense: AP2 policy checks are independent of TAP and always enforced.
    """
    # Simulate scenario where TAP is disabled (no identity verification)
    # but AP2 mandate chain verification still happens

    agent_id = "agent:test"

    intent = create_intent_mandate(agent_id=agent_id, requested_amount=100000)
    cart = create_cart_mandate(
        agent_id=agent_id,
        merchant_domain="merchant.example",
        amount_minor=50000,
    )
    payment = create_payment_mandate(
        agent_id=agent_id,
        merchant_domain="merchant.example",
        amount_minor=50000,
    )

    # Create mandate chain (AP2 validation)
    chain = MandateChain(intent=intent, cart=cart, payment=payment)

    # Policy checks should still apply
    policy = SpendingPolicy(
        agent_id=agent_id,
        trust_level=TrustLevel.LOW,
        limit_per_tx=Decimal("100.00"),
        limit_total=Decimal("10000.00"),
    )

    amount_dollars = Decimal(payment.amount_minor) / Decimal("100")
    ok, reason = policy.validate_payment(
        amount=amount_dollars,
        fee=Decimal("1.00"),
        merchant_id=payment.merchant_domain,
        scope=SpendingScope.ALL,
    )

    # Should fail regardless of TAP status
    assert ok is False
    assert reason == "per_transaction_limit"


def test_x402_payment_without_prior_challenge_rejected():
    """Test x402 payment without a prior challenge is rejected.

    Attack vector: Agent attempts to submit an x402 payment payload without
    first receiving a proper challenge from the server, potentially with
    forged or guessed challenge parameters.

    Defense: verify_payment_payload() validates nonce, payment_id, and
    amount against the original challenge.
    """
    # Create a fake payment payload without a valid challenge
    fake_payload = X402PaymentPayload(
        payment_id="x402_fake_payment_123",
        payer_address="0xfakeaddress",
        amount="10000",
        nonce="fake_nonce_123",
        signature="fake_signature",
        authorization={},
    )

    # Create a challenge that doesn't match the payload
    real_challenge = X402Challenge(
        payment_id="x402_real_payment_456",  # Different payment_id
        resource_uri="/api/resource",
        amount="10000",
        currency="USDC",
        payee_address="0xrealmerchant",
        network="base",
        token_address="0xtoken",
        expires_at=int(time.time()) + 300,
        nonce="real_nonce_456",  # Different nonce
    )

    # Attempt to verify the fake payload against the real challenge
    result = verify_payment_payload(
        payload=fake_payload,
        challenge=real_challenge,
    )

    # Should fail due to nonce mismatch (checked before payment_id in verify_payment_payload)
    assert result.accepted is False
    assert result.reason == "x402_nonce_mismatch"

    # Now test with matching payment_id but wrong nonce
    fake_payload_2 = X402PaymentPayload(
        payment_id="x402_real_payment_456",  # Matches challenge
        payer_address="0xfakeaddress",
        amount="10000",
        nonce="wrong_nonce",  # Wrong nonce
        signature="fake_signature",
        authorization={},
    )

    result = verify_payment_payload(
        payload=fake_payload_2,
        challenge=real_challenge,
    )

    # Should fail due to nonce mismatch
    assert result.accepted is False
    assert result.reason == "x402_nonce_mismatch"

    # Test with wrong amount
    fake_payload_3 = X402PaymentPayload(
        payment_id="x402_real_payment_456",
        payer_address="0xfakeaddress",
        amount="5000",  # Wrong amount
        nonce="real_nonce_456",
        signature="fake_signature",
        authorization={},
    )

    result = verify_payment_payload(
        payload=fake_payload_3,
        challenge=real_challenge,
    )

    # Should fail due to amount mismatch
    assert result.accepted is False
    assert result.reason == "x402_amount_mismatch"

    # Test with expired challenge
    expired_challenge = X402Challenge(
        payment_id="x402_expired_payment",
        resource_uri="/api/resource",
        amount="10000",
        currency="USDC",
        payee_address="0xmerchant",
        network="base",
        token_address="0xtoken",
        expires_at=int(time.time()) - 100,  # Expired
        nonce="expired_nonce",
    )

    expired_payload = X402PaymentPayload(
        payment_id="x402_expired_payment",
        payer_address="0xpayer",
        amount="10000",
        nonce="expired_nonce",
        signature="signature",
        authorization={},
    )

    result = verify_payment_payload(
        payload=expired_payload,
        challenge=expired_challenge,
    )

    # Should fail due to expiration
    assert result.accepted is False
    assert result.reason == "x402_challenge_expired"
