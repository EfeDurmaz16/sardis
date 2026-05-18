"""Compatibility import for secure checkout routes.

New code should import from `sardis_api.routes.commerce.secure_checkout`.
"""
import sys

from sardis_api.routes.commerce import secure_checkout as _implementation

sys.modules[__name__] = _implementation
