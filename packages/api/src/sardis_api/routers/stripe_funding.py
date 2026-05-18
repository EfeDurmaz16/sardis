"""Compatibility import for Stripe funding routes.

New code should import from `sardis_api.routes.providers.stripe_funding`.
"""
import sys

from sardis_api.routes.providers import stripe_funding as _implementation

sys.modules[__name__] = _implementation
