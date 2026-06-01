"""Execution-time enforcement of the Attenuated Delegation Graph through the
real :class:`PaymentOrchestrator` + :class:`DelegationAwareMandateLookup`.

These tests pin the wiring required by the primitive:

* a DELEGATEE's payment is re-checked against the WHOLE chain at execution time
  (Phase 0.5) — every link non-revoked + within cap/scope + non-expired;
* an authorized delegated payment settles AND decrements the leaf delegation
  AND every ancestor delegation (a child spend consumes parent budget), without
  double-counting the root SpendingMandate;
* a payment exceeding the delegated cap is DENIED fail-closed;
* a payment after a parent (mandate or middle hop) is revoked is DENIED;
* a scope-violating payment (out-of-scope counterparty) is DENIED.

The chain: human -> $500 root mandate (agent_A) -> $50 delegation (agent_B) ->
$20 delegation (tool_C).  tool_C is the acting sub-agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis.core.delegation import DelegationScope, DelegatorKind
from sardis.core.delegation_engine import DelegationEngine
from sardis.core.delegation_lookup import DelegationAwareMandateLookup
from sardis.core.delegation_repository import InMemoryDelegationStore
from sardis.core.orchestrator import PaymentOrchestrator, PolicyViolationError
from sardis.core.revocation import RevocationTargetKind
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import (
    DelegationSubtreeRevoker,
    InMemoryMandateRevoker,
)
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import SpendingMandate

SECRET = "test-delegation-exec-secret"


# ── Fake payment / chain plumbing (mirrors test_orchestrator_delegation) ─


@dataclass
class _FakePayment:
    mandate_id: str = "exec_001"
    agent_id: str | None = "tool_C"  # the acting SUB-agent (leaf delegatee)
    wallet_id: str | None = None
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 10_000_000  # 10 USDC
    destination: str = "openai.com"
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "openai.com"
    merchant_category: str | None = None
    rail: str | None = "usdc"
    fee: Any = None
    amount: Any = None


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtx"
    chain: str = "base"
    block_number: int = 1
    audit_anchor: str = "0x" + "00" * 32


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


class _InMemoryBaseLookup:
    """A minimal base SpendingMandateLookupPort over a dict of mandates.

    Resolves the root mandate by agent/wallet and records spend against its
    ``spent_total`` (the delegation-aware wrapper layers chain enforcement +
    ancestor-cap decrement on top).
    """

    def __init__(self, mandates: dict[str, SpendingMandate]) -> None:
        self._by_id = mandates

    async def get_active_mandate(self, agent_id=None, wallet_id=None, payment=None):
        for m in self._by_id.values():
            if m.status.value != "active":
                continue
            if agent_id and m.agent_id == agent_id:
                return m
            if wallet_id and m.wallet_id == wallet_id:
                return m
        return None

    async def record_spend(self, mandate_id, amount):
        m = self._by_id.get(mandate_id)
        if m is not None:
            m.spent_total = (m.spent_total or Decimal("0")) + Decimal(str(amount))


def _root_mandate() -> SpendingMandate:
    return SpendingMandate(
        principal_id="usr_human", issuer_id="usr_human", id="mandate_root_A",
        agent_id="agent_A", amount_total=Decimal("500"), amount_per_tx=Decimal("500"),
        currency="USDC", merchant_scope={"allowed": ["openai.com"]},
        allowed_rails=["usdc"], expires_at=datetime.now(UTC) + timedelta(days=30),
    )


async def _setup():
    root = _root_mandate()
    dstore = InMemoryDelegationStore()
    mandates = {root.id: root}

    async def resolver(mid):
        return mandates.get(mid)

    eng = DelegationEngine(
        store=dstore, mandate_resolver=resolver, signing_secret=SECRET
    )
    b = await eng.delegate(
        delegator_ref=root.id, delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B", delegator_principal="agent_A", amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
    )
    c = await eng.delegate(
        delegator_ref=b.id, delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C", delegator_principal="agent_B", amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
    )
    base = _InMemoryBaseLookup(mandates)
    lookup = DelegationAwareMandateLookup(base=base, engine=eng)
    return root, eng, dstore, base, lookup, b, c


def _orchestrator(lookup):
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()
    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())
    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())
    ledger = MagicMock()
    ledger.append = MagicMock(return_value=MagicMock(tx_id="ltx_1"))
    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr, compliance=compliance, chain_executor=chain_exec,
        ledger=ledger, spending_mandate_lookup=lookup,
    )
    return orch, chain_exec


# ── (a) within the chain: succeeds + decrements ancestors ───────────────


@pytest.mark.asyncio
async def test_delegatee_payment_succeeds_and_decrements_ancestors():
    root, eng, dstore, base, lookup, b, c = await _setup()
    orch, chain_exec = _orchestrator(lookup)

    # tool_C pays 10 USDC (<= C's $20 cap, <= B's $50, <= root $500).
    result = await orch.execute_chain(_FakeMandateChain())
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()

    # The resolved chain was recorded on the result (for Proof-of-Authority):
    # root mandate + B + C, root-first.
    assert [getattr(x, "id", None) for x in result.delegation_chain] == [
        root.id, b.id, c.id,
    ]

    # Ancestor decrement: BOTH the leaf C and the ancestor B were drawn down by
    # 10 — a child spend consumes parent budget.
    b_after = await dstore.get(b.id)
    c_after = await dstore.get(c.id)
    assert c_after.spent_total == Decimal("10")
    assert c_after.remaining == Decimal("10")  # 20 - 10
    assert b_after.spent_total == Decimal("10")
    assert b_after.remaining == Decimal("40")  # 50 - 10

    # Root mandate spent_total recorded once (no double-count from the chain).
    assert base._by_id[root.id].spent_total == Decimal("10")


# ── (b) exceeding the delegated cap: DENIED ─────────────────────────────


@pytest.mark.asyncio
async def test_payment_exceeding_delegated_cap_denied():
    root, eng, dstore, base, lookup, b, c = await _setup()
    orch, chain_exec = _orchestrator(lookup)

    # tool_C tries 25 USDC > C's $20 cap (fits B and root, but C is the leaf).
    over_cap = _FakeMandateChain(
        payment=_FakePayment(mandate_id="exec_overcap", amount_minor=25_000_000)
    )
    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(over_cap)
    chain_exec.dispatch_payment.assert_not_awaited()

    # Nothing decremented — no money moved.
    assert (await dstore.get(c.id)).spent_total == Decimal("0")
    assert (await dstore.get(b.id)).spent_total == Decimal("0")
    assert base._by_id[root.id].spent_total == Decimal("0")


# ── (c) after a parent is revoked: DENIED (subtree propagation) ─────────


@pytest.mark.asyncio
async def test_payment_after_parent_revoked_denied():
    root, eng, dstore, base, lookup, b, c = await _setup()
    orch, chain_exec = _orchestrator(lookup)

    # Revoke the MIDDLE hop B — propagation marks the whole subtree (C) revoked.
    rev_engine = RevocationEngine(
        store=InMemoryRevocationStore(),
        mandate_revoker=InMemoryMandateRevoker(
            {root.id: {"status": "active", "agent_id": "agent_A",
                       "principal_id": "usr_human"}}
        ),
        delegation_revoker=DelegationSubtreeRevoker(dstore),
        signing_secret=SECRET,
    )
    await rev_engine.revoke(
        target_kind=RevocationTargetKind.DELEGATION,
        target_ref=b.id, requested_by="agent_A", reason="kill subtree",
    )

    # tool_C's chain now has a revoked link (B) -> check_chain denies ->
    # the lookup returns None -> orchestrator DENIES before dispatch.
    denied = _FakeMandateChain(payment=_FakePayment(mandate_id="exec_revoked"))
    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(denied)
    chain_exec.dispatch_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_payment_after_root_mandate_revoked_denied():
    root, eng, dstore, base, lookup, b, c = await _setup()
    orch, chain_exec = _orchestrator(lookup)

    # Revoke the ROOT mandate — propagates to the entire delegation subtree.
    rev_engine = RevocationEngine(
        store=InMemoryRevocationStore(),
        mandate_revoker=InMemoryMandateRevoker(
            {root.id: {"status": "active", "agent_id": "agent_A",
                       "principal_id": "usr_human"}}
        ),
        delegation_revoker=DelegationSubtreeRevoker(dstore),
        signing_secret=SECRET,
    )
    await rev_engine.revoke(
        target_kind=RevocationTargetKind.MANDATE,
        target_ref=root.id, requested_by="usr_human", reason="kill",
    )
    # Reflect revocation on the base mandate row too (the revoker drives the
    # delegation subtree; the mandate-status flip is the base lookup's domain).
    root.status = root.status.__class__("revoked")

    denied = _FakeMandateChain(payment=_FakePayment(mandate_id="exec_root_revoked"))
    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(denied)
    chain_exec.dispatch_payment.assert_not_awaited()


# ── (d) scope-violating payment: DENIED ─────────────────────────────────


@pytest.mark.asyncio
async def test_scope_violating_payment_denied():
    root, eng, dstore, base, lookup, b, c = await _setup()
    orch, chain_exec = _orchestrator(lookup)

    # tool_C pays a counterparty OUTSIDE its delegated scope (only openai.com).
    out_of_scope = _FakeMandateChain(
        payment=_FakePayment(
            mandate_id="exec_scope",
            destination="aws.amazon.com",
            merchant_id="aws.amazon.com",
        )
    )
    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(out_of_scope)
    chain_exec.dispatch_payment.assert_not_awaited()
    assert (await dstore.get(c.id)).spent_total == Decimal("0")


# ── direct (non-delegated) root-holder payment still works ──────────────


@pytest.mark.asyncio
async def test_direct_root_holder_payment_unaffected():
    root, eng, dstore, base, lookup, b, c = await _setup()
    orch, chain_exec = _orchestrator(lookup)

    # agent_A is the ROOT mandate holder (not a delegatee) — no chain, direct path.
    direct = _FakeMandateChain(
        payment=_FakePayment(mandate_id="exec_direct", agent_id="agent_A")
    )
    result = await orch.execute_chain(direct)
    assert result.status == "submitted"
    assert result.delegation_chain == []  # not a delegated payment
    chain_exec.dispatch_payment.assert_awaited_once()
    # Root spent_total moved; delegation hops untouched.
    assert base._by_id[root.id].spent_total == Decimal("10")
    assert (await dstore.get(c.id)).spent_total == Decimal("0")
