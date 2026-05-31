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
from sardis.core.spending_mandate import SpendingMandate

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


def _build_orchestrator(
    *, spending_mandate_lookup=None, reconciliation_queue=None, ledger=None
):
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

    if ledger is None:
        ledger = MagicMock()
        ledger.append = MagicMock(return_value=_FakeLedgerTx())

    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
        reconciliation_queue=reconciliation_queue,
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


class _RealSpendingMandate(SpendingMandate):
    """A real SpendingMandate with a $100 per-tx + lifetime limit.

    Records every ``record_spend`` call so the orchestrator's post-settlement
    mandate-spend persistence (P1-3) can be asserted.
    """

    def __init__(self) -> None:
        super().__init__(
            principal_id="prn_1",
            issuer_id="iss_1",
            id="smdt_limit_001",
            agent_id="agent_revoked",
            amount_per_tx=Decimal("100"),
            amount_total=Decimal("100"),
            currency="USDC",
        )
        self.recorded: list[Decimal] = []

    def record_spend(self, amount: Decimal) -> None:  # noqa: D401 - test stub
        self.recorded.append(Decimal(str(amount)))
        self.spent_total += Decimal(str(amount))


@pytest.mark.asyncio
async def test_amount_minor_checked_in_token_units_not_raw_minor():
    """P1-2: a 50-USDC payment (amount_minor=50_000_000) must be checked as 50,
    not 50_000_000, against the mandate's token-unit ($100) limits.

    A typed PaymentMandate has no major-unit ``amount`` — only ``amount_minor``.
    The orchestrator must normalize minor -> token units before check_payment,
    or a 50-USDC payment is falsely denied against a $100 cap.
    """
    mandate = _RealSpendingMandate()
    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=mandate)

    orch, chain_exec = _build_orchestrator(spending_mandate_lookup=lookup)
    # 50 USDC == 50_000_000 minor units; no major-unit `amount` (typed mandate).
    chain = _FakeMandateChain(
        payment=_FakePayment(amount=None, amount_minor=50_000_000, token="USDC")
    )

    result = await orch.execute_chain(chain)

    # Must pass: 50 USDC <= $100 per-tx limit.
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_mandate_spend_persisted_after_success():
    """P1-3: after a successful settlement the mandate's spent_total must be
    persisted via the lookup's record_spend, in token units (50, not 50e6)."""
    mandate = _RealSpendingMandate()
    lookup = MagicMock()
    lookup.get_active_mandate = AsyncMock(return_value=mandate)
    lookup.record_spend = AsyncMock()

    orch, chain_exec = _build_orchestrator(spending_mandate_lookup=lookup)
    chain = _FakeMandateChain(
        payment=_FakePayment(amount=None, amount_minor=50_000_000, token="USDC")
    )

    result = await orch.execute_chain(chain)
    assert result.status == "submitted"

    # The mandate spend was persisted exactly once, in token units.
    lookup.record_spend.assert_awaited_once()
    kwargs = lookup.record_spend.await_args.kwargs
    args = lookup.record_spend.await_args.args
    recorded_amount = kwargs.get("amount") if "amount" in kwargs else (args[1] if len(args) > 1 else args[0])
    assert Decimal(str(recorded_amount)) == Decimal("50")


@pytest.mark.asyncio
async def test_async_reconciliation_enqueue_is_awaited():
    """P1-6: an async reconciliation queue's enqueue (coroutine) must be awaited.

    The Postgres reconciliation queue's ``enqueue`` is async; calling it without
    awaiting silently dropped the row. On a simulated ledger-append failure, the
    orchestrator must actually await the coroutine so the recon row is written.
    """
    enqueued: list[Any] = []

    class _AsyncReconQueue:
        async def enqueue(self, entry: Any) -> str:
            enqueued.append(entry)
            return entry.mandate_id

        def get_pending(self, limit: int = 100) -> list[Any]:
            return list(enqueued)

        def mark_resolved(self, mandate_id: str) -> bool:
            return True

        def increment_retry(self, mandate_id: str) -> bool:
            return True

    # Ledger append fails -> orchestrator must enqueue reconciliation (awaited).
    ledger = MagicMock()
    ledger.append = MagicMock(side_effect=RuntimeError("ledger down"))

    orch, chain_exec = _build_orchestrator(
        reconciliation_queue=_AsyncReconQueue(), ledger=ledger
    )
    chain = _FakeMandateChain()

    result = await orch.execute_chain(chain)

    # Payment still succeeded on-chain; ledger queued for reconciliation.
    assert result.status == "reconciliation_pending"
    chain_exec.dispatch_payment.assert_awaited_once()
    # The async enqueue was actually awaited (row recorded, no un-awaited coro).
    assert len(enqueued) == 1
    assert enqueued[0].mandate_id == chain.payment.mandate_id


@pytest.mark.asyncio
async def test_dedup_reserve_blocks_duplicate_execution():
    """P1-5: a dedup store reservation already held blocks a second dispatch."""

    class _AlreadyReservedDedup:
        async def check(self, mandate_id: str):
            return None

        async def check_and_set(self, mandate_id: str, result: Any):
            return None

        async def reserve(self, mandate_id: str) -> bool:
            return False  # someone else holds the reservation

    from sardis.core.orchestrator import ChainExecutionError

    orch, chain_exec = _build_orchestrator()
    orch._dedup_store = _AlreadyReservedDedup()
    chain = _FakeMandateChain()

    with pytest.raises(ChainExecutionError):
        await orch.execute_chain(chain)

    # The duplicate must NOT have dispatched a second on-chain transaction.
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_failure_releases_reservation_for_retry():
    """P1-5: a failed dispatch releases the dedup reservation so a retry of the
    same mandate is not blocked for the full dedup TTL (no money moved)."""
    from sardis.core.dedup_store import InMemoryDedupStore
    from sardis.core.orchestrator import ChainExecutionError

    dedup = InMemoryDedupStore()
    orch, chain_exec = _build_orchestrator()
    orch._dedup_store = dedup
    # First dispatch raises (no money moved).
    chain_exec.dispatch_payment = AsyncMock(side_effect=RuntimeError("rpc down"))
    chain = _FakeMandateChain()

    with pytest.raises(ChainExecutionError):
        await orch.execute_chain(chain)

    # The reservation must have been released — a retry can reserve again.
    assert await dedup.reserve(chain.payment.mandate_id) is True
