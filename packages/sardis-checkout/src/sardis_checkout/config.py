"""Checkout configuration."""
from __future__ import annotations

import os


def get_enabled_payment_methods() -> list[str]:
    """Get list of enabled payment methods from environment config.

    Default: card, apple_pay, google_pay, link
    Optional (require Stripe activation): klarna, paypal
    """
    configured = os.getenv(
        "SARDIS_CHECKOUT_PAYMENT_METHODS",
        "card,apple_pay,google_pay,link",
    )
    return [m.strip() for m in configured.split(",") if m.strip()]
