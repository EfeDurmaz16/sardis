"""Compatibility import for A2A protocol routes.

New code should import from `sardis_api.routes.protocol.a2a`.
"""
import sys

from sardis_api.routes.protocol import a2a as _implementation

sys.modules[__name__] = _implementation
