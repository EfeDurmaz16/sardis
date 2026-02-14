"""E2E integration tests for the full Sardis transaction flow.

Tests the complete lifecycle:
- Fund wallet via Onramper widget
- Issue and fund card via offramp
- Wallet-to-wallet crypto transfer
- Offramp to bank
"""
import hashlib
import hmac as hmac_mod
import json
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.ramp import (
    router as ramp_router,
    public_router as ramp_public_router,
    get_deps as ramp_get_deps,
    RampDependencies,
)
from sardis_api.routers.wallets import router as wallets_router, get_deps as wallets_get_deps, WalletDependencies
from sardis_api.routers.cards import create_cards_router
from sardis_cards.offramp import (
    OfframpQuote, OfframpTransaction, OfframpProvider, OfframpStatus,
)

pytestmark = pytest.mark.e2e


@pytest.fixture
def wallet_mock():
    wallet = MagicMock()
    wallet.wallet_id = "wallet_e2e"
    wallet.agent_id = "agent_e2e"
    wallet.mpc_provider = "turnkey"
    wallet.addresses = {"base": "0xe2eWalletAddress", "base_sepolia": "0xe2eWalletAddress"}
    wallet.currency = "USDC"
    wallet.limit_per_tx = 500
    wallet.limit_total = 5000
    wallet.is_active = True
    wallet.is_frozen = False
    wallet.frozen_by = None
    wallet.freeze_reason = None
    wallet.audit_anchor = None
    wallet.get_address.side_effect = lambda c: wallet.addresses.get(c)
    wallet.created_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00Z")
    wallet.updated_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00Z")
    return wallet


@pytest.fixture
def wallet_repo(wallet_mock):
    repo = AsyncMock()
    repo.get.return_value = wallet_mock
    repo.get_by_agent.return_value = wallet_mock
    return repo


@pytest.fixture
def agent_repo():
    repo = AsyncMock()
    agent = MagicMock()
    agent.agent_id = "agent_e2e"
    agent.owner_id = "org_demo"
    repo.get.return_value = agent
    return repo


@pytest.fixture
def offramp_service():
    quote = OfframpQuote(
        quote_id="quote_e2e",
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=100_000_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=99_500_000,
        exchange_rate=Decimal("1.0"),
        fee_cents=500_000,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    tx = OfframpTransaction(
        transaction_id="tx_e2e",
        quote_id=quote.quote_id,
        provider=OfframpProvider.MOCK,
        input_token=quote.input_token,
        input_amount_minor=quote.input_amount_minor,
        input_chain=quote.input_chain,
        output_currency=quote.output_currency,
        output_amount_cents=quote.output_amount_cents,
        destination_account="bank_acct_123",
        status=OfframpStatus.PROCESSING,
        created_at=datetime.now(timezone.utc),
    )
    service = AsyncMock()
    service.get_quote = AsyncMock(return_value=quote)
    service.execute = AsyncMock(return_value=tx)
    service.get_status = AsyncMock(return_value=tx)
    return service


@pytest.fixture
def chain_executor():
    executor = AsyncMock()
    receipt = MagicMock()
    receipt.tx_hash = "0xe2e_tx_hash"
    receipt.audit_anchor = None
    executor.dispatch_payment.return_value = receipt
    return executor


@pytest.fixture
def card_repo():
    repo = AsyncMock()
    repo.create.return_value = {
        "card_id": "card_e2e", "wallet_id": "wallet_e2e",
        "provider": "lithic", "status": "active", "funded_amount": 0,
    }
    repo.get_by_card_id.return_value = {
        "card_id": "card_e2e", "wallet_id": "wallet_e2e",
        "provider": "lithic", "provider_card_id": "li_e2e",
        "status": "active", "funded_amount": 0,
    }
    repo.update_funded_amount.return_value = {
        "card_id": "card_e2e", "funded_amount": 100.0,
    }
    return repo


@pytest.fixture
def card_provider():
    provider = AsyncMock()
    provider.create_card.return_value = MagicMock(provider_card_id="li_e2e")
    provider.fund_card.return_value = MagicMock(status="active")
    return provider


@pytest.fixture
def e2e_app(wallet_repo, agent_repo, offramp_service, chain_executor, card_repo, card_provider):
    app = FastAPI()

    # Wire ramp router
    ramp_deps = RampDependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        offramp_service=offramp_service,
        onramper_api_key="e2e_key",
        onramper_webhook_secret="e2e_secret",
    )
    app.dependency_overrides[ramp_get_deps] = lambda: ramp_deps
    app.include_router(ramp_router, prefix="/api/v2/ramp")
    app.include_router(ramp_public_router, prefix="/api/v2/ramp")

    # Wire wallets router
    wallet_deps = WalletDependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=chain_executor,
    )
    app.dependency_overrides[wallets_get_deps] = lambda: wallet_deps
    app.include_router(wallets_router, prefix="/api/v2/wallets")

    # Wire cards router
    cards_r = create_cards_router(
        card_repo=card_repo,
        card_provider=card_provider,
        offramp_service=offramp_service,
        chain_executor=chain_executor,
        wallet_repo=wallet_repo,
    )
    app.include_router(cards_r, prefix="/api/v2/cards")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )

    return app


class TestFundWalletViaOnramper:
    def test_widget_url_generation_and_webhook(self, e2e_app):
        client = TestClient(e2e_app)

        # Step 1: Generate widget URL
        resp = client.post("/api/v2/ramp/onramp/widget", json={
            "wallet_id": "wallet_e2e",
            "amount_usd": 500,
            "chain": "base",
            "token": "USDC",
        })
        assert resp.status_code == 200
        assert "buy.onramper.com" in resp.json()["widget_url"]

        # Step 2: Simulate webhook callback
        payload = json.dumps({
            "type": "transaction.completed",
            "payload": {
                "wallet_address": "0xe2eWalletAddress",
                "crypto_amount": "500.0",
                "crypto_currency": "USDC",
                "tx_hash": "0xonramp_tx",
            },
        }).encode()
        ts = str(int(time.time()))
        sig = hmac_mod.new(b"e2e_secret", payload, hashlib.sha256).hexdigest()
        resp = client.post(
            "/api/v2/ramp/onramp/webhook",
            content=payload,
            headers={
                "content-type": "application/json",
                "x-onramper-signature": sig,
                "x-onramper-timestamp": ts,
            },
        )
        assert resp.status_code == 200


class TestIssueAndFundCard:
    @patch.dict("os.environ", {"LITHIC_FUNDING_ACCOUNT_ID": "e2e_funding"})
    def test_issue_and_fund_card_real(self, e2e_app):
        client = TestClient(e2e_app)

        # Fund card via offramp
        resp = client.post("/api/v2/cards/card_e2e/fund", json={
            "amount": 100.0,
            "source": "stablecoin",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "offramp_tx_id" in data
        assert data["offramp_status"] in ("processing", "completed")


class TestWalletToWalletTransfer:
    def test_a2a_transfer(self, e2e_app, chain_executor):
        client = TestClient(e2e_app)
        resp = client.post("/api/v2/wallets/wallet_e2e/transfer", json={
            "destination": "0xrecipientAgent",
            "amount": 25.0,
            "token": "USDC",
            "chain": "base_sepolia",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["tx_hash"] == "0xe2e_tx_hash"
        assert data["to_address"] == "0xrecipientAgent"
        chain_executor.dispatch_payment.assert_called_once()


class TestOfframpToBank:
    def test_offramp_to_bank(self, e2e_app):
        client = TestClient(e2e_app)

        # Get quote
        resp = client.post("/api/v2/ramp/offramp/quote", json={
            "input_token": "USDC",
            "input_amount": 200.0,
            "input_chain": "base",
            "output_currency": "USD",
        })
        assert resp.status_code == 200
        quote = resp.json()
        assert float(quote["output_amount"]) > 0

        # Execute offramp
        resp = client.post("/api/v2/ramp/offramp/execute", json={
            "quote_id": quote["quote_id"],
            "wallet_id": "wallet_e2e",
            "destination_account": "bank_acct_123",
        })
        assert resp.status_code == 200
        tx = resp.json()
        assert tx["status"] in ("processing", "completed", "pending")

        # Check status
        resp = client.get(f"/api/v2/ramp/offramp/status/{tx['transaction_id']}")
        assert resp.status_code == 200
