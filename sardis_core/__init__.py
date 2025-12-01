"""Compatibility shim exposing legacy Sardis Core modules."""
from __future__ import annotations

import importlib
import sys

_legacy = importlib.import_module("legacy.sardis_core")

# Re-export attributes so `from sardis_core import X` continues to work
for name, value in vars(_legacy).items():
    if name.startswith("__") and name not in {"__path__", "__all__"}:
        continue
    globals()[name] = value

__all__ = getattr(_legacy, "__all__", [])
__path__ = _legacy.__path__
sys.modules[__name__] = _legacy
