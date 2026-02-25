from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.routers.partner_card_webhooks import (
    PartnerCardWebhookDeps,
    get_deps,
    router,
)


class _FakeCardRepo:
    def __init__(self) -> None:
        self.card = {
            "card_id": "vc_1",
            "provider_card_id": "card_provider_1",
            "wallet_id": "wallet_1",
            "status": "active",
        }
        self.transactions = []

    async def get_by_provider_card_id(self, provider_card_id: str):
        if provider_card_id == self.card["provider_card_id"]:
            return self.card
        return None

    async def get_by_card_id(self, card_id: str):
        if card_id == self.card["card_id"]:
            return self.card
        return None

    async def update_status(self, card_id: str, status_value: str):
        if card_id == self.card["card_id"]:
            self.card["status"] = status_value
        return self.card

    async def record_transaction(self, **kwargs):
        self.transactions.append(kwargs)
        return kwargs


class _FakeWalletRepo:
    async def get(self, wallet_id: str):
        return SimpleNamespace(agent_id="agent_1")


class _FakeAgentRepo:
    async def get(self, agent_id: str):
        return SimpleNamespace(owner_id="org_demo")


class _FakeCanonicalRepo:
    def __init__(self) -> None:
        self.events = []

    async def ingest_event(self, event, *, drift_tolerance_minor: int = 0):
        self.events.append((event, drift_tolerance_minor))
        return {"ok": True}


class _FakeTreasuryRepo:
    def __init__(self) -> None:
        self.events = []

    async def record_treasury_webhook_event(self, **kwargs):
        self.events.append(kwargs)


def _build_app(deps: PartnerCardWebhookDeps) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: deps
    app.include_router(router, prefix="/api/v2")
    return app


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_bridge_webhook_rejects_invalid_signature_in_production():
    deps = PartnerCardWebhookDeps(
        card_repo=_FakeCardRepo(),
        wallet_repo=_FakeWalletRepo(),
        agent_repo=_FakeAgentRepo(),
        canonical_repo=_FakeCanonicalRepo(),
        treasury_repo=_FakeTreasuryRepo(),
        bridge_webhook_secret="bridge_secret",
        environment="prod",
    )
    app = _build_app(deps)
    client = TestClient(app)

    payload = {
        "id": "evt_1",
        "type": "transaction.authorized",
        "data": {
            "card_id": "card_provider_1",
            "amount": "10.00",
            "currency": "USD",
            "status": "approved",
        },
    }
    response = client.post(
        "/api/v2/webhooks/cards/bridge",
        content=json.dumps(payload),
        headers={"x-bridge-signature": "bad"},
    )

    assert response.status_code == 401


def test_bridge_webhook_transaction_records_and_canonicalizes():
    card_repo = _FakeCardRepo()
    canonical_repo = _FakeCanonicalRepo()
    treasury_repo = _FakeTreasuryRepo()
    deps = PartnerCardWebhookDeps(
        card_repo=card_repo,
        wallet_repo=_FakeWalletRepo(),
        agent_repo=_FakeAgentRepo(),
        canonical_repo=canonical_repo,
        treasury_repo=treasury_repo,
        bridge_webhook_secret="bridge_secret",
        environment="prod",
    )
    app = _build_app(deps)
    client = TestClient(app)

    payload = {
        "id": "evt_2",
        "type": "transaction.settled",
        "data": {
            "card_id": "card_provider_1",
            "transaction_id": "tx_1",
            "amount": "12.50",
            "currency": "USD",
            "status": "settled",
            "merchant_name": "Bridge Merchant",
            "mcc": "5734",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/api/v2/webhooks/cards/bridge",
        content=body,
        headers={"x-bridge-signature": _sign("bridge_secret", body)},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "received"
    assert len(card_repo.transactions) == 1
    assert card_repo.transactions[0]["status"] == "settled"
    assert len(canonical_repo.events) == 1
    assert len(treasury_repo.events) == 1


def test_rain_lifecycle_webhook_updates_card_status():
    card_repo = _FakeCardRepo()
    deps = PartnerCardWebhookDeps(
        card_repo=card_repo,
        wallet_repo=_FakeWalletRepo(),
        agent_repo=_FakeAgentRepo(),
        canonical_repo=_FakeCanonicalRepo(),
        treasury_repo=_FakeTreasuryRepo(),
        rain_webhook_secret="rain_secret",
        environment="prod",
    )
    app = _build_app(deps)
    client = TestClient(app)

    payload = {
        "id": "evt_3",
        "type": "card.updated",
        "data": {
            "card_id": "card_provider_1",
            "status": "paused",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/api/v2/webhooks/cards/rain",
        content=body,
        headers={"x-rain-signature": _sign("rain_secret", body)},
    )

    assert response.status_code == 200
    assert card_repo.card["status"] == "frozen"
