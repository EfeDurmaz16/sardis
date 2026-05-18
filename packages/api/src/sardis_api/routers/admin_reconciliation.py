"""Compatibility import for admin reconciliation routes.

New code should import from `sardis_api.routes.admin.reconciliation`.
"""
import sys

from sardis_api.routes.admin import reconciliation as _implementation

sys.modules[__name__] = _implementation
