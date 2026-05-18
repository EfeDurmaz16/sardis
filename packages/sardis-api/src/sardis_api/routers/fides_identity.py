"""Compatibility import for FIDES identity routes.

New code should import from `sardis_api.routes.identity.fides_identity`.
"""
import sys

from sardis_api.routes.identity import fides_identity as _implementation

sys.modules[__name__] = _implementation
