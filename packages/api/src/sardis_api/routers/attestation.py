"""Compatibility import for attestation routes.

New code should import from `sardis_api.routes.evidence.attestation`.
"""
import sys

from sardis_api.routes.evidence import attestation as _implementation

sys.modules[__name__] = _implementation
