"""Compatibility import for fallback policy routes.

New code should import from `sardis_api.routes.policy.fallback_policies`.
"""
import sys

from sardis_api.routes.policy import fallback_policies as _implementation

sys.modules[__name__] = _implementation
