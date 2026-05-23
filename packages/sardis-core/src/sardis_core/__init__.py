"""Deprecation shim — `sardis_core` is being consolidated into `sardis.core`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.core import Wallet, retry, ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_core is deprecated. Install `sardis` and use "
    "`from sardis.core import ...`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.core as _core  # noqa: E402
from sardis.core import *  # noqa: F401, F403, E402

# Rebind __path__ so `from sardis_core.<submodule> import X`
# resolves to `sardis.core.<submodule>`.
__path__ = _core.__path__
__version__ = getattr(_core, "__version__", "0.99.0")
