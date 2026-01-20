"""Error models for Sardis SDK."""
from __future__ import annotations

from typing import Any, Optional


class SardisError(Exception):
    """Base exception for Sardis SDK."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "SARDIS_ERROR"
        self.details = details or {}
        self.request_id = request_id
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "request_id": self.request_id,
            }
        }


class APIError(SardisError):
    """Error from API response."""
    
    def __init__(
        self,
        message: str,
        status_code: int,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message, code, details, request_id)
        self.status_code = status_code
    
    @classmethod
    def from_response(cls, status_code: int, body: dict[str, Any]) -> "APIError":
        """Create APIError from HTTP response."""
        error_data = body.get("error", body.get("detail", {}))
        if isinstance(error_data, str):
            return cls(
                message=error_data,
                status_code=status_code,
                code="API_ERROR",
            )
        if isinstance(error_data, list):
            return cls(
                message="Validation Error",
                status_code=status_code,
                code="VALIDATION_ERROR",
                details={"errors": error_data},
            )
        return cls(
            message=error_data.get("message", "Unknown error"),
            status_code=status_code,
            code=error_data.get("code", "API_ERROR"),
            details=error_data.get("details"),
            request_id=error_data.get("request_id"),
        )


class ValidationError(SardisError):
    """Validation error."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field})
        self.field = field


class InsufficientBalanceError(SardisError):
    """Insufficient balance error."""
    
    def __init__(
        self,
        message: str,
        required: str,
        available: str,
        currency: str,
    ):
        super().__init__(
            message,
            code="INSUFFICIENT_BALANCE",
            details={
                "required": required,
                "available": available,
                "currency": currency,
            },
        )
        self.required = required
        self.available = available
        self.currency = currency


class RateLimitError(SardisError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, code="RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class AuthenticationError(SardisError):
    """Authentication error."""
    
    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, code="AUTHENTICATION_ERROR")


class NotFoundError(SardisError):
    """Resource not found error."""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            code="NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )
        self.resource_type = resource_type
        self.resource_id = resource_id
