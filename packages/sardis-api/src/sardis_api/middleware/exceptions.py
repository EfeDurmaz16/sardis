"""Global exception handler middleware for Sardis API.

Provides consistent error responses for all exception types with:
- Proper HTTP status codes
- Structured error response format
- Request ID correlation
- Secure error messaging (no internal details in production)
"""
from __future__ import annotations

import logging
import os
import traceback
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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


def get_request_id(request: Request) -> str:
    """Extract request ID from request state or headers."""
    # Check request state first (set by logging middleware)
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    # Fall back to header
    return request.headers.get("X-Request-ID", "unknown")


def is_production() -> bool:
    """Check if running in production environment."""
    env = os.getenv("SARDIS_ENVIRONMENT", "dev")
    return env in ("production", "prod")


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    request_id: str,
    details: dict | None = None,
) -> JSONResponse:
    """Create a standardized error response."""
    content = {
        "error": error_code,
        "message": message,
        "request_id": request_id,
    }
    if details:
        content["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    
    @app.exception_handler(SardisException)
    async def sardis_exception_handler(
        request: Request, exc: SardisException
    ) -> JSONResponse:
        """Handle all Sardis-specific exceptions."""
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
        )
    
    @app.exception_handler(SardisRateLimitError)
    async def rate_limit_handler(
        request: Request, exc: SardisRateLimitError
    ) -> JSONResponse:
        """Handle rate limit exceeded errors with Retry-After header."""
        request_id = get_request_id(request)
        
        logger.warning(
            f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}",
            extra={"request_id": request_id},
        )
        
        headers = {"X-Request-ID": request_id}
        retry_after = exc.details.get("retry_after_seconds")
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": exc.message,
                "request_id": request_id,
            },
            headers=headers,
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Handle ValueError as validation error."""
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
        )
    
    @app.exception_handler(PermissionError)
    async def permission_error_handler(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Handle PermissionError as authorization error."""
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
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all handler for unhandled exceptions.
        
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
            )
