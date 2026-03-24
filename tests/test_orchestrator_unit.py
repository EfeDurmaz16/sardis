"""Unit tests for the PaymentOrchestrator 6-phase pipeline.

Tests the orchestrator's behavior through mock dependencies:
  Phase 0: KYA verification
  Phase 0.5: Mandate validation
  Phase 1: Policy validation
  Phase 2: Compliance check
  Phase 3: Chain execution
  Phase 3.5: Spend recording
  Phase 4: Ledger append
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sardis_v2_core.mandates import (
    CartMandate,
    IntentMandate,
    MandateChain,
    PaymentMandate,
    VCProof,
)
from sardis_v2_core.orchestrator import (
    ChainExecutionError,
    ComplianceViolationError,
    KYAViolationError,
    PaymentOrchestrator,
    PaymentResult,
    PolicyViolationError,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _stub_proof() -> VCProof:
    return VCProof(
        verification_method="test#key-1",
        created="2026-01-01T00:00:00Z",
        proof_value="stub",
    )


def _make_chain(mandate_id: str = "mandate_test_001") -> MandateChain:
    """Build a minimal MandateChain for testing."""
    wallet_manager = MagicMock()
    wallet_manager.async_validate_policies = AsyncMock(
        return_value=FakePolicyResult(allowed=policy_allowed, reason=policy_reason)
    )
    if spend_record_fail:
        wallet_manager.async_record_spend = AsyncMock(side_effect=RuntimeError("DB down"))
    else:
        wallet_manager.async_record_spend = AsyncMock()

    compliance = MagicMock()
    compliance.preflight = AsyncMock(
        return_value=FakeComplianceResult(allowed=compliance_allowed, reason=compliance_reason)
    )

    chain_executor = MagicMock()
    if chain_fail:
        chain_executor.dispatch_payment = AsyncMock(
            side_effect=RuntimeError("chain timeout")
        )
    else:
        chain_executor.dispatch_payment = AsyncMock(return_value=FakeChainReceipt())

    ledger = MagicMock()
    if ledger_fail:
        ledger.append = MagicMock(side_effect=RuntimeError("ledger write failed"))
    else:
        ledger.append = MagicMock(return_value=FakeLedgerTx())

    kya_service = None
    if with_kya:
        kya_service = MagicMock()
        kya_service.check_agent = AsyncMock(
            return_value=FakeKYAResult(
                allowed=kya_allowed,
                reason=kya_reason,
                level=kya_level,
            )
        )

    return PaymentOrchestrator(
        wallet_manager=wallet_manager,
        compliance=compliance,
        chain_executor=chain_executor,
        ledger=ledger,
        kya_service=kya_service,
    )


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_happy_path_all_phases_pass():
    """All phases pass => payment executes and returns a PaymentResult."""
    orch = _build_orchestrator()
    chain = _make_chain()

    result = await orch.execute_chain(chain)

    assert isinstance(result, PaymentResult)
    assert result.chain_tx_hash == "0xdeadbeef"
    assert result.chain == "base"
    assert result.ledger_tx_id == "ltx_001"
    assert result.status == "submitted"


@pytest.mark.asyncio
async def test_kya_fail_closed_blocks_payment():
    """Phase 0: KYA verification denies => KYAViolationError."""
    orch = _build_orchestrator(
        with_kya=True,
        kya_allowed=False,
        kya_reason="agent_suspended",
    )
    chain = _make_chain()

    with pytest.raises(KYAViolationError, match="agent_suspended"):
        await orch.execute_chain(chain)


@pytest.mark.asyncio
async def test_policy_deny_blocks_payment():
    """Phase 1: Policy validation denies => PolicyViolationError, no chain/compliance."""
    orch = _build_orchestrator(
        policy_allowed=False,
        policy_reason="per_transaction_limit",
    )
    chain = _make_chain()

    with pytest.raises(PolicyViolationError, match="per_transaction_limit"):
        await orch.execute_chain(chain)

    # Compliance and chain should NOT have been called
    orch._compliance.preflight.assert_not_called()
    orch._chain_executor.dispatch_payment.assert_not_called()


@pytest.mark.asyncio
async def test_compliance_deny_after_policy_pass():
    """Phase 2: Compliance denies after policy passes => ComplianceViolationError."""
    orch = _build_orchestrator(
        compliance_allowed=False,
        compliance_reason="sanctions_hit",
    )
    chain = _make_chain()

    with pytest.raises(ComplianceViolationError, match="sanctions_hit"):
        await orch.execute_chain(chain)

    # Policy was checked, chain was NOT
    orch._wallet_manager.async_validate_policies.assert_called_once()
    orch._chain_executor.dispatch_payment.assert_not_called()


@pytest.mark.asyncio
async def test_chain_execution_success_records_spend_and_ledger():
    """Phase 3: Chain executes => spend is recorded and ledger appended."""
    orch = _build_orchestrator()
    chain = _make_chain()

    result = await orch.execute_chain(chain)

    assert result.chain_tx_hash == "0xdeadbeef"
    orch._wallet_manager.async_record_spend.assert_called_once()
    orch._ledger.append.assert_called_once()


@pytest.mark.asyncio
async def test_chain_execution_failure_raises():
    """Phase 3: Chain failure => ChainExecutionError, no spend/ledger."""
    orch = _build_orchestrator(chain_fail=True)
    chain = _make_chain()

    with pytest.raises(ChainExecutionError, match="Chain execution failed"):
        await orch.execute_chain(chain)

    orch._wallet_manager.async_record_spend.assert_not_called()
    orch._ledger.append.assert_not_called()


@pytest.mark.asyncio
async def test_spend_recording_failure_queues_reconciliation():
    """Phase 3.5: Spend recording fails after chain success => reconciliation queued."""
    orch = _build_orchestrator(spend_record_fail=True)
    chain = _make_chain()

    result = await orch.execute_chain(chain)

    # Payment should still succeed (chain already executed)
    assert result.chain_tx_hash == "0xdeadbeef"
    # Reconciliation queue should have an entry
    assert orch.get_pending_reconciliation_count() >= 1


@pytest.mark.asyncio
async def test_ledger_failure_returns_reconciliation_pending():
    """Phase 4: Ledger append fails => result has reconciliation_pending status."""
    orch = _build_orchestrator(ledger_fail=True)
    chain = _make_chain()

    result = await orch.execute_chain(chain)

    assert result.chain_tx_hash == "0xdeadbeef"
    assert result.status == "reconciliation_pending"
    assert result.ledger_tx_id == "PENDING_RECONCILIATION"
    assert orch.get_pending_reconciliation_count() >= 1


@pytest.mark.asyncio
async def test_audit_log_tracks_phases():
    """The orchestrator's audit log records entries for each phase."""
    orch = _build_orchestrator()
    chain = _make_chain("audit_test_001")

    await orch.execute_chain(chain)

    log = orch.get_audit_log("audit_test_001")
    phases = [e.phase.value for e in log]

    assert "policy_validation" in phases
    assert "compliance_check" in phases
    assert "chain_execution" in phases
    assert "ledger_append" in phases
    assert "completed" in phases


@pytest.mark.asyncio
async def test_dedup_blocks_duplicate_execution():
    """Duplicate mandate_id is blocked by dedup store."""
    orch = _build_orchestrator()
    chain = _make_chain("dedup_test_001")

    result1 = await orch.execute_chain(chain)
    result2 = await orch.execute_chain(chain)

    # Both should return the same result (second is cached)
    assert result1.chain_tx_hash == result2.chain_tx_hash
    # Chain executor should only be called once
    assert orch._chain_executor.dispatch_payment.call_count == 1
