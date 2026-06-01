"""sardis — Payment OS for the Agent Economy.

Public surface is intentionally tiny so ``import sardis`` stays fast.
The thin-client submodules (``sardis.cli``, ``sardis.integrations``) load
lazily via PEP 562 ``__getattr__`` only when accessed.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from sardis._version import __version__

if TYPE_CHECKING:
    from sardis._client import AsyncSardis, Sardis

__all__ = ["Sardis", "AsyncSardis", "__version__"]

# Public, advertised submodules shipped in the published wheel. The thin-client
# surface only — the CLI and the framework integrations. The backend engine
# (core, chain, cards, checkout, compliance, wallet, ledger, ucp, ramp,
# guardrails, protocol) lives in the private service repository and is not part
# of this public package.
_LAZY_SUBMODULES = frozenset({
    "cli", "integrations",
})


# Backward-compat aliases (legacy SardisClient -> Sardis; will be removed in v2.0.0)
_LEGACY_ALIASES = {
    "SardisClient": "Sardis",
    "AsyncSardisClient": "AsyncSardis",
}


def __getattr__(name: str) -> Any:
    # Legacy alias passthrough
    if name in _LEGACY_ALIASES:
        target = _LEGACY_ALIASES[name]
        module = importlib.import_module("sardis._client")
        value = getattr(module, target)
        globals()[name] = value
        return value
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
    # Only advertise the published thin-client surface.
    return sorted({*globals(), *_LAZY_SUBMODULES, "Sardis", "AsyncSardis", *_LEGACY_ALIASES})
