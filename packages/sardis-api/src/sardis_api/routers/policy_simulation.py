"""Compatibility import for policy simulation routes.

New code should import from `sardis_api.routes.policy.policy_simulation`.
"""
import sys

from sardis_api.routes.policy import policy_simulation as _implementation

sys.modules[__name__] = _implementation
