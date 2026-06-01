"""Tests for the Propagating Revocation primitive (the lead wedge).

Pins the contract:

* ONE revoke propagates to every rail kind (mandate, spend objects, cards,
  approvals, in-flight) — each object recorded as a PropagationTarget with its
  kill_status;
* a downstream kill failure is recorded ``blocked_pending`` (NEVER silent
  success) and forces the overall outcome to ``blocked_pending_downstream``;
* after a (partial) revocation the mandate is revoked, so the orchestrator's
  lookup still denies at execution time (authority never stays silently alive);
* the signed RevocationProof verifies independently from its own fields, and
  binds the full target list (tampering breaks verification);
* re-revoke is idempotent — same revocation + same proof, no double-propagation;
* a rail-killer that RAISES becomes a synthetic ``failed`` target, never aborts
  the kill, and never inflates the proof.
"""

from __future__ import annotations

import pytest

from sardis.core.revocation import (
    KillStatus,
    PropagationKind,
    RevocationStatus,
    RevocationTargetKind,
)
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import (
    InMemoryApprovalRevoker,
    InMemoryCardFreezer,
    InMemoryInFlightBlocker,
    InMemoryMandateRevoker,
    InMemorySpendObjectRevoker,
)
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import MandateStatus
from sardis.core.spending_mandate_lookup import SpendingMandateLookup

SECRET = "test-revocation-secret"

AGENT = "agent_kill_me"
MANDATE = "mandate_abc"


def _fixtures():
    """Shared in-memory rail state for an agent with authority on every rail."""
    mandates = {
        MANDATE: {"status": "active", "agent_id": AGENT, "principal_id": "usr_1"},
    }
    spend_objects = {
        "po_1": {"mandate_id": MANDATE, "status": "minted"},
        "po_2": {"mandate_id": MANDATE, "status": "settled"},  # already terminal
    }
    cards = {
        "card_1": {"agent_id": AGENT, "principal_id": "usr_1", "state": "active"},
        "card_other": {"agent_id": "someone_else", "state": "active"},
    }
    approvals = {
        "apreq_1": {"agent_id": AGENT, "mandate_id": MANDATE, "status": "pending"},
    }
    payments = {
        "pay_1": {"agent_id": AGENT, "mandate_id": MANDATE, "status": "pending"},
    }
    return mandates, spend_objects, cards, approvals, payments


def _engine(*, card_fail=None, inflight_fail=None, fixtures=None):
    mandates, spend_objects, cards, approvals, payments = fixtures or _fixtures()
    store = InMemoryRevocationStore()
    eng = RevocationEngine(
        store=store,
        mandate_revoker=InMemoryMandateRevoker(mandates),
        spend_object_revoker=InMemorySpendObjectRevoker(spend_objects),
        card_freezer=InMemoryCardFreezer(cards, fail_refs=card_fail),
        approval_revoker=InMemoryApprovalRevoker(approvals),
        in_flight_blocker=InMemoryInFlightBlocker(payments, fail_refs=inflight_fail),
        signing_secret=SECRET,
    )
    return eng, store, (mandates, spend_objects, cards, approvals, payments)


def _by_kind(rev, kind: PropagationKind):
    return [t for t in rev.targets if t.kind == kind]


# ── propagation to every rail ──────────────────────────────────────────


async def test_revoke_propagates_to_all_rails():
    eng, _store, state = _engine()
    mandates, spend_objects, cards, approvals, payments = state

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT,
        target_ref=AGENT,
        requested_by="usr_1",
        reason="compromised",
    )

    # Outcome is fully propagated (no failures injected).
    assert rev.status == RevocationStatus.PROPAGATED
    assert rev.revoked_at is not None

    # Mandate killed.
    mt = _by_kind(rev, PropagationKind.MANDATE)
    assert [t.ref for t in mt] == [MANDATE]
    assert mt[0].kill_status == KillStatus.KILLED
    assert mandates[MANDATE]["status"] == "revoked"

    # Spend objects: po_1 revoked, po_2 already terminal (already_dead).
    so = {t.ref: t.kill_status for t in _by_kind(rev, PropagationKind.SPEND_OBJECT)}
    assert so["po_1"] == KillStatus.KILLED
    assert so["po_2"] == KillStatus.ALREADY_DEAD
    assert spend_objects["po_1"]["status"] == "revoked"

    # Cards: only the agent's card frozen; the other agent's card untouched.
    cd = {t.ref: t.kill_status for t in _by_kind(rev, PropagationKind.CARD)}
    assert cd == {"card_1": KillStatus.KILLED}
    assert cards["card_1"]["state"] == "frozen"
    assert cards["card_other"]["state"] == "active"

    # Pending approval denied.
    ap = _by_kind(rev, PropagationKind.APPROVAL)
    assert [t.ref for t in ap] == ["apreq_1"]
    assert ap[0].kill_status == KillStatus.KILLED
    assert approvals["apreq_1"]["status"] == "denied"

    # In-flight payment blocked.
    inf = _by_kind(rev, PropagationKind.IN_FLIGHT)
    assert [t.ref for t in inf] == ["pay_1"]
    assert inf[0].kill_status == KillStatus.KILLED
    assert payments["pay_1"]["status"] == "blocked"


async def test_every_target_recorded_with_status_and_detail():
    eng, _store, _state = _engine()
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    # Every kind present, every target carries a status + non-empty detail.
    kinds = {t.kind for t in rev.targets}
    assert kinds == {
        PropagationKind.MANDATE,
        PropagationKind.SPEND_OBJECT,
        PropagationKind.CARD,
        PropagationKind.APPROVAL,
        PropagationKind.IN_FLIGHT,
    }
    for t in rev.targets:
        assert isinstance(t.kill_status, KillStatus)
        assert t.detail  # human-readable explanation always present


# ── fail-closed: downstream failure is blocked_pending, not silent success ─


async def test_card_freeze_failure_is_blocked_pending_not_silent_success():
    eng, _store, state = _engine(card_fail={"card_1"})
    _mandates, _so, cards, _ap, _pay = state

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )

    # The card target is blocked_pending — NOT killed, NOT silently dropped.
    card_targets = _by_kind(rev, PropagationKind.CARD)
    assert [t.kill_status for t in card_targets] == [KillStatus.BLOCKED_PENDING]
    assert "blocked at execution" in card_targets[0].detail
    # The mock did not flip the card to frozen (the kill was not confirmed).
    assert cards["card_1"]["state"] == "active"

    # Overall outcome reflects the partial propagation — never "propagated".
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM
    assert rev.has_unconfirmed() is True


async def test_partial_propagation_still_revokes_mandate_so_orchestrator_denies():
    # Even when a downstream rail fails, the mandate (authority root) is revoked,
    # so the orchestrator's mandate lookup returns no active mandate -> deny.
    eng, _store, state = _engine(card_fail={"card_1"}, inflight_fail={"pay_1"})
    mandates, _so, _cd, _ap, _pay = state

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM
    # Authority root is dead.
    assert mandates[MANDATE]["status"] == "revoked"

    # Hydrate the (now revoked) mandate row the way the orchestrator's lookup
    # does, and confirm it fails closed — get_active_mandate would never even
    # return this row (status != 'active'), but the hydrated object also denies.
    revoked_row = {
        "id": MANDATE,
        "principal_id": "usr_1",
        "issuer_id": "usr_1",
        "agent_id": AGENT,
        "status": "revoked",
        "currency": "USDC",
    }
    mandate = SpendingMandateLookup._row_to_mandate(revoked_row)
    assert mandate.status == MandateStatus.REVOKED
    assert mandate.is_active is False
    # A payment check on a revoked mandate fails closed.
    from decimal import Decimal

    check = mandate.check_payment(amount=Decimal("1"))
    assert check.approved is False
    assert check.error_code == "MANDATE_NOT_ACTIVE"


async def test_raising_rail_becomes_failed_target_and_does_not_abort_kill():
    class ExplodingCardFreezer:
        kind = PropagationKind.CARD

        async def freeze_for_target(self, *, target_kind, target_ref, requested_by):
            raise RuntimeError("card provider 500")

    mandates, spend_objects, _cards, approvals, payments = _fixtures()
    store = InMemoryRevocationStore()
    eng = RevocationEngine(
        store=store,
        mandate_revoker=InMemoryMandateRevoker(mandates),
        spend_object_revoker=InMemorySpendObjectRevoker(spend_objects),
        card_freezer=ExplodingCardFreezer(),
        approval_revoker=InMemoryApprovalRevoker(approvals),
        in_flight_blocker=InMemoryInFlightBlocker(payments),
        signing_secret=SECRET,
    )

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )

    # The card rail raised -> one synthetic failed target; the kill continued.
    card_targets = _by_kind(rev, PropagationKind.CARD)
    assert [t.kill_status for t in card_targets] == [KillStatus.FAILED]
    assert "raised" in card_targets[0].detail
    # The other rails still ran.
    assert mandates[MANDATE]["status"] == "revoked"
    assert payments["pay_1"]["status"] == "blocked"
    # Outcome is honest about the failure.
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM


# ── signed proof ───────────────────────────────────────────────────────


async def test_proof_verifies_independently():
    eng, _store, _state = _engine()
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    proof = rev.proof
    assert proof is not None
    assert proof.verify(SECRET) is True
    # Independent verification from a round-tripped dict (no live system).
    from sardis.core.revocation import RevocationProof

    rehydrated = RevocationProof.from_dict(proof.to_dict())
    assert rehydrated.verify(SECRET) is True


async def test_proof_binds_target_list_tamper_breaks_verification():
    eng, _store, _state = _engine()
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    proof = rev.proof
    assert proof.verify(SECRET) is True

    # Downgrade a recorded "killed" to "blocked_pending" without re-signing
    # (the kind of tamper that would let a caller claim a thing is dead when the
    # proof says otherwise): the decision_hash no longer matches the bound
    # target list -> verify fails.
    from sardis.core.revocation import RevocationProof

    tampered = RevocationProof.from_dict(proof.to_dict())
    killed_idx = next(
        i for i, t in enumerate(tampered.targets) if t["kill_status"] == "killed"
    )
    tampered.targets[killed_idx]["kill_status"] = "blocked_pending"
    assert tampered.verify(SECRET) is False

    # Wrong key also fails.
    assert proof.verify("wrong-key") is False


async def test_proof_outcome_matches_partial_state():
    eng, _store, _state = _engine(card_fail={"card_1"})
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    assert rev.proof.outcome == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM.value
    assert rev.proof.verify(SECRET) is True


# ── idempotency ────────────────────────────────────────────────────────


async def test_re_revoke_is_idempotent_same_proof():
    eng, _store, _state = _engine()
    first = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    second = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_2"
    )
    # Same revocation id and same signed proof — no re-propagation.
    assert second.id == first.id
    assert second.proof.signature == first.proof.signature
    assert second.requested_by == "usr_1"  # original requester preserved


async def test_idempotent_revoke_does_not_double_record_targets():
    eng, _store, _state = _engine()
    first = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    n = len(first.targets)
    second = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    assert len(second.targets) == n  # not doubled


# ── mandate target reaches cards via the agent ─────────────────────────


async def test_mandate_target_freezes_cards_via_agent_hint():
    eng, _store, state = _engine()
    _mandates, _so, cards, _ap, _pay = state
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.MANDATE,
        target_ref=MANDATE,
        requested_by="usr_1",
        agent_id=AGENT,  # mandate carries the agent; cards reached by it
    )
    assert cards["card_1"]["state"] == "frozen"
    assert rev.status == RevocationStatus.PROPAGATED


async def test_revoke_with_no_optional_rails_only_kills_mandate():
    mandates = {MANDATE: {"status": "active", "agent_id": AGENT, "principal_id": "usr_1"}}
    eng = RevocationEngine(
        store=InMemoryRevocationStore(),
        mandate_revoker=InMemoryMandateRevoker(mandates),
        signing_secret=SECRET,
    )
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    kinds = {t.kind for t in rev.targets}
    assert kinds == {PropagationKind.MANDATE}
    assert rev.status == RevocationStatus.PROPAGATED
    assert rev.proof.verify(SECRET) is True


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
