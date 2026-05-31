"""Tests for fail-closed enforcement on revoked/missing spending mandates.

Bug context (Phase 0 — Engine Consolidation, Task 2):
The MANDATE_VALIDATION phase passed payments THROUGH when no active spending
mandate was found ("no_active_mandate_found" -> allowed).  Because the DB-backed
``SpendingMandateLookup`` only returns rows with ``status = 'active'``, a
revoked / suspended / expired mandate yields ``None`` from
``get_active_mandate`` — which previously meant the payment was ALLOWED,
defeating revocation entirely.

These tests pin the corrected behavior: when a spending_mandate_lookup is
configured and returns ``None``, execution must FAIL CLOSED (raise
PolicyViolationError) before compliance / chain / ledger run, and no money may
move.  The happy path (an active mandate) must still proceed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis.core.orchestrator import PaymentOrchestrator, PolicyViolationError

# ── Helpers ───────────────────────────────────────────────────────────


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_revoke_001"
    agent_id: str | None = "agent_revoked"
    wallet_id: str | None = "wal_revoked"
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 5000
    destination: str = "0x" + "ab" * 20
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = None
    merchant_category: str | None = None
    rail: str | None = None
    fee: Any = None
    amount: Any = None


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


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


@dataclass
class _FakeMandateCheck:
    approved: bool = True
    reason: str = "OK"
    error_code: str | None = None
    requires_approval: bool = False
    mandate_version: int = 1


class _FakeActiveMandate:
    """Stand-in for an ACTIVE SpendingMandate that approves the payment."""

    id = "smdt_active_001"
    approval_threshold = None

    def check_payment(self, **_kwargs: Any) -> _FakeMandateCheck:
        return _FakeMandateCheck(approved=True)


def _build_orchestrator(*, spending_mandate_lookup=None):
    """Create an orchestrator with all collaborators mocked.

    Returns (orchestrator, chain_executor) so tests can assert on dispatch.
    """
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
        spending_mandate_lookup=spending_mandate_lookup,
    )
    return orch, chain_exec


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoked_mandate_fails_closed_and_moves_no_money():
    """A revoked mandate -> get_active_mandate returns None -> deny.

    Must raise PolicyViolationError before chain execution and never dispatch.
    """
    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=None)  # revoked => no active row

    orch, chain_exec = _build_orchestrator(spending_mandate_lookup=lookup)
    chain = _FakeMandateChain()

    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(chain)

    # No money moved.
    chain_exec.dispatch_payment.assert_not_awaited()
    # The lookup was actually consulted.
    lookup.get_active_mandate.assert_awaited_once()


@pytest.mark.asyncio
async def test_active_mandate_allows_execution_to_proceed():
    """An ACTIVE mandate must NOT raise at the mandate phase (happy path)."""
    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=_FakeActiveMandate())

    orch, chain_exec = _build_orchestrator(spending_mandate_lookup=lookup)
    chain = _FakeMandateChain()

    result = await orch.execute_chain(chain)

    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()
    lookup.get_active_mandate.assert_awaited_once()
