"""Deprecation shim — `sardis_wallet` is being consolidated into `sardis.wallet`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.wallet import ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_wallet is deprecated. Install `sardis` and use "
    "`from sardis.wallet import ...`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.wallet as _new  # noqa: E402

# Re-bind __path__ so submodule imports work (e.g., from sardis_wallet.foo import X)
__path__ = _new.__path__


def __getattr__(name):
    """Transparent passthrough — any name access falls through to sardis.wallet."""
    return getattr(_new, name)


def __dir__():
    return dir(_new)
