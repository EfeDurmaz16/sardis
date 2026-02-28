"""Tests for TAP (Trusted Agent Protocol) validation."""
import time

import pytest

from sardis_protocol.tap import (
    TapSignatureInput,
    build_signature_base,
    parse_signature_header,
    parse_signature_input,
    validate_agentic_consumer_object,
    validate_agentic_payment_container,
    validate_tap_headers,
    validate_tap_version,
)


def _make_signature_input(
    *,
    label: str = "sig1",
    components: str = '"@authority" "@path"',
    created: int | None = None,
    expires: int | None = None,
    keyid: str = "agent-key-1",
    alg: str = "ed25519",
    nonce: str = "abc123",
    tag: str = "agent-browser-auth",
) -> str:
    now = int(time.time())
    created = created or (now - 10)
    expires = expires or (now + 300)
    return (
        f'{label}=({components});'
        f"created={created};"
        f'keyid="{keyid}";'
        f'alg="{alg}";'
        f"expires={expires};"
        f'nonce="{nonce}";'
        f'tag="{tag}"'
    )


def _make_signature_header(label: str = "sig1", sig: str = "dGVzdHNpZw==") -> str:
    return f"{label}=:{sig}:"


# --- validate_tap_version ---


class TestValidateTapVersion:
    def test_supported_version(self):
        ok, reason = validate_tap_version("1.0")
        assert ok is True
        assert reason is None

    def test_empty_version_defaults(self):
        ok, reason = validate_tap_version("")
        assert ok is True

    def test_unsupported_major(self):
        ok, reason = validate_tap_version("9.0")
        assert ok is False
        assert "unsupported" in reason

    def test_same_major_unknown_minor(self):
        ok, reason = validate_tap_version("1.5")
        assert ok is True


# --- parse_signature_input ---


class TestParseSignatureInput:
    def test_valid_parse(self):
        header = _make_signature_input()
        result = parse_signature_input(header)
        assert isinstance(result, TapSignatureInput)
        assert result.label == "sig1"
        assert result.alg == "ed25519"
        assert result.tag == "agent-browser-auth"
        assert "@authority" in result.components
        assert "@path" in result.components

    def test_missing_components(self):
        with pytest.raises(ValueError, match="missing_components"):
            parse_signature_input('sig1=();created=1;keyid="k";alg="ed25519";expires=2;nonce="n";tag="agent-browser-auth"')

    def test_missing_required_param(self):
        # Missing nonce
        with pytest.raises(ValueError, match="missing_nonce"):
            parse_signature_input('sig1=("@authority" "@path");created=1;keyid="k";alg="ed25519";expires=2;tag="agent-browser-auth"')

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="invalid_signature_input_format"):
            parse_signature_input("garbage")


# --- parse_signature_header ---


class TestParseSignatureHeader:
    def test_valid_parse(self):
        label, sig = parse_signature_header("sig1=:dGVzdA==:")
        assert label == "sig1"
        assert sig == "dGVzdA=="

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="invalid_signature_header_format"):
            parse_signature_header("not-valid")


# --- build_signature_base ---


class TestBuildSignatureBase:
    def test_builds_correct_base(self):
        si = parse_signature_input(_make_signature_input())
        base = build_signature_base("api.sardis.sh", "/v2/pay", si)
        assert "@authority: api.sardis.sh" in base
        assert "@path: /v2/pay" in base
        assert "@signature-params" in base


# --- validate_tap_headers ---


class TestValidateTapHeaders:
    def test_valid_headers(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 300)
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is True

    def test_label_mismatch(self):
        now = int(time.time())
        si_header = _make_signature_input(label="sig1", created=now - 10, expires=now + 300)
        sig_header = _make_signature_header(label="sig2")

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is False
        assert "label_mismatch" in result.reason

    def test_expired(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 600, expires=now - 1)
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is False
        assert "expired" in result.reason

    def test_created_in_future(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now + 10, expires=now + 300)
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is False
        assert "not_in_past" in result.reason

    def test_window_too_large(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 9999)
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is False
        assert "window_too_large" in result.reason

    def test_invalid_tag(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 300, tag="bad-tag")
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is False
        assert "tag_invalid" in result.reason

    def test_invalid_alg(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 300, alg="rsa-sha512")
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
        )
        assert result.accepted is False
        assert "alg_invalid" in result.reason

    def test_nonce_replay_detection(self):
        now = int(time.time())
        nonce_set: set[str] = set()
        si_header = _make_signature_input(created=now - 10, expires=now + 300, nonce="unique1")
        sig_header = _make_signature_header()

        result1 = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
            nonce_cache=nonce_set,
        )
        assert result1.accepted is True

        result2 = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
            nonce_cache=nonce_set,
        )
        assert result2.accepted is False
        assert "replayed" in result2.reason

    def test_signature_verification_callback(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 300)
        sig_header = _make_signature_header()

        def verify_fn(base, sig_b64, keyid, alg):
            return True

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
            verify_signature_fn=verify_fn,
        )
        assert result.accepted is True

    def test_signature_verification_failure(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 300)
        sig_header = _make_signature_header()

        def verify_fn(base, sig_b64, keyid, alg):
            return False

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
            verify_signature_fn=verify_fn,
        )
        assert result.accepted is False
        assert "verification_failed" in result.reason

    def test_unsupported_tap_version(self):
        now = int(time.time())
        si_header = _make_signature_input(created=now - 10, expires=now + 300)
        sig_header = _make_signature_header()

        result = validate_tap_headers(
            signature_input_header=si_header,
            signature_header=sig_header,
            authority="api.sardis.sh",
            path="/v2/pay",
            now=now,
            tap_version="9.0",
        )
        assert result.accepted is False
        assert "unsupported" in result.reason


# --- validate_agentic_consumer_object ---


class TestValidateAgenticConsumerObject:
    def _valid_obj(self) -> dict:
        return {
            "nonce": "abc123",
            "idToken": "eyJ...",
            "contextualData": {"task": "buy cloud"},
            "kid": "agent-key-1",
            "alg": "ed25519",
            "signature": "c2lnbmF0dXJl",
        }

    def test_valid_object(self):
        result = validate_agentic_consumer_object(self._valid_obj())
        assert result.accepted is True

    def test_missing_field(self):
        obj = self._valid_obj()
        del obj["idToken"]
        result = validate_agentic_consumer_object(obj)
        assert result.accepted is False
        assert "missing_idToken" in result.reason

    def test_invalid_alg(self):
        obj = self._valid_obj()
        obj["alg"] = "none"
        result = validate_agentic_consumer_object(obj)
        assert result.accepted is False
        assert "alg_invalid" in result.reason

    def test_nonce_mismatch(self):
        obj = self._valid_obj()
        result = validate_agentic_consumer_object(obj, header_nonce="different")
        assert result.accepted is False
        assert "nonce_mismatch" in result.reason

    def test_signature_verification(self):
        obj = self._valid_obj()
        result = validate_agentic_consumer_object(
            obj,
            verify_signature_fn=lambda base, sig, kid, alg: True,
        )
        assert result.accepted is True

    def test_signature_verification_failure(self):
        obj = self._valid_obj()
        result = validate_agentic_consumer_object(
            obj,
            verify_signature_fn=lambda base, sig, kid, alg: False,
        )
        assert result.accepted is False
        assert "signature_invalid" in result.reason


# --- validate_agentic_payment_container ---


class TestValidateAgenticPaymentContainer:
    def _valid_obj(self) -> dict:
        return {
            "nonce": "abc123",
            "kid": "agent-key-1",
            "alg": "ed25519",
            "signature": "c2lnbmF0dXJl",
            "amount": "1000000",
        }

    def test_valid_container(self):
        result = validate_agentic_payment_container(self._valid_obj())
        assert result.accepted is True

    def test_missing_field(self):
        obj = self._valid_obj()
        del obj["kid"]
        result = validate_agentic_payment_container(obj)
        assert result.accepted is False
        assert "missing_kid" in result.reason

    def test_nonce_mismatch_with_require(self):
        obj = self._valid_obj()
        result = validate_agentic_payment_container(
            obj,
            header_nonce="different",
            require_nonce_match=True,
        )
        assert result.accepted is False

    def test_nonce_mismatch_without_require(self):
        obj = self._valid_obj()
        result = validate_agentic_payment_container(
            obj,
            header_nonce="different",
            require_nonce_match=False,
        )
        assert result.accepted is True
