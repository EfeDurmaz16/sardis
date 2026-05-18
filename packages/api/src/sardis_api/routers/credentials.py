"""Compatibility import for delegated credential routes.

New code should import from `sardis_api.routes.authority.credentials`.
"""
import sys

from sardis_api.routes.authority import credentials as _implementation

sys.modules[__name__] = _implementation
