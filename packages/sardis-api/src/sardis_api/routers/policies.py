"""Compatibility import for policy route modules.

New code should import from `sardis_api.routes.policy.policies`.
"""
import sys

from sardis_api.routes.policy import policies as _implementation

sys.modules[__name__] = _implementation
