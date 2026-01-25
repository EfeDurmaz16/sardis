"""
Centralized constants and configuration values for Sardis Core.

This module provides a single source of truth for all magic numbers,
timeout values, limits, and configuration defaults used throughout
the sardis-core package.

Usage:
    from sardis_v2_core.constants import Timeouts, Limits, ErrorCodes

All values are organized into logical namespaces using classes.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Final

# Python 3.10 compatibility for StrEnum
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        """String enum for Python < 3.11 compatibility."""
        pass


# =============================================================================
# Timeout Constants (in seconds unless specified)
# =============================================================================

class Timeouts:
    """Network and operation timeout configuration.

    All timeout values are in seconds unless otherwise specified.
    """

    # HTTP/API timeouts
    HTTP_DEFAULT: Final[float] = 30.0
    HTTP_CONNECT: Final[float] = 10.0
    HTTP_READ: Final[float] = 30.0
    HTTP_WRITE: Final[float] = 30.0

    # External service timeouts
    WEBHOOK_DELIVERY: Final[float] = 10.0
    MPC_SIGNING: Final[float] = 60.0
    RPC_CALL: Final[float] = 30.0
    KYC_VERIFICATION: Final[float] = 45.0
    SANCTIONS_CHECK: Final[float] = 30.0
    CARD_PROVIDER: Final[float] = 45.0

    # Database timeouts
    DB_COMMAND: Final[float] = 60.0
    DB_CONNECT: Final[float] = 10.0
    DB_POOL_ACQUIRE: Final[float] = 30.0

    # Cache timeouts
    CACHE_OPERATION: Final[float] = 5.0

    # Circuit breaker recovery
    CIRCUIT_RECOVERY_DEFAULT: Final[float] = 30.0
    CIRCUIT_RECOVERY_MPC: Final[float] = 60.0
    CIRCUIT_RECOVERY_RPC: Final[float] = 15.0


# =============================================================================
# Retry Configuration
# =============================================================================

class RetryConfig:
    """Retry configuration for various operations."""

    # Default retry settings
    DEFAULT_MAX_RETRIES: Final[int] = 3
    DEFAULT_BASE_DELAY: Final[float] = 1.0
    DEFAULT_MAX_DELAY: Final[float] = 60.0
    DEFAULT_EXPONENTIAL_BASE: Final[float] = 2.0
    DEFAULT_JITTER: Final[float] = 0.1

    # Webhook-specific retry
    WEBHOOK_MAX_RETRIES: Final[int] = 3
    WEBHOOK_DELAYS: Final[tuple[int, ...]] = (1, 5, 30)

    # MPC signing retry
    MPC_MAX_RETRIES: Final[int] = 3
    MPC_BASE_DELAY: Final[float] = 2.0
    MPC_MAX_DELAY: Final[float] = 30.0

    # RPC call retry
    RPC_MAX_RETRIES: Final[int] = 5
    RPC_BASE_DELAY: Final[float] = 0.5
    RPC_MAX_DELAY: Final[float] = 10.0

    # Database operation retry
    DB_MAX_RETRIES: Final[int] = 3
    DB_BASE_DELAY: Final[float] = 0.5
    DB_MAX_DELAY: Final[float] = 5.0


# =============================================================================
# Circuit Breaker Configuration
# =============================================================================

class CircuitBreakerDefaults:
    """Default circuit breaker configuration."""

    FAILURE_THRESHOLD: Final[int] = 5
    RECOVERY_TIMEOUT: Final[float] = 30.0
    SUCCESS_THRESHOLD: Final[int] = 2
    FAILURE_WINDOW: Final[float] = 60.0

    # Service-specific configurations
    TURNKEY_FAILURE_THRESHOLD: Final[int] = 3
    TURNKEY_RECOVERY_TIMEOUT: Final[float] = 60.0

    PERSONA_FAILURE_THRESHOLD: Final[int] = 5
    PERSONA_RECOVERY_TIMEOUT: Final[float] = 30.0

    ELLIPTIC_FAILURE_THRESHOLD: Final[int] = 5
    ELLIPTIC_RECOVERY_TIMEOUT: Final[float] = 30.0

    LITHIC_FAILURE_THRESHOLD: Final[int] = 5
    LITHIC_RECOVERY_TIMEOUT: Final[float] = 45.0

    RPC_FAILURE_THRESHOLD: Final[int] = 10
    RPC_RECOVERY_TIMEOUT: Final[float] = 15.0


# =============================================================================
# Pool and Connection Limits
# =============================================================================

class PoolLimits:
    """Connection pool and resource limits."""

    # Database pool
    DB_POOL_MIN_SIZE: Final[int] = 2
    DB_POOL_MAX_SIZE: Final[int] = 10

    # Webhook pool
    WEBHOOK_POOL_MIN_SIZE: Final[int] = 1
    WEBHOOK_POOL_MAX_SIZE: Final[int] = 5

    # HTTP connection pool
    HTTP_MAX_CONNECTIONS: Final[int] = 100
    HTTP_MAX_KEEPALIVE_CONNECTIONS: Final[int] = 20
    HTTP_KEEPALIVE_EXPIRY: Final[float] = 5.0


# =============================================================================
# Cache Configuration
# =============================================================================

class CacheTTL:
    """Cache time-to-live values (in seconds)."""

    # Balance cache
    BALANCE: Final[int] = 60  # 1 minute

    # Wallet cache
    WALLET: Final[int] = 300  # 5 minutes

    # Agent cache
    AGENT: Final[int] = 300  # 5 minutes

    # Rate limit window
    RATE_LIMIT: Final[int] = 60  # 1 minute

    # Session cache
    SESSION: Final[int] = 3600  # 1 hour

    # API key cache
    API_KEY: Final[int] = 300  # 5 minutes


class CacheLimits:
    """Cache size limits."""

    # TTLDict defaults
    DEFAULT_TTL_SECONDS: Final[float] = 86400.0  # 24 hours
    DEFAULT_MAX_ITEMS: Final[int] = 10000
    DEFAULT_CLEANUP_INTERVAL: Final[float] = 300.0  # 5 minutes

    # Wallet repository cache
    WALLET_TTL_SECONDS: Final[float] = 7 * 24 * 60 * 60  # 7 days
    WALLET_MAX_ITEMS: Final[int] = 10000

    # Holds repository cache
    HOLDS_TTL_SECONDS: Final[float] = 7 * 24 * 60 * 60  # 7 days
    HOLDS_MAX_ITEMS: Final[int] = 10000


# =============================================================================
# Transaction and Payment Limits
# =============================================================================

class PaymentLimits:
    """Payment and transaction limits."""

    # Default wallet limits
    DEFAULT_LIMIT_PER_TX: Final[Decimal] = Decimal("100.00")
    DEFAULT_LIMIT_TOTAL: Final[Decimal] = Decimal("1000.00")

    # Trust level limits
    LOW_TRUST_PER_TX: Final[Decimal] = Decimal("50.00")
    LOW_TRUST_DAILY: Final[Decimal] = Decimal("100.00")
    LOW_TRUST_WEEKLY: Final[Decimal] = Decimal("500.00")
    LOW_TRUST_MONTHLY: Final[Decimal] = Decimal("1000.00")
    LOW_TRUST_TOTAL: Final[Decimal] = Decimal("5000.00")

    MEDIUM_TRUST_PER_TX: Final[Decimal] = Decimal("500.00")
    MEDIUM_TRUST_DAILY: Final[Decimal] = Decimal("1000.00")
    MEDIUM_TRUST_WEEKLY: Final[Decimal] = Decimal("5000.00")
    MEDIUM_TRUST_MONTHLY: Final[Decimal] = Decimal("10000.00")
    MEDIUM_TRUST_TOTAL: Final[Decimal] = Decimal("50000.00")

    HIGH_TRUST_PER_TX: Final[Decimal] = Decimal("5000.00")
    HIGH_TRUST_DAILY: Final[Decimal] = Decimal("10000.00")
    HIGH_TRUST_WEEKLY: Final[Decimal] = Decimal("50000.00")
    HIGH_TRUST_MONTHLY: Final[Decimal] = Decimal("100000.00")
    HIGH_TRUST_TOTAL: Final[Decimal] = Decimal("500000.00")

    UNLIMITED_MAX: Final[Decimal] = Decimal("999999999.00")

    # Token minimum transfer amounts
    MIN_TRANSFER_AMOUNT: Final[Decimal] = Decimal("0.01")


# =============================================================================
# Hold Configuration
# =============================================================================

class HoldConfig:
    """Hold (pre-authorization) configuration."""

    DEFAULT_EXPIRATION_HOURS: Final[int] = 168  # 7 days
    MAX_HOLD_HOURS: Final[int] = 720  # 30 days
    MIN_HOLD_HOURS: Final[int] = 1


# =============================================================================
# Virtual Card Configuration
# =============================================================================

class CardLimits:
    """Virtual card limits."""

    DEFAULT_LIMIT_PER_TX: Final[Decimal] = Decimal("500.00")
    DEFAULT_LIMIT_DAILY: Final[Decimal] = Decimal("2000.00")
    DEFAULT_LIMIT_MONTHLY: Final[Decimal] = Decimal("10000.00")


# =============================================================================
# Token Configuration
# =============================================================================

class TokenConfig:
    """Token-related constants."""

    # Standard ERC20 decimals
    USDC_DECIMALS: Final[int] = 6
    USDT_DECIMALS: Final[int] = 6
    PYUSD_DECIMALS: Final[int] = 6
    EURC_DECIMALS: Final[int] = 6

    # Default peg ratios (to USD)
    EURC_PEG_RATIO: Final[Decimal] = Decimal("1.08")

    # ERC20 function selectors
    BALANCE_OF_SELECTOR: Final[str] = "70a08231"
    TRANSFER_SELECTOR: Final[str] = "a9059cbb"
    APPROVE_SELECTOR: Final[str] = "095ea7b3"
    TRANSFER_FROM_SELECTOR: Final[str] = "23b872dd"


# =============================================================================
# API Configuration
# =============================================================================

class APIConfig:
    """API-related configuration."""

    # Pagination
    DEFAULT_PAGE_SIZE: Final[int] = 50
    MAX_PAGE_SIZE: Final[int] = 100

    # Rate limiting (requests per window)
    DEFAULT_RATE_LIMIT: Final[int] = 100
    DEFAULT_RATE_WINDOW_SECONDS: Final[int] = 60

    # API versioning
    CURRENT_API_VERSION: Final[str] = "2024-01"

    # Request size limits
    MAX_REQUEST_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB
    MAX_WEBHOOK_PAYLOAD_SIZE: Final[int] = 64 * 1024  # 64 KB


# =============================================================================
# Security Configuration
# =============================================================================

class SecurityConfig:
    """Security-related constants."""

    # Key sizes
    MIN_SECRET_KEY_LENGTH: Final[int] = 32

    # Mandate TTL
    DEFAULT_MANDATE_TTL_SECONDS: Final[int] = 300  # 5 minutes

    # Session expiry
    SESSION_EXPIRY_SECONDS: Final[int] = 3600  # 1 hour

    # API key prefix length
    API_KEY_PREFIX_LENGTH: Final[int] = 8

    # Signature algorithms
    SUPPORTED_ALGORITHMS: Final[tuple[str, ...]] = ("ed25519", "ecdsa-p256")
    DEFAULT_ALGORITHM: Final[str] = "ed25519"


# =============================================================================
# Logging Configuration
# =============================================================================

class LoggingConfig:
    """Logging-related constants."""

    # Sensitive fields to mask in logs
    SENSITIVE_FIELDS: Final[frozenset[str]] = frozenset({
        "password",
        "secret",
        "token",
        "api_key",
        "apiKey",
        "api_secret",
        "apiSecret",
        "private_key",
        "privateKey",
        "secret_key",
        "secretKey",
        "access_token",
        "accessToken",
        "refresh_token",
        "refreshToken",
        "authorization",
        "auth",
        "credential",
        "credentials",
        "card_number",
        "cardNumber",
        "cvv",
        "cvc",
        "ssn",
        "social_security",
        "bank_account",
        "routing_number",
        "account_number",
    })

    # Mask pattern for sensitive data
    MASK_PATTERN: Final[str] = "***REDACTED***"

    # Max log message length
    MAX_LOG_MESSAGE_LENGTH: Final[int] = 10000

    # Response body truncation for logs
    MAX_RESPONSE_BODY_LOG_LENGTH: Final[int] = 500


# =============================================================================
# Reconciliation Configuration
# =============================================================================

class ReconciliationConfig:
    """Reconciliation queue configuration."""

    MAX_RETRIES: Final[int] = 5
    DEFAULT_BATCH_SIZE: Final[int] = 10
    RETRY_DELAY_SECONDS: Final[int] = 60


# =============================================================================
# Error Codes
# =============================================================================

class ErrorCodes(StrEnum):
    """Standardized error codes for API responses.

    Format: CATEGORY_SPECIFIC_ERROR
    """

    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"

    # Authentication errors (401)
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"

    # Authorization errors (403)
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    WALLET_NOT_FOUND = "WALLET_NOT_FOUND"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    HOLD_NOT_FOUND = "HOLD_NOT_FOUND"

    # Conflict errors (409)
    CONFLICT = "CONFLICT"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"

    # Rate limit errors (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Payment errors
    PAYMENT_ERROR = "PAYMENT_ERROR"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"

    # Mandate errors
    MANDATE_ERROR = "MANDATE_ERROR"
    MANDATE_EXPIRED = "MANDATE_EXPIRED"
    MANDATE_REPLAY = "MANDATE_REPLAY"
    MANDATE_CHAIN_INVALID = "MANDATE_CHAIN_INVALID"
    SIGNATURE_ERROR = "SIGNATURE_ERROR"

    # Chain errors
    CHAIN_ERROR = "CHAIN_ERROR"
    RPC_ERROR = "RPC_ERROR"
    MPC_ERROR = "MPC_ERROR"

    # Compliance errors
    COMPLIANCE_ERROR = "COMPLIANCE_ERROR"
    KYC_REQUIRED = "KYC_REQUIRED"
    KYC_EXPIRED = "KYC_EXPIRED"
    SANCTIONS_HIT = "SANCTIONS_HIT"
    TRAVEL_RULE_REQUIRED = "TRAVEL_RULE_REQUIRED"

    # Hold errors
    HOLD_ERROR = "HOLD_ERROR"
    HOLD_EXPIRED = "HOLD_EXPIRED"
    HOLD_ALREADY_CAPTURED = "HOLD_ALREADY_CAPTURED"
    HOLD_ALREADY_VOIDED = "HOLD_ALREADY_VOIDED"

    # Configuration errors
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_NOT_CONFIGURED = "DEPENDENCY_NOT_CONFIGURED"

    # Service errors (5xx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


# =============================================================================
# HTTP Status Code Mapping
# =============================================================================

ERROR_CODE_TO_HTTP_STATUS: Final[dict[str, int]] = {
    # 400 Bad Request
    ErrorCodes.VALIDATION_ERROR: 400,
    ErrorCodes.INVALID_INPUT: 400,
    ErrorCodes.MISSING_FIELD: 400,
    ErrorCodes.INVALID_FORMAT: 400,
    ErrorCodes.VALUE_OUT_OF_RANGE: 400,
    ErrorCodes.PAYMENT_ERROR: 400,
    ErrorCodes.POLICY_VIOLATION: 400,
    ErrorCodes.MANDATE_ERROR: 400,
    ErrorCodes.MANDATE_EXPIRED: 400,
    ErrorCodes.MANDATE_REPLAY: 400,
    ErrorCodes.MANDATE_CHAIN_INVALID: 400,
    ErrorCodes.SIGNATURE_ERROR: 400,
    ErrorCodes.HOLD_ERROR: 400,
    ErrorCodes.HOLD_EXPIRED: 400,
    ErrorCodes.HOLD_ALREADY_CAPTURED: 400,
    ErrorCodes.HOLD_ALREADY_VOIDED: 400,

    # 401 Unauthorized
    ErrorCodes.AUTHENTICATION_ERROR: 401,
    ErrorCodes.INVALID_CREDENTIALS: 401,
    ErrorCodes.TOKEN_EXPIRED: 401,
    ErrorCodes.TOKEN_INVALID: 401,

    # 403 Forbidden
    ErrorCodes.AUTHORIZATION_ERROR: 403,
    ErrorCodes.PERMISSION_DENIED: 403,
    ErrorCodes.INSUFFICIENT_PERMISSIONS: 403,
    ErrorCodes.COMPLIANCE_ERROR: 403,
    ErrorCodes.KYC_REQUIRED: 403,
    ErrorCodes.KYC_EXPIRED: 403,
    ErrorCodes.SANCTIONS_HIT: 403,
    ErrorCodes.TRAVEL_RULE_REQUIRED: 403,

    # 404 Not Found
    ErrorCodes.NOT_FOUND: 404,
    ErrorCodes.RESOURCE_NOT_FOUND: 404,
    ErrorCodes.WALLET_NOT_FOUND: 404,
    ErrorCodes.AGENT_NOT_FOUND: 404,
    ErrorCodes.TRANSACTION_NOT_FOUND: 404,
    ErrorCodes.HOLD_NOT_FOUND: 404,

    # 409 Conflict
    ErrorCodes.CONFLICT: 409,
    ErrorCodes.DUPLICATE_RESOURCE: 409,
    ErrorCodes.CONCURRENT_MODIFICATION: 409,

    # 429 Too Many Requests
    ErrorCodes.RATE_LIMIT_EXCEEDED: 429,

    # 500 Internal Server Error
    ErrorCodes.UNKNOWN_ERROR: 500,
    ErrorCodes.INTERNAL_ERROR: 500,
    ErrorCodes.CONFIGURATION_ERROR: 500,

    # 502 Bad Gateway
    ErrorCodes.CHAIN_ERROR: 502,
    ErrorCodes.RPC_ERROR: 502,
    ErrorCodes.MPC_ERROR: 502,
    ErrorCodes.TRANSACTION_FAILED: 502,

    # 503 Service Unavailable
    ErrorCodes.SERVICE_UNAVAILABLE: 503,
    ErrorCodes.DATABASE_ERROR: 503,
    ErrorCodes.CIRCUIT_BREAKER_OPEN: 503,
    ErrorCodes.DEPENDENCY_NOT_CONFIGURED: 503,

    # 504 Gateway Timeout
    ErrorCodes.TIMEOUT_ERROR: 504,
}


def get_http_status_for_error(error_code: str) -> int:
    """Get HTTP status code for an error code.

    Args:
        error_code: The error code string

    Returns:
        HTTP status code (defaults to 500 if not found)
    """
    return ERROR_CODE_TO_HTTP_STATUS.get(error_code, 500)


# =============================================================================
# Chain Error Mapping
# =============================================================================

CHAIN_ERROR_MAPPING: Final[dict[str, str]] = {
    # Common RPC errors
    "execution reverted": ErrorCodes.TRANSACTION_FAILED,
    "insufficient funds": ErrorCodes.INSUFFICIENT_BALANCE,
    "nonce too low": ErrorCodes.TRANSACTION_FAILED,
    "nonce too high": ErrorCodes.TRANSACTION_FAILED,
    "gas price too low": ErrorCodes.TRANSACTION_FAILED,
    "replacement transaction underpriced": ErrorCodes.TRANSACTION_FAILED,
    "transaction underpriced": ErrorCodes.TRANSACTION_FAILED,
    "intrinsic gas too low": ErrorCodes.TRANSACTION_FAILED,
    "max fee per gas less than block base fee": ErrorCodes.TRANSACTION_FAILED,
    "timeout": ErrorCodes.TIMEOUT_ERROR,
    "connection refused": ErrorCodes.SERVICE_UNAVAILABLE,
    "rate limited": ErrorCodes.RATE_LIMIT_EXCEEDED,
}


def map_chain_error(error_message: str) -> str:
    """Map a chain error message to an error code.

    Args:
        error_message: The raw error message from the chain

    Returns:
        Mapped error code
    """
    error_lower = error_message.lower()
    for pattern, code in CHAIN_ERROR_MAPPING.items():
        if pattern in error_lower:
            return code
    return ErrorCodes.CHAIN_ERROR
