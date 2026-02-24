from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.cards import create_cards_router


class _NoopCardRepo:
    pass


class _WalletRepo:
    async def get(self, wallet_id: str):
        return SimpleNamespace(agent_id="agent_1")


class _AgentRepo:
    async def get(self, agent_id: str):
        return SimpleNamespace(owner_id="org_demo")


class _ResolverProvider:
    name = "org_router(lithic)"

    async def resolve_provider_for_wallet(self, wallet_id: str) -> str:
        return "rain"


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal

    provider_wrapper = SimpleNamespace(_provider=_ResolverProvider())
    router = create_cards_router(
        card_repo=_NoopCardRepo(),
        card_provider=provider_wrapper,
        wallet_repo=_WalletRepo(),
        agent_repo=_AgentRepo(),
    )
    app.include_router(router, prefix="/api/v2/cards")
    return app


def test_cards_provider_readiness_endpoint():
    app = _build_app()
    client = TestClient(app)

    response = client.get("/api/v2/cards/providers/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_provider"] == "org_router(lithic)"
    issuer_names = {item["name"] for item in payload["issuers"]}
    assert "stripe_issuing" in issuer_names
    assert "lithic" in issuer_names


def test_cards_provider_resolve_endpoint():
    app = _build_app()
    client = TestClient(app)

    response = client.get("/api/v2/cards/providers/resolve", params={"wallet_id": "wallet_1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["wallet_id"] == "wallet_1"
    assert payload["provider"] == "rain"
