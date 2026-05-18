"""Compatibility import for MPP protocol routes.

New code should import from `sardis_api.routes.protocol.mpp`.
"""
import sys

from sardis_api.routes.protocol import mpp as _implementation

sys.modules[__name__] = _implementation
