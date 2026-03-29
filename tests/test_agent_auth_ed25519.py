"""Tests for Ed25519 signature verification in the Agent Auth Protocol.

Verifies that:
  - Valid Ed25519 signatures pass verification
  - Invalid signatures are rejected with 401/None
  - Missing signatures are rejected
  - Tampered payloads are rejected
  - Expired tokens are rejected
  - Unregistered agents are rejected
  - Revoked agents are rejected
"""
from __future__ import annotations

import base64
import json
import time
from unittest.mock import MagicMock

import pytest
from nacl.signing import SigningKey

from sardis_api.routers.agent_auth import (
    _agent_registry,
    _capability_grants,
    _verify_agent_jwt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    """base64url-encode without padding (standard JWT encoding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_signed_jwt(
    signing_key: SigningKey,
    payload: dict,
    header: dict | None = None,
) -> str:
    """Build a properly signed Ed25519 JWT.

    Format: <header_b64url>.<payload_b64url>.<signature_b64url>
    Signature covers the ASCII bytes of "<header_b64url>.<payload_b64url>".
    """
    if header is None:
        header = {"alg": "EdDSA", "typ": "JWT"}

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signed = signing_key.sign(signing_input)
    # signed.signature is the detached 64-byte Ed25519 signature
    sig_b64 = _b64url_encode(signed.signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def _make_request_with_jwt(token: str) -> MagicMock:
    """Create a mock Request object with the X-Agent-JWT header set."""
    request = MagicMock()
    request.headers = {"x-agent-jwt": token}
    return request


def _register_agent(agent_id: str, public_key_hex: str, status: str = "active") -> None:
    """Insert an agent directly into the in-memory registry."""
    _agent_registry[agent_id] = {
        "agent_id": agent_id,
        "org_id": "org_test",
        "agent_name": "Test Agent",
        "agent_description": "Test",
        "public_key": public_key_hex,
        "algorithm": "Ed25519",
        "mode": "delegated",
        "status": status,
        "callback_url": None,
        "metadata": {},
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_active_at": "2026-01-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure the agent registry is clean before and after each test."""
    _agent_registry.clear()
    _capability_grants.clear()
    yield
    _agent_registry.clear()
    _capability_grants.clear()


@pytest.fixture()
def keypair():
    """Generate a fresh Ed25519 keypair."""
    sk = SigningKey.generate()
    pk_hex = sk.verify_key.encode().hex()
    return sk, pk_hex


@pytest.fixture()
def registered_agent(keypair):
    """Register an agent with the generated keypair, return (agent_id, signing_key)."""
    sk, pk_hex = keypair
    agent_id = "agent_auth_test12345"
    _register_agent(agent_id, pk_hex)
    return agent_id, sk


# ---------------------------------------------------------------------------
# Tests: Valid signatures
# ---------------------------------------------------------------------------

class TestValidSignatures:

    def test_valid_signature_returns_payload(self, registered_agent):
        """A correctly signed JWT from a registered active agent must pass."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is not None
        assert result["sub"] == agent_id

    def test_valid_signature_no_exp(self, registered_agent):
        """A JWT without exp claim should still pass if signature is valid."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is not None
        assert result["sub"] == agent_id

    def test_valid_signature_with_extra_claims(self, registered_agent):
        """Extra claims in the payload should not break verification."""
        agent_id, sk = registered_agent
        payload = {
            "sub": agent_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "capability": "payment",
            "custom_field": "test_value",
        }
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is not None
        assert result["sub"] == agent_id
        assert result["capability"] == "payment"


# ---------------------------------------------------------------------------
# Tests: Invalid signatures
# ---------------------------------------------------------------------------

class TestInvalidSignatures:

    def test_wrong_signing_key_rejected(self, registered_agent):
        """A JWT signed with a DIFFERENT key must be rejected."""
        agent_id, _sk = registered_agent
        wrong_sk = SigningKey.generate()  # different key
        payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = _make_signed_jwt(wrong_sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None

    def test_corrupted_signature_rejected(self, registered_agent):
        """A JWT with a corrupted signature must be rejected."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = _make_signed_jwt(sk, payload)

        # Corrupt the signature by decoding, flipping bytes, and re-encoding
        parts = token.split(".")
        sig_b64 = parts[2]
        padded = sig_b64 + "=" * (4 - len(sig_b64) % 4) if len(sig_b64) % 4 else sig_b64
        sig_bytes = bytearray(base64.urlsafe_b64decode(padded))
        # Flip every byte to guarantee corruption
        for i in range(len(sig_bytes)):
            sig_bytes[i] ^= 0xFF
        parts[2] = base64.urlsafe_b64encode(bytes(sig_bytes)).rstrip(b"=").decode()
        corrupted_token = ".".join(parts)

        request = _make_request_with_jwt(corrupted_token)
        result = _verify_agent_jwt(request)

        assert result is None

    def test_empty_signature_rejected(self, registered_agent):
        """A JWT with an empty signature field must be rejected."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = _make_signed_jwt(sk, payload)

        parts = token.split(".")
        parts[2] = ""  # empty signature
        empty_sig_token = ".".join(parts)

        request = _make_request_with_jwt(empty_sig_token)
        result = _verify_agent_jwt(request)

        assert result is None

    def test_truncated_signature_rejected(self, registered_agent):
        """A JWT with a truncated signature must be rejected."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = _make_signed_jwt(sk, payload)

        parts = token.split(".")
        parts[2] = parts[2][:10]  # only 10 chars of signature
        truncated_token = ".".join(parts)

        request = _make_request_with_jwt(truncated_token)
        result = _verify_agent_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Missing signature / header
# ---------------------------------------------------------------------------

class TestMissingSignature:

    def test_no_jwt_header_returns_none(self):
        """Request with no X-Agent-JWT header must return None."""
        request = MagicMock()
        request.headers = {}

        result = _verify_agent_jwt(request)

        assert result is None

    def test_empty_jwt_header_returns_none(self):
        """Request with empty X-Agent-JWT header must return None."""
        request = _make_request_with_jwt("")
        result = _verify_agent_jwt(request)

        assert result is None

    def test_malformed_jwt_two_parts(self, registered_agent):
        """A token with only two parts (no signature) must be rejected."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id}
        header = {"alg": "EdDSA", "typ": "JWT"}

        header_b64 = _b64url_encode(json.dumps(header).encode())
        payload_b64 = _b64url_encode(json.dumps(payload).encode())

        token = f"{header_b64}.{payload_b64}"  # missing third part
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None

    def test_malformed_jwt_one_part(self):
        """A single string with no dots must be rejected."""
        request = _make_request_with_jwt("not-a-jwt-at-all")
        result = _verify_agent_jwt(request)

        assert result is None

    def test_four_part_token_rejected(self, registered_agent):
        """A token with four parts must be rejected."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id}
        token = _make_signed_jwt(sk, payload)
        token_with_extra = token + ".extra"
        request = _make_request_with_jwt(token_with_extra)

        result = _verify_agent_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Tampered payloads
# ---------------------------------------------------------------------------

class TestTamperedPayloads:

    def test_tampered_payload_rejected(self, registered_agent):
        """Modifying the payload after signing must break verification."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = _make_signed_jwt(sk, payload)

        # Tamper: replace the payload with a different one
        tampered_payload = {"sub": agent_id, "iat": int(time.time()), "exp": int(time.time()) + 7200, "admin": True}
        tampered_payload_b64 = _b64url_encode(json.dumps(tampered_payload, separators=(",", ":")).encode())

        parts = token.split(".")
        parts[1] = tampered_payload_b64
        tampered_token = ".".join(parts)

        request = _make_request_with_jwt(tampered_token)
        result = _verify_agent_jwt(request)

        assert result is None

    def test_tampered_header_rejected(self, registered_agent):
        """Modifying the header after signing must break verification."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)

        # Tamper: replace header
        tampered_header = {"alg": "none", "typ": "JWT"}
        tampered_header_b64 = _b64url_encode(json.dumps(tampered_header, separators=(",", ":")).encode())

        parts = token.split(".")
        parts[0] = tampered_header_b64
        tampered_token = ".".join(parts)

        request = _make_request_with_jwt(tampered_token)
        result = _verify_agent_jwt(request)

        assert result is None

    def test_swapped_agent_id_rejected(self, keypair):
        """Signing as agent A but claiming sub=agent_B must be rejected."""
        sk, pk_hex = keypair
        agent_a = "agent_auth_aaaa"
        agent_b = "agent_auth_bbbb"

        # Register both agents — agent_b has a DIFFERENT public key
        other_sk = SigningKey.generate()
        _register_agent(agent_a, pk_hex)
        _register_agent(agent_b, other_sk.verify_key.encode().hex())

        # Sign with agent_a's key but claim sub=agent_b
        payload = {"sub": agent_b, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)  # signed with agent_a's key

        request = _make_request_with_jwt(token)
        result = _verify_agent_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Agent state
# ---------------------------------------------------------------------------

class TestAgentState:

    def test_unregistered_agent_rejected(self):
        """A JWT with a sub that does not exist in the registry must be rejected."""
        sk = SigningKey.generate()
        payload = {"sub": "agent_auth_nonexistent", "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None

    def test_revoked_agent_rejected(self, keypair):
        """A JWT for a revoked agent must be rejected even with valid signature."""
        sk, pk_hex = keypair
        agent_id = "agent_auth_revoked"
        _register_agent(agent_id, pk_hex, status="revoked")

        payload = {"sub": agent_id, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None

    def test_suspended_agent_rejected(self, keypair):
        """A JWT for a suspended agent must be rejected even with valid signature."""
        sk, pk_hex = keypair
        agent_id = "agent_auth_suspended"
        _register_agent(agent_id, pk_hex, status="suspended")

        payload = {"sub": agent_id, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None

    def test_expired_token_rejected(self, registered_agent):
        """A JWT that has expired must be rejected even with valid signature."""
        agent_id, sk = registered_agent
        payload = {"sub": agent_id, "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Malformed public key in registry
# ---------------------------------------------------------------------------

class TestMalformedPublicKey:

    def test_invalid_hex_public_key_rejected(self):
        """If the stored public key is not valid hex, verification must fail safely."""
        sk = SigningKey.generate()
        agent_id = "agent_auth_badhex"
        _register_agent(agent_id, "not-valid-hex-string")

        payload = {"sub": agent_id, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None

    def test_wrong_length_public_key_rejected(self):
        """If the stored public key is hex but wrong length, verification must fail safely."""
        sk = SigningKey.generate()
        agent_id = "agent_auth_shortkey"
        _register_agent(agent_id, "aabbccdd")  # too short for Ed25519

        payload = {"sub": agent_id, "iat": int(time.time())}
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Missing sub claim
# ---------------------------------------------------------------------------

class TestMissingClaims:

    def test_missing_sub_claim_rejected(self, keypair):
        """A JWT without a 'sub' claim must be rejected."""
        sk, pk_hex = keypair
        payload = {"iat": int(time.time()), "capability": "payment"}  # no sub
        token = _make_signed_jwt(sk, payload)
        request = _make_request_with_jwt(token)

        result = _verify_agent_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: Import guard (module-level fail-closed)
# ---------------------------------------------------------------------------

class TestImportGuard:

    def test_nacl_imports_available(self):
        """Verify that nacl.signing.VerifyKey and BadSignatureError are importable.

        The module uses top-level imports — if PyNaCl is missing,
        agent_auth.py will raise ImportError at load time (fail-closed).
        """
        from nacl.exceptions import BadSignatureError as _BadSig
        from nacl.signing import VerifyKey as _VK

        assert _VK is not None
        assert _BadSig is not None
