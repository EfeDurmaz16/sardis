"""Tests: revoking a parent propagates to the entire delegation subtree.

Revoking a mandate / agent / delegation must kill every descendant delegation
(recorded as PropagationTargets kind=delegation in the signed proof), and a
payment exercising a descendant's authority must then be DENIED fail-closed by
the execution-time chain re-check.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis.core.delegation import DelegationScope, DelegationStatus, DelegatorKind
from sardis.core.delegation_engine import DelegationEngine
from sardis.core.delegation_repository import InMemoryDelegationStore
from sardis.core.revocation import PropagationKind, RevocationStatus, RevocationTargetKind
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import (
    DelegationSubtreeRevoker,
    InMemoryMandateRevoker,
)
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import SpendingMandate

SECRET = "test-secret"


def _root_mandate() -> SpendingMandate:
    return SpendingMandate(
        principal_id="usr_human",
        issuer_id="usr_human",
        id="mandate_root_A",
        agent_id="agent_A",
        amount_total=Decimal("500"),
        amount_per_tx=Decimal("500"),
        currency="USDC",
        merchant_scope={"allowed": ["openai.com", "aws.amazon.com"]},
        allowed_rails=["usdc"],
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )


async def _build_chain(root: SpendingMandate):
    """root -> A delegates $50 to B -> B delegates $20 to C. Returns (eng, store, b, c)."""
    store = InMemoryDelegationStore()
    mandates = {root.id: root}

    async def resolver(mid: str):
        return mandates.get(mid)

    eng = DelegationEngine(store=store, mandate_resolver=resolver, signing_secret=SECRET)
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
    return eng, store, b, c


def _revocation_engine(store, delegation_store, *, mandates):
    """A RevocationEngine wired with the in-memory mandate revoker + subtree revoker."""
    mandate_revoker = InMemoryMandateRevoker(mandates)
    delegation_revoker = DelegationSubtreeRevoker(delegation_store)
    return RevocationEngine(
        store=store,
        mandate_revoker=mandate_revoker,
        delegation_revoker=delegation_revoker,
        signing_secret=SECRET,
    )


@pytest.mark.asyncio
async def test_revoking_root_mandate_kills_entire_subtree():
    root = _root_mandate()
    eng, dstore, b, c = await _build_chain(root)

    # Mandate-revoker view of the mandate (keyed by id).
    mandates = {root.id: {"status": "active", "agent_id": "agent_A", "principal_id": "usr_human"}}
    rev_engine = _revocation_engine(InMemoryRevocationStore(), dstore, mandates=mandates)

    rev = await rev_engine.revoke(
        target_kind=RevocationTargetKind.MANDATE,
        target_ref=root.id,
        requested_by="usr_human",
        reason="kill the tree",
    )

    # The proof lists BOTH delegations as killed delegation targets.
    dlg_targets = {t.ref: t for t in rev.targets if t.kind == PropagationKind.DELEGATION}
    assert b.id in dlg_targets and c.id in dlg_targets
    assert dlg_targets[b.id].kill_status.value == "killed"
    assert dlg_targets[c.id].kill_status.value == "killed"
    # Fully propagated + the signed proof verifies.
    assert rev.status == RevocationStatus.PROPAGATED
    assert rev.proof.verify(SECRET) is True

    # Both delegations are now revoked in the store.
    assert (await dstore.get(b.id)).status == DelegationStatus.REVOKED
    assert (await dstore.get(c.id)).status == DelegationStatus.REVOKED


@pytest.mark.asyncio
async def test_revoking_middle_delegation_kills_only_its_subtree():
    root = _root_mandate()
    eng, dstore, b, c = await _build_chain(root)

    rev_engine = _revocation_engine(InMemoryRevocationStore(), dstore, mandates={})

    # Revoke B directly (delegation target).
    rev = await rev_engine.revoke(
        target_kind=RevocationTargetKind.DELEGATION,
        target_ref=b.id,
        requested_by="agent_A",
        reason="revoke B",
    )

    dlg = {t.ref: t for t in rev.targets if t.kind == PropagationKind.DELEGATION}
    # B and its descendant C are killed.
    assert dlg[b.id].kill_status.value == "killed"
    assert dlg[c.id].kill_status.value == "killed"
    assert (await dstore.get(b.id)).status == DelegationStatus.REVOKED
    assert (await dstore.get(c.id)).status == DelegationStatus.REVOKED


@pytest.mark.asyncio
async def test_revoked_subtree_denies_descendant_chain_check():
    """After revoking the root, the descendant C's chain re-check must DENY.

    This is the execution-time backstop: even though the orchestrator looks the
    payment up via C's chain, the revoked links break the chain -> fail-closed.
    """
    root = _root_mandate()
    eng, dstore, b, c = await _build_chain(root)

    # Before revocation: C's chain authorizes.
    chain_before = await eng.resolve_chain("tool_C")
    res_before = await eng.check_chain(
        chain_before, amount=Decimal("10"), counterparty="openai.com", rail="usdc"
    )
    assert res_before.authorized is True

    # Revoke the whole subtree at the root.
    mandates = {root.id: {"status": "active", "agent_id": "agent_A", "principal_id": "usr_human"}}
    rev_engine = _revocation_engine(InMemoryRevocationStore(), dstore, mandates=mandates)
    await rev_engine.revoke(
        target_kind=RevocationTargetKind.MANDATE, target_ref=root.id,
        requested_by="usr_human", reason="kill",
    )

    # After revocation: C is no longer the active delegatee, so resolve returns
    # empty -> not authorized. And even resolving from the (now revoked) leaf and
    # re-checking denies on the broken link.
    chain_empty = await eng.resolve_chain("tool_C")
    assert chain_empty == []  # C's delegation is revoked, no longer active
    res_empty = await eng.check_chain(chain_empty, amount=Decimal("10"), counterparty="openai.com")
    assert res_empty.authorized is False

    c_revoked = await dstore.get(c.id)
    chain_from_leaf = await eng.resolve_chain_for(c_revoked)
    res = await eng.check_chain(
        chain_from_leaf, amount=Decimal("10"), counterparty="openai.com", rail="usdc"
    )
    assert res.authorized is False
    assert res.error_code == "DELEGATION_REVOKED"


@pytest.mark.asyncio
async def test_revoking_agent_kills_held_delegation_subtree():
    """Revoking agent_B (the delegatee of B) kills B + its descendant C."""
    root = _root_mandate()
    eng, dstore, b, c = await _build_chain(root)

    # agent_B holds delegation B; revoking the agent must sweep its held subtree.
    mandates = {}
    rev_engine = _revocation_engine(InMemoryRevocationStore(), dstore, mandates=mandates)
    rev = await rev_engine.revoke(
        target_kind=RevocationTargetKind.AGENT,
        target_ref="agent_B",
        requested_by="usr_human",
        reason="agent compromised",
    )

    dlg = {t.ref: t for t in rev.targets if t.kind == PropagationKind.DELEGATION}
    assert dlg[b.id].kill_status.value == "killed"
    assert dlg[c.id].kill_status.value == "killed"


@pytest.mark.asyncio
async def test_idempotent_revoke_is_already_dead_on_resweep():
    root = _root_mandate()
    eng, dstore, b, c = await _build_chain(root)
    rev_engine = _revocation_engine(
        InMemoryRevocationStore(), dstore,
        mandates={},
    )
    # First revoke kills B + C.
    await rev_engine.revoke(
        target_kind=RevocationTargetKind.DELEGATION, target_ref=b.id,
        requested_by="agent_A", reason="x",
    )
    # A direct re-sweep via the subtree revoker reports already_dead (idempotent).
    revoker = DelegationSubtreeRevoker(dstore)
    outcomes = await revoker.revoke_subtree(
        mandate_ids=[], agent_id=None, delegation_ids=[b.id],
        requested_by="agent_A", reason="x",
    )
    by_ref = {o.ref: o for o in outcomes}
    assert by_ref[b.id].kill_status.value == "already_dead"
    assert by_ref[c.id].kill_status.value == "already_dead"
