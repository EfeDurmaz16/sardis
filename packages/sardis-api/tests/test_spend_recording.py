"""Tests: Spend recording across all payment dispatch sites."""
from __future__ import annotations

import inspect
import pytest


class TestSpendRecordingMandates:
    """Mandates router should record spend at both execute paths."""

    def test_has_record_spend(self):
        from sardis_api.routers import mandates
        source = inspect.getsource(mandates)
        count = source.count("async_record_spend")
        assert count >= 2, f"Expected async_record_spend at 2 dispatch sites in mandates.py, found {count}"

    def test_record_spend_after_dispatch(self):
        """Verify record_spend appears AFTER dispatch_payment in source order."""
        from sardis_api.routers import mandates
        source = inspect.getsource(mandates)
        dispatch_pos = source.find("dispatch_payment")
        record_pos = source.find("async_record_spend")
        assert dispatch_pos > 0, "dispatch_payment not found"
        assert record_pos > 0, "async_record_spend not found"
        assert record_pos > dispatch_pos, "record_spend should come after dispatch_payment"


class TestSpendRecordingMVP:
    """MVP router should record spend after execution."""

    def test_has_record_spend(self):
        from sardis_api.routers import mvp
        source = inspect.getsource(mvp)
        assert "async_record_spend" in source

    def test_record_spend_after_dispatch(self):
        from sardis_api.routers import mvp
        source = inspect.getsource(mvp)
        dispatch_pos = source.find("dispatch_payment")
        record_pos = source.find("async_record_spend")
        assert record_pos > dispatch_pos, "record_spend should come after dispatch_payment"


class TestSpendRecordingA2A:
    """A2A router should record spend at both /pay and /messages paths."""

    def test_has_record_spend_in_both_paths(self):
        from sardis_api.routers import a2a
        source = inspect.getsource(a2a)
        count = source.count("async_record_spend")
        assert count >= 2, f"Expected async_record_spend at 2 dispatch sites in a2a.py, found {count}"


class TestSpendRecordingWallets:
    """Wallets router should record spend after transfer."""

    def test_has_record_spend(self):
        from sardis_api.routers import wallets
        source = inspect.getsource(wallets)
        assert "async_record_spend" in source

    def test_record_spend_after_dispatch(self):
        from sardis_api.routers import wallets
        source = inspect.getsource(wallets)
        dispatch_pos = source.find("dispatch_payment")
        record_pos = source.find("async_record_spend")
        assert record_pos > dispatch_pos, "record_spend should come after dispatch_payment"


class TestSpendRecordingAP2:
    """AP2 orchestrator already has spend recording - verify it's still there."""

    def test_ap2_orchestrator_has_record_spend(self):
        from sardis_api.routers import ap2
        source = inspect.getsource(ap2)
        # AP2 may use orchestrator pattern - check for either direct or orchestrator spend recording
        has_record = "async_record_spend" in source or "record_spend" in source
        assert has_record, "AP2 should have spend recording (direct or via orchestrator)"


class TestAllPathsCoverage:
    """Meta-test: verify all 5 router files have spend recording."""

    @pytest.mark.parametrize("module_name", [
        "sardis_api.routers.mandates",
        "sardis_api.routers.mvp",
        "sardis_api.routers.a2a",
        "sardis_api.routers.wallets",
    ])
    def test_router_has_spend_recording(self, module_name):
        import importlib
        mod = importlib.import_module(module_name)
        source = inspect.getsource(mod)
        assert "async_record_spend" in source, f"{module_name} missing async_record_spend call"
