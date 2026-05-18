"""Compatibility import for developer utility routes.

New code should import from `sardis_api.routes.developer.dev`.
"""
import sys

from sardis_api.routes.developer import dev as _implementation

sys.modules[__name__] = _implementation
