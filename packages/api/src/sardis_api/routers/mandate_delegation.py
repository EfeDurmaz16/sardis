"""Compatibility import for mandate delegation routes.

New code should import from `sardis_api.routes.authority.mandate_delegation`.
"""
import sys

from sardis_api.routes.authority import mandate_delegation as _implementation

sys.modules[__name__] = _implementation
