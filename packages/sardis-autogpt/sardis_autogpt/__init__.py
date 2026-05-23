"""Deprecation shim — `sardis_autogpt` has been consolidated into `sardis.integrations.autogpt`.

Install the umbrella package with the integration extra:

    pip install 'sardis[autogpt]'
    from sardis.integrations.autogpt import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_autogpt is deprecated. Install `sardis[autogpt]` and use "
    "`from sardis.integrations.autogpt import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.autogpt as _module  # noqa: E402
from sardis.integrations.autogpt import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
