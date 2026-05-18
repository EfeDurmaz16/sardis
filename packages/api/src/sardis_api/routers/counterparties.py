"""Compatibility import for counterparty routes.

New code should import from `sardis_api.routes.commerce.counterparties`.
"""
import sys

from sardis_api.routes.commerce import counterparties as _implementation

sys.modules[__name__] = _implementation
