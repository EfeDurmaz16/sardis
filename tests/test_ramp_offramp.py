"""Tests for ramp offramp endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sardis_api.routers.ramp import router as ramp_router, get_deps, RampDependencies
from sardis_cards.offramp import OfframpQuote, OfframpTransaction, OfframpProvider, OfframpStatus


@pytest.fixture
def mock_wallet_repo():
    repo = AsyncMock()
    wallet = MagicMock()
    wallet.wallet_id = "wallet_1"
    wallet.get_address.return_value = "0xabc123"
    wallet.addresses = {"base": "0xabc123"}
    wallet.is_active = True
    repo.get.return_value = wallet
    return repo


@pytest.fixture
def mock_offramp_service():
    svc = AsyncMock()
    svc.get_quote.return_value = OfframpQuote(
        quote_id="q_123",
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=100_000_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=9950,
        exchange_rate=Decimal("1.0"),
        fee_cents=50,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    svc.execute.return_value = OfframpTransaction(
        transaction_id="tx_123",
        quote_id="q_123",
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=100_000_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=9950,
        destination_account="acct_456",
        status=OfframpStatus.PROCESSING,
    )
    svc.get_status.return_value = OfframpTransaction(
        transaction_id="tx_123",
        quote_id="q_123",
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=100_000_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=9950,
        destination_account="acct_456",
        status=OfframpStatus.COMPLETED,
        completed_at=datetime.now(timezone.utc),
    )
    return svc


@pytest.fixture
def app_with_ramp(mock_wallet_repo, mock_offramp_service):
    app = FastAPI()
    deps = RampDependencies(
        wallet_repo=mock_wallet_repo,
        offramp_service=mock_offramp_service,
        onramper_api_key="test_key",
    )
    app.dependency_overrides[get_deps] = lambda: deps
    app.include_router(ramp_router, prefix="/api/v2/ramp")
    return app


class TestOfframpQuote:
    def test_get_quote(self, app_with_ramp, mock_offramp_service):
        client = TestClient(app_with_ramp)
        resp = client.post("/api/v2/ramp/offramp/quote", json={
            "input_token": "USDC",
            "input_amount": 100.0,
            "input_chain": "base",
            "output_currency": "USD",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["quote_id"] == "q_123"
        assert data["output_amount"] == "99.50"
        assert data["fee"] == "0.50"
        mock_offramp_service.get_quote.assert_called_once()


class TestOfframpExecute:
    def test_execute(self, app_with_ramp, mock_offramp_service):
        client = TestClient(app_with_ramp)
        resp = client.post("/api/v2/ramp/offramp/execute", json={
            "quote_id": "q_123",
            "wallet_id": "wallet_1",
            "destination_account": "acct_456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction_id"] == "tx_123"
        assert data["status"] == "processing"

    def test_execute_wallet_not_found(self, app_with_ramp, mock_wallet_repo):
        mock_wallet_repo.get.return_value = None
        client = TestClient(app_with_ramp)
        resp = client.post("/api/v2/ramp/offramp/execute", json={
            "quote_id": "q_123",
            "wallet_id": "nonexistent",
            "destination_account": "acct_456",
        })
        assert resp.status_code == 404


class TestOfframpStatus:
    def test_get_status(self, app_with_ramp, mock_offramp_service):
        client = TestClient(app_with_ramp)
        resp = client.get("/api/v2/ramp/offramp/status/tx_123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction_id"] == "tx_123"
        assert data["status"] == "completed"

    def test_get_status_not_found(self, app_with_ramp, mock_offramp_service):
        mock_offramp_service.get_status.side_effect = ValueError("not found")
        client = TestClient(app_with_ramp)
        resp = client.get("/api/v2/ramp/offramp/status/nonexistent")
        assert resp.status_code == 404
