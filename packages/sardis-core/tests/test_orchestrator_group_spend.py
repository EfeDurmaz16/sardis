"""Tests for group spend recording after successful payment execution.

Verifies that after a successful chain execution, the orchestrator calls
group_policy.record_spend() with the correct agent_id and amount.

Bug context: Group budgets were checked pre-execution (Phase 1.5) but never
decremented post-execution, allowing agents to spend unlimited amounts
against their group budget.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis_v2_core.orchestrator import PaymentOrchestrator


# ── Helpers ──────────────────────────────────────────────────────────


@dataclass
class _FakePayment:
    """Minimal payment object for orchestrator tests.

    Uses a plain dataclass (no slots) so we can add agent_id dynamically,
    and provides all attributes the orchestrator accesses via getattr.
    """
    mandate_id: str = "mdt_test_001"
    agent_id: str | None = "agent_group_test"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 5000
    destination: str = "0x" + "ab" * 20
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = None
    merchant_category: str | None = None
    fee: Any = None
    amount: Any = None


@dataclass
class _FakeMandateChain:
    """Minimal mandate chain wrapper for orchestrator tests."""
    payment: _FakePayment = field(default_factory=_FakePayment)


def _make_mandate_chain(
    *,
    mandate_id: str = "mdt_test_001",
    agent_id: str = "agent_group_test",
    amount_minor: int = 5000,
) -> _FakeMandateChain:
    """Build a minimal mandate chain for orchestrator tests."""
    payment = _FakePayment(
        mandate_id=mandate_id,
        agent_id=agent_id,
        amount_minor=amount_minor,
    )
    return _FakeMandateChain(payment=payment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtxhash_test"
    chain: str = "base"
    block_number: int = 12345
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakeLedgerTx:
    tx_id: str = "ltx_test_001"


@dataclass
class _FakePolicyResult:
    allowed: bool = True
    reason: str = "OK"
    rule_id: str | None = None


@dataclass
class _FakeComplianceResult:
    allowed: bool = True
    reason: str = "OK"
    provider: str = "mock"
    rule_id: str = "mock_rule"
    audit_id: str = "audit_001"


def _build_orchestrator(*, group_policy=None) -> PaymentOrchestrator:
    """Create an orchestrator with all mocks wired in."""
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()

    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())

    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())

    ledger = MagicMock()
    ledger.append = MagicMock(return_value=_FakeLedgerTx())

    return PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        group_policy=group_policy,
    )


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_group_spend_recorded_after_successful_payment():
    """After successful chain execution, group_policy.record_spend is called."""
    group_policy = AsyncMock()
    group_policy.evaluate = AsyncMock(
        return_value=MagicMock(allowed=True, reason="OK", group_id="grp_1")
    )
    group_policy.record_spend = AsyncMock()

    orch = _build_orchestrator(group_policy=group_policy)
    chain = _make_mandate_chain(amount_minor=5000, agent_id="agent_g1")

    result = await orch.execute_chain(chain)

    assert result.status == "submitted"

    # record_spend must have been called exactly once with correct args
    group_policy.record_spend.assert_awaited_once_with(
        agent_id="agent_g1",
        amount=Decimal("5000"),
    )


@pytest.mark.asyncio
async def test_group_spend_not_called_when_no_group_policy():
    """When group_policy is None, no group spend recording happens."""
    orch = _build_orchestrator(group_policy=None)
    chain = _make_mandate_chain()

    result = await orch.execute_chain(chain)

    assert result.status == "submitted"
    # No group_policy means nothing to call — test just ensures no crash


@pytest.mark.asyncio
async def test_group_spend_failure_does_not_block_payment():
    """If group_policy.record_spend raises, the payment still succeeds."""
    group_policy = AsyncMock()
    group_policy.evaluate = AsyncMock(
        return_value=MagicMock(allowed=True, reason="OK")
    )
    group_policy.record_spend = AsyncMock(side_effect=RuntimeError("redis down"))

    orch = _build_orchestrator(group_policy=group_policy)
    chain = _make_mandate_chain(amount_minor=2500, agent_id="agent_g2")

    result = await orch.execute_chain(chain)

    # Payment still succeeds despite group spend failure
    assert result.status == "submitted"
    assert result.chain_tx_hash == "0xtxhash_test"

    # record_spend was attempted
    group_policy.record_spend.assert_awaited_once()


@pytest.mark.asyncio
async def test_group_spend_uses_correct_amount():
    """record_spend receives the payment amount as a Decimal."""
    group_policy = AsyncMock()
    group_policy.evaluate = AsyncMock(
        return_value=MagicMock(allowed=True, reason="OK")
    )
    group_policy.record_spend = AsyncMock()

    orch = _build_orchestrator(group_policy=group_policy)

    for amount in [100, 99999, 1]:
        group_policy.record_spend.reset_mock()
        chain = _make_mandate_chain(
            mandate_id=f"mdt_amt_{amount}",
            amount_minor=amount,
            agent_id="agent_amt",
        )
        await orch.execute_chain(chain)

        group_policy.record_spend.assert_awaited_once_with(
            agent_id="agent_amt",
            amount=Decimal(str(amount)),
        )


@pytest.mark.asyncio
async def test_group_spend_skipped_when_no_agent_id():
    """If payment has no agent_id attribute, group spend is skipped gracefully."""
    group_policy = AsyncMock()
    group_policy.evaluate = AsyncMock(
        return_value=MagicMock(allowed=True, reason="OK")
    )
    group_policy.record_spend = AsyncMock()

    orch = _build_orchestrator(group_policy=group_policy)
    chain = _make_mandate_chain(agent_id="agent_noid")

    # Set agent_id to None to simulate missing agent identity
    chain.payment.agent_id = None

    result = await orch.execute_chain(chain)
    assert result.status == "submitted"

    # record_spend should NOT have been called because agent_id is None
    group_policy.record_spend.assert_not_awaited()
