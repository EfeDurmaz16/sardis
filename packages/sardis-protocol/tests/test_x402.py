"""Tests for x402 HTTP 402 Payment Required protocol."""
import time

import pytest

from sardis_protocol.x402 import (
    X402Challenge,
    X402HeaderBuilder,
    X402PaymentPayload,
    generate_challenge,
    parse_challenge_header,
    serialize_challenge_header,
    validate_x402_version,
    verify_payment_payload,
)


def _make_challenge(**overrides) -> X402Challenge:
    defaults = {
        "payment_id": "x402_test123",
        "resource_uri": "/api/premium/data",
        "amount": "1000000",
        "currency": "USDC",
        "payee_address": "0x1234567890abcdef1234567890abcdef12345678",
        "network": "base",
        "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "expires_at": int(time.time()) + 300,
        "nonce": "testnonce123",
    }
    defaults.update(overrides)
    return X402Challenge(**defaults)


def _make_payload(challenge: X402Challenge, **overrides) -> X402PaymentPayload:
    defaults = {
        "payment_id": challenge.payment_id,
        "payer_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        "amount": challenge.amount,
        "nonce": challenge.nonce,
        "signature": "0xdeadbeef",
    }
    defaults.update(overrides)
    return X402PaymentPayload(**defaults)


# --- generate_challenge ---


class TestGenerateChallenge:
    def test_generates_valid_challenge(self):
        resp = generate_challenge(
            resource_uri="/api/data",
            amount="500000",
            currency="USDC",
            payee_address="0x1234",
            network="base",
        )
        assert resp.http_status == 402
        assert resp.challenge.resource_uri == "/api/data"
        assert resp.challenge.amount == "500000"
        assert resp.challenge.payment_id.startswith("x402_")
        assert resp.challenge.expires_at > int(time.time())
        assert len(resp.challenge.nonce) > 0

    def test_custom_ttl(self):
        now = int(time.time())
        resp = generate_challenge(
            resource_uri="/api/data",
            amount="100",
            currency="USDC",
            payee_address="0x1234",
            ttl_seconds=60,
        )
        assert resp.challenge.expires_at <= now + 61
        assert resp.challenge.expires_at >= now + 59

    def test_header_value_populated(self):
        resp = generate_challenge(
            resource_uri="/api/data",
            amount="100",
            currency="USDC",
            payee_address="0x1234",
        )
        assert len(resp.header_value) > 0


# --- serialize / parse challenge header ---


class TestChallengeHeaderSerialization:
    def test_roundtrip(self):
        original = _make_challenge()
        serialized = serialize_challenge_header(original)
        parsed = parse_challenge_header(serialized)

        assert parsed.payment_id == original.payment_id
        assert parsed.resource_uri == original.resource_uri
        assert parsed.amount == original.amount
        assert parsed.currency == original.currency
        assert parsed.payee_address == original.payee_address
        assert parsed.network == original.network
        assert parsed.nonce == original.nonce
        assert parsed.expires_at == original.expires_at

    def test_invalid_header_raises(self):
        with pytest.raises(ValueError, match="invalid_challenge_header"):
            parse_challenge_header("not-base64-json!")


# --- verify_payment_payload ---


class TestVerifyPaymentPayload:
    def test_valid_payload(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge)
        result = verify_payment_payload(payload, challenge)
        assert result.accepted is True
        assert result.payload is payload

    def test_expired_challenge(self):
        challenge = _make_challenge(expires_at=int(time.time()) - 10)
        payload = _make_payload(challenge)
        result = verify_payment_payload(payload, challenge)
        assert result.accepted is False
        assert "expired" in result.reason

    def test_nonce_mismatch(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge, nonce="wrong_nonce")
        result = verify_payment_payload(payload, challenge)
        assert result.accepted is False
        assert "nonce_mismatch" in result.reason

    def test_amount_mismatch(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge, amount="999")
        result = verify_payment_payload(payload, challenge)
        assert result.accepted is False
        assert "amount_mismatch" in result.reason

    def test_payment_id_mismatch(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge, payment_id="x402_wrong")
        result = verify_payment_payload(payload, challenge)
        assert result.accepted is False
        assert "payment_id_mismatch" in result.reason

    def test_signature_verification_pass(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge)

        def verify_fn(canonical, sig, payer):
            return True

        result = verify_payment_payload(
            payload, challenge, verify_signature_fn=verify_fn,
        )
        assert result.accepted is True

    def test_signature_verification_fail(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge)

        def verify_fn(canonical, sig, payer):
            return False

        result = verify_payment_payload(
            payload, challenge, verify_signature_fn=verify_fn,
        )
        assert result.accepted is False
        assert "signature_invalid" in result.reason

    def test_signature_verification_exception(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge)

        def verify_fn(canonical, sig, payer):
            raise RuntimeError("crypto error")

        result = verify_payment_payload(
            payload, challenge, verify_signature_fn=verify_fn,
        )
        assert result.accepted is False
        assert "signature_invalid" in result.reason

    def test_explicit_now_parameter(self):
        future = int(time.time()) + 600
        challenge = _make_challenge(expires_at=future + 100)
        payload = _make_payload(challenge)
        result = verify_payment_payload(payload, challenge, now=future)
        assert result.accepted is True


# --- validate_x402_version ---


class TestValidateX402Version:
    def test_supported_v1(self):
        ok, reason = validate_x402_version("1.0")
        assert ok is True

    def test_supported_v2(self):
        ok, reason = validate_x402_version("2.0")
        assert ok is True

    def test_empty_defaults(self):
        ok, reason = validate_x402_version("")
        assert ok is True

    def test_unsupported(self):
        ok, reason = validate_x402_version("3.0")
        assert ok is False
        assert "unsupported" in reason


# --- X402HeaderBuilder ---


class TestX402HeaderBuilder:
    def test_payment_required_header(self):
        challenge = _make_challenge()
        headers = X402HeaderBuilder.build_payment_required_header(challenge)
        assert "PaymentRequired" in headers
        assert headers["Content-Type"] == "application/json"

    def test_payment_signature_header_roundtrip(self):
        challenge = _make_challenge()
        payload = _make_payload(challenge)
        headers = X402HeaderBuilder.build_payment_signature_header(payload)
        assert "PAYMENT-SIGNATURE" in headers

        parsed = X402HeaderBuilder.parse_payment_signature_header(
            headers["PAYMENT-SIGNATURE"]
        )
        assert parsed.payment_id == payload.payment_id
        assert parsed.payer_address == payload.payer_address
        assert parsed.amount == payload.amount
        assert parsed.nonce == payload.nonce

    def test_payment_response_header(self):
        headers = X402HeaderBuilder.build_payment_response_header(
            {"tx_hash": "0xabc", "status": "settled"}
        )
        assert "PAYMENT-RESPONSE" in headers

    def test_parse_invalid_signature_header(self):
        with pytest.raises(ValueError, match="invalid_payment_signature_header"):
            X402HeaderBuilder.parse_payment_signature_header("not-valid!")
