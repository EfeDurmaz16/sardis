"""End-to-end test of the escrow/recourse API — money routes through RecourseHold.

Exercises the routes the product needs against the REAL
:class:`~sardis.core.recourse_engine.RecourseEngine` (InMemory store +
NoopRecourseExecutor — no live keys, no chain, no DB):

* open a windowed escrow hold -> a durable ``held`` RecourseHold appears;
* refund WITHIN the window -> funds return to the payer, hold terminal ``refunded``;
* a second refund / a refund-over-held is rejected fail-closed (409);
* confirm-delivery RELEASES to the recipient (and double-release is 409);
* window EXPIRY settles via the engine sweep -> ``released``;
* org-scoping: a hold opened by org A is invisible (404) to org B.

The actor is the authenticated principal, and every hold is stamped with the
caller's organization so the surface is org-scoped and fail-closed.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis.core.recourse_engine import RecourseEngine
from sardis.core.recourse_executor import NoopRecourseExecutor
from sardis.core.recourse_hold_repository import InMemoryRecourseHoldStore

from server.authz import Principal, require_principal
from server.routes.commerce import escrow_disputes as ed

# ── Scaffold ────────────────────────────────────────────────────────────


def _engine() -> RecourseEngine:
    return RecourseEngine(
        store=InMemoryRecourseHoldStore(),
        executor=NoopRecourseExecutor(),
        signing_secret="test-recourse",
    )


def _client(engine: RecourseEngine, *, org: str = "org_a") -> TestClient:
    app = FastAPI()
    app.state.recourse_engine = engine
    app.include_router(ed.router, prefix="/api/v2")

    def _fake_principal() -> Principal:
        return Principal(kind="api_key", organization_id=org, scopes=["*"])

    app.dependency_overrides[require_principal] = _fake_principal
    return TestClient(app)


def _open_escrow(client: TestClient, *, amount: str = "100", hours: int = 72) -> dict:
    resp = client.post(
        "/api/v2/escrow",
        json={
            "payment_object_id": f"po_{amount}_{hours}",
            "merchant_id": "merch_1",
            "amount": amount,
            "currency": "USDC",
            "timelock_hours": hours,
            "chain": "base",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Tests ───────────────────────────────────────────────────────────────


def test_open_then_refund_within_window_returns_funds():
    engine = _engine()
    client = _client(engine)

    created = _open_escrow(client, amount="100")
    hold_id = created["hold_id"]
    assert created["status"] == "held"
    assert created["amount"] == "100"

    # It shows up in the org's open list and by id.
    listed = client.get("/api/v2/escrow").json()
    assert [h["hold_id"] for h in listed] == [hold_id]
    assert client.get(f"/api/v2/escrow/{hold_id}").json()["status"] == "held"

    # Refund WITHIN the window -> funds return to payer, hold terminal.
    resp = client.post(f"/api/v2/escrow/{hold_id}/refund", json={"reason": "buyer changed mind"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "refunded"

    # No longer open; a second refund is rejected fail-closed.
    assert client.get("/api/v2/escrow").json() == []
    again = client.post(f"/api/v2/escrow/{hold_id}/refund", json={})
    assert again.status_code == 409


def test_partial_refund_over_held_is_rejected():
    engine = _engine()
    client = _client(engine)
    hold_id = _open_escrow(client, amount="10")["hold_id"]

    # 10 USDC held = 10_000_000 minor; asking 999 USDC must fail-closed (409).
    resp = client.post(f"/api/v2/escrow/{hold_id}/refund", json={"amount": "999"})
    assert resp.status_code == 409
    # Hold untouched — still refundable.
    assert client.get(f"/api/v2/escrow/{hold_id}").json()["status"] == "held"


def test_confirm_delivery_releases_and_double_release_is_409():
    engine = _engine()
    client = _client(engine)
    hold_id = _open_escrow(client)["hold_id"]

    resp = client.post(f"/api/v2/escrow/{hold_id}/confirm-delivery", json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "released"

    # Releasing again (or refunding a released hold) is fail-closed.
    assert client.post(f"/api/v2/escrow/{hold_id}/confirm-delivery", json={}).status_code == 409
    assert client.post(f"/api/v2/escrow/{hold_id}/refund", json={}).status_code == 409


@pytest.mark.asyncio
async def test_window_expiry_settles_via_sweep():
    engine = _engine()
    client = _client(engine)
    hold_id = _open_escrow(client, hours=1)["hold_id"]

    # No money settled while the window is open.
    assert client.get(f"/api/v2/escrow/{hold_id}").json()["status"] == "held"

    # Sweep AS-OF after the window -> the engine releases to the recipient.
    released = await engine.sweep_expired(as_of=datetime.now(UTC) + timedelta(hours=2))
    assert released == [hold_id]
    assert client.get(f"/api/v2/escrow/{hold_id}").json()["status"] == "released"


def test_org_scoping_hides_cross_org_holds():
    engine = _engine()
    a = _client(engine, org="org_a")
    hold_id = _open_escrow(a)["hold_id"]

    b = _client(engine, org="org_b")
    # Org B cannot see, get, or act on org A's hold.
    assert b.get("/api/v2/escrow").json() == []
    assert b.get(f"/api/v2/escrow/{hold_id}").status_code == 404
    assert b.post(f"/api/v2/escrow/{hold_id}/refund", json={}).status_code == 404
    assert b.post(f"/api/v2/escrow/{hold_id}/confirm-delivery", json={}).status_code == 404


def test_recourse_engine_unavailable_fails_closed():
    app = FastAPI()
    app.state.recourse_engine = None
    app.include_router(ed.router, prefix="/api/v2")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key", organization_id="org_a", scopes=["*"]
    )
    client = TestClient(app)
    resp = client.post(
        "/api/v2/escrow",
        json={"payment_object_id": "po_x", "merchant_id": "m", "amount": "5"},
    )
    assert resp.status_code == 503
