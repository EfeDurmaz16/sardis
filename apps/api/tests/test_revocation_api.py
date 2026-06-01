"""End-to-end test of the Propagating-Revocation (kill-switch) API.

Exercises the routes the product/UI consumes against the REAL
:class:`~sardis.core.revocation_engine.RevocationEngine` (in-memory store +
real per-rail adapters over fakes — no live keys, no chain, no DB):

* ``POST /api/v2/revocations`` propagates across every rail and returns the
  propagation SUMMARY (mandates revoked, cards frozen, spend objects killed,
  approvals + in-flight blocked) plus the signed RevocationProof;
* the headline guarantee: after the revoke, the next payment for that mandate is
  DENIED at execution (the mandate is revoked → MANDATE_NOT_ACTIVE);
* ``POST /api/v2/revocations/verify`` independently verifies the returned proof
  from its own fields, and rejects a tampered target list;
* ``GET`` list + by-id are org-scoped and return the proof;
* a re-revoke is idempotent (same id + proof, ``idempotent_replay=true``);
* a blocked-pending card freeze is reported honestly (NOT fully propagated) and
  the authority is STILL denied at execution;
* the engine being absent fails the surface closed (503).
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis.core.approval_gate import ApprovalGate
from sardis.core.approval_request import build_approval_request
from sardis.core.approval_request_repository import InMemoryApprovalRequestStore
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import (
    ApprovalGateRevoker,
    CallbackInFlightBlocker,
    PostgresMandateRevoker,
    PostgresSpendObjectRevoker,
    ProviderCardFreezer,
)
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import MandateStatus
from sardis.core.spending_mandate_lookup import SpendingMandateLookup

from server.authz import Principal, require_principal
from server.routes.authority import revocations as rev_routes

SECRET = "test-revocation-api-secret"
AGENT = "agent_kill_me"
MANDATE = "mandate_abc"


# ── A minimal fake Database (execute/fetch) mirroring the wiring test ──────


class FakeRow(dict):
    pass


class FakeDB:
    def __init__(self, mandates: dict, spend_objects: dict) -> None:
        self.mandates = mandates
        self.spend_objects = spend_objects
        self.transitions: list[dict] = []

    async def fetch(self, query: str, *args):
        q = " ".join(query.split())
        if "FROM spending_mandates" in q:
            if "agent_id = $1" in q:
                key, val = "agent_id", args[0]
            elif "principal_id = $1" in q:
                key, val = "principal_id", args[0]
            else:
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


class FakeProviderResult:
    def __init__(self, ok: bool, error: str | None = None) -> None:
        self.ok = ok
        self.provider = "fake"
        self.error = error


class FakeCardPort:
    def __init__(self, cards: dict, *, fail_refs=None) -> None:
        self.cards = cards
        self.fail = set(fail_refs or ())

    async def set_state(self, card_ref: str, *, state: str):
        if card_ref in self.fail:
            return FakeProviderResult(ok=False, error="freeze rejected")
        self.cards[card_ref]["state"] = state
        return FakeProviderResult(ok=True)


def _card_enumerator(cards: dict):
    async def enumerate_cards(*, target_kind: str, target_ref: str):
        return [
            ref for ref, c in cards.items()
            if c.get("agent_id") == target_ref and c.get("state") != "closed"
        ]
    return enumerate_cards


# ── Engine + app scaffold ──────────────────────────────────────────────


def _engine(*, card_fail=None):
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
    card_port = FakeCardPort(cards, fail_refs=card_fail)
    gate = ApprovalGate(store=InMemoryApprovalRequestStore(), signing_secret="appr-secret")
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
    return eng, db, cards, gate, payments


def _client(engine, *, org: str = "org_a") -> TestClient:
    app = FastAPI()
    app.state.revocation_engine = engine
    app.include_router(rev_routes.router, prefix="/api/v2/revocations")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key", organization_id=org, scopes=["*"]
    )
    return TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_signing_key(monkeypatch):
    # The /verify route resolves the HMAC key from the env (fail-closed in prod).
    # The proof here was signed with SECRET via the engine's signing_secret; for
    # the env-resolved verify path we point the env key at the same secret.
    monkeypatch.setenv("SARDIS_REVOCATION_HMAC_KEY", SECRET)
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "test")


async def _seed_pending_approval(gate: ApprovalGate) -> str:
    req = build_approval_request(
        agent_id=AGENT, mandate_id="pmt_1", spending_mandate_id=MANDATE,
        amount=Decimal("100"), currency="USDC", counterparty="acme", reason="buy",
    )
    await gate._store.create(req)
    return req.id


# ── The end-to-end flow: revoke -> summary + proof -> denied -> verify ────


@pytest.mark.asyncio
async def test_revoke_returns_summary_and_proof_then_payment_denied_then_verify():
    engine, db, cards, gate, payments = _engine()
    apreq_id = await _seed_pending_approval(gate)
    client = _client(engine)

    # 1) ONE revoke across every rail.
    resp = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT, "reason": "compromised"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # The propagation SUMMARY the UI consumes: per-rail kill counts.
    summary = body["summary"]
    assert summary["outcome"] == "propagated"
    assert summary["fully_propagated"] is True
    assert summary["mandates_revoked"] == 1
    assert summary["cards_frozen"] == 1          # card_1 (card_other untouched)
    assert summary["spend_objects_killed"] == 2  # po_1 killed + po_2 already_dead
    assert summary["approvals_blocked"] == 1     # the seeded pending approval
    assert summary["in_flight_blocked"] == 1     # pay_1
    assert summary["blocked_pending"] == 0
    assert body["idempotent_replay"] is False

    # The rails were actually swept.
    assert cards["card_1"]["state"] == "frozen"
    assert cards["card_other"]["state"] == "active"
    assert payments["pay_1"]["status"] == "blocked"
    assert (await gate.get(apreq_id)).status.value == "denied"

    # The signed proof is on the response.
    proof = body["proof"]
    assert proof is not None
    assert proof["outcome"] == "propagated"
    assert proof["signature"] and proof["decision_hash"]

    # 2) The headline guarantee: the next payment for that mandate is DENIED at
    #    execution (the mandate is revoked → orchestrator denies).
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

    # 3) Independently verify the proof from its own fields.
    verify = client.post("/api/v2/revocations/verify", json=proof)
    assert verify.status_code == 200, verify.text
    v = verify.json()
    assert v["valid"] is True
    assert v["hash_matches"] is True
    assert v["signature_matches"] is True
    assert v["revocation_id"] == proof["revocation_id"]


def test_verify_rejects_tampered_target_list():
    engine, _db, _cards, _gate, _pay = _engine()
    client = _client(engine)
    proof = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    ).json()["proof"]

    # Flip a recorded kill_status: a card that was blocked is now claimed killed.
    tampered = dict(proof)
    tampered["targets"] = [dict(t) for t in proof["targets"]]
    for t in tampered["targets"]:
        if t["kind"] == "card":
            t["kill_status"] = "killed"
            t["detail"] = "forged: claim frozen"

    verify = client.post("/api/v2/revocations/verify", json=tampered).json()
    assert verify["valid"] is False
    assert verify["hash_matches"] is False
    assert "tampered" in verify["detail"]


def test_verify_rejects_forged_signature():
    engine, _db, _cards, _gate, _pay = _engine()
    client = _client(engine)
    proof = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    ).json()["proof"]

    forged = dict(proof)
    forged["signature"] = "0" * 64  # right shape, wrong value

    verify = client.post("/api/v2/revocations/verify", json=forged).json()
    assert verify["valid"] is False
    assert verify["hash_matches"] is True       # body untouched → hash still ok
    assert verify["signature_matches"] is False
    assert "signature mismatch" in verify["detail"]


def test_re_revoke_is_idempotent():
    engine, _db, _cards, _gate, _pay = _engine()
    client = _client(engine)
    first = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    ).json()
    assert first["idempotent_replay"] is False

    second = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    ).json()
    assert second["idempotent_replay"] is True
    assert second["revocation"]["id"] == first["revocation"]["id"]
    assert second["proof"]["signature"] == first["proof"]["signature"]


def test_blocked_pending_card_freeze_reported_honestly():
    # The card provider rejects the freeze: the kill is blocked_pending, the
    # overall outcome is NOT propagated, but the mandate is still revoked.
    engine, db, cards, _gate, _pay = _engine(card_fail={"card_1"})
    client = _client(engine)
    body = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    ).json()

    summary = body["summary"]
    assert summary["outcome"] == "blocked_pending_downstream"
    assert summary["fully_propagated"] is False
    assert summary["cards_frozen"] == 0      # NOT claimed frozen
    assert summary["blocked_pending"] >= 1
    assert summary["mandates_revoked"] == 1  # authority root still dead
    assert cards["card_1"]["state"] == "active"  # provider did NOT freeze it
    assert db.mandates[MANDATE]["status"] == "revoked"

    # The proof still verifies — it honestly reports the mixed state.
    verify = client.post("/api/v2/revocations/verify", json=body["proof"]).json()
    assert verify["valid"] is True
    assert verify["outcome"] == "blocked_pending_downstream"


def test_list_and_get_are_org_scoped():
    engine, _db, _cards, _gate, _pay = _engine()
    a = _client(engine, org="org_a")
    created = a.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    ).json()
    rev_id = created["revocation"]["id"]

    # Owner can list + get.
    listed = a.get("/api/v2/revocations").json()
    assert [r["id"] for r in listed] == [rev_id]
    assert a.get(f"/api/v2/revocations/{rev_id}").status_code == 200

    # Another org sees nothing and cannot fetch it (404, not 403).
    b = _client(engine, org="org_b")
    assert b.get("/api/v2/revocations").json() == []
    assert b.get(f"/api/v2/revocations/{rev_id}").status_code == 404


def test_engine_absent_fails_closed():
    app = FastAPI()
    app.state.revocation_engine = None
    app.include_router(rev_routes.router, prefix="/api/v2/revocations")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key", organization_id="org_a", scopes=["*"]
    )
    client = TestClient(app)
    resp = client.post(
        "/api/v2/revocations",
        json={"target_kind": "agent", "target_ref": AGENT},
    )
    assert resp.status_code == 503
