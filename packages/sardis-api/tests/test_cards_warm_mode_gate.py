from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.cards import create_cards_router


class _CardRepo:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    async def create(
        self,
        *,
        card_id: str,
        wallet_id: str,
        provider: str,
        provider_card_id: str,
        card_type: str,
        limit_per_tx: float,
        limit_daily: float,
        limit_monthly: float,
    ):
        row = {
            "card_id": card_id,
            "wallet_id": wallet_id,
            "provider": provider,
            "provider_card_id": provider_card_id,
            "card_type": card_type,
            "limit_per_tx": limit_per_tx,
            "limit_daily": limit_daily,
            "limit_monthly": limit_monthly,
            "funded_amount": 0.0,
        }
        self.rows[card_id] = row
        return row

    async def get_by_card_id(self, card_id: str):
        return self.rows.get(card_id)

    async def update_funded_amount(self, card_id: str, amount: float):
        row = self.rows.get(card_id)
        if row is None:
            return None
        row["funded_amount"] = amount
        return row


class _Provider:
    name = "stripe_issuing"

    async def create_card(self, **kwargs):
        return SimpleNamespace(provider="stripe_issuing", provider_card_id="ic_test_123")

    async def fund_card(self, provider_card_id: str, amount: float):
        return {"provider_card_id": provider_card_id, "amount": amount}

    async def freeze_card(self, provider_card_id: str):
        return {"provider_card_id": provider_card_id, "status": "frozen"}

    async def unfreeze_card(self, provider_card_id: str):
        return {"provider_card_id": provider_card_id, "status": "active"}

    async def cancel_card(self, provider_card_id: str):
        return {"provider_card_id": provider_card_id, "status": "cancelled"}

    async def update_limits(self, provider_card_id: str, **kwargs):
        return {"provider_card_id": provider_card_id, **kwargs}


class _WalletRepo:
    async def get(self, wallet_id: str):
        return SimpleNamespace(agent_id="agent_1")


class _AgentRepo:
    async def get(self, agent_id: str):
        return SimpleNamespace(owner_id="org_demo")


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app() -> tuple[FastAPI, _CardRepo]:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    card_repo = _CardRepo()
    router = create_cards_router(
        card_repo=card_repo,
        card_provider=_Provider(),
        environment="production",
        wallet_repo=_WalletRepo(),
        agent_repo=_AgentRepo(),
    )
    app.include_router(router, prefix="/api/v2/cards")
    return app, card_repo


def test_issue_card_blocked_in_production_when_issuing_live_disabled(monkeypatch):
    monkeypatch.delenv("SARDIS_ISSUING_LIVE_ENABLED", raising=False)
    app, _ = _build_app()
    client = TestClient(app)

    response = client.post(
        "/api/v2/cards",
        json={
            "wallet_id": "wallet_1",
            "card_type": "multi_use",
            "limit_per_tx": "50.00",
            "limit_daily": "200.00",
            "limit_monthly": "1000.00",
            "funding_source": "fiat",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "issuing_warm_mode_enabled:issue_card"


def test_issue_card_allowed_when_issuing_live_enabled(monkeypatch):
    monkeypatch.setenv("SARDIS_ISSUING_LIVE_ENABLED", "true")
    app, _ = _build_app()
    client = TestClient(app)

    response = client.post(
        "/api/v2/cards",
        json={
            "wallet_id": "wallet_1",
            "card_type": "multi_use",
            "limit_per_tx": "50.00",
            "limit_daily": "200.00",
            "limit_monthly": "1000.00",
            "funding_source": "fiat",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "stripe_issuing"

