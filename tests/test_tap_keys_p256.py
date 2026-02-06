"""ECDSA-P256 (ES256) signature verification tests for TAP keys.

Tests real cryptographic operations using the cryptography library.
"""
from __future__ import annotations

import base64
import pytest

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

from sardis_protocol.tap_keys import verify_signature_with_jwk, select_jwk_by_kid

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.tap]


def _generate_p256_keypair():
    """Generate a P-256 keypair and return (private_key, jwk_dict)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    # Convert x, y to base64url encoding (32 bytes each for P-256)
    x_bytes = public_numbers.x.to_bytes(32, byteorder="big")
    y_bytes = public_numbers.y.to_bytes(32, byteorder="big")
    x_b64 = base64.urlsafe_b64encode(x_bytes).rstrip(b"=").decode()
    y_b64 = base64.urlsafe_b64encode(y_bytes).rstrip(b"=").decode()

    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": x_b64,
        "y": y_b64,
        "kid": "test-p256-key",
    }
    return private_key, jwk


def _sign_message(private_key, message: bytes) -> bytes:
    """Sign a message with P-256 private key."""
    return private_key.sign(message, ec.ECDSA(hashes.SHA256()))


class TestECDSAP256Verification:
    def test_valid_p256_signature_verifies(self):
        """Valid P-256 signature should verify successfully."""
        private_key, jwk = _generate_p256_keypair()
        message = b"test message for P-256 verification"
        signature = _sign_message(private_key, message)
        sig_b64 = base64.b64encode(signature).decode()

        result = verify_signature_with_jwk(
            signature_base=message,
            signature_b64=sig_b64,
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is True

    def test_valid_p256_signature_verifies_es256_alias(self):
        """Valid P-256 signature should verify with ES256 algorithm name."""
        private_key, jwk = _generate_p256_keypair()
        message = b"test message for ES256 verification"
        signature = _sign_message(private_key, message)
        sig_b64 = base64.b64encode(signature).decode()

        result = verify_signature_with_jwk(
            signature_base=message,
            signature_b64=sig_b64,
            jwk=jwk,
            alg="ES256",
        )
        assert result is True

    def test_invalid_p256_signature_rejected(self):
        """Tampered signature should be rejected."""
        private_key, jwk = _generate_p256_keypair()
        message = b"test message"
        signature = _sign_message(private_key, message)

        # Tamper with signature
        tampered = bytearray(signature)
        tampered[-1] ^= 0xFF
        sig_b64 = base64.b64encode(bytes(tampered)).decode()

        result = verify_signature_with_jwk(
            signature_base=message,
            signature_b64=sig_b64,
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is False

    def test_wrong_message_rejected(self):
        """Signature for different message should be rejected."""
        private_key, jwk = _generate_p256_keypair()
        signature = _sign_message(private_key, b"original message")
        sig_b64 = base64.b64encode(signature).decode()

        result = verify_signature_with_jwk(
            signature_base=b"different message",
            signature_b64=sig_b64,
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is False

    def test_malformed_jwk_returns_false(self):
        """Malformed JWK should return False, not crash."""
        jwk = {"kty": "EC", "crv": "P-256"}  # Missing x, y
        result = verify_signature_with_jwk(
            signature_base=b"message",
            signature_b64="dGVzdA==",
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is False

    def test_wrong_curve_rejected(self):
        """JWK with wrong curve should be rejected."""
        private_key, jwk = _generate_p256_keypair()
        message = b"test message"
        signature = _sign_message(private_key, message)
        sig_b64 = base64.b64encode(signature).decode()

        # Modify curve to something else
        jwk["crv"] = "P-384"

        result = verify_signature_with_jwk(
            signature_base=message,
            signature_b64=sig_b64,
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is False

    def test_wrong_kty_rejected(self):
        """JWK with wrong key type should be rejected."""
        private_key, jwk = _generate_p256_keypair()
        message = b"test message"
        signature = _sign_message(private_key, message)
        sig_b64 = base64.b64encode(signature).decode()

        # Change kty to RSA
        jwk["kty"] = "RSA"

        result = verify_signature_with_jwk(
            signature_base=message,
            signature_b64=sig_b64,
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is False

    def test_invalid_base64_signature_rejected(self):
        """Invalid base64 signature should be rejected."""
        _, jwk = _generate_p256_keypair()

        result = verify_signature_with_jwk(
            signature_base=b"message",
            signature_b64="not-valid-base64!!!",
            jwk=jwk,
            alg="ecdsa-p256",
        )
        assert result is False

    def test_jwk_selection_by_kid(self):
        """JWK selection by kid should work for EC keys."""
        _, jwk = _generate_p256_keypair()
        jwks = {"keys": [jwk]}
        selected = select_jwk_by_kid(jwks, "test-p256-key")
        assert selected is not None
        assert selected["crv"] == "P-256"
        assert selected["kty"] == "EC"

    def test_unknown_kid_returns_none(self):
        """Unknown kid should return None."""
        _, jwk = _generate_p256_keypair()
        jwks = {"keys": [jwk]}
        selected = select_jwk_by_kid(jwks, "nonexistent-key")
        assert selected is None

    def test_multiple_keys_selects_correct_one(self):
        """Should select correct key when multiple keys present."""
        _, jwk1 = _generate_p256_keypair()
        jwk1["kid"] = "key-1"

        _, jwk2 = _generate_p256_keypair()
        jwk2["kid"] = "key-2"

        jwks = {"keys": [jwk1, jwk2]}
        selected = select_jwk_by_kid(jwks, "key-2")
        assert selected is not None
        assert selected["kid"] == "key-2"
