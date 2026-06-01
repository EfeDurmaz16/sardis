"""Orchestrator integration tests for the Guard / RiskEngine (Phase 1.6).

Pins the wiring required by the task:

* internal risk score drives each action;
* a BLOCK denies the payment with NO chain dispatch (fail-closed, audited);
* a REQUIRE_APPROVAL opens a durable ApprovalRequest and moves NO money;
* a FLAG allows + records the signal (payment settles);
* a signal-provider error on a high-value tx fails closed (no silent allow).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request import ApprovalState
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore
from sardis.core.orchestrator import (
    PaymentOrchestrator,
    RiskViolationError,
)
from sardis.guardrails.risk_engine import RiskEngine

# ── fakes (mirroring test_orchestrator_approval_loop scaffold) ──────────


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_risk_001"
    agent_id: str | None = "agent_risk"
    wallet_id: str | None = "wal_risk"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 50_000_000  # 50 USDC
    destination: str = "0x" + "cd" * 20
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "merch_x"
    merchant_category: str | None = None
    rail: str | None = None
    fee: Any = None
    amount: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtxhash_risk"
    chain: str = "base"
    block_number: int = 1
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakeLedgerTx:
    tx_id: str = "ltx_risk_001"


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


# ── stub anomaly engine: fixed internal 0-1 score ──────────────────────


@dataclass
class _StubAnomaly:
    score_01: float

    def assess_risk(self, **kwargs):
        from datetime import UTC, datetime

        from sardis.guardrails.anomaly_engine import RiskAction, RiskAssessment

        return RiskAssessment(
            agent_id=kwargs.get("agent_id", "a"),
            overall_score=self.score_01,
            action=RiskAction.ALLOW,
            signals=[],
            timestamp=datetime.now(UTC),
            transaction_amount=kwargs.get("amount"),
        )


@dataclass
class _FakeSignal:
    provider: str
    score: float
    recommended_action: str = "allow"
    reasons: tuple[str, ...] = ()
    sandbox: bool = True


@dataclass
class _FakeFeed:
    provider: str = "seon"
    signal: _FakeSignal | None = None
    raises: bool = False

    async def score(self, context: dict) -> _FakeSignal:
        if self.raises:
            raise RuntimeError("feed down")
        return self.signal or _FakeSignal(self.provider, 0.0)


class _MockNotifier:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_approval_request(self, **kwargs: Any) -> Any:
        self.sent.append(kwargs)
        return MagicMock(
            provider="mock", handle="dlv", channels=(), step_up_issued=False, ok=True
        )


def _build(*, risk_engine, with_gate=True):
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()

    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())

    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())

    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())

    gate = None
    store = None
    if with_gate:
        store = InMemoryApprovalRequestStore()
        gate = ApprovalGate(store=store, notifier=_MockNotifier(), signing_secret="s")

    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        approval_gate=gate,
        risk_engine=risk_engine,
    )
    return orch, chain_exec, gate, store


def _chain(amount_minor=50_000_000, **meta):
    p = _FakePayment(amount_minor=amount_minor, metadata=dict(meta))
    return _FakeMandateChain(payment=p)


# ── tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allow_proceeds_to_settlement():
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.05))
    orch, chain_exec, _, _ = _build(risk_engine=eng)
    result = await orch.execute_chain(_chain())
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_flag_allows_and_settles_and_records():
    # internal 0.40 -> 40 -> FLAG; payment still settles.
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.40))
    orch, chain_exec, _, _ = _build(risk_engine=eng)
    result = await orch.execute_chain(_chain())
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()
    # The FLAG was audited as a recorded risk signal.
    risk_entries = [
        e for e in orch.get_audit_log()
        if e.phase.value == "risk_assessment"
    ]
    assert risk_entries and risk_entries[0].details.get("flagged") is True


@pytest.mark.asyncio
async def test_block_denies_with_no_dispatch():
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.95))  # 95 -> BLOCK
    orch, chain_exec, _, _ = _build(risk_engine=eng)
    with pytest.raises(RiskViolationError) as exc:
        await orch.execute_chain(_chain())
    chain_exec.dispatch_payment.assert_not_awaited()
    assert exc.value.evidence  # carries the decision evidence for audit


@pytest.mark.asyncio
async def test_require_approval_opens_request_and_moves_no_money():
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.70))  # 70 -> REQUIRE_APPROVAL
    orch, chain_exec, gate, store = _build(risk_engine=eng)
    result = await orch.execute_chain(_chain())

    assert result.status == "pending_approval"
    assert result.approval_id
    assert result.chain_tx_hash == ""
    chain_exec.dispatch_payment.assert_not_awaited()

    req = await store.get(result.approval_id)
    assert req is not None and req.status == ApprovalState.PENDING


@pytest.mark.asyncio
async def test_require_approval_without_gate_fails_closed():
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.70))
    orch, chain_exec, _, _ = _build(risk_engine=eng, with_gate=False)
    with pytest.raises(RiskViolationError):
        await orch.execute_chain(_chain())
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_signal_error_on_high_value_fails_closed():
    # Calm internal, but the feed errors on a HIGH-VALUE tx (>= 1000) ->
    # escalate to REQUIRE_APPROVAL (no silent allow, no money moved).
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.05), fraud_feeds=[_FakeFeed(raises=True)])
    orch, chain_exec, gate, store = _build(risk_engine=eng)
    result = await orch.execute_chain(_chain(amount_minor=5_000_000_000))  # 5000 USDC
    assert result.status == "pending_approval"
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_external_feed_decline_blocks_even_with_calm_internal():
    feed = _FakeFeed("seon", _FakeSignal("seon", score=95.0, recommended_action="decline"))
    eng = RiskEngine(anomaly_engine=_StubAnomaly(0.05), fraud_feeds=[feed])
    orch, chain_exec, _, _ = _build(risk_engine=eng)
    with pytest.raises(RiskViolationError):
        await orch.execute_chain(_chain())
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_risk_engine_is_unchanged_passthrough():
    orch, chain_exec, _, _ = _build(risk_engine=None)
    result = await orch.execute_chain(_chain())
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()
