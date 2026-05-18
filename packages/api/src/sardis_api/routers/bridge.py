"""Compatibility import for cross-chain bridge routes.

New code should import from `sardis_api.routes.money_movement.bridge`.
"""
import sys

from sardis_api.routes.money_movement import bridge as _implementation

sys.modules[__name__] = _implementation
