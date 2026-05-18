"""Compatibility import for emergency operations routes.

New code should import from `sardis_api.routes.operations.emergency`.
"""
import sys

from sardis_api.routes.operations import emergency as _implementation

sys.modules[__name__] = _implementation
