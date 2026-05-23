"""Deprecation shim — `sardis_adk` has been consolidated into `sardis.integrations.adk`.

Install the umbrella package with the integration extra:

    pip install 'sardis[adk]'
    from sardis.integrations.adk import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_adk is deprecated. Install `sardis[adk]` and use "
    "`from sardis.integrations.adk import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.adk as _module  # noqa: E402
from sardis.integrations.adk import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
