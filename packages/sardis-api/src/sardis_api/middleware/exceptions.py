"""Global exception handler middleware for Sardis API.

Provides RFC 7807 Problem Details compliant error responses with:
- Proper HTTP status codes
- Standardized error format (RFC 7807)
- Request ID correlation
- Secure error messaging (no internal details in production)
- Error categorization and logging

RFC 7807 Problem Details Format:
{
    "type": "https://api.sardis.io/errors/<error-type>",
    "title": "Human-readable error title",
    "status": 400,
    "detail": "Detailed error description",
    "instance": "/api/v2/resource/123",
    "request_id": "req_abc123",
    ... additional fields
}
"""
from __future__ import annotations

import logging
import os
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from sardis_v2_core.exceptions import (
    SardisException,
    SardisDependencyNotConfiguredError,
    SardisValidationError,
    SardisNotFoundError,
    SardisAuthenticationError,
    SardisAuthorizationError,
    SardisRateLimitError,
)

logger = logging.getLogger(__name__)

# Base URL for error type URIs
ERROR_TYPE_BASE = "https://api.sardis.io/errors"


@dataclass
class RFC7807Error:
    """RFC 7807 Problem Details representation."""
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
    extensions: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to RFC 7807 compliant dictionary."""
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": self.instance,
            "request_id": self.request_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if self.extensions:
            result.update(self.extensions)
        return result


# Error type mappings for consistent error URIs
ERROR_TYPES = {
    "VALIDATION_ERROR": ("validation-error", "Validation Error"),
    "NOT_FOUND": ("not-found", "Resource Not Found"),
    "AUTHENTICATION_REQUIRED": ("authentication-required", "Authentication Required"),
    "INVALID_CREDENTIALS": ("invalid-credentials", "Invalid Credentials"),
    "FORBIDDEN": ("forbidden", "Access Denied"),
    "INSUFFICIENT_PERMISSIONS": ("insufficient-permissions", "Insufficient Permissions"),
    "RATE_LIMIT_EXCEEDED": ("rate-limit-exceeded", "Rate Limit Exceeded"),
    "SERVICE_UNAVAILABLE": ("service-unavailable", "Service Unavailable"),
    "INTERNAL_ERROR": ("internal-error", "Internal Server Error"),
    "BAD_REQUEST": ("bad-request", "Bad Request"),
    "CONFLICT": ("conflict", "Resource Conflict"),
    "UNPROCESSABLE_ENTITY": ("unprocessable-entity", "Unprocessable Entity"),
    "METHOD_NOT_ALLOWED": ("method-not-allowed", "Method Not Allowed"),
    "REQUEST_ENTITY_TOO_LARGE": ("request-entity-too-large", "Request Entity Too Large"),
    "UNSUPPORTED_MEDIA_TYPE": ("unsupported-media-type", "Unsupported Media Type"),
}


def get_request_id(request: Request) -> str:
    """Extract request ID from request state or headers."""
    # Check request state first (set by logging middleware)
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    # Fall back to header
    return request.headers.get("X-Request-ID", "unknown")


def is_production() -> bool:
    """Check if running in a production-like environment.

    SECURITY: Staging environments should also hide internal details (tracebacks,
    dependency names, etc.) since they are often network-accessible and may share
    production data. Only dev/test/local are considered safe for verbose errors.
    """
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    # Only dev/test/local show verbose errors; everything else is treated as production
    return env not in ("dev", "test", "local")


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    request_id: str,
    details: dict | None = None,
    instance: str = "",
) -> JSONResponse:
    """
    Create an RFC 7807 compliant error response.

    Args:
        error_code: Internal error code (e.g., "VALIDATION_ERROR")
        message: Human-readable error message
        status_code: HTTP status code
        request_id: Request correlation ID
        details: Additional error details (extensions)
        instance: Request path/instance identifier

    Returns:
        JSONResponse with RFC 7807 Problem Details format
    """
    # Get error type and title from mapping, or use defaults
    type_info = ERROR_TYPES.get(error_code, (error_code.lower().replace("_", "-"), error_code.replace("_", " ").title()))
    error_uri = f"{ERROR_TYPE_BASE}/{type_info[0]}"
    error_title = type_info[1]

    error = RFC7807Error(
        type=error_uri,
        title=error_title,
        status=status_code,
        detail=message,
        instance=instance,
        request_id=request_id,
        extensions=details,
    )

    return JSONResponse(
        status_code=status_code,
        content=error.to_dict(),
        headers={
            "X-Request-ID": request_id,
            "Content-Type": "application/problem+json",
        },
    )


def create_validation_error_response(
    errors: list,
    request_id: str,
    instance: str,
) -> JSONResponse:
    """
    Create RFC 7807 response for validation errors.

    Includes detailed field-level errors in the 'errors' extension.
    """
    error = RFC7807Error(
        type=f"{ERROR_TYPE_BASE}/validation-error",
        title="Validation Error",
        status=422,
        detail="One or more fields failed validation",
        instance=instance,
        request_id=request_id,
        extensions={"errors": errors},
    )

    return JSONResponse(
        status_code=422,
        content=error.to_dict(),
        headers={
            "X-Request-ID": request_id,
            "Content-Type": "application/problem+json",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""

    # Ensure middleware-level exceptions are converted to RFC 7807 responses
    # when this helper is used directly in tests/minimal apps.
    app.add_middleware(ExceptionHandlerMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors with RFC 7807 format."""
        request_id = get_request_id(request)

        # Format validation errors for the response
        errors = []
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
            })

        logger.warning(
            f"Validation error: {len(errors)} field(s) failed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "errors": errors,
            },
        )

        return create_validation_error_response(
            errors=errors,
            request_id=request_id,
            instance=request.url.path,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions with RFC 7807 format."""
        request_id = get_request_id(request)

        # Map status codes to error codes
        status_to_code = {
            400: "BAD_REQUEST",
            401: "AUTHENTICATION_REQUIRED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            413: "REQUEST_ENTITY_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "UNPROCESSABLE_ENTITY",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_ERROR",
            502: "SERVICE_UNAVAILABLE",
            503: "SERVICE_UNAVAILABLE",
            504: "SERVICE_UNAVAILABLE",
        }

        error_code = status_to_code.get(exc.status_code, "INTERNAL_ERROR")

        if exc.status_code >= 500:
            logger.error(
                f"HTTP error {exc.status_code}: {exc.detail}",
                extra={"request_id": request_id, "path": request.url.path},
            )
        else:
            logger.warning(
                f"HTTP error {exc.status_code}: {exc.detail}",
                extra={"request_id": request_id, "path": request.url.path},
            )

        return create_error_response(
            error_code=error_code,
            message=str(exc.detail) if exc.detail else "An error occurred",
            status_code=exc.status_code,
            request_id=request_id,
            instance=request.url.path,
        )

    @app.exception_handler(SardisException)
    async def sardis_exception_handler(
        request: Request, exc: SardisException
    ) -> JSONResponse:
        """Handle all Sardis-specific exceptions with RFC 7807 format."""
        request_id = get_request_id(request)

        # Log at appropriate level based on status code
        if exc.http_status >= 500:
            logger.error(
                f"Server error: {exc.error_code} - {exc.message}",
                extra={
                    "request_id": request_id,
                    "error_code": exc.error_code,
                    "details": exc.details,
                },
                exc_info=True,
            )
        elif exc.http_status >= 400:
            logger.warning(
                f"Client error: {exc.error_code} - {exc.message}",
                extra={
                    "request_id": request_id,
                    "error_code": exc.error_code,
                },
            )

        # Build response
        details = exc.details if not is_production() or exc.http_status < 500 else None

        return create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.http_status,
            request_id=request_id,
            details=details,
            instance=request.url.path,
        )

    @app.exception_handler(SardisDependencyNotConfiguredError)
    async def dependency_not_configured_handler(
        request: Request, exc: SardisDependencyNotConfiguredError
    ) -> JSONResponse:
        """Handle missing dependency errors (503 Service Unavailable)."""
        request_id = get_request_id(request)

        logger.error(
            f"Dependency not configured: {exc.details.get('dependency', 'unknown')}",
            extra={
                "request_id": request_id,
                "dependency": exc.details.get("dependency"),
            },
        )

        # In production, don't expose which dependency is missing
        message = (
            "Service temporarily unavailable"
            if is_production()
            else exc.message
        )

        return create_error_response(
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=503,
            request_id=request_id,
            instance=request.url.path,
        )

    @app.exception_handler(SardisRateLimitError)
    async def rate_limit_handler(
        request: Request, exc: SardisRateLimitError
    ) -> JSONResponse:
        """Handle rate limit exceeded errors with RFC 7807 format and Retry-After header."""
        request_id = get_request_id(request)

        logger.warning(
            f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}",
            extra={"request_id": request_id},
        )

        retry_after = exc.details.get("retry_after_seconds", 60)

        error = RFC7807Error(
            type=f"{ERROR_TYPE_BASE}/rate-limit-exceeded",
            title="Rate Limit Exceeded",
            status=429,
            detail=exc.message,
            instance=request.url.path,
            request_id=request_id,
            extensions={
                "retry_after_seconds": retry_after,
            },
        )

        return JSONResponse(
            status_code=429,
            content=error.to_dict(),
            headers={
                "X-Request-ID": request_id,
                "Retry-After": str(retry_after),
                "Content-Type": "application/problem+json",
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Handle ValueError as validation error with RFC 7807 format."""
        request_id = get_request_id(request)

        logger.warning(
            f"Validation error: {exc}",
            extra={"request_id": request_id},
        )

        return create_error_response(
            error_code="VALIDATION_ERROR",
            message=str(exc),
            status_code=400,
            request_id=request_id,
            instance=request.url.path,
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Handle PermissionError as authorization error with RFC 7807 format."""
        request_id = get_request_id(request)

        logger.warning(
            f"Permission denied: {exc}",
            extra={"request_id": request_id},
        )

        return create_error_response(
            error_code="FORBIDDEN",
            message="Permission denied",
            status_code=403,
            request_id=request_id,
            instance=request.url.path,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all handler for unhandled exceptions with RFC 7807 format.

        In production, returns generic error without details.
        In development, includes exception type and message.
        """
        request_id = get_request_id(request)

        # Always log the full exception
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc}",
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
            },
            exc_info=True,
        )

        if is_production():
            # Generic message in production
            message = "An internal error occurred"
            details = None
        else:
            # Include details in development
            message = f"{type(exc).__name__}: {exc}"
            details = {
                "exception_type": type(exc).__name__,
                "traceback": traceback.format_exc().split("\n")[-10:],
            }

        return create_error_response(
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=500,
            request_id=request_id,
            details=details,
            instance=request.url.path,
        )


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware wrapper for exception handling.

    This provides an additional layer of exception handling that catches
    errors that occur outside of route handlers (e.g., in other middleware).
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> JSONResponse:
        try:
            return await call_next(request)
        except SardisException as exc:
            # Let the exception handlers deal with it
            raise
        except Exception as exc:
            # Log and return generic error for middleware-level exceptions
            request_id = get_request_id(request)

            logger.error(
                f"Middleware exception: {type(exc).__name__}: {exc}",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                },
                exc_info=True,
            )

            message = (
                "An internal error occurred"
                if is_production()
                else f"{type(exc).__name__}: {exc}"
            )

            return create_error_response(
                error_code="INTERNAL_ERROR",
                message=message,
                status_code=500,
                request_id=request_id,
                instance=request.url.path,
            )
