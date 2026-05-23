"""Deprecation shim — `sardis_ucp` is being consolidated into `sardis.ucp`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.ucp import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_ucp is deprecated. Install `sardis` and use "
    "`from sardis.ucp import ...`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.ucp as _module  # noqa: E402
from sardis.ucp import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
