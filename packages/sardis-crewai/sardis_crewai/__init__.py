"""Deprecation shim — `sardis_crewai` has been consolidated into `sardis.integrations.crewai`.

Install the umbrella package with the integration extra:

    pip install 'sardis[crewai]'
    from sardis.integrations.crewai import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_crewai is deprecated. Install `sardis[crewai]` and use "
    "`from sardis.integrations.crewai import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.crewai as _module  # noqa: E402
from sardis.integrations.crewai import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
