"""Compatibility import for A2A payment protocol routes.

New code should import from `sardis_api.routes.protocol.a2a_payments`.
"""
import sys

from sardis_api.routes.protocol import a2a_payments as _implementation

sys.modules[__name__] = _implementation
