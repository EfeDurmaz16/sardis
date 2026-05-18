"""Compatibility import for policy analytics routes.

New code should import from `sardis_api.routes.policy.policy_analytics`.
"""
import sys

from sardis_api.routes.policy import policy_analytics as _implementation

sys.modules[__name__] = _implementation
