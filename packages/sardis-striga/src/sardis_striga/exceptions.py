"""Striga provider exceptions."""
from __future__ import annotations


class StrigaError(Exception):
    """Base exception for Striga operations."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class StrigaAuthError(StrigaError):
    """Authentication/authorization failure."""
    pass


class StrigaValidationError(StrigaError):
    """Request validation error from Striga API."""
    pass


class StrigaRateLimitError(StrigaError):
    """Rate limit exceeded."""
    pass


class StrigaKYCRequiredError(StrigaError):
    """Operation requires completed KYC."""
    pass


class StrigaInsufficientFundsError(StrigaError):
    """Insufficient funds for the operation."""
    pass


class StrigaWebhookVerificationError(StrigaError):
    """Webhook signature verification failed."""
    pass
