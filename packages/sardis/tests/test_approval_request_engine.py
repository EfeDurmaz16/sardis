"""Unit tests for the ApprovalRequest engine: state machine + signed evidence."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis.core.approval_request import (
    ApprovalState,
    ApprovalStateError,
    DecisionChannel,
    build_approval_request,
)
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore


def _req(**over):
    base = {
        "agent_id": "a1",
        "mandate_id": "m1",
        "amount": Decimal("50"),
        "currency": "USDC",
        "counterparty": "0xabc",
        "reason": "over threshold",
        "policy_hash": "ph",
        "mandate_hash": "mh",
    }
    base.update(over)
    return build_approval_request(**base)


def test_approve_records_verifiable_signed_evidence():
    r = _req()
    ev = r.approve(approver="efe@sardis.sh", channel=DecisionChannel.DASHBOARD, secret="k")
    assert r.status == ApprovalState.APPROVED
    assert r.decided_by == "efe@sardis.sh"
    assert ev.verify(secret="k")
    # Bound to the exact request + policy/mandate snapshot.
    assert ev.request_hash == r.request_hash()
    assert ev.policy_hash == "ph" and ev.mandate_hash == "mh"


def test_tampered_evidence_fails_verification():
    r = _req()
    ev = r.deny(approver="efe", secret="k")
    assert ev.verify(secret="k")
    # Tamper with the decision -> recomputed hash no longer matches the stored
    # decision_hash, so verification fails.
    ev.decision = "approved"
    assert not ev.verify(secret="k")


def test_double_decision_is_illegal():
    r = _req()
    r.approve(approver="efe", secret="k")
    with pytest.raises(ApprovalStateError):
        r.deny(approver="efe", secret="k")
    with pytest.raises(ApprovalStateError):
        r.approve(approver="efe", secret="k")


def test_step_up_required_blocks_unverified_approval():
    r = _req(amount=Decimal("50000"), requires_step_up=True)
    with pytest.raises(ApprovalStateError):
        r.approve(approver="efe", secret="k")  # no step-up
    # With step-up verified it goes through.
    ev = r.approve(approver="efe", step_up_verified=True, secret="k")
    assert r.status == ApprovalState.APPROVED
    assert ev.step_up_verified is True


def test_expiry_is_terminal_and_fail_closed():
    r = _req()
    r.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    assert r.is_expired()
    r.expire(secret="k")
    assert r.status == ApprovalState.EXPIRED
    with pytest.raises(ApprovalStateError):
        r.approve(approver="efe", secret="k")


@pytest.mark.asyncio
async def test_store_roundtrip_and_pending_listing():
    store = InMemoryApprovalRequestStore()
    r = _req()
    await store.create(r)
    assert (await store.get(r.id)).status == ApprovalState.PENDING
    assert len(await store.list_pending()) == 1
    r.approve(approver="efe", secret="k")
    await store.save(r)
    assert (await store.get(r.id)).status == ApprovalState.APPROVED
    assert len(await store.list_pending()) == 0


@pytest.mark.asyncio
async def test_expired_pending_query():
    store = InMemoryApprovalRequestStore()
    fresh = _req(mandate_id="m_fresh")
    stale = _req(mandate_id="m_stale")
    stale.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await store.create(fresh)
    await store.create(stale)
    expired = await store.list_expired_pending()
    assert {e.id for e in expired} == {stale.id}
