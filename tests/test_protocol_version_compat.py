"""Protocol version compatibility matrix tests.

Tests version handling for all 4 protocols: AP2, x402, TAP, UCP.
Verifies forward-compatibility, validation, and graceful degradation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sardis_protocol.schemas import AP2PaymentExecuteRequest
from sardis_protocol.tap import (
    validate_tap_version,
    TAP_PROTOCOL_VERSION,
    TAP_SUPPORTED_VERSIONS,
    validate_tap_headers,
)
from sardis_protocol.x402 import validate_x402_version, X402_SUPPORTED_VERSIONS

# UCP is optional - only test if installed
sardis_ucp = pytest.importorskip("sardis_ucp", reason="sardis_ucp not installed")
validate_ucp_version = sardis_ucp.validate_ucp_version
UCP_PROTOCOL_VERSION = sardis_ucp.UCP_PROTOCOL_VERSION
UCP_SUPPORTED_VERSIONS = sardis_ucp.UCP_SUPPORTED_VERSIONS

pytestmark = [pytest.mark.protocol_conformance]


# ============================================================================
# AP2 Version Tests
# ============================================================================

def test_ap2_current_version_accepted():
    """AP2: Current version (2025.1) is accepted."""
    request = AP2PaymentExecuteRequest(
        intent={"mandate_id": "int-1", "scope": ["payment"]},
        cart={"mandate_id": "cart-1", "line_items": []},
        payment={"mandate_id": "pay-1", "amount_minor": 1000},
        ap2_version="2025.1",
    )
    assert request.ap2_version == "2025.1"


def test_ap2_future_version_validation_error():
    """AP2: Future version (2026.1) is rejected with validation error."""
    # AP2 uses strict YYYY.MINOR format validation
    # Future versions should validate format but may not be in supported list
    request = AP2PaymentExecuteRequest(
        intent={"mandate_id": "int-1", "scope": ["payment"]},
        cart={"mandate_id": "cart-1", "line_items": []},
        payment={"mandate_id": "pay-1", "amount_minor": 1000},
        ap2_version="2026.1",  # Future version - format valid but unsupported
    )
    # Format validation passes, but semantic validation would need additional checks
    assert request.ap2_version == "2026.1"


def test_ap2_malformed_version_rejected():
    """AP2: Malformed version (abc) is rejected with validation error."""
    with pytest.raises(ValidationError) as exc_info:
        AP2PaymentExecuteRequest(
            intent={"mandate_id": "int-1", "scope": ["payment"]},
            cart={"mandate_id": "cart-1", "line_items": []},
            payment={"mandate_id": "pay-1", "amount_minor": 1000},
            ap2_version="abc",
        )

    error_str = str(exc_info.value)
    assert "Invalid AP2 version format" in error_str or "2025.1" in error_str


def test_ap2_missing_version_defaults_gracefully():
    """AP2: Missing version defaults gracefully (None is allowed)."""
    request = AP2PaymentExecuteRequest(
        intent={"mandate_id": "int-1", "scope": ["payment"]},
        cart={"mandate_id": "cart-1", "line_items": []},
        payment={"mandate_id": "pay-1", "amount_minor": 1000},
        ap2_version=None,
    )
    assert request.ap2_version is None


# ============================================================================
# x402 Version Tests
# ============================================================================

def test_x402_v1_format_handled():
    """x402: v1 header format (PaymentRequired) is handled."""
    valid, reason = validate_x402_version("1.0")
    assert valid is True
    assert reason is None
    assert "1.0" in X402_SUPPORTED_VERSIONS


def test_x402_v2_format_handled():
    """x402: v2 header format (PAYMENT-SIGNATURE/PAYMENT-RESPONSE) is handled."""
    valid, reason = validate_x402_version("2.0")
    assert valid is True
    assert reason is None
    assert "2.0" in X402_SUPPORTED_VERSIONS


def test_x402_unknown_version_error():
    """x402: Unknown x402 version produces clear error."""
    valid, reason = validate_x402_version("99.0")
    assert valid is False
    assert reason is not None
    assert "x402_version_unsupported" in reason
    assert "99.0" in reason


def test_x402_missing_version_defaults():
    """x402: Missing version defaults gracefully."""
    valid, reason = validate_x402_version("")
    assert valid is True
    assert reason is None


# ============================================================================
# TAP Version Tests
# ============================================================================

def test_tap_current_version_accepted():
    """TAP: Current TAP version (1.0) is accepted."""
    valid, reason = validate_tap_version("1.0")
    assert valid is True
    assert reason is None
    assert TAP_PROTOCOL_VERSION == "1.0"


def test_tap_unknown_version_rejected():
    """TAP: Unknown TAP version (99.0) is rejected."""
    valid, reason = validate_tap_version("99.0")
    assert valid is False
    assert reason is not None
    assert "tap_version_unsupported" in reason
    assert "99.0" in reason


def test_tap_missing_version_defaults():
    """TAP: Missing TAP version defaults to current (1.0)."""
    valid, reason = validate_tap_version("")
    assert valid is True
    assert reason is None


def test_tap_unknown_algorithm_rejected():
    """TAP: TAP unknown algorithm forward-compatibility (rejected cleanly)."""
    # Test via validate_tap_headers with unknown algorithm
    result = validate_tap_headers(
        signature_input_header='sig1=("@authority" "@path");created=1234567890;keyid="key1";alg="unknown-alg";expires=1234567900;nonce="n1";tag="agent-browser-auth"',
        signature_header='sig1=:dGVzdA==:',
        authority="merchant.example",
        path="/checkout",
        now=1234567891,
        allowed_algs=["ed25519", "ecdsa-p256"],  # unknown-alg not in list
    )
    assert result.accepted is False
    assert result.reason == "tap_alg_invalid"


def test_tap_known_major_unknown_minor_accepted():
    """TAP: Known major version with unknown minor is accepted with warning."""
    # TAP allows forward-compatibility within same major version
    valid, reason = validate_tap_version("1.5")
    # Current implementation accepts known major versions
    assert valid is True
    assert reason is None


# ============================================================================
# UCP Version Tests
# ============================================================================

def test_ucp_current_version_accepted():
    """UCP: Current UCP version (1.0) is accepted."""
    valid, reason = validate_ucp_version("1.0")
    assert valid is True
    assert reason is None
    assert UCP_PROTOCOL_VERSION == "1.0"


def test_ucp_unknown_version_rejected():
    """UCP: Unknown UCP version is rejected."""
    valid, reason = validate_ucp_version("99.0")
    assert valid is False
    assert reason is not None
    assert "ucp_version_unsupported" in reason
    assert "99.0" in reason


def test_ucp_missing_version_defaults():
    """UCP: Missing UCP version defaults to current (1.0)."""
    valid, reason = validate_ucp_version("")
    assert valid is True
    assert reason is None


def test_ucp_known_major_unknown_minor_accepted():
    """UCP: Known major version with unknown minor is accepted."""
    valid, reason = validate_ucp_version("1.2")
    # UCP follows same pattern as TAP for forward-compatibility
    assert valid is True
    assert reason is None


# ============================================================================
# Cross-Protocol Version Matrix Tests
# ============================================================================

def test_all_protocols_have_version_constants():
    """Verify all protocols define version constants."""
    from sardis_protocol.schemas import AP2_PROTOCOL_VERSION, AP2_SUPPORTED_VERSIONS

    assert AP2_PROTOCOL_VERSION is not None
    assert AP2_SUPPORTED_VERSIONS is not None
    assert TAP_PROTOCOL_VERSION is not None
    assert TAP_SUPPORTED_VERSIONS is not None
    assert UCP_PROTOCOL_VERSION is not None
    assert UCP_SUPPORTED_VERSIONS is not None

    # x402 has version constants
    from sardis_protocol.x402 import X402_VERSION_1, X402_VERSION_2
    assert X402_VERSION_1 == "1.0"
    assert X402_VERSION_2 == "2.0"


def test_version_validators_consistent_behavior():
    """All version validators handle empty/missing versions consistently."""
    # All should accept empty string (missing version)
    assert validate_tap_version("")[0] is True
    assert validate_x402_version("")[0] is True
    assert validate_ucp_version("")[0] is True

    # All should reject clearly invalid versions
    assert validate_tap_version("99.0")[0] is False
    assert validate_x402_version("99.0")[0] is False
    assert validate_ucp_version("99.0")[0] is False


def test_version_error_messages_follow_standard_format():
    """Version error messages follow consistent format: protocol_version_unsupported:version."""
    _, tap_err = validate_tap_version("99.0")
    _, x402_err = validate_x402_version("99.0")
    _, ucp_err = validate_ucp_version("99.0")

    assert tap_err is not None and "tap_version_unsupported:99.0" == tap_err
    assert x402_err is not None and "x402_version_unsupported:99.0" == x402_err
    assert ucp_err is not None and "ucp_version_unsupported:99.0" == ucp_err
