"""Tests for the human-in-the-loop approval loop.

The audit found this loop missing: ``requires_approval`` -> deliver -> approve
-> re-execute through the single fail-closed path was never wired.  These tests
pin the corrected behavior end to end:

* ``requires_approval`` -> a durable, signed ApprovalRequest is created, a
  notification is emitted (mock), and NO money moves;
* approve -> ``execute_on_approval`` re-executes exactly once and a receipt is
  returned; a duplicate approve callback does NOT settle twice (idempotent);
* deny / expire -> blocked, no money moved;
* a mandate revoked AFTER approval is STILL blocked at re-execution (the engine
  re-checks at execution time and never trusts a stale approval).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request import ApprovalState, DecisionChannel
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore
from sardis.core.orchestrator import PaymentOrchestrator, PolicyViolationError

# ── Helpers (mirroring test_orchestrator_revocation scaffold) ──────────


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_appr_001"
    agent_id: str | None = "agent_appr"
    wallet_id: str | None = "wal_appr"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 250_000_000  # 250 USDC
    destination: str = "0x" + "cd" * 20
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "merch_x"
    merchant_category: str | None = None
    rail: str | None = None
    fee: Any = None
    amount: Any = None


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtxhash_appr"
    chain: str = "base"
    block_number: int = 999
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakeLedgerTx:
    tx_id: str = "ltx_appr_001"


@dataclass
class _FakePolicyResult:
    allowed: bool = True
    reason: str = "OK"
    rule_id: str | None = None
    required_approvals: int = 0


@dataclass
class _FakeComplianceResult:
    allowed: bool = True
    reason: str = "OK"
    provider: str = "mock"
    rule_id: str = "mock_rule"
    audit_id: str = "audit_001"


@dataclass
class _FakeMandateCheck:
    approved: bool = True
    reason: str = "OK"
    error_code: str | None = None
    requires_approval: bool = False
    mandate_version: int = 1


class _ApprovalMandate:
    """ACTIVE mandate that demands approval above its threshold."""

    id = "smdt_appr_001"
    approval_threshold = Decimal("100")

    def __init__(self) -> None:
        self.recorded: list[Decimal] = []

    def check_payment(self, *, amount: Decimal, **_kwargs: Any) -> _FakeMandateCheck:
        if amount > self.approval_threshold:
            return _FakeMandateCheck(approved=True, requires_approval=True)
        return _FakeMandateCheck(approved=True)

    def record_spend(self, amount: Decimal) -> None:  # pragma: no cover - stub
        self.recorded.append(Decimal(str(amount)))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "approval_threshold": str(self.approval_threshold)}


class _MockNotifier:
    """Stand-in NotificationPort: records dispatched approvals, never decides."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_approval_request(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return MagicMock(
            provider="mock", handle="dlv_1",
            channels=kwargs.get("channels", ()), step_up_issued=False, ok=True,
        )


def _build(*, mandate, notifier=None):
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()

    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())

    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())

    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())

    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=mandate)
    lookup.record_spend = AsyncMock()

    store = InMemoryApprovalRequestStore()
    gate = ApprovalGate(store=store, notifier=notifier, signing_secret="test-secret")

    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        spending_mandate_lookup=lookup,
        approval_gate=gate,
    )
    return orch, chain_exec, gate, store, lookup


# ── Tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_requires_approval_creates_pending_and_emits_and_does_not_execute():
    notifier = _MockNotifier()
    orch, chain_exec, gate, store, _ = _build(mandate=_ApprovalMandate(), notifier=notifier)

    result = await orch.execute_chain(_FakeMandateChain())

    # PENDING — no money moved.
    assert result.status == "pending_approval"
    assert result.approval_id
    assert result.chain_tx_hash == ""
    chain_exec.dispatch_payment.assert_not_awaited()

    # Durable, signed, pending request exists.
    req = await store.get(result.approval_id)
    assert req is not None
    assert req.status == ApprovalState.PENDING
    assert req.amount == Decimal("250")
    assert req.chain_snapshot is not None

    # Notification emitted exactly once via the mock.
    assert len(notifier.sent) == 1
    assert notifier.sent[0]["approval_id"] == result.approval_id


@pytest.mark.asyncio
async def test_approve_reexecutes_once_and_returns_receipt():
    orch, chain_exec, gate, store, _ = _build(mandate=_ApprovalMandate(), notifier=_MockNotifier())

    pending = await orch.execute_chain(_FakeMandateChain())
    approval_id = pending.approval_id

    # Human approves (signed evidence recorded).
    req = await gate.record_decision(
        approval_id=approval_id, decision="approve",
        approver="efe@sardis.sh", channel=DecisionChannel.DASHBOARD,
    )
    assert req.status == ApprovalState.APPROVED
    assert req.evidence is not None and req.evidence.verify(secret="test-secret")

    # Re-execute through the single fail-closed path.
    result = await orch.execute_on_approval(approval_id)
    assert result.status == "submitted"
    assert result.chain_tx_hash == "0xtxhash_appr"
    chain_exec.dispatch_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_double_approve_callback_settles_only_once():
    orch, chain_exec, gate, store, _ = _build(mandate=_ApprovalMandate(), notifier=_MockNotifier())
    pending = await orch.execute_chain(_FakeMandateChain())
    await gate.record_decision(
        approval_id=pending.approval_id, decision="approve", approver="efe",
    )

    # First re-execution settles.
    first = await orch.execute_on_approval(pending.approval_id)
    assert first.status == "submitted"

    # A duplicate approve callback must NOT settle a second time.
    with pytest.raises(PolicyViolationError):
        await orch.execute_on_approval(pending.approval_id)

    chain_exec.dispatch_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_deny_blocks_and_moves_no_money():
    orch, chain_exec, gate, store, _ = _build(mandate=_ApprovalMandate(), notifier=_MockNotifier())
    pending = await orch.execute_chain(_FakeMandateChain())

    req = await gate.record_decision(
        approval_id=pending.approval_id, decision="deny",
        approver="efe@sardis.sh", reason="not budgeted",
    )
    assert req.status == ApprovalState.DENIED
    assert req.evidence is not None and req.evidence.verify(secret="test-secret")

    # Denied -> not executable -> fail closed, no dispatch.
    with pytest.raises(PolicyViolationError):
        await orch.execute_on_approval(pending.approval_id)
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_expire_blocks_and_moves_no_money():
    orch, chain_exec, gate, store, _ = _build(mandate=_ApprovalMandate(), notifier=_MockNotifier())
    pending = await orch.execute_chain(_FakeMandateChain())

    # Force the request past its deadline, then sweep.
    req = await store.get(pending.approval_id)
    from datetime import UTC, datetime, timedelta

    req.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await store.save(req)
    swept = await gate.sweep_expired()
    assert swept == 1
    assert (await store.get(pending.approval_id)).status == ApprovalState.EXPIRED

    with pytest.raises(PolicyViolationError):
        await orch.execute_on_approval(pending.approval_id)
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoked_after_approval_still_blocked_at_reexecution():
    """Fail-closed: a mandate revoked AFTER a human approved must still be
    blocked at re-execution — the engine re-checks at execution time and never
    trusts a stale approval."""
    mandate = _ApprovalMandate()
    orch, chain_exec, gate, store, lookup = _build(mandate=mandate, notifier=_MockNotifier())

    pending = await orch.execute_chain(_FakeMandateChain())
    await gate.record_decision(
        approval_id=pending.approval_id, decision="approve", approver="efe",
    )

    # Revoke the mandate AFTER approval: the active-mandate lookup now returns
    # None (revoked rows are not 'active').
    lookup.get_active_mandate = AsyncMock(return_value=None)

    with pytest.raises(PolicyViolationError):
        await orch.execute_on_approval(pending.approval_id)

    # No money moved despite a valid prior approval.
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_gate_preserves_legacy_fail_closed_raise():
    """Back-compat: with no approval_gate configured, requires_approval still
    fails closed via MandateViolationError (legacy behavior)."""
    from sardis.core.orchestrator import MandateViolationError

    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())
    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())
    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())
    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=_ApprovalMandate())

    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr, compliance=compliance, chain_executor=chain_exec,
        ledger=ledger, spending_mandate_lookup=lookup, approval_gate=None,
    )

    with pytest.raises(MandateViolationError):
        await orch.execute_chain(_FakeMandateChain())
    chain_exec.dispatch_payment.assert_not_awaited()
