"""Compatibility import for developer sandbox routes.

New code should import from `sardis_api.routes.developer.sandbox`.
"""
import sys

from sardis_api.routes.developer import sandbox as _implementation

sys.modules[__name__] = _implementation
