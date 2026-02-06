"""JWKS and signature verification helpers for TAP integrations."""
from __future__ import annotations

import base64
from typing import Any, Mapping, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from nacl import signing
from nacl.exceptions import BadSignatureError


def _b64url_decode(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + pad)


def select_jwk_by_kid(jwks: Mapping[str, Any], kid: str) -> Optional[Mapping[str, Any]]:
    """Select a JWK entry by key id from a JWKS payload."""
    keys = jwks.get("keys", [])
    if not isinstance(keys, list):
        return None
    for key in keys:
        if isinstance(key, Mapping) and str(key.get("kid", "")) == kid:
            return key
    return None


def verify_signature_with_jwk(
    *,
    signature_base: bytes,
    signature_b64: str,
    jwk: Mapping[str, Any],
    alg: str,
) -> bool:
    """
    Verify signature bytes against a JWK using supported algorithms.

    Supported:
      - Ed25519 with JWK kty=OKP, crv=Ed25519, x=<base64url>
      - PS256 with JWK kty=RSA, n/e
    """
    try:
        signature = base64.b64decode(signature_b64)
    except Exception:
        return False

    normalized_alg = str(alg).upper()
    kty = str(jwk.get("kty", "")).upper()

    if normalized_alg == "ED25519":
        if kty != "OKP" or str(jwk.get("crv", "")) != "Ed25519":
            return False
        x = jwk.get("x")
        if not isinstance(x, str):
            return False
        try:
            verify_key = signing.VerifyKey(_b64url_decode(x))
            verify_key.verify(signature_base, signature)
            return True
        except (BadSignatureError, ValueError):
            return False

    if normalized_alg == "PS256":
        if kty != "RSA":
            return False
        n = jwk.get("n")
        e = jwk.get("e")
        if not isinstance(n, str) or not isinstance(e, str):
            return False
        try:
            public_numbers = rsa.RSAPublicNumbers(
                e=int.from_bytes(_b64url_decode(e), "big"),
                n=int.from_bytes(_b64url_decode(n), "big"),
            )
            public_key = public_numbers.public_key()
            public_key.verify(
                signature,
                signature_base,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=hashes.SHA256().digest_size),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    return False


__all__ = [
    "select_jwk_by_kid",
    "verify_signature_with_jwk",
]
