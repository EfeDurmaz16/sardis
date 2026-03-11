"""Tests for ERC-8128 Signed HTTP Requests.

Covers issue #128. Requires eth-account package.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

eth_account = pytest.importorskip("eth_account", reason="eth-account not installed")

from sardis_protocol.erc8128 import (
    ERC8128SignatureInput,
    ERC8128VerificationResult,
    build_keyid,
    build_signature_base,
    build_signature_input_header,
    compute_content_digest,
    extract_signature_bytes,
    parse_signature_input,
    sign_request,
    verify_request,
)


# Test wallet (DO NOT use in production — this is a well-known test key)
TEST_PRIVATE_KEY = "0x4c0883a69102937d6231471b5dbb6204fe512961708279f47e9e3e2b30cd9ad3"
TEST_ADDRESS = "0x0aEc616Dff22F6066AcD22EA10A63017CE58cadf"


class TestBuildKeyid:
    def test_default_chain(self):
        keyid = build_keyid("0xABC123")
        assert keyid == "erc8128:1:0xABC123"

    def test_custom_chain(self):
        keyid = build_keyid("0xDEF456", chain_id=8453)
        assert keyid == "erc8128:8453:0xDEF456"


class TestContentDigest:
    def test_sha256_digest(self):
        body = b'{"amount": 100}'
        digest = compute_content_digest(body)
        assert digest.startswith("sha-256=:")
        assert digest.endswith(":")
        # Should be deterministic
        assert compute_content_digest(body) == digest

    def test_empty_body(self):
        digest = compute_content_digest(b"")
        assert digest.startswith("sha-256=:")


class TestBuildSignatureBase:
    def test_basic_components(self):
        base = build_signature_base(
            method="POST",
            target_uri="https://api.sardis.sh/v2/payments",
            headers={},
            covered_components=["@method", "@target-uri"],
            created=1700000000,
            keyid="erc8128:1:0xABC",
        )
        assert '"@method": POST' in base
        assert '"@target-uri": https://api.sardis.sh/v2/payments' in base
        assert '"@signature-params"' in base
        assert "erc8128:1:0xABC" in base

    def test_with_content_digest(self):
        digest = compute_content_digest(b'{"test": true}')
        base = build_signature_base(
            method="POST",
            target_uri="https://api.example.com/test",
            headers={"content-digest": digest},
            covered_components=["@method", "@target-uri", "content-digest"],
            created=1700000000,
            keyid="erc8128:1:0xABC",
        )
        assert '"content-digest":' in base


class TestBuildSignatureInputHeader:
    def test_format(self):
        header = build_signature_input_header(
            covered_components=["@method", "@target-uri"],
            created=1700000000,
            keyid="erc8128:1:0xABC",
        )
        assert header.startswith('sig=("@method" "@target-uri")')
        assert "created=1700000000" in header
        assert 'keyid="erc8128:1:0xABC"' in header
        assert 'alg="erc8128-secp256k1"' in header


class TestParseSignatureInput:
    def test_valid_input(self):
        header = 'sig=("@method" "@target-uri" "content-digest");created=1700000000;keyid="erc8128:1:0xABC";alg="erc8128-secp256k1"'
        result = parse_signature_input(header)
        assert result is not None
        assert result.keyid == "erc8128:1:0xABC"
        assert result.created == 1700000000
        assert result.covered_components == ["@method", "@target-uri", "content-digest"]
        assert result.address == "0xABC"
        assert result.chain_id == 1

    def test_invalid_input(self):
        result = parse_signature_input("garbage")
        assert result is None


class TestExtractSignatureBytes:
    def test_valid_signature(self):
        import base64
        raw = b"\x01" * 65
        encoded = base64.b64encode(raw).decode()
        header = f"sig=:{encoded}:"
        result = extract_signature_bytes(header)
        assert result == raw

    def test_invalid_label(self):
        result = extract_signature_bytes("wrong=:abc:")
        assert result is None


class TestSignAndVerify:
    """End-to-end sign → verify flow."""

    def test_sign_and_verify_no_body(self):
        headers = sign_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            private_key=TEST_PRIVATE_KEY,
            address=TEST_ADDRESS,
            chain_id=1,
        )

        assert "signature-input" in headers
        assert "signature" in headers

        # Verify
        result = verify_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            headers=headers,
        )
        assert result.valid is True
        assert result.signer_address.lower() == TEST_ADDRESS.lower()
        assert result.chain_id == 1

    def test_sign_and_verify_with_body(self):
        body = b'{"amount": 100, "token": "USDC"}'
        headers = sign_request(
            method="POST",
            target_uri="https://api.sardis.sh/v2/payments",
            body=body,
            private_key=TEST_PRIVATE_KEY,
            address=TEST_ADDRESS,
        )

        assert "content-digest" in headers

        result = verify_request(
            method="POST",
            target_uri="https://api.sardis.sh/v2/payments",
            headers=headers,
            body=body,
        )
        assert result.valid is True
        assert result.signer_address.lower() == TEST_ADDRESS.lower()

    def test_tampered_body_fails(self):
        body = b'{"amount": 100}'
        headers = sign_request(
            method="POST",
            target_uri="https://api.sardis.sh/v2/payments",
            body=body,
            private_key=TEST_PRIVATE_KEY,
            address=TEST_ADDRESS,
        )

        # Tamper with body
        tampered_body = b'{"amount": 99999}'
        result = verify_request(
            method="POST",
            target_uri="https://api.sardis.sh/v2/payments",
            headers=headers,
            body=tampered_body,
        )
        assert result.valid is False
        assert "Content-Digest mismatch" in result.error

    def test_expired_signature_fails(self):
        # Sign with a timestamp far in the past
        with patch("sardis_protocol.erc8128.time") as mock_time:
            mock_time.time.return_value = 1600000000  # Way in the past
            headers = sign_request(
                method="GET",
                target_uri="https://api.sardis.sh/v2/wallets",
                private_key=TEST_PRIVATE_KEY,
                address=TEST_ADDRESS,
            )

        result = verify_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            headers=headers,
            max_age_seconds=300,
        )
        assert result.valid is False
        assert "expired" in result.error

    def test_missing_signature_input_fails(self):
        result = verify_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            headers={},
        )
        assert result.valid is False
        assert "Missing Signature-Input" in result.error

    def test_missing_signature_fails(self):
        headers = sign_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            private_key=TEST_PRIVATE_KEY,
            address=TEST_ADDRESS,
        )
        del headers["signature"]

        result = verify_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            headers=headers,
        )
        assert result.valid is False
        assert "Missing Signature" in result.error

    def test_wrong_address_fails(self):
        headers = sign_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            private_key=TEST_PRIVATE_KEY,
            address="0x0000000000000000000000000000000000000BAD",  # Wrong address
        )

        result = verify_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            headers=headers,
        )
        assert result.valid is False
        assert "mismatch" in result.error

    def test_base_chain_id(self):
        headers = sign_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            private_key=TEST_PRIVATE_KEY,
            address=TEST_ADDRESS,
            chain_id=8453,  # Base
        )

        result = verify_request(
            method="GET",
            target_uri="https://api.sardis.sh/v2/wallets",
            headers=headers,
        )
        assert result.valid is True
        assert result.chain_id == 8453


class TestERC8128SignatureInput:
    def test_chain_id_parsing(self):
        sig = ERC8128SignatureInput(
            keyid="erc8128:8453:0xABC",
            created=0,
            algorithm="erc8128-secp256k1",
            covered_components=[],
        )
        assert sig.chain_id == 8453
        assert sig.address == "0xABC"


class TestModuleExports:
    def test_sign_request_exported(self):
        from sardis_protocol import erc8128_sign_request
        assert erc8128_sign_request is not None

    def test_verify_request_exported(self):
        from sardis_protocol import erc8128_verify_request
        assert erc8128_verify_request is not None

    def test_build_keyid_exported(self):
        from sardis_protocol import build_keyid
        assert build_keyid is not None
