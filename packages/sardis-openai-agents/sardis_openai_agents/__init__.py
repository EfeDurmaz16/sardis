"""Deprecation shim — `sardis_openai_agents` has been consolidated into `sardis.integrations.openai_agents`.

Install the umbrella package with the integration extra:

    pip install 'sardis[openai-agents]'
    from sardis.integrations.openai_agents import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_openai_agents is deprecated. Install `sardis[openai-agents]` and use "
    "`from sardis.integrations.openai_agents import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.openai_agents as _module  # noqa: E402
from sardis.integrations.openai_agents import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
