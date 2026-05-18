"""Compatibility import for evidence route modules.

New code should import from `sardis_api.routes.evidence.evidence`.
"""
import sys

from sardis_api.routes.evidence import evidence as _implementation

sys.modules[__name__] = _implementation
