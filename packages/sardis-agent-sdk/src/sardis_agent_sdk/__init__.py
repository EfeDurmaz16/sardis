"""Deprecation shim — `sardis_agent_sdk` has been consolidated into `sardis.integrations.anthropic`.

Install the umbrella package with the integration extra:

    pip install 'sardis[agent-sdk]'
    from sardis.integrations.anthropic import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_agent_sdk is deprecated. Install `sardis[agent-sdk]` and use "
    "`from sardis.integrations.anthropic import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.anthropic as _module  # noqa: E402
from sardis.integrations.anthropic import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
