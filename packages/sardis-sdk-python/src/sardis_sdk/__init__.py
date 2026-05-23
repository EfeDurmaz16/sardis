"""Deprecation shim — `sardis_sdk` has been consolidated into `sardis`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis import Sardis, AsyncSardis

This shim will be removed 2026-11-23 (6-month sunset window).

Class renames (kept as aliases here):
    sardis_sdk.SardisClient        -> sardis.Sardis
    sardis_sdk.AsyncSardisClient   -> sardis.AsyncSardis
"""
import warnings

warnings.warn(
    "sardis_sdk is deprecated. Install `sardis` and use "
    "`from sardis import Sardis, AsyncSardis`. This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

from sardis import Sardis, AsyncSardis  # noqa: E402,F401
from sardis import Sardis as SardisClient  # noqa: E402
from sardis import AsyncSardis as AsyncSardisClient  # noqa: E402

# Re-export submodules for `from sardis_sdk.resources import ...` compatibility.
import sardis as _root  # noqa: E402
import sardis.resources  # noqa: E402,F401
import sardis.models  # noqa: E402,F401

__all__ = ["Sardis", "AsyncSardis", "SardisClient", "AsyncSardisClient"]
__version__ = getattr(_root, "__version__", "0.99.0")
