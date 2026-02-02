import hashlib
import hmac as hmac_mod
import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture
def mock_card_repo():
    repo = AsyncMock()
    repo.create.return_value = {
        "id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1",
        "provider": "lithic", "provider_card_id": "li_card_123",
        "status": "pending", "limit_daily": 1000, "limit_per_tx": 500,
        "limit_monthly": 10000, "funded_amount": 0,
        "card_type": "multi_use", "created_at": "2026-01-01T00:00:00Z",
    }
    repo.get_by_card_id.return_value = {
        "id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1",
        "provider": "lithic", "provider_card_id": "li_card_123",
        "status": "active", "limit_daily": 1000, "limit_per_tx": 500,
        "limit_monthly": 10000, "funded_amount": 100,
        "card_type": "multi_use", "created_at": "2026-01-01T00:00:00Z",
    }
    repo.get_by_wallet_id.return_value = [repo.get_by_card_id.return_value]
    repo.update_status.return_value = {
        "id": "uuid-1", "card_id": "card_1", "status": "frozen",
    }
    repo.update_limits.return_value = {
        "id": "uuid-1", "card_id": "card_1", "limit_daily": 2000,
    }
    repo.update_funded_amount.return_value = {
        "id": "uuid-1", "card_id": "card_1", "funded_amount": 200,
    }
    repo.list_transactions.return_value = []
    return repo


@pytest.fixture
def mock_card_provider():
    provider = AsyncMock()
    provider.create_card.return_value = MagicMock(
        provider_card_id="li_card_123",
        card_number_last4="4242",
        status="pending",
    )
    provider.freeze_card.return_value = MagicMock(status="frozen")
    provider.unfreeze_card.return_value = MagicMock(status="active")
    provider.cancel_card.return_value = MagicMock(status="cancelled")
    provider.update_limits.return_value = MagicMock(status="active")
    provider.fund_card.return_value = MagicMock(status="active")
    return provider


@pytest.fixture
def app_with_cards(mock_card_repo, mock_card_provider):
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location(
        "cards_router",
        "/Users/efebarandurmaz/Desktop/sardis 2/packages/sardis-api/src/sardis_api/routers/cards.py",
    )
    cards_mod = importlib.util.module_from_spec(spec)
    sys.modules["cards_router"] = cards_mod
    spec.loader.exec_module(cards_mod)
    create_cards_router = cards_mod.create_cards_router
    app = FastAPI()
    router = create_cards_router(
        card_repo=mock_card_repo,
        card_provider=mock_card_provider,
    )
    app.include_router(router, prefix="/api/v2/cards")
    return app


def test_create_card_calls_provider_and_persists(app_with_cards, mock_card_provider, mock_card_repo):
    client = TestClient(app_with_cards)
    resp = client.post("/api/v2/cards", json={
        "wallet_id": "wallet_1",
        "card_type": "multi_use",
        "limit_daily": 1000,
    })
    assert resp.status_code == 201
    mock_card_provider.create_card.assert_called_once()
    mock_card_repo.create.assert_called_once()


def test_freeze_card_calls_provider_and_updates_db(app_with_cards, mock_card_provider, mock_card_repo):
    client = TestClient(app_with_cards)
    resp = client.post("/api/v2/cards/card_1/freeze")
    assert resp.status_code == 200
    mock_card_provider.freeze_card.assert_called_once()
    mock_card_repo.update_status.assert_called_once_with("card_1", "frozen")


def test_get_card_reads_from_db(app_with_cards, mock_card_repo):
    client = TestClient(app_with_cards)
    resp = client.get("/api/v2/cards/card_1")
    assert resp.status_code == 200
    mock_card_repo.get_by_card_id.assert_called_once_with("card_1")


def test_get_card_not_found(app_with_cards, mock_card_repo):
    mock_card_repo.get_by_card_id.return_value = None
    client = TestClient(app_with_cards)
    resp = client.get("/api/v2/cards/nonexistent")
    assert resp.status_code == 404


# ---- Webhook HMAC tests ----

@pytest.fixture
def app_with_webhook_secret(mock_card_repo, mock_card_provider):
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location(
        "cards_router_wh",
        "/Users/efebarandurmaz/Desktop/sardis 2/packages/sardis-api/src/sardis_api/routers/cards.py",
    )
    cards_mod = importlib.util.module_from_spec(spec)
    sys.modules["cards_router_wh"] = cards_mod
    spec.loader.exec_module(cards_mod)
    app = FastAPI()
    router = cards_mod.create_cards_router(
        card_repo=mock_card_repo,
        card_provider=mock_card_provider,
        webhook_secret="test_secret_key",
    )
    app.include_router(router, prefix="/api/v2/cards")
    return app


def test_webhook_rejects_missing_signature(app_with_webhook_secret):
    client = TestClient(app_with_webhook_secret)
    resp = client.post("/api/v2/cards/webhooks", json={"event_type": "test"})
    assert resp.status_code == 401


def test_webhook_rejects_invalid_signature(app_with_webhook_secret):
    client = TestClient(app_with_webhook_secret)
    resp = client.post(
        "/api/v2/cards/webhooks",
        json={"event_type": "test"},
        headers={"x-lithic-hmac": "bad_sig"},
    )
    assert resp.status_code == 401


def test_webhook_accepts_valid_signature(app_with_webhook_secret, mock_card_repo):
    body = json.dumps({"event_type": "card.transaction.created", "card_token": "card_1", "data": {"token": "txn_1", "amount": 100, "currency": "USD", "merchant": {"descriptor": "Test", "mcc": "5411"}, "status": "pending"}})
    sig = hmac_mod.new(b"test_secret_key", body.encode(), hashlib.sha256).hexdigest()
    client = TestClient(app_with_webhook_secret)
    resp = client.post(
        "/api/v2/cards/webhooks",
        content=body,
        headers={"x-lithic-hmac": sig, "content-type": "application/json"},
    )
    assert resp.status_code == 200
    mock_card_repo.record_transaction.assert_called_once()


def test_webhook_no_secret_accepts_all(app_with_cards):
    client = TestClient(app_with_cards)
    resp = client.post("/api/v2/cards/webhooks", json={"event_type": "test"})
    assert resp.status_code == 200
