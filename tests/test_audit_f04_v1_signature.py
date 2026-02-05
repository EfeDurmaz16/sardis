"""Test that V1 signatures without merchant_domain are rejected."""
import base64
import time

from nacl.signing import SigningKey

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_protocol.verifier import MandateVerifier


def test_v1_signature_rejected():
    """V1-style signatures (without merchant_domain) must be rejected."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)

    signing_key = SigningKey.generate()
    public_key_hex = bytes(signing_key.verify_key).hex()

    mandate_id = "test-mandate-v1"
    agent_id = "agent:test@example.com"
    merchant_domain = "merchant.com"
    destination = "0x1234567890123456789012345678901234567890"
    audit_hash = "test-audit-hash"
    domain = "example.com"
    nonce = "test-nonce"
    purpose = "checkout"

    # Sign V1-style payload (WITHOUT merchant_domain) - this is the wrong format
    payload_v1 = "|".join([
        mandate_id, agent_id, "1000000", "USDC", "base",
        destination, audit_hash,
    ]).encode()

    # Wrap with domain|nonce|purpose as the verifier expects
    full_payload = b"|".join([domain.encode(), nonce.encode(), purpose.encode(), payload_v1])
    signed = signing_key.sign(full_payload)
    signature = signed.signature

    mandate = PaymentMandate(
        mandate_id=mandate_id,
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=int(time.time()) + 3600,
        domain=domain,
        merchant_domain=merchant_domain,
        purpose=purpose,
        nonce=nonce,
        amount_minor=1000000,
        token="USDC",
        chain="base",
        destination=destination,
        audit_hash=audit_hash,
        proof=VCProof(
            verification_method=f"ed25519:{public_key_hex}",
            created=str(int(time.time())),
            proof_value=base64.b64encode(signature).decode(),
        ),
    )

    # Verify - should FAIL because V1 payload doesn't include merchant_domain
    result = verifier.verify(mandate)
    assert not result.accepted, "V1 signature (without merchant_domain) should be rejected"


def test_v2_signature_accepted():
    """V2-style signatures (with merchant_domain) should still work."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)

    signing_key = SigningKey.generate()
    public_key_hex = bytes(signing_key.verify_key).hex()

    mandate_id = "test-mandate-v2"
    agent_id = "agent:test@example.com"
    merchant_domain = "merchant.com"
    destination = "0x1234567890123456789012345678901234567890"
    audit_hash = "test-audit-hash"
    domain = "example.com"
    nonce = "test-nonce"
    purpose = "checkout"

    # Sign V2-style payload (WITH merchant_domain) - correct format
    canonical = "|".join([
        mandate_id, agent_id, "1000000", "USDC", "base",
        destination, merchant_domain, audit_hash,
    ]).encode()

    full_payload = b"|".join([domain.encode(), nonce.encode(), purpose.encode(), canonical])
    signed = signing_key.sign(full_payload)
    signature = signed.signature

    mandate = PaymentMandate(
        mandate_id=mandate_id,
        mandate_type="payment",
        subject=agent_id,
        issuer=agent_id,
        expires_at=int(time.time()) + 3600,
        domain=domain,
        merchant_domain=merchant_domain,
        purpose=purpose,
        nonce=nonce,
        amount_minor=1000000,
        token="USDC",
        chain="base",
        destination=destination,
        audit_hash=audit_hash,
        proof=VCProof(
            verification_method=f"ed25519:{public_key_hex}",
            created=str(int(time.time())),
            proof_value=base64.b64encode(signature).decode(),
        ),
    )

    # Verify - should PASS
    result = verifier.verify(mandate)
    assert result.accepted, f"V2 signature should be accepted: {result.reason}"
