"""Deprecation shim — `sardis_browser_use` has been consolidated into `sardis.integrations.browser_use`.

Install the umbrella package with the integration extra:

    pip install 'sardis[browser-use]'
    from sardis.integrations.browser_use import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_browser_use is deprecated. Install `sardis[browser-use]` and use "
    "`from sardis.integrations.browser_use import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.browser_use as _module  # noqa: E402
from sardis.integrations.browser_use import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
