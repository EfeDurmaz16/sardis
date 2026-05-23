"""sardis — Payment OS for the Agent Economy.

Public surface is intentionally tiny so ``import sardis`` stays fast.
Submodules (``sardis.core``, ``sardis.cards``, etc.) load lazily via PEP 562
``__getattr__`` only when accessed.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from sardis._version import __version__

if TYPE_CHECKING:
    from sardis._client import AsyncSardis, Sardis

__all__ = ["Sardis", "AsyncSardis", "__version__"]

_LAZY_SUBMODULES = frozenset({
    "core", "cards", "ledger", "chain", "ucp", "protocol",
    "compliance", "guardrails", "checkout", "wallet", "ramp",
    "cli", "integrations",
})


def __getattr__(name: str) -> Any:
    if name in {"Sardis", "AsyncSardis"}:
        module = importlib.import_module("sardis._client")
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _LAZY_SUBMODULES:
        module = importlib.import_module(f"sardis.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module 'sardis' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_SUBMODULES, "Sardis", "AsyncSardis"})
