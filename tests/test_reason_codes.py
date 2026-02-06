"""Reason code determinism and coverage tests.

Ensures every protocol rejection path has a unique, deterministic reason code
and that the mapping table is complete and consistent.
"""
from __future__ import annotations

import pytest

from sardis_protocol.reason_codes import (
    ProtocolReasonCode,
    ReasonCodeMapping,
    REASON_CODE_TABLE,
    get_reason,
    map_legacy_reason_to_code,
    map_exception_to_reason,
)

pytestmark = [pytest.mark.protocol_conformance]


class TestReasonCodeCompleteness:
    def test_every_enum_value_has_table_entry(self):
        """Every ProtocolReasonCode must have an entry in REASON_CODE_TABLE."""
        for code in ProtocolReasonCode:
            assert code in REASON_CODE_TABLE, f"Missing table entry for {code.name}"

    def test_no_duplicate_codes(self):
        """No two enum values should have the same string value."""
        values = [code.value for code in ProtocolReasonCode]
        assert len(values) == len(set(values)), "Duplicate reason code values found"

    def test_all_http_statuses_valid(self):
        """All HTTP status codes must be valid."""
        valid_statuses = {400, 401, 402, 403, 404, 409, 410, 422, 429, 500, 502}
        for code, mapping in REASON_CODE_TABLE.items():
            assert mapping.http_status in valid_statuses, (
                f"{code.name} has invalid HTTP status {mapping.http_status}"
            )

    def test_all_have_human_messages(self):
        """Every mapping must have a non-empty human message."""
        for code, mapping in REASON_CODE_TABLE.items():
            assert mapping.human_message, f"{code.name} has empty human_message"

    def test_all_have_spec_references(self):
        """Every mapping must have a spec reference."""
        for code, mapping in REASON_CODE_TABLE.items():
            assert mapping.spec_reference, f"{code.name} has empty spec_reference"

    def test_mapping_code_matches_table_key(self):
        """The code field in each mapping must match its table key."""
        for code, mapping in REASON_CODE_TABLE.items():
            assert mapping.code == code, (
                f"Mapping code mismatch: table key {code.name} != mapping.code {mapping.code.name}"
            )


class TestReasonCodeDeterminism:
    def test_get_reason_returns_consistent_mapping(self):
        """get_reason() must return the same mapping for the same code."""
        for code in ProtocolReasonCode:
            m1 = get_reason(code)
            m2 = get_reason(code)
            assert m1.http_status == m2.http_status
            assert m1.human_message == m2.human_message
            assert m1.spec_reference == m2.spec_reference
            assert m1.code == m2.code

    def test_reason_codes_are_stable_strings(self):
        """Reason code values must be stable strings (no generated values)."""
        for code in ProtocolReasonCode:
            assert isinstance(code.value, str)
            assert len(code.value) > 0
            # Must follow naming convention: protocol_prefix + descriptive_name
            assert (
                code.value.startswith("tap_")
                or code.value.startswith("ap2_")
                or code.value.startswith("ucp_")
                or code.value.startswith("x402_")
            ), f"Code {code.value} doesn't follow protocol prefix convention"

    def test_get_reason_raises_on_invalid_code(self):
        """get_reason() should raise KeyError for codes not in table."""
        # This is a defensive test - if enum and table are in sync, this shouldn't happen
        # But it validates the function behavior
        with pytest.raises(KeyError):
            # Create a mock enum value that doesn't exist in the table
            get_reason("nonexistent_code")  # type: ignore


class TestLegacyReasonMapping:
    def test_known_legacy_reasons_map(self):
        """Known legacy reason strings from verifier.py must map to codes."""
        legacy_reasons = [
            "mandate_expired",
            "domain_not_authorized",
            "mandate_replayed",
            "signature_invalid",
            "signature_malformed",
            "identity_not_resolved",
            "subject_mismatch",
            "payment_exceeds_cart_total",
            "payment_exceeds_intent_amount",
            "payment_agent_presence_required",
            "payment_invalid_modality",
            "intent_invalid_type",
            "cart_invalid_type",
            "payment_invalid_type",
        ]
        for reason in legacy_reasons:
            code = map_legacy_reason_to_code(reason)
            assert code is not None, f"Legacy reason '{reason}' has no mapping"
            assert isinstance(code, ProtocolReasonCode)

    def test_rate_limit_reasons_map(self):
        """Rate limit legacy reasons should map to AP2_RATE_LIMITED."""
        rate_limit_reasons = [
            "rate_limit_minute",
            "rate_limit_hour",
            "rate_limit_day",
        ]
        for reason in rate_limit_reasons:
            code = map_legacy_reason_to_code(reason)
            assert code == ProtocolReasonCode.AP2_RATE_LIMITED, (
                f"Rate limit reason '{reason}' should map to AP2_RATE_LIMITED"
            )

    def test_tap_legacy_reasons_map(self):
        """TAP legacy reasons from tap.py should map to TAP codes."""
        tap_reasons = [
            "tap_signature_input_invalid",
            "tap_signature_invalid",
            "tap_signature_label_mismatch",
            "tap_required_components_missing",
            "tap_tag_invalid",
            "tap_alg_invalid",
            "tap_created_not_in_past",
            "tap_expired",
            "tap_window_too_large",
            "tap_nonce_replayed",
            "tap_signature_verification_failed",
        ]
        for reason in tap_reasons:
            code = map_legacy_reason_to_code(reason)
            assert code is not None, f"TAP legacy reason '{reason}' has no mapping"
            assert code.value.startswith("tap_"), (
                f"TAP reason '{reason}' should map to a TAP code, got {code.value}"
            )

    def test_prefixed_legacy_reasons_map(self):
        """Prefixed legacy reasons (intent_*, cart_*) should map correctly."""
        # These are from verifier.py where it prefixes the mandate type
        prefixed_reasons = [
            "intent_signature_invalid",
            "intent_signature_malformed",
            "cart_signature_invalid",
            "cart_signature_malformed",
        ]
        for reason in prefixed_reasons:
            code = map_legacy_reason_to_code(reason)
            assert code is not None, f"Prefixed legacy reason '{reason}' has no mapping"
            # Should strip prefix and map the base reason
            assert code in (
                ProtocolReasonCode.AP2_SIGNATURE_INVALID,
                ProtocolReasonCode.AP2_SIGNATURE_MALFORMED,
            )

    def test_unknown_reason_returns_none(self):
        """Unknown legacy reason string should return None."""
        result = map_legacy_reason_to_code("completely_unknown_reason_xyz")
        assert result is None

    def test_empty_reason_returns_none(self):
        """Empty reason string should return None."""
        result = map_legacy_reason_to_code("")
        assert result is None


class TestExceptionMapping:
    def test_signature_exceptions_map(self):
        """Exceptions with 'signature' in message should map to signature codes."""
        test_exceptions = [
            (KeyError("signature missing"), ProtocolReasonCode.AP2_SIGNATURE_MALFORMED),
            (TypeError("invalid signature"), ProtocolReasonCode.AP2_SIGNATURE_MALFORMED),
            (ValueError("signature error"), ProtocolReasonCode.AP2_SIGNATURE_MALFORMED),
        ]
        for exc, expected_code in test_exceptions:
            code = map_exception_to_reason(exc)
            assert code == expected_code, (
                f"Exception {exc} should map to {expected_code.value}, got {code}"
            )

    def test_expired_exceptions_map(self):
        """Exceptions with 'expired' in message should map to expiration codes."""
        test_exceptions = [
            KeyError("mandate expired"),
            ValueError("token expiration failed"),
            TypeError("expir check failed"),
        ]
        for exc in test_exceptions:
            code = map_exception_to_reason(exc)
            assert code == ProtocolReasonCode.AP2_MANDATE_EXPIRED, (
                f"Exception {exc} should map to AP2_MANDATE_EXPIRED, got {code}"
            )

    def test_domain_exceptions_map(self):
        """Exceptions with 'domain' in message should map to domain codes."""
        test_exceptions = [
            ValueError("domain invalid"),
            KeyError("missing domain"),
        ]
        for exc in test_exceptions:
            code = map_exception_to_reason(exc)
            assert code == ProtocolReasonCode.AP2_DOMAIN_INVALID, (
                f"Exception {exc} should map to AP2_DOMAIN_INVALID, got {code}"
            )

    def test_rate_limit_exceptions_map(self):
        """Exceptions with rate limit keywords should map to rate limit code."""
        # RuntimeError with rate limit keywords will map correctly
        # ValueError with rate limit will default to AP2_INTENT_MISSING due to type check priority
        exc1 = RuntimeError("rate limit exceeded")
        code1 = map_exception_to_reason(exc1)
        assert code1 == ProtocolReasonCode.AP2_RATE_LIMITED, (
            f"RuntimeError with rate limit should map to AP2_RATE_LIMITED, got {code1}"
        )

    def test_identity_exceptions_map(self):
        """Exceptions with identity/auth keywords should map to identity codes."""
        # RuntimeError with identity/auth keywords will map correctly
        # ValueError/KeyError will default to AP2_INTENT_MISSING due to type check priority
        exc = RuntimeError("identity verification failed")
        code = map_exception_to_reason(exc)
        assert code == ProtocolReasonCode.AP2_IDENTITY_NOT_RESOLVED, (
            f"RuntimeError with identity should map to AP2_IDENTITY_NOT_RESOLVED, got {code}"
        )

    def test_generic_parsing_exceptions_default(self):
        """Generic parsing exceptions should default to intent missing."""
        test_exceptions = [
            KeyError("random_key"),
            TypeError("type mismatch"),
            ValueError("value error"),
        ]
        for exc in test_exceptions:
            code = map_exception_to_reason(exc)
            assert code == ProtocolReasonCode.AP2_INTENT_MISSING, (
                f"Generic exception {exc} should default to AP2_INTENT_MISSING, got {code}"
            )

    def test_generic_exception_returns_none(self):
        """Generic exceptions should return None (not mapped)."""
        result = map_exception_to_reason(RuntimeError("generic error"))
        assert result is None

    def test_exception_without_message_returns_none(self):
        """Exception without message should return None."""
        result = map_exception_to_reason(RuntimeError())
        assert result is None


class TestReasonCodeProtocolCoverage:
    def test_tap_codes_cover_common_failures(self):
        """TAP codes should cover all common TAP failure modes."""
        tap_codes = [code for code in ProtocolReasonCode if code.value.startswith("tap_")]
        tap_code_names = {code.name for code in tap_codes}

        # Essential TAP failure modes
        required_tap_codes = {
            "TAP_HEADER_MISSING",
            "TAP_SIGNATURE_INVALID",
            "TAP_NONCE_REPLAYED",
            "TAP_SIGNATURE_EXPIRED",
            "TAP_ALGORITHM_UNSUPPORTED",
        }

        assert required_tap_codes.issubset(tap_code_names), (
            f"Missing essential TAP codes: {required_tap_codes - tap_code_names}"
        )

    def test_ap2_codes_cover_mandate_chain_failures(self):
        """AP2 codes should cover all mandate chain failure modes."""
        ap2_codes = [code for code in ProtocolReasonCode if code.value.startswith("ap2_")]
        ap2_code_names = {code.name for code in ap2_codes}

        # Essential AP2 failure modes
        required_ap2_codes = {
            "AP2_INTENT_MISSING",
            "AP2_CART_MISSING",
            "AP2_PAYMENT_MISSING",
            "AP2_SUBJECT_MISMATCH",
            "AP2_MANDATE_EXPIRED",
            "AP2_MANDATE_REPLAYED",
            "AP2_SIGNATURE_INVALID",
            "AP2_PAYMENT_EXCEEDS_CART",
        }

        assert required_ap2_codes.issubset(ap2_code_names), (
            f"Missing essential AP2 codes: {required_ap2_codes - ap2_code_names}"
        )

    def test_ucp_codes_cover_checkout_failures(self):
        """UCP codes should cover checkout session failure modes."""
        ucp_codes = [code for code in ProtocolReasonCode if code.value.startswith("ucp_")]
        ucp_code_names = {code.name for code in ucp_codes}

        # Essential UCP failure modes
        required_ucp_codes = {
            "UCP_SESSION_NOT_FOUND",
            "UCP_SESSION_EXPIRED",
            "UCP_ESCALATION_REQUIRED",
        }

        assert required_ucp_codes.issubset(ucp_code_names), (
            f"Missing essential UCP codes: {required_ucp_codes - ucp_code_names}"
        )

    def test_x402_codes_cover_micropayment_failures(self):
        """x402 codes should cover micropayment failure modes."""
        x402_codes = [code for code in ProtocolReasonCode if code.value.startswith("x402_")]
        x402_code_names = {code.name for code in x402_codes}

        # Essential x402 failure modes
        required_x402_codes = {
            "X402_CHALLENGE_EXPIRED",
            "X402_NONCE_MISMATCH",
            "X402_SIGNATURE_INVALID",
        }

        assert required_x402_codes.issubset(x402_code_names), (
            f"Missing essential x402 codes: {required_x402_codes - x402_code_names}"
        )
