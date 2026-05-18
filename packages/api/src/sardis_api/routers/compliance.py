"""Compatibility import for compliance routes.

New code should import from `sardis_api.routes.compliance.compliance`.
"""
import sys

from sardis_api.routes.compliance import compliance as _implementation

sys.modules[__name__] = _implementation
