"""
Sardis Python SDK

A comprehensive SDK for interacting with the Sardis stablecoin execution layer.
"""

from .client import SardisClient
from .models.errors import (
    APIError,
    AuthenticationError,
    InsufficientBalanceError,
    NotFoundError,
    RateLimitError,
    SardisError,
    ValidationError,
)
from .models.hold import Hold, HoldStatus, CreateHoldRequest, CaptureHoldRequest
from .models.payment import (
    Payment,
    PaymentStatus,
    ExecutePaymentRequest,
    ExecutePaymentResponse,
    ExecuteAP2Request,
    ExecuteAP2Response,
)
from .models.webhook import Webhook, WebhookEvent, WebhookEventType
from .models.marketplace import (
    Service,
    ServiceOffer,
    ServiceCategory,
    ServiceStatus,
    OfferStatus,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "SardisClient",
    # Errors
    "SardisError",
    "APIError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "InsufficientBalanceError",
    "NotFoundError",
    # Payment models
    "Payment",
    "PaymentStatus",
    "ExecutePaymentRequest",
    "ExecutePaymentResponse",
    "ExecuteAP2Request",
    "ExecuteAP2Response",
    # Hold models
    "Hold",
    "HoldStatus",
    "CreateHoldRequest",
    "CaptureHoldRequest",
    # Webhook models
    "Webhook",
    "WebhookEvent",
    "WebhookEventType",
    # Marketplace models
    "Service",
    "ServiceOffer",
    "ServiceCategory",
    "ServiceStatus",
    "OfferStatus",
]
