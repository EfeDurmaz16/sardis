"""Deprecation shim — `sardis_ledger` is being consolidated into `sardis.ledger`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.ledger import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_ledger is deprecated. Install `sardis` and use `from sardis.ledger import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.ledger as _mod  # noqa: E402
from sardis.ledger import *  # noqa: F401, F403, E402

__path__ = _mod.__path__
__version__ = getattr(_mod, "__version__", "0.99.0")
