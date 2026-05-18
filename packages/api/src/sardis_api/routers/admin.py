"""Compatibility import for admin control routes.

New code should import from `sardis_api.routes.admin.control`.
"""
import sys

from sardis_api.routes.admin import control as _implementation

sys.modules[__name__] = _implementation
