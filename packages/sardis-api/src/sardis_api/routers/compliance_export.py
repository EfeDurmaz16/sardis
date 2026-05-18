"""Compatibility import for compliance export routes.

New code should import from `sardis_api.routes.compliance.compliance_export`.
"""
import sys

from sardis_api.routes.compliance import compliance_export as _implementation

sys.modules[__name__] = _implementation
