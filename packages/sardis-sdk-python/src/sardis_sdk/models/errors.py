"""
Comprehensive error handling for Sardis SDK.

This module provides a complete error hierarchy with standardized error codes,
detailed error information, and helper methods for error handling.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union


class ErrorCode(str, Enum):
    """Standardized error codes for the Sardis SDK.

    These codes provide machine-readable error identification
    for programmatic error handling.
    """

    # General errors (1000-1099)
    UNKNOWN_ERROR = "SARDIS_1000"
    INTERNAL_ERROR = "SARDIS_1001"
    CONFIGURATION_ERROR = "SARDIS_1002"
    INITIALIZATION_ERROR = "SARDIS_1003"

    # Authentication errors (1100-1199)
    AUTHENTICATION_ERROR = "SARDIS_1100"
    INVALID_API_KEY = "SARDIS_1101"
    EXPIRED_API_KEY = "SARDIS_1102"
    INSUFFICIENT_PERMISSIONS = "SARDIS_1103"
    FORBIDDEN = "SARDIS_1104"
    TOKEN_EXPIRED = "SARDIS_1105"
    TOKEN_INVALID = "SARDIS_1106"

    # Validation errors (1200-1299)
    VALIDATION_ERROR = "SARDIS_1200"
    INVALID_FIELD = "SARDIS_1201"
    MISSING_FIELD = "SARDIS_1202"
    INVALID_FORMAT = "SARDIS_1203"
    VALUE_OUT_OF_RANGE = "SARDIS_1204"
    INVALID_ENUM_VALUE = "SARDIS_1205"
    CONSTRAINT_VIOLATION = "SARDIS_1206"

    # Resource errors (1300-1399)
    NOT_FOUND = "SARDIS_1300"
    AGENT_NOT_FOUND = "SARDIS_1301"
    WALLET_NOT_FOUND = "SARDIS_1302"
    PAYMENT_NOT_FOUND = "SARDIS_1303"
    HOLD_NOT_FOUND = "SARDIS_1304"
    WEBHOOK_NOT_FOUND = "SARDIS_1305"
    SERVICE_NOT_FOUND = "SARDIS_1306"
    OFFER_NOT_FOUND = "SARDIS_1307"
    TRANSACTION_NOT_FOUND = "SARDIS_1308"
    RESOURCE_ALREADY_EXISTS = "SARDIS_1309"

    # Payment errors (1400-1499)
    INSUFFICIENT_BALANCE = "SARDIS_1400"
    PAYMENT_FAILED = "SARDIS_1401"
    PAYMENT_DECLINED = "SARDIS_1402"
    INVALID_AMOUNT = "SARDIS_1403"
    AMOUNT_TOO_SMALL = "SARDIS_1404"
    AMOUNT_TOO_LARGE = "SARDIS_1405"
    UNSUPPORTED_CURRENCY = "SARDIS_1406"
    PAYMENT_ALREADY_PROCESSED = "SARDIS_1407"
    HOLD_EXPIRED = "SARDIS_1408"
    HOLD_ALREADY_CAPTURED = "SARDIS_1409"
    HOLD_ALREADY_VOIDED = "SARDIS_1410"
    CAPTURE_AMOUNT_EXCEEDS_HOLD = "SARDIS_1411"

    # Rate limiting errors (1500-1599)
    RATE_LIMIT_EXCEEDED = "SARDIS_1500"
    QUOTA_EXCEEDED = "SARDIS_1501"
    TOO_MANY_REQUESTS = "SARDIS_1502"
    CONCURRENT_LIMIT_EXCEEDED = "SARDIS_1503"

    # Network errors (1600-1699)
    NETWORK_ERROR = "SARDIS_1600"
    CONNECTION_ERROR = "SARDIS_1601"
    TIMEOUT_ERROR = "SARDIS_1602"
    DNS_ERROR = "SARDIS_1603"
    SSL_ERROR = "SARDIS_1604"
    CONNECTION_RESET = "SARDIS_1605"

    # API errors (1700-1799)
    API_ERROR = "SARDIS_1700"
    BAD_REQUEST = "SARDIS_1701"
    SERVER_ERROR = "SARDIS_1702"
    SERVICE_UNAVAILABLE = "SARDIS_1703"
    BAD_GATEWAY = "SARDIS_1704"
    GATEWAY_TIMEOUT = "SARDIS_1705"

    # Blockchain errors (1800-1899)
    BLOCKCHAIN_ERROR = "SARDIS_1800"
    TRANSACTION_FAILED = "SARDIS_1801"
    GAS_ESTIMATION_FAILED = "SARDIS_1802"
    INSUFFICIENT_GAS = "SARDIS_1803"
    NONCE_TOO_LOW = "SARDIS_1804"
    CONTRACT_ERROR = "SARDIS_1805"
    CHAIN_NOT_SUPPORTED = "SARDIS_1806"
    TOKEN_NOT_SUPPORTED = "SARDIS_1807"

    # Compliance errors (1900-1999)
    COMPLIANCE_ERROR = "SARDIS_1900"
    KYC_REQUIRED = "SARDIS_1901"
    SANCTIONS_CHECK_FAILED = "SARDIS_1902"
    TRANSACTION_BLOCKED = "SARDIS_1903"
    POLICY_VIOLATION = "SARDIS_1904"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SardisError(Exception):
    """Base exception for all Sardis SDK errors.

    All SDK exceptions inherit from this class, making it easy to catch
    all Sardis-related errors with a single except clause.

    Attributes:
        message: Human-readable error message
        code: Standardized error code (see ErrorCode enum)
        details: Additional error details as a dictionary
        request_id: Unique identifier for the request that caused the error
        severity: Error severity level
        retryable: Whether the operation that caused this error can be retried
        cause: The underlying exception that caused this error (if any)
    """

    default_code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    default_message: str = "An unexpected error occurred"
    default_severity: ErrorSeverity = ErrorSeverity.MEDIUM
    default_retryable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[Union[str, ErrorCode]] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        retryable: Optional[bool] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message or self.default_message
        self.code = code if isinstance(code, str) else (code.value if code else self.default_code.value)
        self.details = details or {}
        self.request_id = request_id
        self.severity = severity or self.default_severity
        self.retryable = retryable if retryable is not None else self.default_retryable
        self.cause = cause

        super().__init__(self.message)

    def __str__(self) -> str:
        parts = [f"[{self.code}]", self.message]
        if self.request_id:
            parts.append(f"(request_id: {self.request_id})")
        return " ".join(parts)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"request_id={self.request_id!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to a dictionary representation.

        Returns:
            Dictionary containing error information
        """
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
                "severity": self.severity.value,
                "retryable": self.retryable,
            }
        }

        if self.details:
            result["error"]["details"] = self.details

        if self.request_id:
            result["error"]["request_id"] = self.request_id

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SardisError":
        """Create an error from a dictionary.

        Args:
            data: Dictionary containing error information

        Returns:
            Appropriate error instance
        """
        error_data = data.get("error", data)
        return cls(
            message=error_data.get("message"),
            code=error_data.get("code"),
            details=error_data.get("details"),
            request_id=error_data.get("request_id"),
        )

    def with_request_id(self, request_id: str) -> "SardisError":
        """Create a copy of this error with a request ID attached.

        Args:
            request_id: The request ID to attach

        Returns:
            New error instance with request ID
        """
        return self.__class__(
            message=self.message,
            code=self.code,
            details=self.details,
            request_id=request_id,
            severity=self.severity,
            retryable=self.retryable,
            cause=self.cause,
        )


class APIError(SardisError):
    """Error returned from the Sardis API.

    Raised when the API returns an error response (4xx or 5xx status codes).

    Attributes:
        status_code: HTTP status code from the response
    """

    default_code = ErrorCode.API_ERROR
    default_message = "API request failed"

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: int = 0,
        code: Optional[Union[str, ErrorCode]] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        **kwargs: Any,
    ):
        self.status_code = status_code
        super().__init__(
            message=message,
            code=code,
            details=details,
            request_id=request_id,
            **kwargs,
        )

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            return f"{base} (HTTP {self.status_code})"
        return base

    @classmethod
    def from_response(
        cls,
        status_code: int,
        body: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> "APIError":
        """Create an APIError from an HTTP response.

        Args:
            status_code: HTTP status code
            body: Response body as dictionary
            request_id: Optional request ID

        Returns:
            Appropriate error instance based on status code and body
        """
        error_data = body.get("error", body.get("detail", body))

        if isinstance(error_data, str):
            message = error_data
            code = None
            details = None
        elif isinstance(error_data, list):
            message = "Validation Error"
            code = ErrorCode.VALIDATION_ERROR
            details = {"errors": error_data}
        else:
            message = error_data.get("message", "Unknown error")
            code = error_data.get("code")
            details = error_data.get("details")

        # Map status codes to specific error classes
        error_class = cls._get_error_class_for_status(status_code)

        return error_class(
            message=message,
            status_code=status_code,
            code=code,
            details=details,
            request_id=request_id or error_data.get("request_id") if isinstance(error_data, dict) else None,
        )

    @staticmethod
    def _get_error_class_for_status(status_code: int) -> Type["APIError"]:
        """Get the appropriate error class for a status code."""
        status_map = {
            400: ValidationError,
            401: AuthenticationError,
            403: AuthenticationError,
            404: NotFoundError,
            422: ValidationError,
            429: RateLimitError,
            500: ServerError,
            502: BadGatewayError,
            503: ServiceUnavailableError,
            504: GatewayTimeoutError,
        }
        return status_map.get(status_code, APIError)


class AuthenticationError(APIError):
    """Authentication or authorization error.

    Raised when:
    - API key is invalid or missing
    - API key has expired
    - API key lacks required permissions
    """

    default_code = ErrorCode.AUTHENTICATION_ERROR
    default_message = "Authentication failed"
    default_severity = ErrorSeverity.HIGH

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[Union[str, ErrorCode]] = None,
        **kwargs: Any,
    ):
        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 401),
            code=code or self.default_code,
            **kwargs,
        )


class ValidationError(APIError):
    """Validation error for request data.

    Raised when request data fails validation, such as:
    - Missing required fields
    - Invalid field formats
    - Values out of range
    """

    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Validation failed"

    def __init__(
        self,
        message: Optional[str] = None,
        field: Optional[str] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {}) or {}
        if field:
            details["field"] = field
        if errors:
            details["errors"] = errors

        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 422),
            details=details,
            **kwargs,
        )
        self.field = field
        self.errors = errors


class NotFoundError(APIError):
    """Resource not found error.

    Raised when a requested resource does not exist.
    """

    default_code = ErrorCode.NOT_FOUND
    default_message = "Resource not found"

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: str = "",
        message: Optional[str] = None,
        **kwargs: Any,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id

        if not message:
            message = f"{resource_type} not found"
            if resource_id:
                message = f"{message}: {resource_id}"

        details = kwargs.pop("details", {}) or {}
        details.update({
            "resource_type": resource_type,
            "resource_id": resource_id,
        })

        super().__init__(
            message=message,
            status_code=kwargs.pop("status_code", 404),
            details=details,
            **kwargs,
        )


class RateLimitError(APIError):
    """Rate limit exceeded error.

    Raised when too many requests have been made in a given time period.

    Attributes:
        retry_after: Number of seconds to wait before retrying
    """

    default_code = ErrorCode.RATE_LIMIT_EXCEEDED
    default_message = "Rate limit exceeded"
    default_retryable = True

    def __init__(
        self,
        message: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ):
        self.retry_after = retry_after

        details = kwargs.pop("details", {}) or {}
        if retry_after is not None:
            details["retry_after"] = retry_after

        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 429),
            details=details,
            retryable=True,
            **kwargs,
        )


class InsufficientBalanceError(APIError):
    """Insufficient balance for the requested operation.

    Raised when a wallet doesn't have enough funds for a payment or hold.

    Attributes:
        required: Amount required for the operation
        available: Amount currently available
        currency: Currency/token type
    """

    default_code = ErrorCode.INSUFFICIENT_BALANCE
    default_message = "Insufficient balance"

    def __init__(
        self,
        message: Optional[str] = None,
        required: Optional[str] = None,
        available: Optional[str] = None,
        currency: str = "USDC",
        **kwargs: Any,
    ):
        self.required = required
        self.available = available
        self.currency = currency

        details = kwargs.pop("details", {}) or {}
        if required:
            details["required"] = required
        if available:
            details["available"] = available
        details["currency"] = currency

        if not message and required and available:
            message = f"Insufficient balance: required {required} {currency}, available {available} {currency}"

        super().__init__(
            message=message or self.default_message,
            details=details,
            **kwargs,
        )


class ServerError(APIError):
    """Internal server error.

    Raised when the API encounters an internal error.
    """

    default_code = ErrorCode.SERVER_ERROR
    default_message = "Internal server error"
    default_severity = ErrorSeverity.HIGH
    default_retryable = True

    def __init__(self, message: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 500),
            **kwargs,
        )


class BadGatewayError(APIError):
    """Bad gateway error.

    Raised when an upstream service returns an invalid response.
    """

    default_code = ErrorCode.BAD_GATEWAY
    default_message = "Bad gateway"
    default_retryable = True

    def __init__(self, message: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 502),
            **kwargs,
        )


class ServiceUnavailableError(APIError):
    """Service unavailable error.

    Raised when the API is temporarily unavailable.
    """

    default_code = ErrorCode.SERVICE_UNAVAILABLE
    default_message = "Service temporarily unavailable"
    default_retryable = True

    def __init__(self, message: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 503),
            **kwargs,
        )


class GatewayTimeoutError(APIError):
    """Gateway timeout error.

    Raised when an upstream service times out.
    """

    default_code = ErrorCode.GATEWAY_TIMEOUT
    default_message = "Gateway timeout"
    default_retryable = True

    def __init__(self, message: Optional[str] = None, **kwargs: Any):
        super().__init__(
            message=message or self.default_message,
            status_code=kwargs.pop("status_code", 504),
            **kwargs,
        )


# Network Errors (not HTTP-based)


class NetworkError(SardisError):
    """Base class for network-related errors.

    Raised when there are issues with the network connection.
    """

    default_code = ErrorCode.NETWORK_ERROR
    default_message = "Network error occurred"
    default_retryable = True


class ConnectionError(NetworkError):
    """Failed to establish connection.

    Raised when the client cannot connect to the API server.
    """

    default_code = ErrorCode.CONNECTION_ERROR
    default_message = "Failed to establish connection"


class TimeoutError(NetworkError):
    """Request timed out.

    Raised when a request takes too long to complete.
    """

    default_code = ErrorCode.TIMEOUT_ERROR
    default_message = "Request timed out"


# Payment-specific errors


class PaymentError(SardisError):
    """Base class for payment-related errors."""

    default_code = ErrorCode.PAYMENT_FAILED
    default_message = "Payment failed"


class HoldError(SardisError):
    """Base class for hold-related errors."""

    default_code = ErrorCode.HOLD_EXPIRED
    default_message = "Hold operation failed"


class HoldExpiredError(HoldError):
    """Hold has expired."""

    default_code = ErrorCode.HOLD_EXPIRED
    default_message = "Hold has expired"


class HoldAlreadyCapturedError(HoldError):
    """Hold has already been captured."""

    default_code = ErrorCode.HOLD_ALREADY_CAPTURED
    default_message = "Hold has already been captured"


class HoldAlreadyVoidedError(HoldError):
    """Hold has already been voided."""

    default_code = ErrorCode.HOLD_ALREADY_VOIDED
    default_message = "Hold has already been voided"


# Blockchain-specific errors


class BlockchainError(SardisError):
    """Base class for blockchain-related errors."""

    default_code = ErrorCode.BLOCKCHAIN_ERROR
    default_message = "Blockchain operation failed"


class TransactionFailedError(BlockchainError):
    """On-chain transaction failed."""

    default_code = ErrorCode.TRANSACTION_FAILED
    default_message = "Transaction failed"


class GasEstimationError(BlockchainError):
    """Failed to estimate gas for transaction."""

    default_code = ErrorCode.GAS_ESTIMATION_FAILED
    default_message = "Gas estimation failed"


class ChainNotSupportedError(BlockchainError):
    """Requested chain is not supported."""

    default_code = ErrorCode.CHAIN_NOT_SUPPORTED
    default_message = "Chain not supported"


# Compliance errors


class ComplianceError(SardisError):
    """Base class for compliance-related errors."""

    default_code = ErrorCode.COMPLIANCE_ERROR
    default_message = "Compliance check failed"
    default_severity = ErrorSeverity.HIGH


class KYCRequiredError(ComplianceError):
    """KYC verification is required."""

    default_code = ErrorCode.KYC_REQUIRED
    default_message = "KYC verification required"


class SanctionsCheckFailedError(ComplianceError):
    """Sanctions check failed."""

    default_code = ErrorCode.SANCTIONS_CHECK_FAILED
    default_message = "Sanctions check failed"


class PolicyViolationError(ComplianceError):
    """Policy violation detected."""

    default_code = ErrorCode.POLICY_VIOLATION
    default_message = "Policy violation detected"


# Error registry for looking up errors by code
ERROR_REGISTRY: Dict[str, Type[SardisError]] = {
    ErrorCode.UNKNOWN_ERROR.value: SardisError,
    ErrorCode.AUTHENTICATION_ERROR.value: AuthenticationError,
    ErrorCode.INVALID_API_KEY.value: AuthenticationError,
    ErrorCode.VALIDATION_ERROR.value: ValidationError,
    ErrorCode.NOT_FOUND.value: NotFoundError,
    ErrorCode.RATE_LIMIT_EXCEEDED.value: RateLimitError,
    ErrorCode.INSUFFICIENT_BALANCE.value: InsufficientBalanceError,
    ErrorCode.NETWORK_ERROR.value: NetworkError,
    ErrorCode.CONNECTION_ERROR.value: ConnectionError,
    ErrorCode.TIMEOUT_ERROR.value: TimeoutError,
    ErrorCode.API_ERROR.value: APIError,
    ErrorCode.SERVER_ERROR.value: ServerError,
    ErrorCode.BLOCKCHAIN_ERROR.value: BlockchainError,
    ErrorCode.COMPLIANCE_ERROR.value: ComplianceError,
}


def error_from_code(
    code: str,
    message: Optional[str] = None,
    **kwargs: Any,
) -> SardisError:
    """Create an error instance from an error code.

    Args:
        code: The error code
        message: Optional custom message
        **kwargs: Additional arguments for the error constructor

    Returns:
        Appropriate error instance
    """
    error_class = ERROR_REGISTRY.get(code, SardisError)
    return error_class(message=message, code=code, **kwargs)


__all__ = [
    # Enums
    "ErrorCode",
    "ErrorSeverity",
    # Base errors
    "SardisError",
    "APIError",
    # Authentication
    "AuthenticationError",
    # Validation
    "ValidationError",
    # Resources
    "NotFoundError",
    # Rate limiting
    "RateLimitError",
    # Balance
    "InsufficientBalanceError",
    # Server
    "ServerError",
    "BadGatewayError",
    "ServiceUnavailableError",
    "GatewayTimeoutError",
    # Network
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    # Payment
    "PaymentError",
    "HoldError",
    "HoldExpiredError",
    "HoldAlreadyCapturedError",
    "HoldAlreadyVoidedError",
    # Blockchain
    "BlockchainError",
    "TransactionFailedError",
    "GasEstimationError",
    "ChainNotSupportedError",
    # Compliance
    "ComplianceError",
    "KYCRequiredError",
    "SanctionsCheckFailedError",
    "PolicyViolationError",
    # Utilities
    "error_from_code",
    "ERROR_REGISTRY",
]
