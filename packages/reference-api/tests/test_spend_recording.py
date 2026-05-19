"""Tests: payment routes enter execution paths that record spend.

Spend accounting no longer has to happen directly in every HTTP route. Newer
routes delegate through PaymentOrchestrator or ControlPlane, where policy,
compliance, chain execution, spend accounting, and ledger recording are composed.
These tests keep route modules pointed at that execution boundary instead of
counting stale direct `async_record_spend` calls in router source.
"""
from __future__ import annotations

import importlib
import inspect

import pytest


def _source(module_name: str) -> str:
    return inspect.getsource(importlib.import_module(module_name))


@pytest.mark.parametrize(
    "module_name",
    [
        "server.routes.authority.mandates",
        "server.routes.authority.mvp",
        "server.routes.wallets.wallets",
    ],
)
def test_payment_orchestrator_routes_execute_mandate_chains(module_name):
    source = _source(module_name)
    assert "payment_orchestrator" in source
    assert "execute_chain" in source
    assert "MandateChain" in source


def test_mandates_router_has_two_orchestrated_execution_paths():
    source = _source("server.routes.authority.mandates")
    assert source.count("execute_chain") >= 2


def test_a2a_routes_record_spend_after_control_plane_success():
    source = _source("server.routes.protocol.a2a")
    assert source.count("ControlPlane(") >= 2
    assert source.count(".submit(") >= 2
    assert source.count("async_record_spend") >= 2


def test_ap2_records_compliance_and_uses_orchestrator_boundary():
    source = _source("server.routes.authority.ap2")
    assert "_append_compliance_decision_audit" in source
    assert "execute_chain" in source
