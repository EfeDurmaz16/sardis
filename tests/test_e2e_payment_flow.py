"""E2E payment flow integration test.

Tests the full agent → wallet → card → transaction lifecycle
using mocked external providers.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI


def _load_cards_module():
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location(
        "cards_router_e2e",
        "/Users/efebarandurmaz/Desktop/sardis 2/packages/sardis-api/src/sardis_api/routers/cards.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cards_router_e2e"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mock_deps():
    repo = AsyncMock()
    provider = AsyncMock()
    provider.create_card.return_value = MagicMock(provider_card_id="li_e2e_001")
    provider.fund_card.return_value = MagicMock(status="funded")
    provider.freeze_card.return_value = MagicMock(status="frozen")
    provider.unfreeze_card.return_value = MagicMock(status="active")
    provider.cancel_card.return_value = MagicMock(status="cancelled")
    return repo, provider


@pytest.fixture
def e2e_app(mock_deps):
    repo, provider = mock_deps
    # Simulate DB state
    card_state = {}

    async def fake_create(**kwargs):
        card = {**kwargs, "id": "uuid-e2e", "status": "active", "funded_amount": 0}
        card_state[kwargs["card_id"]] = card
        return card

    async def fake_get(card_id):
        return card_state.get(card_id)

    async def fake_update_status(card_id, status):
        if card_id in card_state:
            card_state[card_id]["status"] = status
            return card_state[card_id]
        return None

    async def fake_update_funded(card_id, amount):
        if card_id in card_state:
            card_state[card_id]["funded_amount"] = amount
            return card_state[card_id]
        return None

    async def fake_record_txn(**kwargs):
        return kwargs

    async def fake_list_txns(card_id, limit=50):
        return []

    repo.create.side_effect = fake_create
    repo.get_by_card_id.side_effect = fake_get
    repo.update_status.side_effect = fake_update_status
    repo.update_funded_amount.side_effect = fake_update_funded
    repo.record_transaction.side_effect = fake_record_txn
    repo.list_transactions.side_effect = fake_list_txns

    cards_mod = _load_cards_module()
    app = FastAPI()
    router = cards_mod.create_cards_router(card_repo=repo, card_provider=provider)
    app.include_router(router, prefix="/api/v2/cards")
    return app, repo, provider


def test_full_card_lifecycle(e2e_app):
    """Test: issue → fund → freeze → unfreeze → cancel."""
    app, repo, provider = e2e_app
    client = TestClient(app)

    # 1. Issue card
    resp = client.post("/api/v2/cards", json={
        "wallet_id": "wallet_e2e_001",
        "card_type": "multi_use",
        "limit_per_tx": 500,
        "limit_daily": 2000,
        "limit_monthly": 10000,
    })
    assert resp.status_code == 201
    card = resp.json()
    card_id = card["card_id"]
    assert card["status"] == "active"
    provider.create_card.assert_called_once()

    # 2. Fund card
    resp = client.post(f"/api/v2/cards/{card_id}/fund", json={"amount": 100})
    assert resp.status_code == 200
    assert resp.json()["funded_amount"] == 100
    provider.fund_card.assert_called_once()

    # 3. Freeze
    resp = client.post(f"/api/v2/cards/{card_id}/freeze")
    assert resp.status_code == 200
    assert resp.json()["status"] == "frozen"

    # 4. Unfreeze
    resp = client.post(f"/api/v2/cards/{card_id}/unfreeze")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 5. Cancel
    resp = client.delete(f"/api/v2/cards/{card_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_card_not_found_returns_404(e2e_app):
    app, _, _ = e2e_app
    client = TestClient(app)
    resp = client.get("/api/v2/cards/nonexistent_card")
    assert resp.status_code == 404
