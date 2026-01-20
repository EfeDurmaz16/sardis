"""
Sardis Checkout Surface - PSP routing and orchestration.

This package provides the checkout surface that routes agent payments
to existing PSPs (Stripe, PayPal, Coinbase, Circle) while leveraging
the core Agent Wallet OS for policy enforcement.
"""

from sardis_checkout.orchestrator import CheckoutOrchestrator
from sardis_checkout.models import (
    CheckoutRequest,
    CheckoutResponse,
    CheckoutSession,  # Legacy, for backwards compatibility
    PaymentStatus,
    PSPType,
)

__all__ = [
    "CheckoutOrchestrator",
    "CheckoutRequest",
    "CheckoutResponse",
    "CheckoutSession",  # Legacy
    "PaymentStatus",
    "PSPType",
]

__version__ = "0.1.0"
