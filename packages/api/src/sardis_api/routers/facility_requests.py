"""Compatibility import for facility authority routes.

New code should import from `sardis_api.routes.authority.facility_requests`.
"""
import sys

from sardis_api.routes.authority import facility_requests as _implementation

sys.modules[__name__] = _implementation
