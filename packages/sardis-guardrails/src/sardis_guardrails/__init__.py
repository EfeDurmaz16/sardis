"""Deprecation shim — `sardis_guardrails` is being consolidated into `sardis.guardrails`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.guardrails import CircuitBreaker, KillSwitch, RateLimiter, ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_guardrails is deprecated. Install `sardis` and use `from sardis.guardrails import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.guardrails as _guardrails  # noqa: E402
from sardis.guardrails import *  # noqa: F401, F403, E402

# Make `from sardis_guardrails.circuit_breaker import X` resolve transparently.
__path__ = _guardrails.__path__
__version__ = getattr(_guardrails, "__version__", "0.99.0")
