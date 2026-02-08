"""Test F14: fail-closed behavior when identity registry is not configured."""
import os
import time
import base64
import pytest
from unittest.mock import Mock

from nacl.signing import SigningKey

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_protocol.verifier import MandateVerifier, VerificationError


def _create_mandate():
    """Create a test mandate with valid Ed25519 signature."""
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    public_key_bytes = bytes(verify_key)
    public_key_hex = public_key_bytes.hex()

    mandate_id = "test-mandate"
    agent_id = "agent:test@example.com"
    merchant_domain = "merchant.com"
    destination = "0x1234567890123456789012345678901234567890"
    audit_hash = "test-audit-hash"
    domain = "example.com"
    nonce = "test-nonce"
    purpose = "checkout"

    # Build canonical payment payload
    canonical = "|".join([
        mandate_id, agent_id, "1000000", "USDC", "base",
        destination, merchant_domain, audit_hash, "1", "human_present",
    ]).encode()

    # AgentIdentity.verify wraps: domain|nonce|purpose|canonical
    full_payload = b"|".join([domain.encode(), nonce.encode(), purpose.encode(), canonical])
    signed = signing_key.sign(full_payload)
    signature = signed.signature  # just the 64-byte sig

    return PaymentMandate(
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
    ), public_key_bytes


def test_production_requires_identity_registry():
    """In production, must raise VerificationError if no identity registry."""
    original_env = os.getenv("SARDIS_ENV")
    original_environment = os.getenv("SARDIS_ENVIRONMENT")
    try:
        os.environ["SARDIS_ENV"] = "production"
        os.environ["SARDIS_ENVIRONMENT"] = "production"
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings, identity_registry=None)
        mandate, _ = _create_mandate()

        with pytest.raises(VerificationError, match="Identity registry required in"):
            verifier.verify(mandate)
    finally:
        if original_env is None:
            os.environ.pop("SARDIS_ENV", None)
        else:
            os.environ["SARDIS_ENV"] = original_env
        if original_environment is None:
            os.environ.pop("SARDIS_ENVIRONMENT", None)
        else:
            os.environ["SARDIS_ENVIRONMENT"] = original_environment


def test_dev_mode_allows_missing_identity_registry():
    """In dev mode, verification proceeds with warning."""
    original_env = os.getenv("SARDIS_ENV")
    original_environment = os.getenv("SARDIS_ENVIRONMENT")
    try:
        os.environ["SARDIS_ENV"] = "development"
        os.environ["SARDIS_ENVIRONMENT"] = "development"
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings, identity_registry=None)
        mandate, _ = _create_mandate()

        result = verifier.verify(mandate)
        assert result.accepted, f"Dev mode should allow: {result.reason}"
    finally:
        if original_env is None:
            os.environ.pop("SARDIS_ENV", None)
        else:
            os.environ["SARDIS_ENV"] = original_env
        if original_environment is None:
            os.environ.pop("SARDIS_ENVIRONMENT", None)
        else:
            os.environ["SARDIS_ENVIRONMENT"] = original_environment


def test_unset_env_allows_missing_identity_registry():
    """When SARDIS_ENV and SARDIS_ENVIRONMENT are unset, verification proceeds (dev default)."""
    original_env = os.getenv("SARDIS_ENV")
    original_environment = os.getenv("SARDIS_ENVIRONMENT")
    try:
        os.environ.pop("SARDIS_ENV", None)
        os.environ.pop("SARDIS_ENVIRONMENT", None)
        settings = SardisSettings(allowed_domains=["example.com"])
        verifier = MandateVerifier(settings, identity_registry=None)
        mandate, _ = _create_mandate()

        result = verifier.verify(mandate)
        assert result.accepted, f"Unset env should allow: {result.reason}"
    finally:
        if original_env is None:
            os.environ.pop("SARDIS_ENV", None)
        else:
            os.environ["SARDIS_ENV"] = original_env
        if original_environment is None:
            os.environ.pop("SARDIS_ENVIRONMENT", None)
        else:
            os.environ["SARDIS_ENVIRONMENT"] = original_environment


def test_with_identity_registry_works_in_production():
    """With identity registry provided, production mode works."""
    original_env = os.getenv("SARDIS_ENV")
    original_environment = os.getenv("SARDIS_ENVIRONMENT")
    try:
        os.environ["SARDIS_ENV"] = "production"
        os.environ["SARDIS_ENVIRONMENT"] = "production"
        settings = SardisSettings(allowed_domains=["example.com"])
        mandate, pub_key_bytes = _create_mandate()

        mock_registry = Mock()
        mock_registry.verify_binding = Mock(return_value=True)

        verifier = MandateVerifier(settings, identity_registry=mock_registry)
        result = verifier.verify(mandate)
        assert result.accepted, f"Production with registry should work: {result.reason}"

        mock_registry.verify_binding.assert_called_once()
    finally:
        if original_env is None:
            os.environ.pop("SARDIS_ENV", None)
        else:
            os.environ["SARDIS_ENV"] = original_env
        if original_environment is None:
            os.environ.pop("SARDIS_ENVIRONMENT", None)
        else:
            os.environ["SARDIS_ENVIRONMENT"] = original_environment
