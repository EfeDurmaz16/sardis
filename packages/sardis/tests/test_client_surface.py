"""Smoke tests for the public thin-client surface of the ``sardis`` package.

The engine modules (core, chain, cards, checkout, compliance, wallet, ledger,
ramp, guardrails, ucp, protocol) live in the private service repository and are
NOT part of this public package. These tests assert that:

  1. The advertised client surface imports cleanly.
  2. The engine modules are genuinely absent (no policy-bypassing executor, no
     backend dependency bloat leaks into the published wheel).
"""

from __future__ import annotations

import importlib

import pytest

import sardis

CLIENT_SUBMODULES = (
    "sardis._client",
    "sardis._version",
    "sardis.bulk",
    "sardis.pagination",
    "sardis.telemetry",
    "sardis.cli",
    "sardis.integrations",
    "sardis.models",
    "sardis.resources",
)

ENGINE_SUBMODULES = (
    "core",
    "chain",
    "cards",
    "checkout",
    "compliance",
    "wallet",
    "ledger",
    "ramp",
    "guardrails",
    "ucp",
    "protocol",
)


def test_version_is_exposed() -> None:
    assert isinstance(sardis.__version__, str)
    assert sardis.__version__


def test_top_level_client_classes_import() -> None:
    from sardis import AsyncSardis, Sardis

    assert Sardis.__name__ == "Sardis"
    assert AsyncSardis.__name__ == "AsyncSardis"


@pytest.mark.parametrize("module_name", CLIENT_SUBMODULES)
def test_client_submodules_import(module_name: str) -> None:
    assert importlib.import_module(module_name) is not None


@pytest.mark.parametrize("engine_name", ENGINE_SUBMODULES)
def test_engine_submodules_are_absent(engine_name: str) -> None:
    with pytest.raises(AttributeError):
        getattr(sardis, engine_name)
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"sardis.{engine_name}")
