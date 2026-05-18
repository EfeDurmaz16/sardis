"""Compatibility import for checkout control routes.

New code should import from `sardis_api.routes.commerce.checkout_controls`.
"""
import sys

from sardis_api.routes.commerce import checkout_controls as _implementation

_legacy_name = __name__
globals().update({key: value for key, value in _implementation.__dict__.items() if key != "__name__"})
sys.modules[_legacy_name] = _implementation
