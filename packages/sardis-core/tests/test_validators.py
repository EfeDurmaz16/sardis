"""
Comprehensive tests for sardis_v2_core.validators module.

Tests cover:
- Core validation functions (validate_not_none, validate_string, etc.)
- Domain-specific validators (wallet_id, eth_address, etc.)
- Amount and token validation
- URL, email, domain validation
- Timestamp validation
- Hex string and cryptographic key validation
- Composite validators
- Error cases and edge cases
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime, timezone
import time

# Import the validators module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sardis_v2_core.validators import (
    # Core validators
    validate_not_none,
    validate_not_empty,
    validate_string,
    validate_integer,
    validate_decimal,
    # Domain validators
    validate_wallet_id,
    validate_agent_id,
    validate_transaction_id,
    validate_hold_id,
    validate_mandate_id,
    validate_eth_address,
    validate_solana_address,
    validate_chain_address,
    validate_tx_hash,
    validate_amount,
    validate_token,
    validate_chain,
    validate_url,
    validate_email,
    validate_domain,
    validate_timestamp,
    validate_hex_string,
    validate_public_key,
    validate_signature,
    # Composite validators
    validate_payment_request,
    validate_hold_request,
    # Utilities
    ValidationResult,
    validate_inputs,
    # Patterns
    ETH_ADDRESS_PATTERN,
    WALLET_ID_PATTERN,
    AGENT_ID_PATTERN,
)
from sardis_v2_core.exceptions import SardisValidationError


class TestValidateNotNone:
    """Tests for validate_not_none function."""

    def test_valid_value(self):
        """Should pass for non-None values."""
        validate_not_none("test")
        validate_not_none(0)
        validate_not_none(False)
        validate_not_none("")
        validate_not_none([])

    def test_none_raises_error(self):
        """Should raise error for None values."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_not_none(None)
        assert "is required" in str(exc_info.value)

    def test_custom_field_name(self):
        """Should use custom field name in error message."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_not_none(None, field_name="wallet_id")
        assert "wallet_id" in str(exc_info.value)


class TestValidateNotEmpty:
    """Tests for validate_not_empty function."""

    def test_valid_string(self):
        """Should pass for non-empty strings."""
        validate_not_empty("test")

    def test_valid_list(self):
        """Should pass for non-empty lists."""
        validate_not_empty([1, 2, 3])

    def test_empty_string_raises_error(self):
        """Should raise error for empty strings."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_not_empty("")
        assert "cannot be empty" in str(exc_info.value)

    def test_empty_list_raises_error(self):
        """Should raise error for empty lists."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_not_empty([])
        assert "cannot be empty" in str(exc_info.value)

    def test_none_raises_error(self):
        """Should raise error for None values."""
        with pytest.raises(SardisValidationError):
            validate_not_empty(None)


class TestValidateString:
    """Tests for validate_string function."""

    def test_valid_string(self):
        """Should return trimmed string."""
        result = validate_string("  test  ")
        assert result == "test"

    def test_none_raises_error(self):
        """Should raise error for None."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_string(None)
        assert "is required" in str(exc_info.value)

    def test_non_string_raises_error(self):
        """Should raise error for non-string types."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_string(123)
        assert "must be a string" in str(exc_info.value)

    def test_min_length_validation(self):
        """Should validate minimum length."""
        validate_string("test", min_length=4)

        with pytest.raises(SardisValidationError) as exc_info:
            validate_string("ab", min_length=3)
        assert "at least 3 characters" in str(exc_info.value)

    def test_max_length_validation(self):
        """Should validate maximum length."""
        validate_string("test", max_length=10)

        with pytest.raises(SardisValidationError) as exc_info:
            validate_string("this is too long", max_length=5)
        assert "at most 5 characters" in str(exc_info.value)

    def test_pattern_validation(self):
        """Should validate against regex pattern."""
        import re
        pattern = re.compile(r"^[a-z]+$")

        validate_string("test", pattern=pattern)

        with pytest.raises(SardisValidationError) as exc_info:
            validate_string("Test123", pattern=pattern)
        assert "invalid format" in str(exc_info.value)

    def test_allowed_values_validation(self):
        """Should validate against allowed values."""
        validate_string("active", allowed_values=["active", "inactive"])

        with pytest.raises(SardisValidationError) as exc_info:
            validate_string("unknown", allowed_values=["active", "inactive"])
        assert "must be one of" in str(exc_info.value)


class TestValidateInteger:
    """Tests for validate_integer function."""

    def test_valid_integer(self):
        """Should return integer value."""
        assert validate_integer(42) == 42
        assert validate_integer("42") == 42
        assert validate_integer(42.0) == 42

    def test_none_raises_error(self):
        """Should raise error for None."""
        with pytest.raises(SardisValidationError):
            validate_integer(None)

    def test_invalid_value_raises_error(self):
        """Should raise error for non-numeric strings."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_integer("abc")
        assert "must be an integer" in str(exc_info.value)

    def test_min_value_validation(self):
        """Should validate minimum value."""
        assert validate_integer(10, min_value=5) == 10

        with pytest.raises(SardisValidationError) as exc_info:
            validate_integer(3, min_value=5)
        assert "at least 5" in str(exc_info.value)

    def test_max_value_validation(self):
        """Should validate maximum value."""
        assert validate_integer(10, max_value=15) == 10

        with pytest.raises(SardisValidationError) as exc_info:
            validate_integer(20, max_value=15)
        assert "at most 15" in str(exc_info.value)


class TestValidateDecimal:
    """Tests for validate_decimal function."""

    def test_valid_decimal(self):
        """Should return Decimal value."""
        result = validate_decimal("123.45")
        assert result == Decimal("123.45")

        result = validate_decimal(123.45)
        assert result == Decimal("123.45")

        result = validate_decimal(Decimal("100"))
        assert result == Decimal("100")

    def test_none_raises_error(self):
        """Should raise error for None."""
        with pytest.raises(SardisValidationError):
            validate_decimal(None)

    def test_invalid_value_raises_error(self):
        """Should raise error for invalid decimals."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_decimal("not_a_number")
        assert "valid decimal number" in str(exc_info.value)

    def test_nan_raises_error(self):
        """Should raise error for NaN."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_decimal(float("nan"))
        assert "finite number" in str(exc_info.value)

    def test_infinity_raises_error(self):
        """Should raise error for infinity."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_decimal(float("inf"))
        assert "finite number" in str(exc_info.value)

    def test_min_value_validation(self):
        """Should validate minimum value."""
        result = validate_decimal("10.5", min_value=Decimal("5"))
        assert result == Decimal("10.5")

        with pytest.raises(SardisValidationError):
            validate_decimal("3", min_value=Decimal("5"))

    def test_max_value_validation(self):
        """Should validate maximum value."""
        result = validate_decimal("10", max_value=Decimal("15"))
        assert result == Decimal("10")

        with pytest.raises(SardisValidationError):
            validate_decimal("20", max_value=Decimal("15"))

    def test_max_decimal_places_validation(self):
        """Should validate maximum decimal places."""
        validate_decimal("10.12", max_decimal_places=2)
        validate_decimal("10.123456", max_decimal_places=6)

        with pytest.raises(SardisValidationError) as exc_info:
            validate_decimal("10.1234567", max_decimal_places=6)
        assert "at most 6 decimal places" in str(exc_info.value)


class TestValidateWalletId:
    """Tests for validate_wallet_id function."""

    def test_valid_wallet_id(self):
        """Should accept valid wallet IDs."""
        result = validate_wallet_id("wallet_1234567890abcdef")
        assert result == "wallet_1234567890abcdef"

    def test_invalid_prefix(self):
        """Should reject invalid prefix."""
        with pytest.raises(SardisValidationError):
            validate_wallet_id("agent_1234567890abcdef")

    def test_invalid_length(self):
        """Should reject invalid length."""
        with pytest.raises(SardisValidationError):
            validate_wallet_id("wallet_123")

    def test_invalid_characters(self):
        """Should reject invalid characters."""
        with pytest.raises(SardisValidationError):
            validate_wallet_id("wallet_1234567890ABCDEF")  # uppercase not allowed


class TestValidateAgentId:
    """Tests for validate_agent_id function."""

    def test_valid_agent_id(self):
        """Should accept valid agent IDs."""
        result = validate_agent_id("agent_1234567890abcdef")
        assert result == "agent_1234567890abcdef"

    def test_invalid_prefix(self):
        """Should reject invalid prefix."""
        with pytest.raises(SardisValidationError):
            validate_agent_id("wallet_1234567890abcdef")


class TestValidateTransactionId:
    """Tests for validate_transaction_id function."""

    def test_valid_transaction_id(self):
        """Should accept valid transaction IDs."""
        result = validate_transaction_id("tx_12345678901234567890")
        assert result == "tx_12345678901234567890"

    def test_invalid_format(self):
        """Should reject invalid format."""
        with pytest.raises(SardisValidationError):
            validate_transaction_id("tx_123")


class TestValidateHoldId:
    """Tests for validate_hold_id function."""

    def test_valid_hold_id(self):
        """Should accept valid hold IDs."""
        result = validate_hold_id("hold_1234567890abcdef")
        assert result == "hold_1234567890abcdef"


class TestValidateMandateId:
    """Tests for validate_mandate_id function."""

    def test_valid_mandate_id(self):
        """Should accept valid mandate IDs."""
        result = validate_mandate_id("mandate_1234567890abcdef")
        assert result == "mandate_1234567890abcdef"


class TestValidateEthAddress:
    """Tests for validate_eth_address function."""

    def test_valid_eth_address(self):
        """Should accept valid Ethereum addresses."""
        valid_addresses = [
            "0x1234567890123456789012345678901234567890",
            "0xABCDEF1234567890123456789012345678901234",
            "0xabcdef1234567890123456789012345678901234",
        ]
        for addr in valid_addresses:
            result = validate_eth_address(addr)
            assert result.startswith("0x")

    def test_invalid_eth_address_no_prefix(self):
        """Should reject addresses without 0x prefix."""
        with pytest.raises(SardisValidationError):
            validate_eth_address("1234567890123456789012345678901234567890")

    def test_invalid_eth_address_wrong_length(self):
        """Should reject addresses with wrong length."""
        with pytest.raises(SardisValidationError):
            validate_eth_address("0x123456")

    def test_invalid_eth_address_invalid_chars(self):
        """Should reject addresses with invalid characters."""
        with pytest.raises(SardisValidationError):
            validate_eth_address("0xGGGG567890123456789012345678901234567890")


class TestValidateSolanaAddress:
    """Tests for validate_solana_address function."""

    def test_valid_solana_address(self):
        """Should accept valid Solana addresses."""
        # Example Solana address (base58, 32-44 chars)
        valid = "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
        result = validate_solana_address(valid)
        assert result == valid

    def test_invalid_solana_address(self):
        """Should reject invalid Solana addresses."""
        with pytest.raises(SardisValidationError):
            validate_solana_address("0x1234567890")  # ETH format


class TestValidateChainAddress:
    """Tests for validate_chain_address function."""

    def test_ethereum_address(self):
        """Should validate Ethereum addresses."""
        addr = "0x1234567890123456789012345678901234567890"
        for chain in ["ethereum", "polygon", "base", "arbitrum", "optimism"]:
            result = validate_chain_address(addr, chain)
            assert result == addr

    def test_solana_address(self):
        """Should validate Solana addresses."""
        addr = "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
        result = validate_chain_address(addr, "solana")
        assert result == addr

    def test_unknown_chain_fallback(self):
        """Should use fallback validation for unknown chains."""
        addr = "some_address_for_unknown_chain"
        result = validate_chain_address(addr, "unknown_chain")
        assert result == addr


class TestValidateTxHash:
    """Tests for validate_tx_hash function."""

    def test_valid_eth_tx_hash(self):
        """Should accept valid Ethereum transaction hashes."""
        tx_hash = "0x" + "a" * 64
        result = validate_tx_hash(tx_hash, "ethereum")
        assert result == tx_hash

    def test_invalid_eth_tx_hash(self):
        """Should reject invalid Ethereum transaction hashes."""
        with pytest.raises(SardisValidationError):
            validate_tx_hash("0x123", "ethereum")


class TestValidateAmount:
    """Tests for validate_amount function."""

    def test_valid_amount(self):
        """Should accept valid amounts."""
        result = validate_amount("100.50")
        assert result == Decimal("100.50")

    def test_zero_not_allowed_by_default(self):
        """Should reject zero by default."""
        with pytest.raises(SardisValidationError):
            validate_amount("0")

    def test_zero_allowed_when_specified(self):
        """Should accept zero when allow_zero is True."""
        result = validate_amount("0", allow_zero=True)
        assert result == Decimal("0")

    def test_negative_amount_rejected(self):
        """Should reject negative amounts."""
        with pytest.raises(SardisValidationError):
            validate_amount("-10")

    def test_max_decimal_places(self):
        """Should enforce 6 decimal places max."""
        validate_amount("10.123456")

        with pytest.raises(SardisValidationError):
            validate_amount("10.1234567")


class TestValidateToken:
    """Tests for validate_token function."""

    def test_valid_tokens(self):
        """Should accept valid tokens."""
        for token in ["USDC", "USDT", "PYUSD", "EURC"]:
            result = validate_token(token)
            assert result == token

    def test_lowercase_converted(self):
        """Should convert lowercase to uppercase."""
        result = validate_token("usdc")
        assert result == "USDC"

    def test_invalid_token(self):
        """Should reject invalid tokens."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_token("BTC")
        assert "must be one of" in str(exc_info.value)


class TestValidateChain:
    """Tests for validate_chain function."""

    def test_valid_chains(self):
        """Should accept valid chains."""
        valid_chains = ["ethereum", "polygon", "base", "arbitrum", "optimism", "solana"]
        for chain in valid_chains:
            result = validate_chain(chain)
            assert result == chain.lower()

    def test_uppercase_converted(self):
        """Should convert uppercase to lowercase."""
        result = validate_chain("ETHEREUM")
        assert result == "ethereum"

    def test_invalid_chain(self):
        """Should reject invalid chains."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_chain("bitcoin")
        assert "must be one of" in str(exc_info.value)


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_https_url(self):
        """Should accept valid HTTPS URLs."""
        result = validate_url("https://example.com/webhook")
        assert result == "https://example.com/webhook"

    def test_http_url_rejected_by_default(self):
        """Should reject HTTP URLs by default."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_url("http://example.com")
        assert "HTTPS" in str(exc_info.value)

    def test_http_url_allowed_when_specified(self):
        """Should accept HTTP URLs when require_https is False."""
        result = validate_url("http://example.com", require_https=False)
        assert result == "http://example.com"

    def test_invalid_url_format(self):
        """Should reject invalid URL formats."""
        with pytest.raises(SardisValidationError):
            validate_url("not_a_url")


class TestValidateEmail:
    """Tests for validate_email function."""

    def test_valid_email(self):
        """Should accept valid emails."""
        result = validate_email("test@example.com")
        assert result == "test@example.com"

    def test_email_lowercased(self):
        """Should convert to lowercase."""
        result = validate_email("Test@Example.COM")
        assert result == "test@example.com"

    def test_invalid_email(self):
        """Should reject invalid emails."""
        with pytest.raises(SardisValidationError):
            validate_email("not_an_email")

        with pytest.raises(SardisValidationError):
            validate_email("missing@domain")


class TestValidateDomain:
    """Tests for validate_domain function."""

    def test_valid_domain(self):
        """Should accept valid domains."""
        result = validate_domain("example.com")
        assert result == "example.com"

    def test_subdomain(self):
        """Should accept subdomains."""
        result = validate_domain("api.example.com")
        assert result == "api.example.com"

    def test_invalid_domain(self):
        """Should reject invalid domains."""
        with pytest.raises(SardisValidationError):
            validate_domain("not-a-domain")


class TestValidateTimestamp:
    """Tests for validate_timestamp function."""

    def test_valid_timestamp(self):
        """Should accept valid timestamps."""
        now = int(time.time())
        result = validate_timestamp(now)
        assert result == now

    def test_string_timestamp(self):
        """Should convert string timestamps."""
        result = validate_timestamp("1234567890")
        assert result == 1234567890

    def test_negative_timestamp_rejected(self):
        """Should reject negative timestamps."""
        with pytest.raises(SardisValidationError):
            validate_timestamp(-1)

    def test_future_timestamp_rejected_when_specified(self):
        """Should reject future timestamps when allow_future is False."""
        future = int(time.time()) + 3600
        with pytest.raises(SardisValidationError) as exc_info:
            validate_timestamp(future, allow_future=False)
        assert "cannot be in the future" in str(exc_info.value)

    def test_old_timestamp_rejected(self):
        """Should reject timestamps older than max_age_seconds."""
        old = int(time.time()) - 3600
        with pytest.raises(SardisValidationError) as exc_info:
            validate_timestamp(old, max_age_seconds=60)
        assert "too old" in str(exc_info.value)


class TestValidateHexString:
    """Tests for validate_hex_string function."""

    def test_valid_hex_string(self):
        """Should accept valid hex strings."""
        result = validate_hex_string("abcdef1234")
        assert result == "abcdef1234"

    def test_hex_with_0x_prefix(self):
        """Should strip 0x prefix."""
        result = validate_hex_string("0xabcdef1234")
        assert result == "abcdef1234"

    def test_uppercase_converted(self):
        """Should convert to lowercase."""
        result = validate_hex_string("ABCDEF")
        assert result == "abcdef"

    def test_invalid_hex_characters(self):
        """Should reject invalid hex characters."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_hex_string("xyz123")
        assert "valid hex string" in str(exc_info.value)

    def test_odd_length_rejected(self):
        """Should reject odd-length hex strings."""
        with pytest.raises(SardisValidationError) as exc_info:
            validate_hex_string("abc")
        assert "even number of hex characters" in str(exc_info.value)

    def test_min_bytes_validation(self):
        """Should validate minimum bytes."""
        validate_hex_string("aabbccdd", min_bytes=4)

        with pytest.raises(SardisValidationError) as exc_info:
            validate_hex_string("aabb", min_bytes=4)
        assert "at least 4 bytes" in str(exc_info.value)

    def test_max_bytes_validation(self):
        """Should validate maximum bytes."""
        validate_hex_string("aabb", max_bytes=4)

        with pytest.raises(SardisValidationError) as exc_info:
            validate_hex_string("aabbccddee", max_bytes=4)
        assert "at most 4 bytes" in str(exc_info.value)


class TestValidatePublicKey:
    """Tests for validate_public_key function."""

    def test_valid_ed25519_key_bytes(self):
        """Should accept valid ed25519 public key as bytes."""
        key_bytes = b"a" * 32
        result = validate_public_key(key_bytes, algorithm="ed25519")
        assert result == key_bytes

    def test_valid_ed25519_key_hex(self):
        """Should accept valid ed25519 public key as hex string."""
        key_hex = "aa" * 32
        result = validate_public_key(key_hex, algorithm="ed25519")
        assert result == bytes.fromhex(key_hex)

    def test_invalid_key_type(self):
        """Should reject invalid key types."""
        with pytest.raises(SardisValidationError):
            validate_public_key(12345)

    def test_wrong_length(self):
        """Should reject keys with wrong length."""
        with pytest.raises(SardisValidationError):
            validate_public_key(b"short", algorithm="ed25519")


class TestValidateSignature:
    """Tests for validate_signature function."""

    def test_valid_ed25519_signature(self):
        """Should accept valid ed25519 signature."""
        sig_bytes = b"a" * 64
        result = validate_signature(sig_bytes, algorithm="ed25519")
        assert result == sig_bytes

    def test_valid_signature_hex(self):
        """Should accept signature as hex string."""
        sig_hex = "aa" * 64
        result = validate_signature(sig_hex, algorithm="ed25519")
        assert result == bytes.fromhex(sig_hex)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_success_result(self):
        """Should create success result."""
        result = ValidationResult.success(field="test")
        assert result.is_valid is True
        assert result.field == "test"
        assert result.error is None

    def test_failure_result(self):
        """Should create failure result."""
        result = ValidationResult.failure(
            error="Invalid value",
            field="test",
            value="bad"
        )
        assert result.is_valid is False
        assert result.error == "Invalid value"
        assert result.field == "test"
        assert result.value == "bad"


class TestValidatePaymentRequest:
    """Tests for validate_payment_request composite validator."""

    def test_valid_payment_request(self):
        """Should validate complete payment request."""
        result = validate_payment_request(
            wallet_id="wallet_1234567890abcdef",
            amount="100.50",
            token="USDC",
            chain="ethereum",
            to_address="0x1234567890123456789012345678901234567890",
        )
        assert result["wallet_id"] == "wallet_1234567890abcdef"
        assert result["amount"] == Decimal("100.50")
        assert result["token"] == "USDC"
        assert result["chain"] == "ethereum"

    def test_invalid_wallet_id(self):
        """Should reject invalid wallet ID."""
        with pytest.raises(SardisValidationError):
            validate_payment_request(
                wallet_id="invalid",
                amount="100",
                token="USDC",
                chain="ethereum",
                to_address="0x1234567890123456789012345678901234567890",
            )


class TestValidateHoldRequest:
    """Tests for validate_hold_request composite validator."""

    def test_valid_hold_request(self):
        """Should validate complete hold request."""
        result = validate_hold_request(
            wallet_id="wallet_1234567890abcdef",
            amount="100",
            token="USDC",
        )
        assert result["wallet_id"] == "wallet_1234567890abcdef"
        assert result["amount"] == Decimal("100")
        assert result["token"] == "USDC"

    def test_hold_with_optional_fields(self):
        """Should handle optional fields."""
        result = validate_hold_request(
            wallet_id="wallet_1234567890abcdef",
            amount="100",
            token="USDC",
            merchant_id="merchant_123",
            expiration_hours=48,
        )
        assert result["merchant_id"] == "merchant_123"
        assert result["expiration_hours"] == 48


class TestValidateInputsDecorator:
    """Tests for validate_inputs decorator."""

    def test_sync_function(self):
        """Should work with sync functions."""
        @validate_inputs
        def sync_func(x: str) -> str:
            return x.upper()

        result = sync_func("test")
        assert result == "TEST"

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Should work with async functions."""
        @validate_inputs
        async def async_func(x: str) -> str:
            return x.upper()

        result = await async_func("test")
        assert result == "TEST"


# Edge cases and security tests
class TestValidatorSecurityEdgeCases:
    """Tests for security edge cases in validators."""

    def test_sql_injection_in_string(self):
        """Validator should handle SQL injection attempts."""
        dangerous = "'; DROP TABLE users; --"
        # Should not raise, just validate as a string
        result = validate_string(dangerous)
        assert result == dangerous

    def test_xss_in_string(self):
        """Validator should handle XSS attempts."""
        dangerous = "<script>alert('xss')</script>"
        result = validate_string(dangerous)
        assert result == dangerous

    def test_very_long_string(self):
        """Should handle very long strings with max_length."""
        long_string = "a" * 10000
        with pytest.raises(SardisValidationError):
            validate_string(long_string, max_length=1000)

    def test_unicode_in_validation(self):
        """Should handle unicode properly."""
        unicode_str = "test"
        result = validate_string(unicode_str)
        assert len(result) == 4

    def test_null_byte_in_string(self):
        """Should handle null bytes in strings."""
        null_str = "test\x00injection"
        result = validate_string(null_str)
        assert "\x00" in result

    def test_empty_eth_address(self):
        """Should reject empty Ethereum address."""
        with pytest.raises(SardisValidationError):
            validate_eth_address("")

    def test_whitespace_only_string(self):
        """Should handle whitespace-only strings."""
        # String with only whitespace, after strip becomes empty
        with pytest.raises(SardisValidationError):
            validate_string("   ", min_length=1)

    def test_decimal_overflow(self):
        """Should handle very large decimals."""
        large = "9" * 100
        result = validate_decimal(large)
        assert result == Decimal(large)

    def test_decimal_precision(self):
        """Should maintain decimal precision."""
        precise = "123.456789012345678901234567890"
        result = validate_decimal(precise)
        # Decimal should maintain precision
        assert str(result) == precise
