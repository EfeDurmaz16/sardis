"""Tests for TAP JWKS key selection and signature verification."""
from __future__ import annotations

import base64
import pytest

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from nacl.signing import SigningKey

from sardis_protocol.tap_keys import select_jwk_by_kid, verify_signature_with_jwk

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.tap]


def _b64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def test_select_jwk_by_kid():
    jwks = {
        "keys": [
            {"kid": "k1", "kty": "OKP"},
            {"kid": "k2", "kty": "RSA"},
        ]
    }
    assert select_jwk_by_kid(jwks, "k2") == {"kid": "k2", "kty": "RSA"}
    assert select_jwk_by_kid(jwks, "missing") is None


def test_verify_signature_with_jwk_ed25519():
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    message = b"tap-signature-base"
    signature = signing_key.sign(message).signature

    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "kid": "kid-ed",
        "x": _b64url_no_pad(bytes(verify_key)),
    }

    ok = verify_signature_with_jwk(
        signature_base=message,
        signature_b64=base64.b64encode(signature).decode(),
        jwk=jwk,
        alg="Ed25519",
    )
    assert ok is True

    bad = verify_signature_with_jwk(
        signature_base=b"tampered",
        signature_b64=base64.b64encode(signature).decode(),
        jwk=jwk,
        alg="Ed25519",
    )
    assert bad is False


def test_verify_signature_with_jwk_ps256():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()

    message = b"tap-object-signature-base"
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size),
        hashes.SHA256(),
    )

    jwk = {
        "kty": "RSA",
        "kid": "kid-rsa",
        "alg": "PS256",
        "n": _b64url_no_pad(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
        "e": _b64url_no_pad(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")),
    }

    ok = verify_signature_with_jwk(
        signature_base=message,
        signature_b64=base64.b64encode(signature).decode(),
        jwk=jwk,
        alg="PS256",
    )
    assert ok is True
