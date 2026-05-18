"""Compatibility import for trust routes.

New code should import from `sardis_api.routes.identity.trust`.
"""
import sys

from sardis_api.routes.identity import trust as _implementation

sys.modules[__name__] = _implementation
