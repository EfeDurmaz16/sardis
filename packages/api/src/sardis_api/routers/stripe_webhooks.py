"""Compatibility import for Stripe provider webhook routes.

New code should import from `sardis_api.routes.providers.stripe_webhooks`.
"""
from sardis_api.routes.providers.stripe_webhooks import *  # noqa: F401,F403
