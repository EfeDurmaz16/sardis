"""Compatibility import for MPP demo routes.

New code should import from `sardis_api.routes.protocol.mpp_demo`.
"""
import sys

from sardis_api.routes.protocol import mpp_demo as _implementation

sys.modules[__name__] = _implementation
