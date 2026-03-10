"""Lightspark Grid exceptions."""
from __future__ import annotations


class GridError(Exception):
    """Base exception for Grid API operations."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class GridAuthError(GridError):
    """Authentication/authorization failure."""
    pass


class GridValidationError(GridError):
    """Request validation error."""
    pass


class GridRateLimitError(GridError):
    """Rate limit exceeded."""
    pass


class GridQuoteExpiredError(GridError):
    """Transfer quote has expired."""
    pass


class GridInsufficientFundsError(GridError):
    """Insufficient funds for the operation."""
    pass


class GridWebhookVerificationError(GridError):
    """Webhook signature verification failed."""
    pass


class GridUMAResolutionError(GridError):
    """Failed to resolve UMA address."""
    pass
