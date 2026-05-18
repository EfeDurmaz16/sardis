"""Compatibility import for Stripe Connect routes.

New code should import from `sardis_api.routes.providers.stripe_connect`.
"""
import sys

from sardis_api.routes.providers import stripe_connect as _implementation

sys.modules[__name__] = _implementation
