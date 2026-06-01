"""Tests for the production Shared Payment Token (SPT) router.

Proves the fail-closed guarantees:
- grant requires Stripe + an active, non-expired mandate; a Stripe failure does
  NOT return a hollow token; a successful grant is persisted.
- use enforces status / expiry / per-use cap server-side BEFORE charging Stripe.
- revoke marks the token revoked.
"""
from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.authz import Principal, require_principal
from server.routes.protocol.spt import router

ORG = "org_test_001"


def _make_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key", organization_id=ORG, scopes=["*"],
    )
    app.include_router(router, prefix="/api/v2")
    return app


@pytest.fixture()
def client():
    with TestClient(_make_app()) as c:
        yield c


@pytest.fixture(autouse=True)
def _stripe_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "stripe_test_key_dummy")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "test")


def _active_mandate(**over):
    base = {
        "id": "mandate_1",
        "org_id": ORG,
        "agent_id": "agent_1",
        "currency": "USDC",
        "amount_per_tx": 100,  # -> max_amount 10000 cents
        "expires_at": datetime.now(UTC) + timedelta(days=30),
        "status": "active",
    }
    base.update(over)
    return base


# ---- grant -----------------------------------------------------------------


def test_grant_no_stripe_returns_503(client, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    r = client.post("/api/v2/spt/grant", json={"mandate_id": "mandate_1"})
    assert r.status_code == 503


def test_grant_missing_mandate_404(client):
    with patch("sardis.core.database.Database.fetchrow", new=AsyncMock(return_value=None)):
        r = client.post("/api/v2/spt/grant", json={"mandate_id": "nope"})
    assert r.status_code == 404


@respx.mock
def test_grant_stripe_failure_no_hollow_token(client):
    """If Stripe rejects the grant, we must NOT return a token (fail-closed)."""
    respx.post("https://api.stripe.com/v1/test_helpers/shared_payment/granted_tokens").mock(
        return_value=httpx.Response(400, text='{"error":"bad"}')
    )
    with patch("sardis.core.database.Database.fetchrow", new=AsyncMock(return_value=_active_mandate())), \
         patch("sardis.core.database.Database.execute", new=AsyncMock()) as exec_mock:
        r = client.post("/api/v2/spt/grant", json={"mandate_id": "mandate_1"})
    assert r.status_code == 502
    exec_mock.assert_not_called()  # nothing persisted on failure


@respx.mock
def test_grant_expired_mandate_409(client):
    with patch(
        "sardis.core.database.Database.fetchrow",
        new=AsyncMock(return_value=_active_mandate(expires_at=datetime.now(UTC) - timedelta(days=1))),
    ):
        r = client.post("/api/v2/spt/grant", json={"mandate_id": "mandate_1"})
    assert r.status_code == 409


@respx.mock
def test_grant_success_persists(client):
    respx.post("https://api.stripe.com/v1/test_helpers/shared_payment/granted_tokens").mock(
        return_value=httpx.Response(200, json={"id": "spt_stripe_123"})
    )
    with patch("sardis.core.database.Database.fetchrow", new=AsyncMock(return_value=_active_mandate())), \
         patch("sardis.core.database.Database.execute", new=AsyncMock()) as exec_mock:
        r = client.post("/api/v2/spt/grant", json={"mandate_id": "mandate_1"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["stripe_spt_id"] == "spt_stripe_123"
    assert body["usage_limits"]["max_amount"] == 10000
    assert body["status"] == "active"
    exec_mock.assert_awaited_once()  # persisted


# ---- use -------------------------------------------------------------------


class _FakeConn:
    def __init__(self, row):
        self._row = row
        self.executed: list[tuple] = []

    async def fetchrow(self, *args):
        return self._row

    async def execute(self, *args):
        self.executed.append(args)
        return "UPDATE 1"


def _patch_tx(conn):
    @contextlib.asynccontextmanager
    async def _tx():
        yield conn
    return patch("sardis.core.database.Database.transaction", new=_tx)


def _spt_row(**over):
    base = {
        "token_id": "spt_local_1",
        "org_id": ORG,
        "stripe_spt_id": "spt_stripe_123",
        "currency": "usd",
        "max_amount": 10000,
        "expires_at": int((datetime.now(UTC) + timedelta(days=1)).timestamp()),
        "status": "active",
        "spent_amount": 0,
        "use_count": 0,
    }
    base.update(over)
    return base


@respx.mock
def test_use_over_limit_rejected_before_stripe(client):
    """A use above the per-use cap is rejected and Stripe is never called."""
    route = respx.post("https://api.stripe.com/v1/payment_intents").mock(
        return_value=httpx.Response(200, json={"id": "pi_1", "status": "succeeded"})
    )
    conn = _FakeConn(_spt_row(max_amount=5000))
    with _patch_tx(conn):
        r = client.post("/api/v2/spt/use", json={"spt_id": "spt_local_1", "amount": 9999, "currency": "usd"})
    assert r.status_code == 422
    assert not route.called  # fail-closed: no charge attempted
    assert conn.executed == []  # no spend recorded


@respx.mock
def test_use_revoked_token_rejected(client):
    route = respx.post("https://api.stripe.com/v1/payment_intents")
    conn = _FakeConn(_spt_row(status="revoked"))
    with _patch_tx(conn):
        r = client.post("/api/v2/spt/use", json={"spt_id": "spt_local_1", "amount": 100, "currency": "usd"})
    assert r.status_code == 409
    assert not route.called


@respx.mock
def test_use_expired_token_rejected(client):
    route = respx.post("https://api.stripe.com/v1/payment_intents")
    conn = _FakeConn(_spt_row(expires_at=1))
    with _patch_tx(conn):
        r = client.post("/api/v2/spt/use", json={"spt_id": "spt_local_1", "amount": 100, "currency": "usd"})
    assert r.status_code == 409
    assert not route.called


@respx.mock
def test_use_unknown_token_404(client):
    conn = _FakeConn(None)
    with _patch_tx(conn):
        r = client.post("/api/v2/spt/use", json={"spt_id": "nope", "amount": 100, "currency": "usd"})
    assert r.status_code == 404


@respx.mock
def test_use_success_records_spend(client):
    respx.post("https://api.stripe.com/v1/payment_intents").mock(
        return_value=httpx.Response(200, json={"id": "pi_ok", "status": "succeeded"})
    )
    conn = _FakeConn(_spt_row())
    with _patch_tx(conn):
        r = client.post("/api/v2/spt/use", json={"spt_id": "spt_local_1", "amount": 5000, "currency": "usd"})
    assert r.status_code == 200, r.text
    assert r.json()["payment_intent_id"] == "pi_ok"
    # spend recorded under the lock
    assert conn.executed, "spend update should have run"


# ---- revoke ----------------------------------------------------------------


@respx.mock
def test_revoke_marks_revoked(client):
    respx.post(
        "https://api.stripe.com/v1/shared_payment/granted_tokens/spt_stripe_123/deactivate"
    ).mock(return_value=httpx.Response(200, json={"deactivated_at": 1}))
    with patch(
        "sardis.core.database.Database.fetchrow",
        new=AsyncMock(return_value={"token_id": "spt_local_1", "stripe_spt_id": "spt_stripe_123", "status": "active"}),
    ), patch("sardis.core.database.Database.execute", new=AsyncMock()) as exec_mock:
        r = client.post("/api/v2/spt/spt_local_1/revoke")
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"
    exec_mock.assert_awaited_once()


def test_revoke_unknown_404(client):
    with patch("sardis.core.database.Database.fetchrow", new=AsyncMock(return_value=None)):
        r = client.post("/api/v2/spt/nope/revoke")
    assert r.status_code == 404
