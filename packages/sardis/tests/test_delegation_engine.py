"""Tests for the Attenuated Delegation Graph (object-capability for money).

Pins the cardinal rule: a delegate can NEVER exceed its delegator. Attenuation
is enforced fail-closed at mint AND re-checked at execution time over the whole
chain.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis.core.delegation import (
    MAX_DELEGATION_DEPTH,
    DelegationScope,
    DelegationStatus,
    DelegatorKind,
)
from sardis.core.delegation_engine import DelegationEngine, DelegationError
from sardis.core.delegation_repository import InMemoryDelegationStore
from sardis.core.spending_mandate import MandateStatus, SpendingMandate

SECRET = "test-delegation-secret"


# ── Fixtures / helpers ─────────────────────────────────────────────────


def _root_mandate(**overrides) -> SpendingMandate:
    """A $500 root mandate for agent A, scoped to two counterparties."""
    defaults = {
        "principal_id": "usr_human",
        "issuer_id": "usr_human",
        "id": "mandate_root_A",
        "agent_id": "agent_A",
        "amount_total": Decimal("500"),
        "amount_per_tx": Decimal("500"),
        "currency": "USDC",
        "merchant_scope": {"allowed": ["aws.amazon.com", "openai.com", "anthropic.com"]},
        "allowed_rails": ["usdc", "card"],
        "expires_at": datetime.now(UTC) + timedelta(days=30),
    }
    defaults.update(overrides)
    return SpendingMandate(**defaults)


def _engine(mandate: SpendingMandate):
    store = InMemoryDelegationStore()
    mandates = {mandate.id: mandate}

    async def resolver(mandate_id: str):
        return mandates.get(mandate_id)

    return DelegationEngine(store=store, mandate_resolver=resolver, signing_secret=SECRET), store


# ── Attenuation at mint ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_delegation_attenuates_and_signs():
    root = _root_mandate()
    eng, _ = _engine(root)

    dlg = await eng.delegate(
        delegator_ref=root.id,
        delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B",
        delegator_principal="agent_A",
        amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    assert dlg.amount_cap == Decimal("50")
    assert dlg.depth == 1
    assert dlg.root_mandate_id == root.id
    assert dlg.status == DelegationStatus.ACTIVE
    # Signed, independently verifiable.
    assert dlg.evidence is not None
    assert dlg.evidence.verify(SECRET) is True
    assert dlg.evidence.verify("wrong-key") is False


@pytest.mark.asyncio
async def test_over_cap_delegation_rejected():
    root = _root_mandate()  # $500 remaining
    eng, _ = _engine(root)

    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=root.id,
            delegator_kind=DelegatorKind.MANDATE,
            delegatee="agent_B",
            delegator_principal="agent_A",
            amount_cap=Decimal("600"),  # > $500 remaining
        )
    assert exc.value.error_code == "ATTENUATION_VIOLATION"
    assert any("exceeds delegator remaining" in v for v in exc.value.violations)


@pytest.mark.asyncio
async def test_scope_superset_delegation_rejected():
    root = _root_mandate()  # counterparties: aws, openai, anthropic
    eng, _ = _engine(root)

    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=root.id,
            delegator_kind=DelegatorKind.MANDATE,
            delegatee="agent_B",
            delegator_principal="agent_A",
            amount_cap=Decimal("50"),
            # stripe.com is NOT in the parent's allowed counterparties.
            scope=DelegationScope(counterparties=["openai.com", "stripe.com"]),
        )
    assert exc.value.error_code == "ATTENUATION_VIOLATION"
    assert any("counterparties" in v for v in exc.value.violations)


@pytest.mark.asyncio
async def test_longer_expiry_delegation_rejected():
    root = _root_mandate(expires_at=datetime.now(UTC) + timedelta(days=5))
    eng, _ = _engine(root)

    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=root.id,
            delegator_kind=DelegatorKind.MANDATE,
            delegatee="agent_B",
            delegator_principal="agent_A",
            amount_cap=Decimal("50"),
            expires_at=datetime.now(UTC) + timedelta(days=30),  # outlives parent
        )
    assert exc.value.error_code == "ATTENUATION_VIOLATION"
    assert any("after delegator expiry" in v for v in exc.value.violations)


@pytest.mark.asyncio
async def test_uncapped_child_of_capped_parent_rejected():
    root = _root_mandate()
    eng, _ = _engine(root)
    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=root.id,
            delegator_kind=DelegatorKind.MANDATE,
            delegatee="agent_B",
            delegator_principal="agent_A",
            amount_cap=None,  # parent is capped — uncapped child is a widening
        )
    assert exc.value.error_code == "ATTENUATION_VIOLATION"


@pytest.mark.asyncio
async def test_cannot_delegate_from_revoked_delegator():
    root = _root_mandate()
    root.status = MandateStatus.REVOKED
    eng, _ = _engine(root)
    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=root.id,
            delegator_kind=DelegatorKind.MANDATE,
            delegatee="agent_B",
            delegator_principal="agent_A",
            amount_cap=Decimal("50"),
        )
    assert exc.value.error_code == "DELEGATOR_NOT_ACTIVE"


# ── Multi-hop attenuation: B delegates to C ────────────────────────────


@pytest.mark.asyncio
async def test_grandchild_cannot_exceed_child():
    root = _root_mandate()
    eng, _ = _engine(root)
    b = await eng.delegate(
        delegator_ref=root.id,
        delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B",
        delegator_principal="agent_A",
        amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    # C tries to get $80 from B's $50 — must be rejected.
    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=b.id,
            delegator_kind=DelegatorKind.DELEGATION,
            delegatee="tool_C",
            delegator_principal="agent_B",
            amount_cap=Decimal("80"),
            scope=DelegationScope(counterparties=["openai.com"]),
        )
    assert exc.value.error_code == "ATTENUATION_VIOLATION"

    # $20 is fine.
    c = await eng.delegate(
        delegator_ref=b.id,
        delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C",
        delegator_principal="agent_B",
        amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    assert c.depth == 2
    assert c.root_mandate_id == root.id


@pytest.mark.asyncio
async def test_depth_limit_enforced():
    root = _root_mandate(amount_total=Decimal("500"), amount_per_tx=Decimal("500"))
    eng, store = _engine(root)

    # Build a chain right up to MAX_DELEGATION_DEPTH.
    parent_ref, parent_kind = root.id, DelegatorKind.MANDATE
    last = None
    for i in range(MAX_DELEGATION_DEPTH):
        last = await eng.delegate(
            delegator_ref=parent_ref,
            delegator_kind=parent_kind,
            delegatee=f"agent_{i}",
            delegator_principal="p",
            amount_cap=Decimal("10"),
        )
        parent_ref, parent_kind = last.id, DelegatorKind.DELEGATION

    assert last.depth == MAX_DELEGATION_DEPTH
    # One more hop must be rejected.
    with pytest.raises(DelegationError) as exc:
        await eng.delegate(
            delegator_ref=last.id,
            delegator_kind=DelegatorKind.DELEGATION,
            delegatee="agent_too_deep",
            delegator_principal="p",
            amount_cap=Decimal("5"),
        )
    assert exc.value.error_code == "MAX_DEPTH_EXCEEDED"


# ── Chain resolution + execution-time re-check ─────────────────────────


@pytest.mark.asyncio
async def test_valid_chain_resolves_and_authorizes():
    root = _root_mandate()
    eng, _ = _engine(root)
    b = await eng.delegate(
        delegator_ref=root.id,
        delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B",
        delegator_principal="agent_A",
        amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
    )
    c = await eng.delegate(
        delegator_ref=b.id,
        delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C",
        delegator_principal="agent_B",
        amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
    )

    chain = await eng.resolve_chain("tool_C")
    # root mandate + B + C, root-first.
    assert [x.id for x in chain] == [root.id, b.id, c.id]

    res = await eng.check_chain(
        chain, amount=Decimal("15"), counterparty="openai.com", rail="usdc"
    )
    assert res.authorized is True
    assert res.leaf_delegation_id == c.id


@pytest.mark.asyncio
async def test_chain_denied_when_leaf_over_its_cap():
    root = _root_mandate()
    eng, _ = _engine(root)
    b = await eng.delegate(
        delegator_ref=root.id, delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B", delegator_principal="agent_A", amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    c = await eng.delegate(
        delegator_ref=b.id, delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C", delegator_principal="agent_B", amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    chain = await eng.resolve_chain("tool_C")
    # $25 > C's $20 cap, even though it fits B ($50) and root ($500).
    res = await eng.check_chain(chain, amount=Decimal("25"), counterparty="openai.com")
    assert res.authorized is False
    assert res.error_code == "DELEGATION_CAP_EXCEEDED"
    assert res.broken_link == c.id


@pytest.mark.asyncio
async def test_chain_denied_out_of_scope_counterparty():
    root = _root_mandate()
    eng, _ = _engine(root)
    b = await eng.delegate(
        delegator_ref=root.id, delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B", delegator_principal="agent_A", amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    chain = await eng.resolve_chain("agent_B")
    res = await eng.check_chain(chain, amount=Decimal("10"), counterparty="aws.amazon.com")
    assert res.authorized is False
    assert res.error_code == "DELEGATION_COUNTERPARTY_OUT_OF_SCOPE"
    assert res.broken_link == b.id


@pytest.mark.asyncio
async def test_empty_chain_not_authorized():
    root = _root_mandate()
    eng, _ = _engine(root)
    chain = await eng.resolve_chain("agent_nobody")
    assert chain == []
    res = await eng.check_chain(chain, amount=Decimal("1"))
    assert res.authorized is False
    assert res.error_code == "NO_DELEGATION_CHAIN"


# ── Spend walks ancestors ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_spend_walks_ancestors():
    root = _root_mandate()
    eng, store = _engine(root)
    b = await eng.delegate(
        delegator_ref=root.id, delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B", delegator_principal="agent_A", amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    c = await eng.delegate(
        delegator_ref=b.id, delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C", delegator_principal="agent_B", amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    chain = await eng.resolve_chain("tool_C")
    await eng.record_chain_spend(chain, Decimal("15"))

    b_after = await store.get(b.id)
    c_after = await store.get(c.id)
    # Both the leaf and its ancestor delegation were drawn down.
    assert c_after.spent_total == Decimal("15")
    assert c_after.remaining == Decimal("5")
    assert b_after.spent_total == Decimal("15")
    assert b_after.remaining == Decimal("35")

    # A second $5 spend exhausts C (cap 20).
    await eng.record_chain_spend(chain, Decimal("5"))
    c_final = await store.get(c.id)
    assert c_final.spent_total == Decimal("20")
    assert c_final.status == DelegationStatus.EXHAUSTED

    # And C can no longer authorize.
    chain2 = await eng.resolve_chain_for(c_final)
    res = await eng.check_chain(chain2, amount=Decimal("1"), counterparty="openai.com")
    assert res.authorized is False


@pytest.mark.asyncio
async def test_revoked_link_kills_chain_for_descendant():
    root = _root_mandate()
    eng, store = _engine(root)
    b = await eng.delegate(
        delegator_ref=root.id, delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B", delegator_principal="agent_A", amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    c = await eng.delegate(
        delegator_ref=b.id, delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C", delegator_principal="agent_B", amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"]),
    )
    # Revoke the MIDDLE link B directly.
    b.revoke(revoked_by="agent_A", reason="test")
    await store.save(b)

    chain = await eng.resolve_chain_for(c)
    res = await eng.check_chain(chain, amount=Decimal("5"), counterparty="openai.com")
    assert res.authorized is False
    assert res.error_code == "DELEGATION_REVOKED"
    assert res.broken_link == b.id
