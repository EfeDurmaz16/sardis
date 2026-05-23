"""Deprecation shim — `sardis_ramp` is being consolidated into `sardis.ramp`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.ramp import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_ramp is deprecated. Install `sardis` and use "
    "`from sardis.ramp import ...`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.ramp as _module  # noqa: E402
from sardis.ramp import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
