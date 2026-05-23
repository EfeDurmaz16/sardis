"""Deprecation shim — `sardis_composio` has been consolidated into `sardis.integrations.composio`.

Install the umbrella package with the integration extra:

    pip install 'sardis[composio]'
    from sardis.integrations.composio import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_composio is deprecated. Install `sardis[composio]` and use "
    "`from sardis.integrations.composio import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.composio as _module  # noqa: E402
from sardis.integrations.composio import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
