"""Compatibility import for evidence export routes.

New code should import from `sardis_api.routes.evidence.evidence_export`.
"""
import sys

from sardis_api.routes.evidence import evidence_export as _implementation

sys.modules[__name__] = _implementation
