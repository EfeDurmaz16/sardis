"""Deprecation shim — `sardis_cards` is being consolidated into `sardis.cards`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.cards import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_cards is deprecated. Install `sardis` and use "
    "`from sardis.cards import ...`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.cards as _module  # noqa: E402
from sardis.cards import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
