"""TAP message signature and linked object validation tests."""
from __future__ import annotations

import pytest

from sardis_protocol.tap import (
    build_object_signature_base,
    build_signature_base,
    parse_signature_header,
    parse_signature_input,
    validate_agentic_consumer_object,
    validate_agentic_payment_container,
    validate_tap_headers,
)

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.tap]


def _valid_signature_input(*, now: int, nonce: str = "nonce-1", tag: str = "agent-browser-auth") -> str:
    return (
        'sig2=("@authority" "@path");'
        f"created={now - 120};"
        'keyid="kid_123";'
        'alg="Ed25519";'
        f"expires={now + 120};"
        f'nonce="{nonce}";'
        f'tag="{tag}"'
    )


def _valid_signature() -> str:
    return "sig2=:dGVzdHNpZw==:"


def test_parse_signature_input_and_signature_header():
    now = 1_735_690_000
    parsed = parse_signature_input(_valid_signature_input(now=now))
    label, signature_b64 = parse_signature_header(_valid_signature())

    assert parsed.label == "sig2"
    assert parsed.components == ["@authority", "@path"]
    assert parsed.keyid == "kid_123"
    assert label == "sig2"
    assert signature_b64 == "dGVzdHNpZw=="


def test_validate_tap_headers_success_and_signature_base():
    now = 1_735_690_000
    nonce_cache: set[str] = set()
    result = validate_tap_headers(
        signature_input_header=_valid_signature_input(now=now),
        signature_header=_valid_signature(),
        authority="www.example.com",
        path="/checkout",
        now=now,
        nonce_cache=nonce_cache,
    )

    assert result.accepted is True
    assert result.reason is None
    assert result.signature_input is not None
    assert result.signature_base is not None
    assert "@authority: www.example.com" in result.signature_base
    assert "@path: /checkout" in result.signature_base
    assert result.signature_input.nonce in nonce_cache


def test_validate_tap_headers_rejects_replayed_nonce():
    now = 1_735_690_000
    nonce_cache = {"nonce-dup"}
    result = validate_tap_headers(
        signature_input_header=_valid_signature_input(now=now, nonce="nonce-dup"),
        signature_header=_valid_signature(),
        authority="www.example.com",
        path="/checkout",
        now=now,
        nonce_cache=nonce_cache,
    )
    assert result.accepted is False
    assert result.reason == "tap_nonce_replayed"


def test_validate_tap_headers_rejects_invalid_tag_and_window():
    now = 1_735_690_000
    bad_tag = validate_tap_headers(
        signature_input_header=_valid_signature_input(now=now, tag="agent-unknown-auth"),
        signature_header=_valid_signature(),
        authority="www.example.com",
        path="/checkout",
        now=now,
    )
    assert bad_tag.accepted is False
    assert bad_tag.reason == "tap_tag_invalid"

    bad_alg_input = (
        'sig2=("@authority" "@path");'
        f"created={now - 30};"
        'keyid="kid_123";'
        'alg="PS256";'
        f"expires={now + 120};"
        'nonce="nonce-bad-alg";'
        'tag="agent-browser-auth"'
    )
    bad_alg = validate_tap_headers(
        signature_input_header=bad_alg_input,
        signature_header=_valid_signature(),
        authority="www.example.com",
        path="/checkout",
        now=now,
    )
    assert bad_alg.accepted is False
    assert bad_alg.reason == "tap_alg_invalid"

    too_long_window = (
        'sig2=("@authority" "@path");'
        f"created={now - 30};"
        'keyid="kid_123";'
        'alg="Ed25519";'
        f"expires={now + 600};"
        'nonce="nonce-long";'
        'tag="agent-browser-auth"'
    )
    bad_window = validate_tap_headers(
        signature_input_header=too_long_window,
        signature_header=_valid_signature(),
        authority="www.example.com",
        path="/checkout",
        now=now,
    )
    assert bad_window.accepted is False
    assert bad_window.reason == "tap_window_too_large"


def test_build_signature_base_matches_tap_shape():
    now = 1_735_690_000
    parsed = parse_signature_input(_valid_signature_input(now=now))
    signature_base = build_signature_base("example.com", "/example-product", parsed)
    assert signature_base.startswith("@authority: example.com\n@path: /example-product\n")
    assert '"@signature-params": sig2=(' in signature_base
    assert 'keyid="kid_123"' in signature_base


def test_agentic_consumer_object_validation():
    valid_obj = {
        "nonce": "nonce-1",
        "idToken": {"iss": "issuer"},
        "contextualData": {"countryCode": "US"},
        "kid": "kid_123",
        "alg": "PS256",
        "signature": "sig",
    }
    ok = validate_agentic_consumer_object(valid_obj, header_nonce="nonce-1")
    assert ok.accepted is True

    missing = validate_agentic_consumer_object(
        {k: v for k, v in valid_obj.items() if k != "idToken"},
        header_nonce="nonce-1",
    )
    assert missing.accepted is False
    assert missing.reason == "agentic_consumer_missing_idToken"

    mismatch = validate_agentic_consumer_object(valid_obj, header_nonce="different")
    assert mismatch.accepted is False
    assert mismatch.reason == "agentic_consumer_nonce_mismatch"

    bad_alg_obj = dict(valid_obj)
    bad_alg_obj["alg"] = "none"
    bad_alg = validate_agentic_consumer_object(bad_alg_obj, header_nonce="nonce-1")
    assert bad_alg.accepted is False
    assert bad_alg.reason == "agentic_consumer_alg_invalid"

    signed_ok = validate_agentic_consumer_object(
        valid_obj,
        header_nonce="nonce-1",
        verify_signature_fn=lambda *_args: True,
    )
    assert signed_ok.accepted is True

    signed_bad = validate_agentic_consumer_object(
        valid_obj,
        header_nonce="nonce-1",
        verify_signature_fn=lambda *_args: False,
    )
    assert signed_bad.accepted is False
    assert signed_bad.reason == "agentic_consumer_signature_invalid"


def test_agentic_payment_container_validation():
    valid_obj = {
        "nonce": "nonce-1",
        "kid": "kid_123",
        "alg": "PS256",
        "signature": "sig",
    }
    ok = validate_agentic_payment_container(valid_obj, header_nonce="nonce-1")
    assert ok.accepted is True

    missing_sig = validate_agentic_payment_container(
        {k: v for k, v in valid_obj.items() if k != "signature"},
        header_nonce="nonce-1",
    )
    assert missing_sig.accepted is False
    assert missing_sig.reason == "agentic_payment_missing_signature"

    mismatch = validate_agentic_payment_container(valid_obj, header_nonce="different")
    assert mismatch.accepted is False
    assert mismatch.reason == "agentic_payment_nonce_mismatch"

    bad_alg_obj = dict(valid_obj)
    bad_alg_obj["alg"] = "none"
    bad_alg = validate_agentic_payment_container(bad_alg_obj, header_nonce="nonce-1")
    assert bad_alg.accepted is False
    assert bad_alg.reason == "agentic_payment_alg_invalid"

    signed_ok = validate_agentic_payment_container(
        valid_obj,
        header_nonce="nonce-1",
        verify_signature_fn=lambda *_args: True,
    )
    assert signed_ok.accepted is True

    signed_bad = validate_agentic_payment_container(
        valid_obj,
        header_nonce="nonce-1",
        verify_signature_fn=lambda *_args: False,
    )
    assert signed_bad.accepted is False
    assert signed_bad.reason == "agentic_payment_signature_invalid"


def test_build_object_signature_base_excludes_signature_field():
    obj = {
        "nonce": "n1",
        "kid": "kid_1",
        "alg": "PS256",
        "payload": {"a": 1},
        "signature": "signed",
    }
    base = build_object_signature_base(obj)
    assert '"signature"' not in base
    assert '"nonce":"n1"' in base
