"""Wiring + reconciliation tests for the Propagating-Revocation primitive.

The base ``test_revocation.py`` pins the engine contract against the in-memory
mocks.  This file pins the REAL rail legs and the reconciliation sweep:

* the Postgres mandate / spend-object revokers go through the canonical write
  path (UPDATE spending_mandates / payment_objects + a mandate transition audit
  row), report ``already_dead`` for terminal rows, and survive a lost UPDATE
  race;
* the ProviderCardFreezer freezes via a CardPort (``set_state(state="frozen")``)
  and records a not-ok / raising freeze as ``blocked_pending`` — never silent
  success;
* the ApprovalGateRevoker denies the agent's pending approvals through the
  signed gate cascade (the RevokeDialog promise);
* the CallbackInFlightBlocker blocks in-flight payments and reports an
  unconfirmable block ``blocked_pending``;
* the headline guarantee: a revoked agent whose card-freeze came back
  ``blocked_pending`` is STILL denied at execution (the mandate is revoked) and
  the proof lists the mixed statuses honestly;
* the reconciliation sweep retries the blocked_pending card-freeze and, once the
  provider recovers, upgrades it to ``killed`` and flips the overall outcome to
  ``propagated`` — re-signing the proof.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request import build_approval_request
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore
from sardis.core.revocation import (
    KillStatus,
    PropagationKind,
    RevocationStatus,
    RevocationTargetKind,
)
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import (
    ApprovalGateRevoker,
    CallbackInFlightBlocker,
    InMemoryCardFreezer,
    PostgresMandateRevoker,
    PostgresSpendObjectRevoker,
    ProviderCardFreezer,
)
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import MandateStatus
from sardis.core.spending_mandate_lookup import SpendingMandateLookup

SECRET = "test-revocation-secret"
AGENT = "agent_kill_me"
MANDATE = "mandate_abc"


# ── a minimal fake of the Database facade (execute/fetch) ──────────────


class FakeRow(dict):
    """asyncpg-Record-like: subscriptable by column name."""


class FakeDB:
    """In-memory stand-in for ``sardis.core.database.Database``.

    Backs two tables the real adapters write through — ``spending_mandates`` and
    ``payment_objects`` — with just enough SQL-shape awareness to exercise the
    conditional UPDATEs and the ANY($1) enumerate.
    """

    def __init__(self, mandates: dict, spend_objects: dict) -> None:
        self.mandates = mandates  # id -> {status, agent_id, principal_id}
        self.spend_objects = spend_objects  # object_id -> {mandate_id, status}
        self.transitions: list[dict] = []

    async def fetch(self, query: str, *args):
        q = " ".join(query.split())
        if "FROM spending_mandates" in q:
            if "agent_id = $1" in q:
                key, val = "agent_id", args[0]
            elif "principal_id = $1" in q:
                key, val = "principal_id", args[0]
            else:  # id = $1
                key, val = "id", args[0]
            out = []
            for mid, m in self.mandates.items():
                hit = mid == val if key == "id" else m.get(key) == val
                if hit:
                    out.append(FakeRow(id=mid, status=m.get("status")))
            return out
        if "FROM payment_objects" in q:
            wanted = set(args[0])
            return [
                FakeRow(object_id=oid, status=o.get("status"))
                for oid, o in self.spend_objects.items()
                if o.get("mandate_id") in wanted
            ]
        raise AssertionError(f"unexpected fetch: {q}")

    async def execute(self, query: str, *args):
        q = " ".join(query.split())
        if "UPDATE spending_mandates" in q:
            mid = args[0]
            m = self.mandates.get(mid)
            if m and m.get("status") in ("active", "suspended", "draft"):
                m["status"] = "revoked"
                m["revoked_by"] = args[1]
                return "UPDATE 1"
            return "UPDATE 0"
        if "INSERT INTO mandate_state_transitions" in q:
            self.transitions.append({"mandate_id": args[1]})
            return "INSERT 0 1"
        if "UPDATE payment_objects" in q:
            oid = args[0]
            o = self.spend_objects.get(oid)
            terminal = ("settled", "fulfilled", "revoked", "expired", "failed", "refunded")
            if o and o.get("status") not in terminal:
                o["status"] = "revoked"
                return "UPDATE 1"
            return "UPDATE 0"
        raise AssertionError(f"unexpected execute: {q}")


# ── a fake CardPort (the provider-layer set_state surface) ─────────────


class FakeProviderResult:
    def __init__(self, ok: bool, provider: str = "fake", error: str | None = None) -> None:
        self.ok = ok
        self.provider = provider
        self.error = error


class FakeCardPort:
    """Duck-typed CardPort: ``set_state(card_ref, state=...)`` -> ProviderResult.

    ``fail_refs`` returns ok=False (provider rejected the freeze); ``raise_refs``
    raises.  Both must surface as blocked_pending, never silent success.
    """

    def __init__(self, cards: dict, *, fail_refs=None, raise_refs=None) -> None:
        self.cards = cards  # card_ref -> {"state"}
        self.fail = set(fail_refs or ())
        self.raise_ = set(raise_refs or ())

    async def set_state(self, card_ref: str, *, state: str):
        if card_ref in self.raise_:
            raise RuntimeError("card provider 500")
        if card_ref in self.fail:
            return FakeProviderResult(ok=False, error="freeze rejected")
        self.cards[card_ref]["state"] = state
        return FakeProviderResult(ok=True, provider="crossmint")


def _card_enumerator(cards: dict):
    async def enumerate_cards(*, target_kind: str, target_ref: str):
        return [
            ref for ref, c in cards.items()
            if c.get("agent_id") == target_ref and c.get("state") != "closed"
        ]
    return enumerate_cards


# ── real-adapter fixtures ──────────────────────────────────────────────


def _real_engine(*, card_fail=None, card_raise=None):
    mandates = {MANDATE: {"status": "active", "agent_id": AGENT, "principal_id": "usr_1"}}
    spend_objects = {
        "po_1": {"mandate_id": MANDATE, "status": "minted"},
        "po_2": {"mandate_id": MANDATE, "status": "settled"},  # terminal
    }
    cards = {
        "card_1": {"agent_id": AGENT, "state": "active"},
        "card_other": {"agent_id": "someone_else", "state": "active"},
    }
    db = FakeDB(mandates, spend_objects)
    card_port = FakeCardPort(cards, fail_refs=card_fail, raise_refs=card_raise)

    # approvals via a real ApprovalGate + in-memory store
    approval_store = InMemoryApprovalRequestStore()
    gate = ApprovalGate(store=approval_store, signing_secret="appr-secret")

    # in-flight via a callback blocker over a tiny in-memory ledger
    payments = {"pay_1": {"agent_id": AGENT, "status": "pending"}}

    async def enumerate_in_flight(*, agent_id, mandate_ids):
        return [
            (pid, p["status"]) for pid, p in payments.items()
            if p.get("agent_id") == agent_id
        ]

    async def block_one(ref):
        payments[ref]["status"] = "blocked"
        return True

    eng = RevocationEngine(
        store=InMemoryRevocationStore(),
        mandate_revoker=PostgresMandateRevoker(db),
        spend_object_revoker=PostgresSpendObjectRevoker(db),
        card_freezer=ProviderCardFreezer(card_port, _card_enumerator(cards)),
        approval_revoker=ApprovalGateRevoker(gate),
        in_flight_blocker=CallbackInFlightBlocker(enumerate_in_flight, block_one),
        signing_secret=SECRET,
    )
    return eng, db, cards, gate, payments, card_port


async def _seed_pending_approval(gate: ApprovalGate) -> str:
    req = build_approval_request(
        agent_id=AGENT, mandate_id="pmt_1", spending_mandate_id=MANDATE,
        amount=Decimal("100"), currency="USDC", counterparty="acme", reason="buy",
    )
    await gate._store.create(req)
    return req.id


# ── real legs all propagate through the canonical surfaces ─────────────


async def test_real_legs_propagate_through_canonical_surfaces():
    eng, db, cards, gate, payments, _cp = _real_engine()
    apreq_id = await _seed_pending_approval(gate)

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT,
        requested_by="usr_1", reason="compromised",
    )

    assert rev.status == RevocationStatus.PROPAGATED

    # Mandate flipped in the (fake) DB + an audit transition row written.
    assert db.mandates[MANDATE]["status"] == "revoked"
    assert any(t["mandate_id"] == MANDATE for t in db.transitions)

    # Spend objects: po_1 revoked, po_2 already terminal.
    so = {t.ref: t.kill_status for t in rev.targets if t.kind == PropagationKind.SPEND_OBJECT}
    assert so["po_1"] == KillStatus.KILLED
    assert so["po_2"] == KillStatus.ALREADY_DEAD
    assert db.spend_objects["po_1"]["status"] == "revoked"

    # Card frozen via the CardPort; other agent's card untouched.
    cd = {t.ref: t.kill_status for t in rev.targets if t.kind == PropagationKind.CARD}
    assert cd == {"card_1": KillStatus.KILLED}
    assert cards["card_1"]["state"] == "frozen"
    assert cards["card_other"]["state"] == "active"

    # Pending approval denied through the signed gate cascade.
    ap = [t for t in rev.targets if t.kind == PropagationKind.APPROVAL]
    assert [t.ref for t in ap] == [apreq_id]
    assert ap[0].kill_status == KillStatus.KILLED
    decided = await gate.get(apreq_id)
    assert decided.status.value == "denied"
    assert decided.evidence is not None  # signed decision evidence recorded

    # In-flight payment blocked.
    inf = [t for t in rev.targets if t.kind == PropagationKind.IN_FLIGHT]
    assert [t.ref for t in inf] == ["pay_1"]
    assert inf[0].kill_status == KillStatus.KILLED
    assert payments["pay_1"]["status"] == "blocked"

    assert rev.proof.verify(SECRET) is True


async def test_postgres_mandate_revoke_idempotent_on_lost_race():
    # If the mandate is already revoked, the real revoker reports already_dead,
    # not a spurious second kill.
    eng, db, _cards, _gate, _pay, _cp = _real_engine()
    db.mandates[MANDATE]["status"] = "revoked"  # already dead before we start

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    mt = [t for t in rev.targets if t.kind == PropagationKind.MANDATE]
    assert mt[0].kill_status == KillStatus.ALREADY_DEAD
    # No transition audit row for a no-op kill.
    assert db.transitions == []


# ── fail-closed: provider freeze failure is blocked_pending ────────────


async def test_provider_card_freeze_not_ok_is_blocked_pending():
    eng, _db, cards, _gate, _pay, _cp = _real_engine(card_fail={"card_1"})

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    card_targets = [t for t in rev.targets if t.kind == PropagationKind.CARD]
    assert [t.kill_status for t in card_targets] == [KillStatus.BLOCKED_PENDING]
    assert "blocked at execution" in card_targets[0].detail
    assert cards["card_1"]["state"] == "active"  # NOT actually frozen
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM


async def test_provider_card_freeze_raise_is_blocked_pending_not_failed_silent():
    eng, _db, cards, _gate, _pay, _cp = _real_engine(card_raise={"card_1"})
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    card_targets = [t for t in rev.targets if t.kind == PropagationKind.CARD]
    # The ProviderCardFreezer catches the raise per-card and records
    # blocked_pending (the card is still alive, so we must not claim it dead).
    assert [t.kill_status for t in card_targets] == [KillStatus.BLOCKED_PENDING]
    assert cards["card_1"]["state"] == "active"
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM


# ── headline guarantee: revoked agent denied even with blocked card ────


async def test_revoked_agent_denied_at_execution_despite_blocked_card_freeze():
    eng, db, _cards, _gate, _pay, _cp = _real_engine(card_fail={"card_1"})

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    # The proof tells the truth: mixed statuses, overall blocked_pending.
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM
    statuses = {t.kind: t.kill_status for t in rev.targets}
    assert statuses[PropagationKind.MANDATE] == KillStatus.KILLED
    assert statuses[PropagationKind.CARD] == KillStatus.BLOCKED_PENDING

    # The authority root is dead in the DB → the orchestrator's lookup
    # (status='active') would never return it, AND a hydrated revoked row denies.
    assert db.mandates[MANDATE]["status"] == "revoked"
    revoked_row = {
        "id": MANDATE, "principal_id": "usr_1", "issuer_id": "usr_1",
        "agent_id": AGENT, "status": "revoked", "currency": "USDC",
    }
    mandate = SpendingMandateLookup._row_to_mandate(revoked_row)
    assert mandate.status == MandateStatus.REVOKED
    check = mandate.check_payment(amount=Decimal("1"))
    assert check.approved is False
    assert check.error_code == "MANDATE_NOT_ACTIVE"


# ── reconciliation sweep resolves a blocked_pending ────────────────────


async def test_sweep_resolves_blocked_pending_card_freeze():
    card_fail = {"card_1"}
    eng, _db, cards, _gate, _pay, card_port = _real_engine(card_fail=card_fail)

    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    assert rev.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM
    sig_before = rev.proof.signature

    # Provider recovers: clear the freeze failure on its side.
    card_port.fail.clear()

    swept = await eng.reconcile_blocked()
    assert len(swept) == 1
    reconciled = swept[0]
    assert reconciled.id == rev.id

    # The card is now confirmed frozen and the target upgraded killed.
    card_targets = [t for t in reconciled.targets if t.kind == PropagationKind.CARD]
    assert [t.kill_status for t in card_targets] == [KillStatus.KILLED]
    assert "reconciled" in card_targets[0].detail
    assert cards["card_1"]["state"] == "frozen"

    # Outcome flips to fully propagated and the proof is re-signed + valid.
    assert reconciled.status == RevocationStatus.PROPAGATED
    assert reconciled.has_unconfirmed() is False
    assert reconciled.proof.verify(SECRET) is True
    assert reconciled.proof.signature != sig_before  # re-signed after upgrade
    assert reconciled.proof.outcome == RevocationStatus.PROPAGATED.value


async def test_sweep_keeps_blocked_when_provider_still_failing():
    eng, _db, cards, _gate, _pay, _card_port = _real_engine(card_fail={"card_1"})
    await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    # Provider still down — sweep must not invent a confirmation.
    swept = await eng.reconcile_blocked()
    reconciled = swept[0]
    card_targets = [t for t in reconciled.targets if t.kind == PropagationKind.CARD]
    assert [t.kill_status for t in card_targets] == [KillStatus.BLOCKED_PENDING]
    assert reconciled.status == RevocationStatus.BLOCKED_PENDING_DOWNSTREAM
    assert cards["card_1"]["state"] == "active"
    # Still a valid, honest proof.
    assert reconciled.proof.verify(SECRET) is True


async def test_reconcile_noop_on_already_propagated():
    eng, _db, _cards, _gate, _pay, _cp = _real_engine()
    rev = await eng.revoke(
        target_kind=RevocationTargetKind.AGENT, target_ref=AGENT, requested_by="usr_1"
    )
    assert rev.status == RevocationStatus.PROPAGATED
    same = await eng.reconcile(rev.id)
    # Nothing to do — returned unchanged (same signature).
    assert same.proof.signature == rev.proof.signature


async def test_reconcile_missing_revocation_returns_none():
    eng, _db, _cards, _gate, _pay, _cp = _real_engine()
    assert await eng.reconcile("rev_does_not_exist") is None


# ── in-flight unconfirmable block is blocked_pending ───────────────────


async def test_callback_in_flight_unconfirmed_block_is_blocked_pending():
    payments = {"pay_x": {"agent_id": AGENT, "status": "pending"}}

    async def enumerate_in_flight(*, agent_id, mandate_ids):
        return [(pid, p["status"]) for pid, p in payments.items()]

    async def block_one(ref):
        return False  # broadcast already in mempool — cannot confirm

    blocker = CallbackInFlightBlocker(enumerate_in_flight, block_one)
    out = await blocker.block_for_target(
        agent_id=AGENT, mandate_ids=[MANDATE], requested_by="usr_1"
    )
    assert len(out) == 1
    assert out[0].kill_status == KillStatus.BLOCKED_PENDING
    assert "unconfirmed" in out[0].detail


# ── ApprovalGateRevoker only kills matching pending requests ───────────


async def test_approval_gate_revoker_only_denies_matching_pending():
    store = InMemoryApprovalRequestStore()
    gate = ApprovalGate(store=store, signing_secret="appr-secret")
    mine = build_approval_request(
        agent_id=AGENT, mandate_id="p1", spending_mandate_id=MANDATE,
        amount=Decimal("1"), currency="USDC", counterparty="x", reason="r",
    )
    other = build_approval_request(
        agent_id="other_agent", mandate_id="p2", spending_mandate_id="other_mandate",
        amount=Decimal("1"), currency="USDC", counterparty="y", reason="r",
    )
    await store.create(mine)
    await store.create(other)

    revoker = ApprovalGateRevoker(gate)
    out = await revoker.deny_pending_for_target(
        agent_id=AGENT, mandate_ids=[MANDATE], requested_by="usr_1"
    )
    assert [o.ref for o in out] == [mine.id]
    assert out[0].kill_status == KillStatus.KILLED
    assert (await gate.get(mine.id)).status.value == "denied"
    assert (await gate.get(other.id)).status.value == "pending"  # untouched


# ── in-memory + provider freezers agree on the contract ────────────────


async def test_in_memory_and_provider_freezers_agree_on_blocked_pending():
    # Parity check: both freezer impls report blocked_pending on a failed kill.
    mem = InMemoryCardFreezer(
        {"card_1": {"agent_id": AGENT, "state": "active"}}, fail_refs={"card_1"}
    )
    mem_out = await mem.freeze_for_target(
        target_kind="agent", target_ref=AGENT, requested_by="usr_1"
    )
    assert mem_out[0].kill_status == KillStatus.BLOCKED_PENDING

    cards = {"card_1": {"agent_id": AGENT, "state": "active"}}
    prov = ProviderCardFreezer(
        FakeCardPort(cards, fail_refs={"card_1"}), _card_enumerator(cards)
    )
    prov_out = await prov.freeze_for_target(
        target_kind="agent", target_ref=AGENT, requested_by="usr_1"
    )
    assert prov_out[0].kill_status == KillStatus.BLOCKED_PENDING


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
