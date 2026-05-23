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

# Re-export submodules for `from sardis_sdk.resources import ...` compatibility.
import sardis as _root
import sardis.models
import sardis.resources
from sardis import AsyncSardis, Sardis
from sardis import AsyncSardis as AsyncSardisClient
from sardis import Sardis as SardisClient

__all__ = ["AsyncSardis", "AsyncSardisClient", "Sardis", "SardisClient"]
__version__ = getattr(_root, "__version__", "0.99.0")
