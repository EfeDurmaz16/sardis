"""Tests for real card funding via offramp (USDC→USD→Lithic)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sardis_cards.offramp import OfframpQuote, OfframpTransaction, OfframpProvider, OfframpStatus


@pytest.fixture
def mock_card_repo():
    repo = AsyncMock()
    repo.get_by_card_id.return_value = {
        "id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1",
        "provider": "lithic", "provider_card_id": "li_card_123",
        "status": "active", "funded_amount": 0,
    }
    repo.update_funded_amount.return_value = {
        "id": "uuid-1", "card_id": "card_1", "funded_amount": 50.0,
    }
    return repo


@pytest.fixture
def mock_card_provider():
    provider = AsyncMock()
    provider.create_card.return_value = MagicMock(provider_card_id="li_card_123")
    provider.fund_card.return_value = MagicMock(status="active")
    return provider


@pytest.fixture
def mock_offramp_service():
    svc = AsyncMock()
    svc.get_quote.return_value = OfframpQuote(
        quote_id="q_fund_1",
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=50_000_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=4975,
        exchange_rate=Decimal("1.0"),
        fee_cents=25,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    svc.execute.return_value = OfframpTransaction(
        transaction_id="offramp_tx_1",
        quote_id="q_fund_1",
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=50_000_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=4975,
        destination_account="lithic_funding_acct",
        status=OfframpStatus.PROCESSING,
    )
    return svc


@pytest.fixture
def mock_chain_executor():
    return AsyncMock()


@pytest.fixture
def mock_wallet_repo():
    repo = AsyncMock()
    wallet = MagicMock()
    wallet.wallet_id = "wallet_1"
    wallet.get_address.return_value = "0xwallet_addr"
    wallet.addresses = {"base": "0xwallet_addr"}
    repo.get.return_value = wallet
    return repo


@pytest.fixture
def app_with_cards(mock_card_repo, mock_card_provider, mock_offramp_service, mock_chain_executor, mock_wallet_repo):
    from sardis_api.routers.cards import create_cards_router
    app = FastAPI()
    router = create_cards_router(
        card_repo=mock_card_repo,
        card_provider=mock_card_provider,
        offramp_service=mock_offramp_service,
        chain_executor=mock_chain_executor,
        wallet_repo=mock_wallet_repo,
    )
    app.include_router(router, prefix="/api/v2/cards")
    return app


class TestRealCardFunding:
    @patch.dict("os.environ", {"LITHIC_FUNDING_ACCOUNT_ID": "lithic_funding_acct"})
    def test_fund_card_via_offramp(self, app_with_cards, mock_offramp_service, mock_card_repo):
        client = TestClient(app_with_cards)
        resp = client.post("/api/v2/cards/card_1/fund", json={
            "amount": 50.0,
            "source": "stablecoin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["offramp_tx_id"] == "offramp_tx_1"
        assert data["offramp_status"] == "processing"
        mock_offramp_service.get_quote.assert_called_once()
        mock_offramp_service.execute.assert_called_once()

    def test_fund_card_no_wallet(self, app_with_cards, mock_card_repo):
        mock_card_repo.get_by_card_id.return_value = {
            "id": "uuid-1", "card_id": "card_1",
            "status": "active", "funded_amount": 0,
            # no wallet_id
        }
        client = TestClient(app_with_cards)
        resp = client.post("/api/v2/cards/card_1/fund", json={
            "amount": 50.0,
            "source": "stablecoin",
        })
        assert resp.status_code == 400

    def test_fund_card_not_found(self, app_with_cards, mock_card_repo):
        mock_card_repo.get_by_card_id.return_value = None
        client = TestClient(app_with_cards)
        resp = client.post("/api/v2/cards/card_1/fund", json={"amount": 50.0})
        assert resp.status_code == 404

    def test_fund_card_fallback_no_offramp(self, mock_card_repo, mock_card_provider):
        """Without offramp_service, falls back to simple provider funding."""
        from sardis_api.routers.cards import create_cards_router
        app = FastAPI()
        router = create_cards_router(
            card_repo=mock_card_repo,
            card_provider=mock_card_provider,
        )
        app.include_router(router, prefix="/api/v2/cards")
        client = TestClient(app)
        resp = client.post("/api/v2/cards/card_1/fund", json={
            "amount": 50.0,
            "source": "stablecoin",
        })
        assert resp.status_code == 200
        mock_card_provider.fund_card.assert_called_once()
