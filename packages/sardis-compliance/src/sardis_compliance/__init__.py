"""Deprecation shim — `sardis_compliance` is being consolidated into `sardis.compliance`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.compliance import KYAProvider, KYCProvider, RiskScorer, ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_compliance is deprecated. Install `sardis` and use `from sardis.compliance import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.compliance as _compliance  # noqa: E402
from sardis.compliance import *  # noqa: F401, F403, E402

# Make `from sardis_compliance.kyc import X` resolve to `sardis.compliance.kyc`.
__path__ = _compliance.__path__
__version__ = getattr(_compliance, "__version__", "0.99.0")
