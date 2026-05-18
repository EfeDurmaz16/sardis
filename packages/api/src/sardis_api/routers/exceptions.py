"""Compatibility import for exception management routes.

New code should import from `sardis_api.routes.operations.exceptions`.
"""
import sys

from sardis_api.routes.operations import exceptions as _implementation

sys.modules[__name__] = _implementation
