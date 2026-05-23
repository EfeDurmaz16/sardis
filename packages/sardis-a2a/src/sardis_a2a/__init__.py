"""Deprecation shim — `sardis_a2a` has been consolidated into `sardis.integrations.a2a`.

Install the umbrella package with the integration extra:

    pip install 'sardis[a2a]'
    from sardis.integrations.a2a import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_a2a is deprecated. Install `sardis[a2a]` and use "
    "`from sardis.integrations.a2a import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.a2a as _module  # noqa: E402
from sardis.integrations.a2a import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
