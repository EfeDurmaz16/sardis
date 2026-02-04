"""Tests for ramp onramp endpoints."""
import hashlib
import hmac as hmac_mod
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from sardis_api.routers.ramp import router as ramp_router, get_deps, RampDependencies


@pytest.fixture
def mock_wallet_repo():
    repo = AsyncMock()
    wallet = MagicMock()
    wallet.wallet_id = "wallet_1"
    wallet.agent_id = "agent_1"
    wallet.get_address.return_value = "0x1234567890abcdef1234567890abcdef12345678"
    wallet.addresses = {"base": "0x1234567890abcdef1234567890abcdef12345678"}
    wallet.is_active = True
    repo.get.return_value = wallet
    return repo


@pytest.fixture
def mock_agent_repo():
    repo = AsyncMock()
    agent = MagicMock()
    agent.agent_id = "agent_1"
    agent.owner_id = "org_demo"
    repo.get.return_value = agent
    return repo


@pytest.fixture
def mock_offramp_service():
    return AsyncMock()


@pytest.fixture
def app_with_ramp(mock_wallet_repo, mock_agent_repo, mock_offramp_service):
    app = FastAPI()
    deps = RampDependencies(
        wallet_repo=mock_wallet_repo,
        agent_repo=mock_agent_repo,
        offramp_service=mock_offramp_service,
        onramper_api_key="test_onramper_key",
        onramper_webhook_secret="test_webhook_secret",
    )
    app.dependency_overrides[get_deps] = lambda: deps
    app.include_router(ramp_router, prefix="/api/v2/ramp")
    return app


class TestOnrampWidget:
    def test_generate_widget_url(self, app_with_ramp, mock_wallet_repo):
        client = TestClient(app_with_ramp)
        resp = client.post("/api/v2/ramp/onramp/widget", json={
            "wallet_id": "wallet_1",
            "amount_usd": 100,
            "chain": "base",
            "token": "USDC",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "widget_url" in data
        assert "buy.onramper.com" in data["widget_url"]
        assert "test_onramper_key" in data["widget_url"]
        assert data["wallet_address"] == "0x1234567890abcdef1234567890abcdef12345678"
        assert data["chain"] == "base"

    def test_generate_widget_wallet_not_found(self, app_with_ramp, mock_wallet_repo):
        mock_wallet_repo.get.return_value = None
        client = TestClient(app_with_ramp)
        resp = client.post("/api/v2/ramp/onramp/widget", json={
            "wallet_id": "nonexistent",
        })
        assert resp.status_code == 404

    def test_generate_widget_no_address_for_chain(self, app_with_ramp, mock_wallet_repo):
        mock_wallet_repo.get.return_value.get_address.return_value = None
        client = TestClient(app_with_ramp)
        resp = client.post("/api/v2/ramp/onramp/widget", json={
            "wallet_id": "wallet_1",
            "chain": "arbitrum",
        })
        assert resp.status_code == 400


class TestOnrampWebhook:
    def test_valid_webhook(self, app_with_ramp):
        client = TestClient(app_with_ramp)
        payload = json.dumps({
            "type": "transaction.completed",
            "payload": {
                "wallet_address": "0x1234",
                "crypto_amount": "100.0",
                "crypto_currency": "USDC",
                "tx_hash": "0xabc",
            },
        }).encode()
        sig = hmac_mod.new(b"test_webhook_secret", payload, hashlib.sha256).hexdigest()
        resp = client.post(
            "/api/v2/ramp/onramp/webhook",
            content=payload,
            headers={
                "content-type": "application/json",
                "x-onramper-signature": sig,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    def test_invalid_signature(self, app_with_ramp):
        client = TestClient(app_with_ramp)
        payload = json.dumps({"type": "test"}).encode()
        resp = client.post(
            "/api/v2/ramp/onramp/webhook",
            content=payload,
            headers={
                "content-type": "application/json",
                "x-onramper-signature": "bad_sig",
            },
        )
        assert resp.status_code == 401
