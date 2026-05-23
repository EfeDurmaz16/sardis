"""Deprecation shim — `sardis_cli` has been consolidated into `sardis.cli`.

Install the umbrella package and use the `sardis` command directly:

    pip install sardis
    sardis --help

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_cli is deprecated. Install `sardis` and use `sardis` on the "
    "command line (or `from sardis.cli import ...`). This shim will be "
    "removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.cli as _cli  # noqa: E402
from sardis.cli import *  # noqa: F401, F403, E402

__path__ = _cli.__path__
__version__ = getattr(_cli, "__version__", "0.99.0")
