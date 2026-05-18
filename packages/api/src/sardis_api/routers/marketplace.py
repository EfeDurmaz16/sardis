"""Compatibility import for marketplace routes.

New code should import from `sardis_api.routes.commerce.marketplace`.
"""
import sys

from sardis_api.routes.commerce import marketplace as _implementation

sys.modules[__name__] = _implementation
