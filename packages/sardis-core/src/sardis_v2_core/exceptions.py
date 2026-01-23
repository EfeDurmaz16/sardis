"""Unified exception hierarchy for Sardis.

All Sardis-specific exceptions inherit from SardisException, enabling:
- Consistent error handling across packages
- Proper HTTP status code mapping in API layer
- Structured error responses with error codes
"""
from __future__ import annotations

from typing import Any, Optional


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
