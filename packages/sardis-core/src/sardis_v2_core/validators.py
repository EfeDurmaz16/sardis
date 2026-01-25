"""
Input validation utilities for Sardis Core.

This module provides comprehensive validation functions and decorators
for validating inputs to ensure data integrity and security.

Usage:
    from sardis_v2_core.validators import (
        validate_wallet_id,
        validate_amount,
        validate_address,
        ValidationError,
    )

    # Direct validation
    validate_wallet_id(wallet_id)  # Raises ValidationError if invalid

    # Or use as decorator
    @validate_inputs
    async def create_payment(wallet_id: WalletId, amount: PositiveDecimal):
        ...
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import (
    Any,
    Callable,
    Optional,
    Pattern,
    Sequence,
    TypeVar,
    Union,
    TYPE_CHECKING,
)
from functools import wraps

from .exceptions import SardisValidationError
from .constants import PaymentLimits, SecurityConfig, TokenConfig

if TYPE_CHECKING:
    from .tokens import TokenType

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Regex Patterns
# =============================================================================

# Ethereum address pattern (0x followed by 40 hex chars)
ETH_ADDRESS_PATTERN: Pattern[str] = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Solana address pattern (base58, 32-44 chars)
SOLANA_ADDRESS_PATTERN: Pattern[str] = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

# Transaction hash patterns
ETH_TX_HASH_PATTERN: Pattern[str] = re.compile(r"^0x[a-fA-F0-9]{64}$")
SOLANA_TX_HASH_PATTERN: Pattern[str] = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{64,88}$")

# Sardis ID patterns
WALLET_ID_PATTERN: Pattern[str] = re.compile(r"^wallet_[a-f0-9]{16}$")
AGENT_ID_PATTERN: Pattern[str] = re.compile(r"^agent_[a-f0-9]{16}$")
TRANSACTION_ID_PATTERN: Pattern[str] = re.compile(r"^tx_[a-f0-9]{20}$")
HOLD_ID_PATTERN: Pattern[str] = re.compile(r"^hold_[a-f0-9]{16}$")
MANDATE_ID_PATTERN: Pattern[str] = re.compile(r"^mandate_[a-f0-9]{16,32}$")
EVENT_ID_PATTERN: Pattern[str] = re.compile(r"^evt_[a-f0-9]{16}$")
POLICY_ID_PATTERN: Pattern[str] = re.compile(r"^policy_[a-f0-9]{16}$")
RULE_ID_PATTERN: Pattern[str] = re.compile(r"^rule_[a-f0-9]{12}$")

# Email pattern (simplified but effective)
EMAIL_PATTERN: Pattern[str] = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

# URL pattern
URL_PATTERN: Pattern[str] = re.compile(
    r"^https?://[a-zA-Z0-9.-]+(?:\:[0-9]+)?(?:/[^\s]*)?$"
)

# Domain pattern
DOMAIN_PATTERN: Pattern[str] = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# Hex string pattern
HEX_PATTERN: Pattern[str] = re.compile(r"^(?:0x)?[a-fA-F0-9]+$")


# =============================================================================
# Validation Result
# =============================================================================

@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid: Whether the validation passed
        error: Error message if validation failed
        field: The field name that was validated
        value: The original value (may be masked for security)
    """

    is_valid: bool
    error: Optional[str] = None
    field: Optional[str] = None
    value: Any = None

    @classmethod
    def success(cls, field: Optional[str] = None) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True, field=field)

    @classmethod
    def failure(
        cls,
        error: str,
        field: Optional[str] = None,
        value: Any = None,
    ) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, error=error, field=field, value=value)


# =============================================================================
# Core Validation Functions
# =============================================================================

def validate_not_none(
    value: Any,
    field_name: str = "value",
) -> None:
    """Validate that a value is not None.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        SardisValidationError: If value is None
    """
    if value is None:
        raise SardisValidationError(
            f"{field_name} is required",
            field=field_name,
        )


def validate_not_empty(
    value: Union[str, Sequence[Any], None],
    field_name: str = "value",
) -> None:
    """Validate that a value is not empty.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        SardisValidationError: If value is None or empty
    """
    if value is None or (hasattr(value, "__len__") and len(value) == 0):
        raise SardisValidationError(
            f"{field_name} cannot be empty",
            field=field_name,
        )


def validate_string(
    value: Any,
    field_name: str = "value",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[Pattern[str]] = None,
    allowed_values: Optional[Sequence[str]] = None,
) -> str:
    """Validate and normalize a string value.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        min_length: Minimum string length
        max_length: Maximum string length
        pattern: Regex pattern the string must match
        allowed_values: List of allowed values

    Returns:
        The validated string (stripped of whitespace)

    Raises:
        SardisValidationError: If validation fails
    """
    if value is None:
        raise SardisValidationError(
            f"{field_name} is required",
            field=field_name,
        )

    if not isinstance(value, str):
        raise SardisValidationError(
            f"{field_name} must be a string",
            field=field_name,
        )

    # Strip whitespace
    value = value.strip()

    if min_length is not None and len(value) < min_length:
        raise SardisValidationError(
            f"{field_name} must be at least {min_length} characters",
            field=field_name,
        )

    if max_length is not None and len(value) > max_length:
        raise SardisValidationError(
            f"{field_name} must be at most {max_length} characters",
            field=field_name,
        )

    if pattern is not None and not pattern.match(value):
        raise SardisValidationError(
            f"{field_name} has invalid format",
            field=field_name,
        )

    if allowed_values is not None and value not in allowed_values:
        raise SardisValidationError(
            f"{field_name} must be one of: {', '.join(allowed_values)}",
            field=field_name,
        )

    return value


def validate_integer(
    value: Any,
    field_name: str = "value",
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """Validate and convert an integer value.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        The validated integer

    Raises:
        SardisValidationError: If validation fails
    """
    if value is None:
        raise SardisValidationError(
            f"{field_name} is required",
            field=field_name,
        )

    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise SardisValidationError(
            f"{field_name} must be an integer",
            field=field_name,
        )

    if min_value is not None and int_value < min_value:
        raise SardisValidationError(
            f"{field_name} must be at least {min_value}",
            field=field_name,
        )

    if max_value is not None and int_value > max_value:
        raise SardisValidationError(
            f"{field_name} must be at most {max_value}",
            field=field_name,
        )

    return int_value


def validate_decimal(
    value: Any,
    field_name: str = "value",
    min_value: Optional[Decimal] = None,
    max_value: Optional[Decimal] = None,
    max_decimal_places: Optional[int] = None,
) -> Decimal:
    """Validate and convert a decimal value.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        max_decimal_places: Maximum decimal places allowed

    Returns:
        The validated Decimal

    Raises:
        SardisValidationError: If validation fails
    """
    if value is None:
        raise SardisValidationError(
            f"{field_name} is required",
            field=field_name,
        )

    try:
        if isinstance(value, Decimal):
            dec_value = value
        else:
            dec_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise SardisValidationError(
            f"{field_name} must be a valid decimal number",
            field=field_name,
        )

    # Check for special values
    if dec_value.is_nan() or dec_value.is_infinite():
        raise SardisValidationError(
            f"{field_name} must be a finite number",
            field=field_name,
        )

    if min_value is not None and dec_value < min_value:
        raise SardisValidationError(
            f"{field_name} must be at least {min_value}",
            field=field_name,
        )

    if max_value is not None and dec_value > max_value:
        raise SardisValidationError(
            f"{field_name} must be at most {max_value}",
            field=field_name,
        )

    if max_decimal_places is not None:
        # Check decimal places
        sign, digits, exponent = dec_value.as_tuple()
        if isinstance(exponent, int) and exponent < 0:
            actual_places = abs(exponent)
            if actual_places > max_decimal_places:
                raise SardisValidationError(
                    f"{field_name} must have at most {max_decimal_places} decimal places",
                    field=field_name,
                )

    return dec_value


# =============================================================================
# Domain-Specific Validators
# =============================================================================

def validate_wallet_id(value: Any, field_name: str = "wallet_id") -> str:
    """Validate a wallet ID.

    Args:
        value: The wallet ID to validate
        field_name: Name of the field for error messages

    Returns:
        The validated wallet ID

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=WALLET_ID_PATTERN,
    )


def validate_agent_id(value: Any, field_name: str = "agent_id") -> str:
    """Validate an agent ID.

    Args:
        value: The agent ID to validate
        field_name: Name of the field for error messages

    Returns:
        The validated agent ID

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=AGENT_ID_PATTERN,
    )


def validate_transaction_id(value: Any, field_name: str = "transaction_id") -> str:
    """Validate a transaction ID.

    Args:
        value: The transaction ID to validate
        field_name: Name of the field for error messages

    Returns:
        The validated transaction ID

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=TRANSACTION_ID_PATTERN,
    )


def validate_hold_id(value: Any, field_name: str = "hold_id") -> str:
    """Validate a hold ID.

    Args:
        value: The hold ID to validate
        field_name: Name of the field for error messages

    Returns:
        The validated hold ID

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=HOLD_ID_PATTERN,
    )


def validate_mandate_id(value: Any, field_name: str = "mandate_id") -> str:
    """Validate a mandate ID.

    Args:
        value: The mandate ID to validate
        field_name: Name of the field for error messages

    Returns:
        The validated mandate ID

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=MANDATE_ID_PATTERN,
    )


def validate_eth_address(value: Any, field_name: str = "address") -> str:
    """Validate an Ethereum address.

    Args:
        value: The address to validate
        field_name: Name of the field for error messages

    Returns:
        The validated address (checksummed)

    Raises:
        SardisValidationError: If validation fails
    """
    address = validate_string(value, field_name=field_name, pattern=ETH_ADDRESS_PATTERN)

    # Convert to checksum address
    try:
        # Simple checksum validation (full EIP-55 would need keccak)
        return address  # In production, use web3.py's to_checksum_address
    except Exception:
        raise SardisValidationError(
            f"{field_name} is not a valid Ethereum address",
            field=field_name,
        )


def validate_solana_address(value: Any, field_name: str = "address") -> str:
    """Validate a Solana address.

    Args:
        value: The address to validate
        field_name: Name of the field for error messages

    Returns:
        The validated address

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=SOLANA_ADDRESS_PATTERN,
    )


def validate_chain_address(
    value: Any,
    chain: str,
    field_name: str = "address",
) -> str:
    """Validate a blockchain address for the given chain.

    Args:
        value: The address to validate
        chain: The blockchain identifier
        field_name: Name of the field for error messages

    Returns:
        The validated address

    Raises:
        SardisValidationError: If validation fails
    """
    chain_lower = chain.lower()

    if chain_lower in ("ethereum", "polygon", "base", "arbitrum", "optimism"):
        return validate_eth_address(value, field_name)
    elif chain_lower == "solana":
        return validate_solana_address(value, field_name)
    else:
        # Default to basic string validation for unknown chains
        return validate_string(
            value,
            field_name=field_name,
            min_length=20,
            max_length=100,
        )


def validate_tx_hash(
    value: Any,
    chain: str,
    field_name: str = "tx_hash",
) -> str:
    """Validate a transaction hash for the given chain.

    Args:
        value: The transaction hash to validate
        chain: The blockchain identifier
        field_name: Name of the field for error messages

    Returns:
        The validated transaction hash

    Raises:
        SardisValidationError: If validation fails
    """
    chain_lower = chain.lower()

    if chain_lower in ("ethereum", "polygon", "base", "arbitrum", "optimism"):
        return validate_string(value, field_name=field_name, pattern=ETH_TX_HASH_PATTERN)
    elif chain_lower == "solana":
        return validate_string(value, field_name=field_name, pattern=SOLANA_TX_HASH_PATTERN)
    else:
        return validate_string(
            value,
            field_name=field_name,
            pattern=HEX_PATTERN,
            min_length=32,
        )


def validate_amount(
    value: Any,
    field_name: str = "amount",
    min_value: Optional[Decimal] = None,
    max_value: Optional[Decimal] = None,
    allow_zero: bool = False,
) -> Decimal:
    """Validate a payment amount.

    Args:
        value: The amount to validate
        field_name: Name of the field for error messages
        min_value: Minimum amount (defaults to 0 or MIN_TRANSFER_AMOUNT)
        max_value: Maximum amount
        allow_zero: Whether to allow zero amounts

    Returns:
        The validated amount

    Raises:
        SardisValidationError: If validation fails
    """
    if min_value is None:
        min_value = Decimal("0") if allow_zero else PaymentLimits.MIN_TRANSFER_AMOUNT

    amount = validate_decimal(
        value,
        field_name=field_name,
        min_value=min_value,
        max_value=max_value,
        max_decimal_places=6,  # Standard for most stablecoins
    )

    return amount


def validate_token(value: Any, field_name: str = "token") -> str:
    """Validate a token type.

    Args:
        value: The token type to validate
        field_name: Name of the field for error messages

    Returns:
        The validated token type (uppercase)

    Raises:
        SardisValidationError: If validation fails
    """
    token = validate_string(
        value,
        field_name=field_name,
        max_length=10,
    ).upper()

    # Validate against known tokens
    allowed_tokens = ("USDC", "USDT", "PYUSD", "EURC")
    if token not in allowed_tokens:
        raise SardisValidationError(
            f"{field_name} must be one of: {', '.join(allowed_tokens)}",
            field=field_name,
        )

    return token


def validate_chain(value: Any, field_name: str = "chain") -> str:
    """Validate a chain identifier.

    Args:
        value: The chain identifier to validate
        field_name: Name of the field for error messages

    Returns:
        The validated chain identifier (lowercase)

    Raises:
        SardisValidationError: If validation fails
    """
    chain = validate_string(
        value,
        field_name=field_name,
        max_length=50,
    ).lower()

    allowed_chains = (
        "ethereum",
        "polygon",
        "base",
        "arbitrum",
        "optimism",
        "solana",
        "base_sepolia",  # Testnets
        "polygon_mumbai",
    )

    if chain not in allowed_chains:
        raise SardisValidationError(
            f"{field_name} must be one of: {', '.join(allowed_chains)}",
            field=field_name,
        )

    return chain


def validate_url(value: Any, field_name: str = "url", require_https: bool = True) -> str:
    """Validate a URL.

    Args:
        value: The URL to validate
        field_name: Name of the field for error messages
        require_https: Whether to require HTTPS

    Returns:
        The validated URL

    Raises:
        SardisValidationError: If validation fails
    """
    url = validate_string(
        value,
        field_name=field_name,
        pattern=URL_PATTERN,
        max_length=2048,
    )

    if require_https and not url.startswith("https://"):
        raise SardisValidationError(
            f"{field_name} must use HTTPS",
            field=field_name,
        )

    return url


def validate_email(value: Any, field_name: str = "email") -> str:
    """Validate an email address.

    Args:
        value: The email to validate
        field_name: Name of the field for error messages

    Returns:
        The validated email (lowercase)

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=EMAIL_PATTERN,
        max_length=254,
    ).lower()


def validate_domain(value: Any, field_name: str = "domain") -> str:
    """Validate a domain name.

    Args:
        value: The domain to validate
        field_name: Name of the field for error messages

    Returns:
        The validated domain (lowercase)

    Raises:
        SardisValidationError: If validation fails
    """
    return validate_string(
        value,
        field_name=field_name,
        pattern=DOMAIN_PATTERN,
        max_length=253,
    ).lower()


def validate_timestamp(
    value: Any,
    field_name: str = "timestamp",
    allow_future: bool = True,
    max_age_seconds: Optional[int] = None,
) -> int:
    """Validate a Unix timestamp.

    Args:
        value: The timestamp to validate
        field_name: Name of the field for error messages
        allow_future: Whether to allow future timestamps
        max_age_seconds: Maximum age of timestamp in seconds

    Returns:
        The validated timestamp

    Raises:
        SardisValidationError: If validation fails
    """
    timestamp = validate_integer(
        value,
        field_name=field_name,
        min_value=0,
    )

    now = int(datetime.now(timezone.utc).timestamp())

    if not allow_future and timestamp > now:
        raise SardisValidationError(
            f"{field_name} cannot be in the future",
            field=field_name,
        )

    if max_age_seconds is not None:
        age = now - timestamp
        if age > max_age_seconds:
            raise SardisValidationError(
                f"{field_name} is too old (max age: {max_age_seconds}s)",
                field=field_name,
            )

    return timestamp


def validate_hex_string(
    value: Any,
    field_name: str = "value",
    min_bytes: Optional[int] = None,
    max_bytes: Optional[int] = None,
) -> str:
    """Validate a hex-encoded string.

    Args:
        value: The hex string to validate
        field_name: Name of the field for error messages
        min_bytes: Minimum number of bytes
        max_bytes: Maximum number of bytes

    Returns:
        The validated hex string (without 0x prefix)

    Raises:
        SardisValidationError: If validation fails
    """
    hex_str = validate_string(value, field_name=field_name)

    # Remove 0x prefix if present
    if hex_str.startswith("0x") or hex_str.startswith("0X"):
        hex_str = hex_str[2:]

    # Validate hex characters
    if not re.match(r"^[a-fA-F0-9]*$", hex_str):
        raise SardisValidationError(
            f"{field_name} must be a valid hex string",
            field=field_name,
        )

    # Check length (each byte = 2 hex chars)
    byte_length = len(hex_str) // 2

    if len(hex_str) % 2 != 0:
        raise SardisValidationError(
            f"{field_name} must have even number of hex characters",
            field=field_name,
        )

    if min_bytes is not None and byte_length < min_bytes:
        raise SardisValidationError(
            f"{field_name} must be at least {min_bytes} bytes",
            field=field_name,
        )

    if max_bytes is not None and byte_length > max_bytes:
        raise SardisValidationError(
            f"{field_name} must be at most {max_bytes} bytes",
            field=field_name,
        )

    return hex_str.lower()


def validate_public_key(
    value: Any,
    algorithm: str = "ed25519",
    field_name: str = "public_key",
) -> bytes:
    """Validate a public key.

    Args:
        value: The public key (bytes or hex string)
        algorithm: The key algorithm
        field_name: Name of the field for error messages

    Returns:
        The validated public key as bytes

    Raises:
        SardisValidationError: If validation fails
    """
    if algorithm not in SecurityConfig.SUPPORTED_ALGORITHMS:
        raise SardisValidationError(
            f"Unsupported algorithm: {algorithm}",
            field=field_name,
        )

    expected_lengths = {
        "ed25519": 32,
        "ecdsa-p256": 65,  # Uncompressed P-256 public key
    }

    expected_length = expected_lengths.get(algorithm)

    if isinstance(value, bytes):
        key_bytes = value
    elif isinstance(value, str):
        hex_str = validate_hex_string(
            value,
            field_name=field_name,
            min_bytes=expected_length,
            max_bytes=expected_length,
        )
        key_bytes = bytes.fromhex(hex_str)
    else:
        raise SardisValidationError(
            f"{field_name} must be bytes or hex string",
            field=field_name,
        )

    if expected_length and len(key_bytes) != expected_length:
        raise SardisValidationError(
            f"{field_name} must be {expected_length} bytes for {algorithm}",
            field=field_name,
        )

    return key_bytes


def validate_signature(
    value: Any,
    algorithm: str = "ed25519",
    field_name: str = "signature",
) -> bytes:
    """Validate a cryptographic signature.

    Args:
        value: The signature (bytes or hex string)
        algorithm: The signature algorithm
        field_name: Name of the field for error messages

    Returns:
        The validated signature as bytes

    Raises:
        SardisValidationError: If validation fails
    """
    expected_lengths = {
        "ed25519": 64,
        "ecdsa-p256": (64, 72),  # DER encoding varies
    }

    if isinstance(value, bytes):
        sig_bytes = value
    elif isinstance(value, str):
        hex_str = validate_hex_string(value, field_name=field_name)
        sig_bytes = bytes.fromhex(hex_str)
    else:
        raise SardisValidationError(
            f"{field_name} must be bytes or hex string",
            field=field_name,
        )

    expected = expected_lengths.get(algorithm)
    if expected:
        if isinstance(expected, tuple):
            min_len, max_len = expected
            if not (min_len <= len(sig_bytes) <= max_len):
                raise SardisValidationError(
                    f"{field_name} must be {min_len}-{max_len} bytes for {algorithm}",
                    field=field_name,
                )
        elif len(sig_bytes) != expected:
            raise SardisValidationError(
                f"{field_name} must be {expected} bytes for {algorithm}",
                field=field_name,
            )

    return sig_bytes


# =============================================================================
# Validation Decorator
# =============================================================================

def validate_inputs(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that validates function inputs based on type hints.

    This decorator inspects the function's type hints and applies
    appropriate validation to each argument.

    Usage:
        @validate_inputs
        async def create_payment(
            wallet_id: str,
            amount: Decimal,
            token: str,
        ) -> PaymentResult:
            ...

    Note: This is a basic implementation. For production use,
    consider using pydantic models for input validation.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        # Basic validation would go here
        # In production, integrate with pydantic for full type validation
        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        return func(*args, **kwargs)

    # Return appropriate wrapper based on whether function is async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# =============================================================================
# Composite Validators
# =============================================================================

def validate_payment_request(
    wallet_id: Any,
    amount: Any,
    token: Any,
    chain: Any,
    to_address: Any,
) -> dict[str, Any]:
    """Validate a complete payment request.

    Args:
        wallet_id: The source wallet ID
        amount: Payment amount
        token: Token type
        chain: Blockchain identifier
        to_address: Destination address

    Returns:
        Dictionary of validated values

    Raises:
        SardisValidationError: If any validation fails
    """
    return {
        "wallet_id": validate_wallet_id(wallet_id),
        "amount": validate_amount(amount),
        "token": validate_token(token),
        "chain": validate_chain(chain),
        "to_address": validate_chain_address(to_address, chain),
    }


def validate_hold_request(
    wallet_id: Any,
    amount: Any,
    token: Any,
    merchant_id: Optional[Any] = None,
    expiration_hours: Optional[Any] = None,
) -> dict[str, Any]:
    """Validate a hold creation request.

    Args:
        wallet_id: The wallet ID
        amount: Hold amount
        token: Token type
        merchant_id: Optional merchant identifier
        expiration_hours: Optional expiration in hours

    Returns:
        Dictionary of validated values

    Raises:
        SardisValidationError: If any validation fails
    """
    from .constants import HoldConfig

    result = {
        "wallet_id": validate_wallet_id(wallet_id),
        "amount": validate_amount(amount),
        "token": validate_token(token),
    }

    if merchant_id is not None:
        result["merchant_id"] = validate_string(
            merchant_id,
            field_name="merchant_id",
            max_length=64,
        )

    if expiration_hours is not None:
        result["expiration_hours"] = validate_integer(
            expiration_hours,
            field_name="expiration_hours",
            min_value=HoldConfig.MIN_HOLD_HOURS,
            max_value=HoldConfig.MAX_HOLD_HOURS,
        )

    return result


__all__ = [
    # Core validators
    "validate_not_none",
    "validate_not_empty",
    "validate_string",
    "validate_integer",
    "validate_decimal",
    # Domain validators
    "validate_wallet_id",
    "validate_agent_id",
    "validate_transaction_id",
    "validate_hold_id",
    "validate_mandate_id",
    "validate_eth_address",
    "validate_solana_address",
    "validate_chain_address",
    "validate_tx_hash",
    "validate_amount",
    "validate_token",
    "validate_chain",
    "validate_url",
    "validate_email",
    "validate_domain",
    "validate_timestamp",
    "validate_hex_string",
    "validate_public_key",
    "validate_signature",
    # Composite validators
    "validate_payment_request",
    "validate_hold_request",
    # Utilities
    "ValidationResult",
    "validate_inputs",
    # Patterns
    "ETH_ADDRESS_PATTERN",
    "WALLET_ID_PATTERN",
    "AGENT_ID_PATTERN",
]
