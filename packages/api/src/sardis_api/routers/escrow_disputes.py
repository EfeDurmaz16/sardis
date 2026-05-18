"""Compatibility import for escrow and dispute routes.

New code should import from `sardis_api.routes.commerce.escrow_disputes`.
"""
import sys

from sardis_api.routes.commerce import escrow_disputes as _implementation

sys.modules[__name__] = _implementation
