"""Compatibility import for audit anchor routes.

New code should import from `sardis_api.routes.evidence.audit_anchors`.
"""
import sys

from sardis_api.routes.evidence import audit_anchors as _implementation

sys.modules[__name__] = _implementation
