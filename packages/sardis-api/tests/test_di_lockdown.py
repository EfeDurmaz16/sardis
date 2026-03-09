"""Tests for DI container lockdown — chain_executor is private.

Ensures that:
1. ``_chain_executor`` is the canonical (private) cached property.
2. The public ``chain_executor`` accessor emits a DeprecationWarning.
3. ``payment_orchestrator`` is wired to the private ``_chain_executor``
   and does NOT trigger the deprecation path.
4. No *new* router file directly accesses ``deps.chain_executor`` for
   payment dispatch (known legacy violations are tracked explicitly).
"""

from __future__ import annotations

import inspect
import os
import sys
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure sardis_api and its dependencies are importable without conftest
_packages_dir = Path(__file__).resolve().parent.parent.parent
for _pkg_name in [
    "sardis-api",
    "sardis-core",
    "sardis-wallet",
    "sardis-chain",
    "sardis-protocol",
    "sardis-ledger",
    "sardis-cards",
    "sardis-compliance",
    "sardis-checkout",
    "sardis-coinbase",
]:
    _src = _packages_dir / _pkg_name / "src"
    if _src.exists() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("SARDIS_CHAIN_MODE", "simulated")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROUTERS_DIR = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "sardis_api"
    / "routers"
)

# Routers that still call deps.chain_executor.dispatch_payment directly.
# These are tracked for migration — adding a new file here should be a
# conscious decision reviewed in PR.
_KNOWN_LEGACY_DISPATCH_FILES: set[str] = {
    "onchain_payments.py",  # fee + payment dispatch — migrate to orchestrator
    "mvp.py",               # has TODO to migrate
    "wallets.py",           # fee dispatch in transfer endpoint
}


def _router_sources() -> list[tuple[str, str]]:
    """Return (filename, source) pairs for every router module."""
    results: list[tuple[str, str]] = []
    for p in sorted(ROUTERS_DIR.glob("*.py")):
        results.append((p.name, p.read_text()))
    return results


# ---------------------------------------------------------------------------
# Unit tests for DependencyContainer
# ---------------------------------------------------------------------------


class TestChainExecutorPrivate:
    """chain_executor is private in the DI container."""

    def test_private_cached_property_exists(self):
        """DependencyContainer must define ``_chain_executor`` as a cached_property."""
        from sardis_api.dependencies import DependencyContainer

        descriptor = DependencyContainer.__dict__.get("_chain_executor")
        assert descriptor is not None, "_chain_executor not found on DependencyContainer"
        from functools import cached_property as cp

        assert isinstance(descriptor, cp), "_chain_executor should be a cached_property"

    def test_public_accessor_emits_deprecation_warning(self):
        """Accessing ``container.chain_executor`` must emit DeprecationWarning."""
        from sardis_api.dependencies import DependencyContainer

        container = DependencyContainer.__new__(DependencyContainer)
        container._cache = {}
        # Seed the cached_property directly on the instance dict
        container.__dict__["_chain_executor"] = MagicMock(name="mock_chain_executor")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = container.chain_executor

        assert len(w) == 1, f"Expected exactly 1 warning, got {len(w)}"
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
        assert result is container.__dict__["_chain_executor"]

    def test_public_accessor_returns_same_instance(self):
        """Deprecated accessor must return the exact same object as _chain_executor."""
        from sardis_api.dependencies import DependencyContainer

        container = DependencyContainer.__new__(DependencyContainer)
        container._cache = {}
        sentinel = object()
        container.__dict__["_chain_executor"] = sentinel

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert container.chain_executor is sentinel

    def test_payment_orchestrator_uses_private_chain_executor(self):
        """payment_orchestrator property must reference self._chain_executor, not self.chain_executor."""
        from sardis_api.dependencies import DependencyContainer

        source = inspect.getsource(DependencyContainer.payment_orchestrator.func)  # type: ignore[union-attr]
        # Must use the private accessor
        assert "self._chain_executor" in source, (
            "payment_orchestrator should use self._chain_executor"
        )
        # Must NOT use the public (deprecated) accessor
        assert "self.chain_executor" not in source.replace("self._chain_executor", ""), (
            "payment_orchestrator must not use the deprecated self.chain_executor"
        )

    def test_payment_orchestrator_no_deprecation_warning(self):
        """Creating payment_orchestrator must not trigger the deprecation warning."""
        from sardis_api.dependencies import DependencyContainer

        container = DependencyContainer.__new__(DependencyContainer)
        container._cache = {}
        container.__dict__["_chain_executor"] = MagicMock(name="mock_chain_executor")
        container.__dict__["wallet_manager"] = MagicMock(name="mock_wallet")
        container.__dict__["compliance_engine"] = MagicMock(name="mock_compliance")
        container.__dict__["ledger_store"] = MagicMock(name="mock_ledger")
        container.__dict__["group_policy"] = None

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with patch(
                "sardis_v2_core.orchestrator.PaymentOrchestrator",
                return_value=MagicMock(name="orchestrator"),
            ):
                _ = DependencyContainer.payment_orchestrator.func(container)  # type: ignore[union-attr]

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0, (
            f"payment_orchestrator triggered deprecation warning(s): {deprecation_warnings}"
        )


# ---------------------------------------------------------------------------
# Static analysis: no NEW router should use deps.chain_executor.dispatch_payment
# ---------------------------------------------------------------------------


class TestRoutersDontBypassOrchestrator:
    """No new routers should call deps.chain_executor.dispatch_payment."""

    @pytest.mark.parametrize(
        "filename,source",
        _router_sources(),
        ids=[name for name, _ in _router_sources()],
    )
    def test_no_new_dispatch_payment_via_deps_chain_executor(
        self, filename: str, source: str
    ):
        """Routers outside the known legacy set must not call
        deps.chain_executor.dispatch_payment — use payment_orchestrator."""
        if filename in _KNOWN_LEGACY_DISPATCH_FILES:
            pytest.skip(f"{filename} is a known legacy file pending migration")

        assert "deps.chain_executor.dispatch_payment" not in source, (
            f"{filename} calls deps.chain_executor.dispatch_payment — "
            "use payment_orchestrator instead"
        )

    def test_known_legacy_list_is_not_growing(self):
        """Fail loudly if a new router starts bypassing the orchestrator."""
        violators: list[str] = []
        for filename, source in _router_sources():
            if "deps.chain_executor.dispatch_payment" in source:
                violators.append(filename)

        unexpected = set(violators) - _KNOWN_LEGACY_DISPATCH_FILES
        assert not unexpected, (
            f"New router(s) bypassing orchestrator: {unexpected}. "
            "Migrate to payment_orchestrator or add to _KNOWN_LEGACY_DISPATCH_FILES with justification."
        )
