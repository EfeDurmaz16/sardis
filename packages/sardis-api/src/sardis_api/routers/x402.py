"""Compatibility import for x402 protocol routes.

New code should import from `sardis_api.routes.protocol.x402`.
"""
import sys

from sardis_api.routes.protocol import x402 as _implementation

sys.modules[__name__] = _implementation
