from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routes.wallets import virtual_cards


def _make_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )
    app.include_router(virtual_cards.router)
    return app


def test_issue_virtual_card_requires_live_mode_or_explicit_sandbox(monkeypatch) -> None:
    monkeypatch.delenv("SARDIS_VIRTUAL_CARDS_SANDBOX", raising=False)
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "simulated")
    virtual_cards._sandbox_cards.clear()

    with TestClient(_make_app()) as client:
        response = client.post(
            "/cards/virtual/issue",
            json={"amount": "25.00", "currency": "USD", "card_type": "single_use"},
        )

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Virtual cards are unavailable unless SARDIS_CHAIN_MODE=live "
        "or SARDIS_VIRTUAL_CARDS_SANDBOX=true."
    )
    assert virtual_cards._sandbox_cards == {}


def test_issue_virtual_card_allows_explicit_sandbox(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_VIRTUAL_CARDS_SANDBOX", "true")
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "simulated")
    virtual_cards._sandbox_cards.clear()

    with TestClient(_make_app()) as client:
        response = client.post(
            "/cards/virtual/issue",
            json={"amount": "25.00", "currency": "USD", "card_type": "single_use"},
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["sandbox"] is True
    assert payload["status"] == "ready"
    assert payload["card_id"].startswith("sandbox_card_")
    assert payload["card_id"] in virtual_cards._sandbox_cards


def test_virtual_balance_requires_explicit_sandbox_outside_live_mode(monkeypatch) -> None:
    monkeypatch.delenv("SARDIS_VIRTUAL_CARDS_SANDBOX", raising=False)
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "test")

    with TestClient(_make_app()) as client:
        response = client.get("/cards/virtual/balance")

    assert response.status_code == 503, response.text
    assert response.json()["detail"] == (
        "Virtual cards are unavailable unless SARDIS_CHAIN_MODE=live "
        "or SARDIS_VIRTUAL_CARDS_SANDBOX=true."
    )
