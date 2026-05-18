"""Compatibility import for KYC onboarding routes.

New code should import from `sardis_api.routes.compliance.kyc_onboarding`.
"""
import sys

from sardis_api.routes.compliance import kyc_onboarding as _implementation

sys.modules[__name__] = _implementation
