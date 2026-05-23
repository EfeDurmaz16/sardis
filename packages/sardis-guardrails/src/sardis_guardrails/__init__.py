"""Deprecation shim — `sardis_guardrails` is being consolidated into `sardis.guardrails`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.guardrails import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_guardrails is deprecated. Install `sardis` and use "
    "`from sardis.guardrails import ...`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.guardrails as _new  # noqa: E402

# Re-bind __path__ so submodule imports work (e.g., from sardis_guardrails.foo import X)
__path__ = _new.__path__


def __getattr__(name):
    """Transparent passthrough — any name access falls through to sardis.guardrails."""
    return getattr(_new, name)


def __dir__():
    return dir(_new)
