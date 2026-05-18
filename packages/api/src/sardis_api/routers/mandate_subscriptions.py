"""Compatibility import for mandate subscription routes.

New code should import from `sardis_api.routes.authority.mandate_subscriptions`.
"""
import sys

from sardis_api.routes.authority import mandate_subscriptions as _implementation

sys.modules[__name__] = _implementation
