"""Tests for the orchestrator's optional post-execution recourse hook.

Pins the additive, fail-closed contract:

* a payment configured with a recourse window opens a RecourseHold AFTER a
  successful settlement (money moved AND a hold exists);
* no window configured -> unchanged behavior (immediate finality, no hold);
* a recourse-engine failure never crashes a settled payment (the result is
  returned without a hold).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis.core.orchestrator import PaymentOrchestrator
from sardis.core.recourse_engine import RecourseEngine
from sardis.core.recourse_hold import RecourseStatus
from sardis.core.recourse_hold_repository import InMemoryRecourseHoldStore


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_rec_001"
    agent_id: str | None = "agent_rec"
    wallet_id: str | None = "wal_rec"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 250_000_000  # 250 USDC
    destination: str = "0x" + "cd" * 20
    from_address: str = "0x" + "ab" * 20
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "merch_x"
    merchant_category: str | None = None
    rail: str | None = None
    fee: Any = None
    amount: Any = None
    subject: str = "agent_rec"


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtxhash_rec"
    chain: str = "base"
    block_number: int = 1
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakeLedgerTx:
    tx_id: str = "ltx_rec_001"


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


def _build(*, recourse_engine=None, window_resolver=None):
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()

    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())

    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())

    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())

    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        recourse_engine=recourse_engine,
        recourse_window_resolver=window_resolver,
    )
    return orch, chain_exec


@pytest.mark.asyncio
async def test_no_window_means_immediate_finality_no_hold():
    store = InMemoryRecourseHoldStore()
    engine = RecourseEngine(store=store, signing_secret="t")
    # Resolver returns None -> no hold.
    orch, chain_exec = _build(recourse_engine=engine, window_resolver=lambda p, m: None)

    result = await orch.execute_chain(_FakeMandateChain())

    assert result.status == "submitted"
    assert result.chain_tx_hash == "0xtxhash_rec"
    assert result.recourse_hold_id == ""
    chain_exec.dispatch_payment.assert_awaited_once()
    assert await store.list_open() == []


@pytest.mark.asyncio
async def test_recourse_window_opens_hold_after_settlement():
    store = InMemoryRecourseHoldStore()
    engine = RecourseEngine(store=store, signing_secret="t")
    orch, chain_exec = _build(
        recourse_engine=engine,
        window_resolver=lambda p, m: 3600,  # 1h window
    )

    result = await orch.execute_chain(_FakeMandateChain())

    # Money moved AND a hold is open.
    assert result.status == "submitted"
    assert result.chain_tx_hash == "0xtxhash_rec"
    chain_exec.dispatch_payment.assert_awaited_once()
    assert result.recourse_hold_id.startswith("rch_")

    hold = await store.get(result.recourse_hold_id)
    assert hold is not None
    assert hold.status == RecourseStatus.HELD
    assert hold.amount_minor == 250_000_000
    assert hold.currency == "USDC"
    assert hold.recipient == _FakePayment().destination
    assert hold.payer == _FakePayment().from_address
    assert hold.evidence is None  # not yet transitioned


@pytest.mark.asyncio
async def test_recourse_engine_failure_does_not_crash_settled_payment():
    boom = MagicMock()
    boom.open_hold = AsyncMock(side_effect=RuntimeError("recourse store down"))
    orch, chain_exec = _build(
        recourse_engine=boom,
        window_resolver=lambda p, m: 3600,
    )

    result = await orch.execute_chain(_FakeMandateChain())

    # Settled successfully; the recourse failure is swallowed (no hold id).
    assert result.status == "submitted"
    assert result.chain_tx_hash == "0xtxhash_rec"
    assert result.recourse_hold_id == ""
    chain_exec.dispatch_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_recourse_engine_is_fully_unchanged():
    orch, chain_exec = _build(recourse_engine=None)
    result = await orch.execute_chain(_FakeMandateChain())
    assert result.status == "submitted"
    assert result.recourse_hold_id == ""
    chain_exec.dispatch_payment.assert_awaited_once()
