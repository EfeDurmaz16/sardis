"""Unified exception hierarchy for Sardis.

All Sardis-specific exceptions inherit from SardisException, enabling:
- Consistent error handling across packages
- Proper HTTP status code mapping in API layer
- Structured error responses with error codes
- Chain error mapping from raw blockchain errors

Usage:
    from sardis_v2_core.exceptions import (
        SardisException,
        SardisValidationError,
        SardisNotFoundError,
        exception_from_chain_error,
    )

    try:
        result = await chain_call()
    except ChainRPCException as e:
        raise exception_from_chain_error(e, chain="base")

All exceptions have:
- error_code: Machine-readable error code (e.g., "VALIDATION_ERROR")
- http_status: Appropriate HTTP status code for API responses
- message: Human-readable error message
- details: Optional additional context dictionary
- to_dict(): Convert to API response format
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

E = TypeVar("E", bound="SardisException")


class SardisException(Exception):
    """Base exception for all Sardis errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code (e.g., "VALIDATION_ERROR")
        details: Optional additional context
    """
    
    error_code: str = "SARDIS_ERROR"
    http_status: int = 500
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to API response format."""
        result = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# =============================================================================
# Validation & Input Errors (4xx)
# =============================================================================

class SardisValidationError(SardisException):
    """Invalid input data or parameters."""
    
    error_code = "VALIDATION_ERROR"
    http_status = 400
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, details=details)


class SardisNotFoundError(SardisException):
    """Requested resource not found."""
    
    error_code = "NOT_FOUND"
    http_status = 404
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        message = f"{resource_type} '{resource_id}' not found"
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(message, details=details)


class SardisAuthenticationError(SardisException):
    """Authentication failed."""
    
    error_code = "AUTHENTICATION_ERROR"
    http_status = 401


class SardisAuthorizationError(SardisException):
    """Authorization failed - insufficient permissions."""
    
    error_code = "AUTHORIZATION_ERROR"
    http_status = 403


class SardisConflictError(SardisException):
    """Resource conflict (e.g., duplicate, concurrent modification)."""
    
    error_code = "CONFLICT"
    http_status = 409


# =============================================================================
# Payment & Transaction Errors
# =============================================================================

class SardisPaymentError(SardisException):
    """Base class for payment-related errors."""
    
    error_code = "PAYMENT_ERROR"
    http_status = 400


class SardisPolicyViolationError(SardisPaymentError):
    """Payment violates spending policy."""
    
    error_code = "POLICY_VIOLATION"
    
    def __init__(
        self,
        message: str,
        policy_type: Optional[str] = None,
        limit: Optional[str] = None,
        requested: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if policy_type:
            details["policy_type"] = policy_type
        if limit:
            details["limit"] = limit
        if requested:
            details["requested"] = requested
        super().__init__(message, details=details)


class SardisInsufficientBalanceError(SardisPaymentError):
    """Insufficient balance for transaction."""
    
    error_code = "INSUFFICIENT_BALANCE"
    
    def __init__(
        self,
        message: str,
        available: Optional[str] = None,
        required: Optional[str] = None,
        token: Optional[str] = None,
        chain: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if available:
            details["available"] = available
        if required:
            details["required"] = required
        if token:
            details["token"] = token
        if chain:
            details["chain"] = chain
        super().__init__(message, details=details)


class SardisTransactionFailedError(SardisPaymentError):
    """On-chain transaction failed."""
    
    error_code = "TRANSACTION_FAILED"
    
    def __init__(
        self,
        message: str,
        tx_hash: Optional[str] = None,
        chain: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if tx_hash:
            details["tx_hash"] = tx_hash
        if chain:
            details["chain"] = chain
        if reason:
            details["reason"] = reason
        super().__init__(message, details=details)


# =============================================================================
# Mandate & Protocol Errors
# =============================================================================

class SardisMandateError(SardisException):
    """Base class for mandate-related errors."""
    
    error_code = "MANDATE_ERROR"
    http_status = 400


class SardisSignatureError(SardisMandateError):
    """Invalid or missing signature."""
    
    error_code = "SIGNATURE_ERROR"
    
    def __init__(
        self,
        message: str,
        algorithm: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if algorithm:
            details["algorithm"] = algorithm
        super().__init__(message, details=details)


class SardisMandateExpiredError(SardisMandateError):
    """Mandate has expired."""
    
    error_code = "MANDATE_EXPIRED"
    
    def __init__(
        self,
        message: str,
        mandate_id: Optional[str] = None,
        expired_at: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if mandate_id:
            details["mandate_id"] = mandate_id
        if expired_at:
            details["expired_at"] = expired_at
        super().__init__(message, details=details)


class SardisMandateReplayError(SardisMandateError):
    """Mandate has already been processed (replay attack prevention)."""
    
    error_code = "MANDATE_REPLAY"


class SardisMandateChainError(SardisMandateError):
    """Invalid mandate chain (AP2 verification failed)."""
    
    error_code = "MANDATE_CHAIN_INVALID"


# =============================================================================
# Chain & Infrastructure Errors (5xx)
# =============================================================================

class SardisChainError(SardisException):
    """Base class for blockchain-related errors."""
    
    error_code = "CHAIN_ERROR"
    http_status = 502
    
    def __init__(
        self,
        message: str,
        chain: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if chain:
            details["chain"] = chain
        super().__init__(message, details=details)


class SardisRPCError(SardisChainError):
    """RPC call to blockchain node failed."""
    
    error_code = "RPC_ERROR"
    
    def __init__(
        self,
        message: str,
        chain: Optional[str] = None,
        method: Optional[str] = None,
        rpc_error: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if method:
            details["method"] = method
        if rpc_error:
            details["rpc_error"] = rpc_error
        super().__init__(message, chain=chain, details=details)


class SardisDatabaseError(SardisException):
    """Database operation failed."""
    
    error_code = "DATABASE_ERROR"
    http_status = 503
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, details=details)


class SardisMPCError(SardisChainError):
    """MPC signing operation failed."""
    
    error_code = "MPC_ERROR"


# =============================================================================
# Compliance Errors
# =============================================================================

class SardisComplianceError(SardisException):
    """Base class for compliance-related errors."""
    
    error_code = "COMPLIANCE_ERROR"
    http_status = 403


class SardisKYCRequiredError(SardisComplianceError):
    """KYC verification required before operation."""
    
    error_code = "KYC_REQUIRED"
    
    def __init__(
        self,
        message: str = "KYC verification required",
        agent_id: Optional[str] = None,
        verification_url: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if agent_id:
            details["agent_id"] = agent_id
        if verification_url:
            details["verification_url"] = verification_url
        super().__init__(message, details=details)


class SardisKYCExpiredError(SardisComplianceError):
    """KYC verification has expired."""
    
    error_code = "KYC_EXPIRED"


class SardisSanctionsHitError(SardisComplianceError):
    """Address or entity on sanctions list."""
    
    error_code = "SANCTIONS_HIT"
    
    def __init__(
        self,
        message: str = "Transaction blocked due to sanctions screening",
        screening_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if screening_id:
            details["screening_id"] = screening_id
        super().__init__(message, details=details)


class SardisTravelRuleError(SardisComplianceError):
    """Travel rule compliance required."""
    
    error_code = "TRAVEL_RULE_REQUIRED"


# =============================================================================
# Algorithm & Cryptography Errors
# =============================================================================

class SardisAlgorithmNotSupportedError(SardisException):
    """Cryptographic algorithm not supported."""
    
    error_code = "ALGORITHM_NOT_SUPPORTED"
    http_status = 400
    
    def __init__(
        self,
        algorithm: str,
        supported: Optional[list[str]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        message = f"Algorithm '{algorithm}' not supported"
        details = details or {}
        details["algorithm"] = algorithm
        if supported:
            details["supported_algorithms"] = supported
            message += f". Supported: {', '.join(supported)}"
        super().__init__(message, details=details)


# =============================================================================
# Hold Errors
# =============================================================================

class SardisHoldError(SardisException):
    """Base class for hold-related errors."""
    
    error_code = "HOLD_ERROR"
    http_status = 400


class SardisHoldNotFoundError(SardisHoldError, SardisNotFoundError):
    """Hold not found."""
    
    error_code = "HOLD_NOT_FOUND"
    
    def __init__(self, hold_id: str) -> None:
        SardisNotFoundError.__init__(self, "Hold", hold_id)


class SardisHoldExpiredError(SardisHoldError):
    """Hold has expired."""
    
    error_code = "HOLD_EXPIRED"


class SardisHoldAlreadyCapturedError(SardisHoldError):
    """Hold has already been captured."""
    
    error_code = "HOLD_ALREADY_CAPTURED"


class SardisHoldAlreadyVoidedError(SardisHoldError):
    """Hold has already been voided."""
    
    error_code = "HOLD_ALREADY_VOIDED"


# =============================================================================
# Service Configuration Errors
# =============================================================================

class SardisConfigurationError(SardisException):
    """Service configuration error."""
    
    error_code = "CONFIGURATION_ERROR"
    http_status = 500


class SardisDependencyNotConfiguredError(SardisConfigurationError):
    """Required dependency not configured."""
    
    error_code = "DEPENDENCY_NOT_CONFIGURED"
    http_status = 503
    
    def __init__(
        self,
        dependency: str,
        message: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        message = message or f"Required dependency '{dependency}' is not configured"
        details = details or {}
        details["dependency"] = dependency
        super().__init__(message, details=details)


# =============================================================================
# Rate Limiting
# =============================================================================

class SardisRateLimitError(SardisException):
    """Rate limit exceeded."""

    error_code = "RATE_LIMIT_EXCEEDED"
    http_status = 429

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, details=details)


class SardisTimeoutError(SardisException):
    """Operation timed out."""

    error_code = "TIMEOUT_ERROR"
    http_status = 504

    def __init__(
        self,
        message: str = "Operation timed out",
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if operation:
            details["operation"] = operation
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, details=details)


class SardisServiceUnavailableError(SardisException):
    """External service is unavailable."""

    error_code = "SERVICE_UNAVAILABLE"
    http_status = 503

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if service:
            details["service"] = service
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, details=details)


# =============================================================================
# Error Mapping Utilities
# =============================================================================

# Chain error patterns and their corresponding exception types
CHAIN_ERROR_PATTERNS: dict[str, tuple[Type[SardisException], str]] = {
    "execution reverted": (SardisTransactionFailedError, "Transaction execution reverted"),
    "insufficient funds": (SardisInsufficientBalanceError, "Insufficient funds for transaction"),
    "nonce too low": (SardisTransactionFailedError, "Transaction nonce too low"),
    "nonce too high": (SardisTransactionFailedError, "Transaction nonce too high"),
    "gas price too low": (SardisTransactionFailedError, "Gas price too low"),
    "replacement transaction underpriced": (
        SardisTransactionFailedError,
        "Replacement transaction underpriced",
    ),
    "transaction underpriced": (SardisTransactionFailedError, "Transaction underpriced"),
    "intrinsic gas too low": (SardisTransactionFailedError, "Intrinsic gas too low"),
    "max fee per gas less than block base fee": (
        SardisTransactionFailedError,
        "Max fee per gas less than block base fee",
    ),
    "timeout": (SardisTimeoutError, "RPC request timed out"),
    "connection refused": (SardisServiceUnavailableError, "RPC node connection refused"),
    "rate limited": (SardisRateLimitError, "RPC rate limit exceeded"),
    "too many requests": (SardisRateLimitError, "RPC rate limit exceeded"),
    "internal error": (SardisRPCError, "RPC internal error"),
    "method not found": (SardisRPCError, "RPC method not supported"),
    "invalid params": (SardisValidationError, "Invalid RPC parameters"),
}


def exception_from_chain_error(
    error: BaseException,
    chain: Optional[str] = None,
    method: Optional[str] = None,
    tx_hash: Optional[str] = None,
) -> SardisException:
    """Convert a chain/RPC error to the appropriate Sardis exception.

    This function maps raw blockchain errors to typed Sardis exceptions
    for consistent error handling and API responses.

    Args:
        error: The original exception from the chain call
        chain: Optional chain identifier (e.g., "base", "polygon")
        method: Optional RPC method that failed
        tx_hash: Optional transaction hash if applicable

    Returns:
        Appropriate SardisException subclass

    Example:
        try:
            result = await rpc_client.send_transaction(tx)
        except Exception as e:
            raise exception_from_chain_error(e, chain="base")
    """
    error_str = str(error).lower()

    # Check known patterns
    for pattern, (exc_class, message) in CHAIN_ERROR_PATTERNS.items():
        if pattern in error_str:
            details: dict[str, Any] = {"original_error": str(error)}
            if chain:
                details["chain"] = chain
            if method:
                details["method"] = method

            # Handle specific exception constructors
            if exc_class == SardisInsufficientBalanceError:
                return exc_class(
                    message,
                    chain=chain,
                    details=details,
                )
            elif exc_class == SardisTransactionFailedError:
                return exc_class(
                    message,
                    tx_hash=tx_hash,
                    chain=chain,
                    reason=str(error),
                    details=details,
                )
            elif exc_class == SardisTimeoutError:
                return exc_class(
                    message,
                    operation=method,
                    details=details,
                )
            elif exc_class == SardisServiceUnavailableError:
                return exc_class(
                    message,
                    service=f"rpc:{chain}" if chain else "rpc",
                    details=details,
                )
            elif exc_class == SardisRateLimitError:
                return exc_class(
                    message,
                    details=details,
                )
            elif exc_class == SardisRPCError:
                return exc_class(
                    message,
                    chain=chain,
                    method=method,
                    rpc_error=str(error),
                    details=details,
                )
            elif exc_class == SardisValidationError:
                return exc_class(
                    message,
                    details=details,
                )

            # Generic instantiation for other types
            return exc_class(message, details=details)

    # Default to generic RPC error
    return SardisRPCError(
        f"RPC call failed: {error}",
        chain=chain,
        method=method,
        rpc_error=str(error),
    )


def exception_from_mpc_error(
    error: BaseException,
    provider: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> SardisException:
    """Convert an MPC provider error to the appropriate Sardis exception.

    Args:
        error: The original exception from the MPC provider
        provider: MPC provider name (e.g., "turnkey", "fireblocks")
        wallet_id: Optional wallet ID involved

    Returns:
        Appropriate SardisException subclass
    """
    error_str = str(error).lower()
    details: dict[str, Any] = {"original_error": str(error)}
    if provider:
        details["provider"] = provider
    if wallet_id:
        details["wallet_id"] = wallet_id

    # Check for authentication errors
    if any(p in error_str for p in ("unauthorized", "authentication", "invalid credential")):
        return SardisAuthenticationError(
            f"MPC authentication failed: {error}",
            details=details,
        )

    # Check for timeout
    if "timeout" in error_str:
        return SardisTimeoutError(
            "MPC signing timed out",
            operation="mpc_sign",
            details=details,
        )

    # Check for rate limiting
    if "rate limit" in error_str or "too many requests" in error_str:
        return SardisRateLimitError(
            "MPC provider rate limit exceeded",
            details=details,
        )

    # Default to generic MPC error
    return SardisMPCError(
        f"MPC operation failed: {error}",
        details=details,
    )


def exception_from_compliance_error(
    error: BaseException,
    provider: Optional[str] = None,
    check_type: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> SardisException:
    """Convert a compliance provider error to the appropriate Sardis exception.

    Args:
        error: The original exception
        provider: Compliance provider name (e.g., "persona", "elliptic")
        check_type: Type of check (e.g., "kyc", "sanctions")
        agent_id: Optional agent ID involved

    Returns:
        Appropriate SardisException subclass
    """
    error_str = str(error).lower()
    details: dict[str, Any] = {"original_error": str(error)}
    if provider:
        details["provider"] = provider
    if check_type:
        details["check_type"] = check_type
    if agent_id:
        details["agent_id"] = agent_id

    # Check for specific compliance failures
    if "sanctions" in error_str or "blocked" in error_str:
        return SardisSanctionsHitError(
            "Transaction blocked by sanctions screening",
            details=details,
        )

    if "kyc" in error_str and "required" in error_str:
        return SardisKYCRequiredError(
            "KYC verification required",
            agent_id=agent_id,
            details=details,
        )

    if "kyc" in error_str and "expired" in error_str:
        return SardisKYCExpiredError(
            "KYC verification has expired",
            details=details,
        )

    if "travel rule" in error_str:
        return SardisTravelRuleError(
            "Travel rule information required",
            details=details,
        )

    # Default to generic compliance error
    return SardisComplianceError(
        f"Compliance check failed: {error}",
        details=details,
    )


# =============================================================================
# Exception Registry
# =============================================================================

# Map of error codes to exception classes for dynamic instantiation
EXCEPTION_REGISTRY: dict[str, Type[SardisException]] = {
    "SARDIS_ERROR": SardisException,
    "VALIDATION_ERROR": SardisValidationError,
    "NOT_FOUND": SardisNotFoundError,
    "AUTHENTICATION_ERROR": SardisAuthenticationError,
    "AUTHORIZATION_ERROR": SardisAuthorizationError,
    "CONFLICT": SardisConflictError,
    "PAYMENT_ERROR": SardisPaymentError,
    "POLICY_VIOLATION": SardisPolicyViolationError,
    "INSUFFICIENT_BALANCE": SardisInsufficientBalanceError,
    "TRANSACTION_FAILED": SardisTransactionFailedError,
    "MANDATE_ERROR": SardisMandateError,
    "SIGNATURE_ERROR": SardisSignatureError,
    "MANDATE_EXPIRED": SardisMandateExpiredError,
    "MANDATE_REPLAY": SardisMandateReplayError,
    "MANDATE_CHAIN_INVALID": SardisMandateChainError,
    "CHAIN_ERROR": SardisChainError,
    "RPC_ERROR": SardisRPCError,
    "DATABASE_ERROR": SardisDatabaseError,
    "MPC_ERROR": SardisMPCError,
    "COMPLIANCE_ERROR": SardisComplianceError,
    "KYC_REQUIRED": SardisKYCRequiredError,
    "KYC_EXPIRED": SardisKYCExpiredError,
    "SANCTIONS_HIT": SardisSanctionsHitError,
    "TRAVEL_RULE_REQUIRED": SardisTravelRuleError,
    "ALGORITHM_NOT_SUPPORTED": SardisAlgorithmNotSupportedError,
    "HOLD_ERROR": SardisHoldError,
    "HOLD_NOT_FOUND": SardisHoldNotFoundError,
    "HOLD_EXPIRED": SardisHoldExpiredError,
    "HOLD_ALREADY_CAPTURED": SardisHoldAlreadyCapturedError,
    "HOLD_ALREADY_VOIDED": SardisHoldAlreadyVoidedError,
    "CONFIGURATION_ERROR": SardisConfigurationError,
    "DEPENDENCY_NOT_CONFIGURED": SardisDependencyNotConfiguredError,
    "RATE_LIMIT_EXCEEDED": SardisRateLimitError,
    "TIMEOUT_ERROR": SardisTimeoutError,
    "SERVICE_UNAVAILABLE": SardisServiceUnavailableError,
}


def get_exception_class(error_code: str) -> Type[SardisException]:
    """Get the exception class for an error code.

    Args:
        error_code: The error code string

    Returns:
        Exception class (defaults to SardisException if not found)
    """
    return EXCEPTION_REGISTRY.get(error_code, SardisException)


def create_exception(
    error_code: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
) -> SardisException:
    """Create an exception instance from an error code.

    Args:
        error_code: The error code string
        message: Error message
        details: Optional details dictionary

    Returns:
        Exception instance
    """
    exc_class = get_exception_class(error_code)
    return exc_class(message, details=details)
