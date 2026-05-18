"""Compatibility import for outbound webhook subscription routes.

New code should import from `sardis_api.routes.developer.webhook_subscriptions`.
"""
from sardis_api.routes.developer.webhook_subscriptions import *  # noqa: F401,F403
