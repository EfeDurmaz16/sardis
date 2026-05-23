"""Deprecation shim — `sardis_langchain` has been consolidated into `sardis.integrations.langchain`.

Install the umbrella package with the integration extra:

    pip install 'sardis[langchain]'
    from sardis.integrations.langchain import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_langchain is deprecated. Install `sardis[langchain]` and use "
    "`from sardis.integrations.langchain import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.integrations.langchain as _module  # noqa: E402
from sardis.integrations.langchain import *  # noqa: F401, F403, E402

__path__ = _module.__path__
__version__ = getattr(_module, "__version__", "0.99.0")
