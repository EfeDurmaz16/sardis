"""Compatibility import for Shared Payment Token protocol routes.

New code should import from `sardis_api.routes.protocol.spt`.
"""
import sys

from sardis_api.routes.protocol import spt as _implementation

sys.modules[__name__] = _implementation
