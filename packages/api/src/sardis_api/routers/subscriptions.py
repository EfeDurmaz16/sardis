"""Compatibility import for recurring subscription routes.

New code should import from `sardis_api.routes.billing.subscriptions`.
"""
import sys

from sardis_api.routes.billing import subscriptions as _implementation

sys.modules[__name__] = _implementation
