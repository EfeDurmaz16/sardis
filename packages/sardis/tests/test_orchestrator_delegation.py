"""Orchestrator-level: a delegated payment is DENIED fail-closed after the
parent's authority is revoked.

The Attenuated Delegation Graph plugs into the orchestrator's Phase 0.5
(MANDATE_VALIDATION) via a delegation-aware lookup: when a sub-agent acts, the
lookup resolves its delegation chain to the root SpendingMandate and re-checks
EVERY link. If any link is revoked/expired/out-of-cap, the lookup yields no
active authority -> the orchestrator denies before any money moves.
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
from sardis.core.delegation_repository import InMemoryDelegationStore
from sardis.core.orchestrator import PaymentOrchestrator, PolicyViolationError
from sardis.core.revocation import RevocationTargetKind
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import DelegationSubtreeRevoker, InMemoryMandateRevoker
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import SpendingMandate

SECRET = "test-secret"


@dataclass
class _FakePayment:
    mandate_id: str = "mdt_delegated_001"
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


class _DelegationAwareLookup:
    """Phase-0.5 lookup that authorizes via the delegation chain.

    For an acting sub-agent it resolves the chain to the root mandate and
    re-checks every link; only when the whole chain authorizes does it return
    the root SpendingMandate (which the orchestrator then enforces normally).
    Any broken link -> None -> the orchestrator denies fail-closed.
    """

    def __init__(self, eng: DelegationEngine) -> None:
        self._eng = eng

    async def get_active_mandate(self, agent_id=None, wallet_id=None):
        chain = await self._eng.resolve_chain(agent_id)
        if not chain:
            return None
        res = await self._eng.check_chain(
            chain, amount=Decimal("10"), counterparty="openai.com", rail="usdc"
        )
        if not res.authorized:
            return None
        # chain[0] is the root SpendingMandate.
        return chain[0]

    async def record_spend(self, mandate_id, amount):
        return None


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

    eng = DelegationEngine(store=dstore, mandate_resolver=resolver, signing_secret=SECRET)
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
    return root, eng, dstore, b, c


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


@pytest.mark.asyncio
async def test_delegated_payment_authorized_then_denied_after_revocation():
    root, eng, dstore, b, c = await _setup()
    lookup = _DelegationAwareLookup(eng)
    orch, chain_exec = _orchestrator(lookup)

    # Before revocation: tool_C's delegated payment goes through.
    result = await orch.execute_chain(_FakeMandateChain())
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()

    # Revoke the root mandate — propagates to the whole delegation subtree.
    rev_engine = RevocationEngine(
        store=InMemoryRevocationStore(),
        mandate_revoker=InMemoryMandateRevoker(
            {root.id: {"status": "active", "agent_id": "agent_A", "principal_id": "usr_human"}}
        ),
        delegation_revoker=DelegationSubtreeRevoker(dstore),
        signing_secret=SECRET,
    )
    await rev_engine.revoke(
        target_kind=RevocationTargetKind.MANDATE,
        target_ref=root.id, requested_by="usr_human", reason="kill",
    )

    # After revocation: tool_C's chain is broken (its delegation is revoked) ->
    # lookup returns None -> orchestrator DENIES before any dispatch.
    chain_exec.dispatch_payment.reset_mock()
    # Distinct mandate_id so the dedup store does not short-circuit as a duplicate
    # of the first (successful) execution before Phase 0.5 runs.
    denied_chain = _FakeMandateChain(payment=_FakePayment(mandate_id="mdt_delegated_002"))
    with pytest.raises(PolicyViolationError):
        await orch.execute_chain(denied_chain)
    chain_exec.dispatch_payment.assert_not_awaited()
