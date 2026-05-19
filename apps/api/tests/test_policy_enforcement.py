"""Execution-path policy enforcement wiring tests.

These tests intentionally avoid asserting old implementation strings like
``async_validate_policies`` at every route layer. Current Sardis payment routes
mostly delegate policy, compliance, chain execution, ledger writes, and spend
recording to the orchestrator/control-plane adapters. The useful invariant is
that every public money-moving route enters one of those guarded execution
paths and does not bypass policy by calling a raw chain executor directly.
"""
from __future__ import annotations

import inspect


def _source(module_name: str) -> str:
    module = __import__(module_name, fromlist=["_"])
    return inspect.getsource(module)


class TestMandatesPathPolicyEnforcement:
    """Mandates router delegates execution to PaymentOrchestrator."""

    def test_stored_and_legacy_execute_use_orchestrator(self) -> None:
        source = _source("server.routes.authority.mandates")
        assert source.count("payment_orchestrator.execute_chain") >= 2
        assert "PolicyViolationError" in source
        assert "HTTP_403_FORBIDDEN" in source

    def test_validate_endpoint_still_checks_policy_and_compliance(self) -> None:
        source = _source("server.routes.authority.mandates")
        assert "async_validate_policies" in source
        assert "compliance.preflight" in source
        assert source.find("async_validate_policies") < source.find("compliance.preflight")


class TestAP2PathPolicyEnforcement:
    """AP2 router runs deterministic guardrails then delegated execution."""

    def test_ap2_delegates_execution_to_orchestrator(self) -> None:
        source = _source("server.routes.authority.ap2")
        assert "deps.orchestrator.execute_chain" in source
        assert "PolicyViolationError" in source
        assert "HTTP_403_FORBIDDEN" in source

    def test_ap2_compliance_runs_before_execution(self) -> None:
        source = _source("server.routes.authority.ap2")
        compliance_idx = source.find("_compliance_checks_impl")
        execute_idx = source.find("deps.orchestrator.execute_chain")
        assert compliance_idx != -1
        assert execute_idx != -1
        assert compliance_idx < execute_idx


class TestMVPPathPolicyEnforcement:
    """MVP router delegates live execution to PaymentOrchestrator."""

    def test_mvp_delegates_execution_to_orchestrator(self) -> None:
        source = _source("server.routes.authority.mvp")
        assert "payment_orchestrator.execute_chain" in source
        assert "PolicyViolationError" in source
        assert "HTTP_403_FORBIDDEN" in source

    def test_mvp_checks_static_policy_before_execution(self) -> None:
        source = _source("server.routes.authority.mvp")
        policy_idx = source.find("_policy_check")
        execute_idx = source.find("payment_orchestrator.execute_chain")
        assert policy_idx != -1
        assert execute_idx != -1
        assert policy_idx < execute_idx


class TestA2APayPathPolicyEnforcement:
    """A2A routes use the control plane with the policy adapter."""

    def test_a2a_uses_policy_engine_adapter_for_pay_and_messages(self) -> None:
        source = _source("server.routes.protocol.a2a")
        assert source.count("ControlPlane(") >= 2
        assert source.count("PolicyEngineAdapter(deps.wallet_manager)") >= 2
        assert source.count("wallet_manager_not_configured") >= 2

    def test_a2a_records_spend_after_successful_paths(self) -> None:
        source = _source("server.routes.protocol.a2a")
        assert source.count("async_record_spend") >= 2

    def test_a2a_denials_are_fail_closed(self) -> None:
        source = _source("server.routes.protocol.a2a")
        assert "IntentStatus.REJECTED" in source
        assert "policy_denied" in source
        assert "HTTP_403_FORBIDDEN" in source


class TestWalletsTransferPathPolicyEnforcement:
    """Wallet transfers use the payment orchestrator instead of raw dispatch."""

    def test_wallet_transfer_delegates_to_orchestrator(self) -> None:
        source = _source("server.routes.wallets.lifecycle")
        transfer_idx = source.find("async def transfer_crypto")
        execute_idx = source.find("payment_orchestrator.execute_chain", transfer_idx)
        assert transfer_idx != -1
        assert execute_idx != -1
        assert "PolicyViolationError" in source[transfer_idx:execute_idx + 1000]
        assert "HTTP_403_FORBIDDEN" in source[transfer_idx:execute_idx + 1000]

    def test_wallet_transfer_requires_orchestrator(self) -> None:
        source = _source("server.routes.wallets.lifecycle")
        transfer_source = source[source.find("async def transfer_crypto"):]
        assert "payment_orchestrator_not_configured" in transfer_source


class TestCardsWebhookPathPolicyEnforcement:
    """Cards webhook policy behavior remains fail-closed in production."""

    def test_cards_has_policy_evaluation_function(self) -> None:
        source = _source("server.routes.wallets.cards")
        assert "_evaluate_policy_for_card" in source

    def test_cards_webhook_calls_policy_evaluation(self) -> None:
        source = _source("server.routes.wallets.cards")
        assert source.count("_evaluate_policy_for_card") >= 2

    def test_cards_policy_store_mandatory_in_production(self) -> None:
        source = _source("server.routes.wallets.cards")
        assert "policy_enforcement_unavailable_in_production" in source

    def test_cards_policy_denial_marks_transaction_declined(self) -> None:
        source = _source("server.routes.wallets.cards")
        assert "declined_policy" in source

    def test_cards_policy_denial_can_auto_freeze(self) -> None:
        source = _source("server.routes.wallets.cards")
        assert "_auto_freeze_enabled" in source

    def test_cards_policy_uses_wallet_id_and_mcc(self) -> None:
        source = _source("server.routes.wallets.cards")
        assert "wallet_id" in source
        assert "mcc_code" in source
