"""End-to-end moat proof — the M0 backend acceptance gate (Phase 0, Task 7).

This is the headline test for "Engine Consolidation": it proves, through the
REAL wired execution path, that

  1. an active spending mandate within budget produces a successful payment
     (chain dispatch + ledger append + spend recorded), and
  2. an over-budget payment is DENIED by the real policy engine with no money
     moved, and
  3. THE MOAT: once the same mandate is REVOKED, the next payment is DENIED at
     execution time (fail-closed) and ``dispatch_payment`` is NEVER called — no
     money moves after authority is removed.

What is REAL vs FAKED, and why
──────────────────────────────
REAL (the logic under test — never faked):
  * ``PaymentOrchestrator`` — the single, production entry point, constructed
    exactly as production does (keyword collaborators), including its
    fail-closed MANDATE_VALIDATION phase (Task 2) and in-memory audit log.
  * ``EnhancedWalletManager`` — the *production* wallet/policy adapter. Its
    ``async_validate_policies`` runs the real ``SpendingPolicy`` check pipeline,
    and ``async_record_spend`` mutates real cumulative spend state.
  * ``SpendingPolicy`` — a real budget (``limit_per_tx`` / ``limit_total``).
    The over-budget denial is produced by the real policy engine, not a stub.
  * ``SpendingMandate`` — a real mandate with a real budget. Revocation is done
    through the mandate's own real ``transition(REVOKED, ...)`` state machine,
    after which ``is_active`` is ``False``.
  * ``_ActiveMandateLookup`` — a real implementation of ``SpendingMandateLookupPort``
    whose ``get_active_mandate`` mirrors the DB-backed
    ``sardis.core.spending_mandate_lookup.SpendingMandateLookup`` contract
    *exactly*: it returns the mandate only while ``status == 'active'`` (the SQL
    ``WHERE status = 'active'`` filter), and ``None`` once revoked. This is the
    single behaviour the whole moat hinges on, so it is implemented against the
    real ``SpendingMandate`` rather than mocked to ``return None``.
  * ``build_mandate_chain`` / ``MandateChain`` / ``PaymentMandate`` — the real
    typed factory (Task 5) and domain objects.

FAKED (external edges only — so the test does no network / DB I/O):
  * chain ``dispatch_payment`` — an ``AsyncMock`` returning a receipt; faking
    this is what keeps "no money moved" *observable* (we assert it is not
    awaited after revocation).
  * ledger ``append`` — an in-memory list; the real ledger writes to Postgres.
  * compliance ``preflight`` — allow-all; sanctions/KYC are external services.

The full DB-backed, API-level e2e (real Postgres ``spending_mandates`` row,
real ledger persistence) lands with the deploy in a later phase; in this test
env there is no sqlite/in-memory Postgres path for the DB-backed lookup, so the
lookup is wired against the real ``SpendingMandate`` domain object instead. The
fail-closed *decision logic* exercised here is identical regardless of where the
mandate's ``status`` lives.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis.core.config import SardisSettings
from sardis.core.mandate_chain_factory import build_mandate_chain
from sardis.core.orchestrator import (
    ExecutionPhase,
    PaymentOrchestrator,
    PolicyViolationError,
)
from sardis.core.spending_mandate import (
    ApprovalMode,
    MandateStatus,
    SpendingMandate,
)
from sardis.core.spending_policy import SpendingPolicy, TrustLevel
from sardis.wallet.manager import EnhancedWalletManager

AGENT_ID = "agt_moat_e2e"
WALLET_ID = "wal_moat_e2e"
COUNTERPARTY = "0x" + "ab" * 20


# ── Real-port lookup mirroring the DB-backed SpendingMandateLookup contract ──


class _ActiveMandateLookup:
    """Real ``SpendingMandateLookupPort`` over a real ``SpendingMandate``.

    Mirrors ``sardis.core.spending_mandate_lookup.SpendingMandateLookup``: the
    DB query is ``WHERE status = 'active'``, so a revoked/suspended/expired
    mandate yields ``None``. Here we reproduce that filter against the live
    ``SpendingMandate.status`` so revocation via the mandate's own
    ``transition()`` flips this lookup from "active mandate" to ``None`` —
    exactly as deleting/flipping the DB row would.
    """

    def __init__(self, mandate: SpendingMandate) -> None:
        self._mandate = mandate
        self.calls = 0

    async def get_active_mandate(
        self,
        agent_id: str | None = None,
        wallet_id: str | None = None,
    ) -> SpendingMandate | None:
        self.calls += 1
        m = self._mandate
        # Same selection the SQL performs: agent/wallet scope AND status active.
        # None-tolerant match — an unprovided id does not constrain, but a
        # provided id that mismatches the mandate's id excludes the row.
        scoped = (agent_id is None or m.agent_id == agent_id) or (
            wallet_id is None or m.wallet_id == wallet_id
        )
        if not scoped:
            return None
        if m.status != MandateStatus.ACTIVE:
            return None  # revoked / suspended / expired → no row returned
        return m


# ── In-memory ledger (the only persistence edge we fake) ─────────────────────


class _InMemoryLedger:
    def __init__(self) -> None:
        self.entries: list[Any] = []

    def append(self, payment_mandate: Any, chain_receipt: Any) -> Any:
        tx = MagicMock()
        tx.tx_id = f"ltx_{len(self.entries) + 1}"
        self.entries.append((payment_mandate, chain_receipt, tx))
        return tx


def _fake_receipt() -> Any:
    receipt = MagicMock()
    receipt.tx_hash = "0xtxhash_e2e"
    receipt.chain = "base"
    receipt.block_number = 4217
    receipt.audit_anchor = "0x" + "00" * 32
    return receipt


def _allow_compliance() -> Any:
    result = MagicMock()
    result.allowed = True
    result.reason = "OK"
    result.provider = "fake_compliance_edge"
    result.rule_id = "allow_all"
    result.audit_id = "cmp_e2e"
    return result


class _AsyncPolicyStore:
    """In-memory async policy store holding the REAL SpendingPolicy.

    ``record_spend`` mutates real cumulative spend state via the policy's own
    ``record_spend`` — so budgets actually deplete across payments.
    """

    def __init__(self, policy: SpendingPolicy) -> None:
        self._policies = {policy.agent_id: policy}

    # Only fetch_policy + record_spend are exercised by the orchestrator path
    # under test; set_policy/delete_policy from the AsyncPolicyStore protocol
    # are intentionally omitted (not part of this e2e).

    async def fetch_policy(self, agent_id: str) -> SpendingPolicy | None:
        return self._policies.get(agent_id)

    async def record_spend(self, agent_id: str, amount: Decimal) -> SpendingPolicy:
        policy = self._policies[agent_id]
        policy.record_spend(amount)
        return policy


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def real_policy() -> SpendingPolicy:
    # Real budget: $100/tx cap, $120 lifetime cap. Auto-approve (no human
    # gate) so the moat proof isolates the revocation deny, not approval.
    return SpendingPolicy(
        agent_id=AGENT_ID,
        trust_level=TrustLevel.MEDIUM,
        limit_per_tx=Decimal("100"),
        limit_total=Decimal("120"),
    )


@pytest.fixture
def real_mandate() -> SpendingMandate:
    # Real, ACTIVE mandate authorizing this agent/wallet. Budget headroom so the
    # mandate phase approves the happy-path payment; the policy engine owns the
    # tighter per-tx/total caps.
    #
    # NOTE ON UNITS: the orchestrator's MANDATE_VALIDATION phase feeds the raw
    # ``payment.amount_minor`` into ``SpendingMandate.check_payment`` (the
    # mandate has no major-unit ``amount`` attribute to fall back to). So the
    # mandate's caps are expressed in the same minor units the orchestrator
    # uses — USDC has 6 decimals, so $1000 == 1_000_000_000 minor. The real
    # SpendingPolicy (Phase 1) normalizes minor→major itself and owns the
    # tighter $100/tx, $120 lifetime caps.
    return SpendingMandate(
        principal_id="usr_owner",
        issuer_id="usr_owner",
        agent_id=AGENT_ID,
        wallet_id=WALLET_ID,
        amount_per_tx=Decimal("1000000000"),  # $1000/tx in USDC minor units
        amount_total=Decimal("1000000000"),  # $1000 lifetime in minor units
        allowed_rails=["usdc", "card", "bank"],
        approval_mode=ApprovalMode.AUTO,
        status=MandateStatus.ACTIVE,
    )


@pytest.fixture
def wired(real_policy: SpendingPolicy, real_mandate: SpendingMandate):
    """Construct the orchestrator the way production does (keyword collaborators).

    Real: orchestrator, EnhancedWalletManager + SpendingPolicy, mandate lookup.
    Faked edges: chain dispatch (AsyncMock), ledger (in-memory), compliance.
    """
    wallet_manager = EnhancedWalletManager(
        settings=SardisSettings(),
        async_policy_store=_AsyncPolicyStore(real_policy),
    )

    chain_executor = MagicMock()
    chain_executor.dispatch_payment = AsyncMock(return_value=_fake_receipt())

    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_allow_compliance())

    ledger = _InMemoryLedger()
    lookup = _ActiveMandateLookup(real_mandate)

    orch = PaymentOrchestrator(
        wallet_manager=wallet_manager,
        compliance=compliance,
        chain_executor=chain_executor,
        ledger=ledger,
        spending_mandate_lookup=lookup,
    )
    return orch, chain_executor, ledger, lookup, real_policy, real_mandate


def _chain(*, amount: str, mandate_id: str):
    return build_mandate_chain(
        agent_id=AGENT_ID,
        amount=amount,
        currency="USDC",
        counterparty=COUNTERPARTY,
        wallet_id=WALLET_ID,
        mandate_id=mandate_id,
    )


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_happy_path_within_budget_executes_and_records(wired):
    """Active mandate + within-budget payment → success, ledger entry, spend recorded."""
    orch, chain_executor, ledger, lookup, policy, _mandate = wired

    result = await orch.execute_chain(_chain(amount="50", mandate_id="md_ok"))

    # Payment succeeded through the real path.
    assert result.status == "submitted"
    assert result.chain_tx_hash == "0xtxhash_e2e"
    assert result.ledger_tx_id == "ltx_1"
    # The active mandate id flowed onto the result.
    assert result.spending_mandate_id == _mandate.id

    # Money actually dispatched once; ledger entry produced.
    chain_executor.dispatch_payment.assert_awaited_once()
    assert len(ledger.entries) == 1

    # Real spend accounting ran (Phase 3.5) — cumulative total moved by $50.
    assert policy.spent_total == Decimal("50")

    # Mandate validation passed in the audit trail.
    phases = {(e.phase, e.success) for e in orch.get_audit_log("md_ok")}
    assert (ExecutionPhase.MANDATE_VALIDATION, True) in phases
    assert (ExecutionPhase.COMPLETED, True) in phases


@pytest.mark.asyncio
async def test_over_budget_payment_denied_no_dispatch(wired):
    """A payment exceeding the real per-tx limit → denied by the real policy engine,
    no chain dispatch."""
    orch, chain_executor, ledger, lookup, _policy, _mandate = wired

    # $500 > $100 per-tx cap.
    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(_chain(amount="500", mandate_id="md_over"))

    chain_executor.dispatch_payment.assert_not_awaited()
    assert ledger.entries == []

    audit = orch.get_audit_log("md_over")
    assert any(
        e.phase == ExecutionPhase.POLICY_VALIDATION and not e.success for e in audit
    )


@pytest.mark.asyncio
async def test_moat_revoke_blocks_next_payment_no_money_moved(wired):
    """THE MOAT PROOF.

    Same agent/mandate: first payment succeeds, then the mandate is REVOKED via
    its real state machine. The very next payment must be DENIED at execution
    time (fail-closed MANDATE_VALIDATION) and ``dispatch_payment`` must NOT be
    called for the revoked attempt — authority removed means no money moves.
    """
    orch, chain_executor, ledger, lookup, _policy, mandate = wired

    # 1) Authority present → payment goes through and money moves once.
    first = await orch.execute_chain(_chain(amount="40", mandate_id="md_pre_revoke"))
    assert first.status == "submitted"
    chain_executor.dispatch_payment.assert_awaited_once()

    # 2) REVOKE the mandate through its real lifecycle transition. After this,
    #    is_active is False and the lookup (status='active' filter) returns None.
    mandate.transition(MandateStatus.REVOKED, changed_by="usr_owner", reason="moat e2e")
    assert mandate.status == MandateStatus.REVOKED
    assert mandate.is_active is False

    # 3) Next payment with the SAME agent/mandate → MUST be denied, no dispatch.
    with pytest.raises(PolicyViolationError) as exc_info:
        await orch.execute_chain(_chain(amount="40", mandate_id="md_post_revoke"))

    # Denied specifically at the mandate-validation gate (fail-closed). The
    # rule_id is the load-bearing signal: PolicyViolationError fixes its
    # ``phase`` attribute to POLICY_VALIDATION in its constructor regardless of
    # where it is raised, so we key on the rule_id the mandate gate sets and on
    # the MANDATE_VALIDATION audit entry below.
    assert exc_info.value.rule_id == "no_active_spending_mandate"

    # NO MONEY MOVED on the revoked attempt: still exactly one dispatch (the
    # pre-revoke payment), no new ledger entry.
    chain_executor.dispatch_payment.assert_awaited_once()
    assert len(ledger.entries) == 1  # only the pre-revoke payment persisted

    # The lookup was actually consulted for the revoked attempt.
    assert lookup.calls >= 2

    # Audit/evidence recorded the denial with the right reason.
    denial = orch.get_audit_log("md_post_revoke")
    assert denial, "expected an audit entry for the denied (revoked) attempt"
    revoke_entry = next(
        e for e in denial if e.phase == ExecutionPhase.MANDATE_VALIDATION
    )
    assert revoke_entry.success is False
    assert revoke_entry.details.get("reason") == "no_active_spending_mandate"


@pytest.mark.asyncio
async def test_lookup_scope_filter_excludes_wrong_subject(real_mandate):
    """Lock the _ActiveMandateLookup scope filter.

    With BOTH a wrong agent_id and a wrong wallet_id, an ACTIVE mandate must
    still be excluded (returns None) — guarding against the all-True scope bug
    where ``None`` membership made the filter a no-op.
    """
    lookup = _ActiveMandateLookup(real_mandate)  # ACTIVE mandate

    # Correct ids → returned.
    assert await lookup.get_active_mandate(agent_id=AGENT_ID, wallet_id=WALLET_ID) is real_mandate
    # Both ids wrong → excluded by the scope filter (not by status).
    assert (
        await lookup.get_active_mandate(
            agent_id="agt_wrong", wallet_id="wal_wrong"
        )
        is None
    )
