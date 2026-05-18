"""Compatibility import for spending mandate routes.

New code should import from `sardis_api.routes.authority.spending_mandates`.
"""
import sys

from sardis_api.routes.authority import spending_mandates as _implementation

sys.modules[__name__] = _implementation
