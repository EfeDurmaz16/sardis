"""Tests for Conduit Pay onramp service and Conduit wallet fund endpoint path."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis.authz import Principal, require_principal
from sardis.routes.wallets.onramp import router
from sardis.services.conduit_onramp import (
    API_VERSION,
    PRODUCTION_BASE_URL,
    SANDBOX_BASE_URL,
    SUPPORTED_ASSETS,
    SUPPORTED_NETWORKS,
    ConduitAPIError,
    ConduitCustomer,
    ConduitOnrampService,
    ConduitPaymentMethod,
    ConduitQuote,
    ConduitTransaction,
    ConduitTransactionStatus,
    get_conduit_service,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["*"],
        api_key=None,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    app.include_router(router, prefix="/api/v2")
    return app


# ---------------------------------------------------------------------------
# Unit tests — ConduitOnrampService
# ---------------------------------------------------------------------------


class TestConduitConstants:
    """Verify module-level constants are correct."""

    def test_sandbox_url(self):
        assert SANDBOX_BASE_URL == "https://sandbox-api.conduit.financial"

    def test_production_url(self):
        assert PRODUCTION_BASE_URL == "https://api.conduit.financial"

    def test_api_version(self):
        assert API_VERSION == "2024-12-01"

    def test_supported_networks_include_tempo(self):
        assert "tempo" in SUPPORTED_NETWORKS

    def test_supported_networks_include_base(self):
        assert "base" in SUPPORTED_NETWORKS

    def test_supported_assets_include_usdc(self):
        assert "USDC" in SUPPORTED_ASSETS


class TestConduitServiceInit:
    """Test service construction."""

    def test_sandbox_mode(self):
        svc = ConduitOnrampService(
            api_key="key_test",
            api_secret="secret_test",
            sandbox=True,
        )
        assert svc.base_url == SANDBOX_BASE_URL
        assert svc.sandbox is True

    def test_production_mode(self):
        svc = ConduitOnrampService(
            api_key="key_prod",
            api_secret="secret_prod",
            sandbox=False,
        )
        assert svc.base_url == PRODUCTION_BASE_URL
        assert svc.sandbox is False


class TestConduitGetQuote:
    """Unit tests for ConduitOnrampService.get_quote."""

    @pytest.fixture()
    def svc(self):
        return ConduitOnrampService(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
        )

    @pytest.mark.asyncio
    async def test_get_quote_success(self, svc):
        mock_response = {
            "id": "quote_abc123",
            "source": {"amount": "100.00", "asset": "USD"},
            "target": {"amount": "99.50", "asset": "USDC", "network": "tempo"},
            "expiresAt": "2026-03-25T12:00:00Z",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            quote = await svc.get_quote(
                amount_usd="100.00",
                target_asset="USDC",
                target_network="tempo",
            )

        assert isinstance(quote, ConduitQuote)
        assert quote.quote_id == "quote_abc123"
        assert quote.source_amount == "100.00"
        assert quote.source_asset == "USD"
        assert quote.target_amount == "99.50"
        assert quote.target_asset == "USDC"
        assert quote.target_network == "tempo"
        assert quote.expires_at == "2026-03-25T12:00:00Z"

    @pytest.mark.asyncio
    async def test_get_quote_base_network(self, svc):
        mock_response = {
            "id": "quote_base_001",
            "source": {"amount": "50.00", "asset": "USD"},
            "target": {"amount": "49.75", "asset": "USDC", "network": "base"},
            "expiresAt": "2026-03-25T13:00:00Z",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            quote = await svc.get_quote(
                amount_usd="50.00",
                target_asset="USDC",
                target_network="base",
            )

        assert quote.target_network == "base"

    @pytest.mark.asyncio
    async def test_get_quote_unsupported_network(self, svc):
        with pytest.raises(ValueError, match="Unsupported network"):
            await svc.get_quote(
                amount_usd="100.00",
                target_network="avalanche",
            )

    @pytest.mark.asyncio
    async def test_get_quote_unsupported_asset(self, svc):
        with pytest.raises(ValueError, match="Unsupported asset"):
            await svc.get_quote(
                amount_usd="100.00",
                target_asset="DOGE",
            )


class TestConduitCreateCustomer:
    """Unit tests for ConduitOnrampService.create_customer."""

    @pytest.fixture()
    def svc(self):
        return ConduitOnrampService(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
        )

    @pytest.mark.asyncio
    async def test_create_customer_kyb_link(self, svc):
        mock_response = {
            "id": "cus_test123",
            "status": "created",
            "kybLink": "https://portal.conduit.financial/kyb/verify/abc",
            "businessLegalName": "Test Corp",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            customer = await svc.create_customer(
                business_legal_name="Test Corp",
                country="USA",
            )

        assert isinstance(customer, ConduitCustomer)
        assert customer.customer_id == "cus_test123"
        assert customer.status == "created"
        assert customer.kyb_link == "https://portal.conduit.financial/kyb/verify/abc"

    @pytest.mark.asyncio
    async def test_create_customer_direct_flow(self, svc):
        mock_response = {
            "id": "cus_direct456",
            "status": "created",
            "businessLegalName": "Direct Inc",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            customer = await svc.create_customer(
                business_legal_name="Direct Inc",
                country="GBR",
                onboarding_flow="direct",
            )

        assert customer.customer_id == "cus_direct456"
        assert customer.kyb_link is None


class TestConduitCreateWalletPaymentMethod:
    """Unit tests for wallet payment method creation."""

    @pytest.fixture()
    def svc(self):
        return ConduitOnrampService(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
        )

    @pytest.mark.asyncio
    async def test_create_wallet_pm(self, svc):
        mock_response = {
            "id": "pm_wallet_001",
            "type": "crypto_wallet",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            pm = await svc.create_wallet_payment_method(
                customer_id="cus_test123",
                wallet_address="0xabcdef1234567890abcdef1234567890abcdef12",
                network="tempo",
                asset="USDC",
            )

        assert isinstance(pm, ConduitPaymentMethod)
        assert pm.payment_method_id == "pm_wallet_001"
        assert pm.type == "crypto_wallet"
        assert pm.network == "tempo"
        assert pm.address == "0xabcdef1234567890abcdef1234567890abcdef12"


class TestConduitCreateOnrampTransaction:
    """Unit tests for onramp transaction creation."""

    @pytest.fixture()
    def svc(self):
        return ConduitOnrampService(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
        )

    @pytest.mark.asyncio
    async def test_create_onramp_tx(self, svc):
        mock_response = {
            "id": "tx_onramp_001",
            "type": "onramp",
            "status": "awaiting_funds",
            "source": {"amount": "100.00", "asset": "USD"},
            "destination": {"amount": "99.50", "asset": "USDC", "network": "tempo"},
            "onrampInstructions": {
                "status": "ready",
                "data": [{"rail": "ach", "accountNumber": "****1234"}],
            },
            "createdAt": "2026-03-25T10:00:00Z",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            tx = await svc.create_onramp_transaction(
                quote_id="quote_abc123",
                source_payment_method_id="bank_src_001",
                destination_payment_method_id="pm_wallet_001",
                purpose="TreasuryManagement",
                reference="sardis_wal_001",
            )

        assert isinstance(tx, ConduitTransaction)
        assert tx.transaction_id == "tx_onramp_001"
        assert tx.quote_id == "quote_abc123"
        assert tx.status == "awaiting_funds"
        assert tx.source_amount == "100.00"
        assert tx.source_asset == "USD"
        assert tx.target_amount == "99.50"
        assert tx.target_asset == "USDC"
        assert tx.target_network == "tempo"
        assert tx.deposit_instructions is not None
        assert tx.deposit_instructions["status"] == "ready"

    @pytest.mark.asyncio
    async def test_create_onramp_tx_minimal(self, svc):
        """Transaction without optional reference."""
        mock_response = {
            "id": "tx_min_001",
            "type": "onramp",
            "status": "created",
            "source": {"amount": "50.00", "asset": "USD"},
            "destination": {"amount": "49.75", "asset": "USDC", "network": "base"},
            "createdAt": "2026-03-25T11:00:00Z",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            tx = await svc.create_onramp_transaction(
                quote_id="quote_min",
                source_payment_method_id="bank_001",
                destination_payment_method_id="pm_002",
            )

        assert tx.transaction_id == "tx_min_001"
        assert tx.deposit_instructions is None


class TestConduitGetTransactionStatus:
    """Unit tests for transaction status polling."""

    @pytest.fixture()
    def svc(self):
        return ConduitOnrampService(
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True,
        )

    @pytest.mark.asyncio
    async def test_get_status_completed(self, svc):
        mock_response = {
            "id": "tx_001",
            "status": "completed",
            "completedAt": "2026-03-25T12:00:00Z",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            status = await svc.get_transaction_status("tx_001")

        assert isinstance(status, ConduitTransactionStatus)
        assert status.transaction_id == "tx_001"
        assert status.status == "completed"
        assert status.completed_at == "2026-03-25T12:00:00Z"

    @pytest.mark.asyncio
    async def test_get_status_pending(self, svc):
        mock_response = {
            "id": "tx_002",
            "status": "awaiting_funds",
        }
        with patch.object(svc, "_request", new_callable=AsyncMock, return_value=mock_response):
            status = await svc.get_transaction_status("tx_002")

        assert status.status == "awaiting_funds"
        assert status.completed_at is None


class TestConduitAPIError:
    """Test the ConduitAPIError class."""

    def test_error_attributes(self):
        err = ConduitAPIError(status_code=400, detail="Bad request")
        assert err.status_code == 400
        assert err.detail == "Bad request"
        assert "400" in str(err)
        assert "Bad request" in str(err)

    def test_error_inheritance(self):
        err = ConduitAPIError(status_code=500, detail="Server error")
        assert isinstance(err, Exception)


class TestGetConduitServiceFactory:
    """Test the get_conduit_service factory function."""

    def test_returns_none_when_no_env(self, monkeypatch):
        monkeypatch.delenv("CONDUIT_API_KEY", raising=False)
        monkeypatch.delenv("CONDUIT_API_SECRET", raising=False)
        assert get_conduit_service() is None

    def test_returns_none_when_only_key(self, monkeypatch):
        monkeypatch.setenv("CONDUIT_API_KEY", "test_key")
        monkeypatch.delenv("CONDUIT_API_SECRET", raising=False)
        assert get_conduit_service() is None

    def test_returns_service_sandbox(self, monkeypatch):
        monkeypatch.setenv("CONDUIT_API_KEY", "test_key")
        monkeypatch.setenv("CONDUIT_API_SECRET", "test_secret")
        monkeypatch.setenv("CONDUIT_SANDBOX", "true")
        svc = get_conduit_service()
        assert svc is not None
        assert svc.sandbox is True
        assert svc.base_url == SANDBOX_BASE_URL

    def test_returns_service_production(self, monkeypatch):
        monkeypatch.setenv("CONDUIT_API_KEY", "prod_key")
        monkeypatch.setenv("CONDUIT_API_SECRET", "prod_secret")
        monkeypatch.setenv("CONDUIT_SANDBOX", "false")
        svc = get_conduit_service()
        assert svc is not None
        assert svc.sandbox is False
        assert svc.base_url == PRODUCTION_BASE_URL


# ---------------------------------------------------------------------------
# Integration tests — Router endpoints (Conduit path)
# ---------------------------------------------------------------------------


class TestWalletFundConduitEndpoint:
    """Tests for ``POST /api/v2/wallets/{wallet_id}/fund`` with provider=conduit."""

    def test_fund_conduit_returns_503_when_not_configured(self, monkeypatch):
        """When Conduit env vars are missing, return 503."""
        monkeypatch.delenv("CONDUIT_API_KEY", raising=False)
        monkeypatch.delenv("CONDUIT_API_SECRET", raising=False)

        with patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_001/fund",
                json={"amount": "100", "currency": "USD", "provider": "conduit"},
            )
        assert resp.status_code == 503
        assert "Conduit onramp not configured" in resp.json()["detail"]

    def test_fund_conduit_requires_amount(self, monkeypatch):
        """Conduit requires an amount."""
        mock_conduit_svc = AsyncMock()

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_001/fund",
                json={"provider": "conduit"},
            )

        assert resp.status_code == 400
        assert "Amount is required" in resp.json()["detail"]

    def test_fund_conduit_quote_only(self, monkeypatch):
        """Without source payment method, only a quote is returned."""
        mock_quote = ConduitQuote(
            quote_id="quote_test_001",
            source_amount="100.00",
            source_asset="USD",
            target_amount="99.50",
            target_asset="USDC",
            target_network="tempo",
            expires_at="2026-03-25T12:00:00Z",
        )

        mock_conduit_svc = AsyncMock()
        mock_conduit_svc.get_quote.return_value = mock_quote

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_001/fund",
                json={
                    "amount": "100",
                    "currency": "USD",
                    "provider": "conduit",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "conduit"
        assert data["target_chain"] == "tempo"
        assert data["target_token"] == "USDC"
        assert data["quote_id"] == "quote_test_001"
        assert data["source_amount"] == "100.00"
        assert data["target_amount"] == "99.50"
        assert data["status"] == "quote_ready"
        assert data["widget_url"] == ""

    def test_fund_conduit_full_transaction(self, monkeypatch):
        """With source payment method, full transaction is executed."""
        mock_quote = ConduitQuote(
            quote_id="quote_full_001",
            source_amount="200.00",
            source_asset="USD",
            target_amount="199.00",
            target_asset="USDC",
            target_network="tempo",
            expires_at="2026-03-25T14:00:00Z",
        )

        mock_pm = ConduitPaymentMethod(
            payment_method_id="pm_dest_001",
            type="crypto_wallet",
            network="tempo",
            address="0xabcdef1234567890abcdef1234567890abcdef12",
        )

        mock_tx = ConduitTransaction(
            transaction_id="tx_conduit_001",
            quote_id="quote_full_001",
            status="awaiting_funds",
            source_amount="200.00",
            source_asset="USD",
            target_amount="199.00",
            target_asset="USDC",
            target_network="tempo",
            deposit_instructions={"status": "ready", "data": []},
            created_at="2026-03-25T14:01:00Z",
        )

        mock_conduit_svc = AsyncMock()
        mock_conduit_svc.get_quote.return_value = mock_quote
        mock_conduit_svc.create_wallet_payment_method.return_value = mock_pm
        mock_conduit_svc.create_onramp_transaction.return_value = mock_tx

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_001/fund",
                json={
                    "amount": "200",
                    "currency": "USD",
                    "provider": "conduit",
                    "conduit_customer_id": "cus_test",
                    "conduit_source_payment_method_id": "bank_src_001",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "conduit"
        assert data["transaction_id"] == "tx_conduit_001"
        assert data["status"] == "awaiting_funds"
        assert data["deposit_instructions"] is not None
        assert data["deposit_instructions"]["status"] == "ready"
        assert data["quote_id"] == "quote_full_001"

    def test_fund_conduit_custom_target_chain(self, monkeypatch):
        """target_chain parameter overrides default tempo."""
        mock_quote = ConduitQuote(
            quote_id="quote_base_001",
            source_amount="50.00",
            source_asset="USD",
            target_amount="49.75",
            target_asset="USDC",
            target_network="base",
            expires_at="2026-03-25T15:00:00Z",
        )

        mock_conduit_svc = AsyncMock()
        mock_conduit_svc.get_quote.return_value = mock_quote

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0x0000000000000000000000000000000000000001",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_002/fund",
                json={
                    "amount": "50",
                    "provider": "conduit",
                    "target_chain": "base",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["target_chain"] == "base"

    def test_fund_conduit_api_error(self, monkeypatch):
        """When Conduit API returns an error, return 502."""
        mock_conduit_svc = AsyncMock()
        mock_conduit_svc.get_quote.side_effect = ConduitAPIError(
            status_code=400, detail="Invalid amount"
        )

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0x0000000000000000000000000000000000000001",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_003/fund",
                json={"amount": "100", "provider": "conduit"},
            )

        assert resp.status_code == 502
        assert "Conduit API error" in resp.json()["detail"]


class TestWalletFundConduitStatusEndpoint:
    """Tests for GET /api/v2/wallets/{wallet_id}/fund/status/{session_id} with Conduit."""

    def test_conduit_status_success(self):
        mock_status = ConduitTransactionStatus(
            transaction_id="tx_conduit_check",
            status="completed",
            completed_at="2026-03-25T16:00:00Z",
        )
        mock_conduit_svc = AsyncMock()
        mock_conduit_svc.get_transaction_status.return_value = mock_status

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.get(
                "/api/v2/wallets/wal_test/fund/status/tx_conduit_check?provider=conduit"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction_id"] == "tx_conduit_check"
        assert data["status"] == "completed"
        assert data["wallet_id"] == "wal_test"

    def test_conduit_status_not_configured(self, monkeypatch):
        monkeypatch.delenv("CONDUIT_API_KEY", raising=False)
        monkeypatch.delenv("CONDUIT_API_SECRET", raising=False)

        app = _build_app()
        client = TestClient(app)
        resp = client.get(
            "/api/v2/wallets/wal_test/fund/status/tx_001?provider=conduit"
        )
        assert resp.status_code == 503

    def test_conduit_status_upstream_error(self):
        mock_conduit_svc = AsyncMock()
        mock_conduit_svc.get_transaction_status.side_effect = RuntimeError("Conduit down")

        with patch(
            "sardis.routes.wallets.onramp._get_conduit_onramp_service",
            return_value=mock_conduit_svc,
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.get(
                "/api/v2/wallets/wal_test/fund/status/tx_err?provider=conduit"
            )

        assert resp.status_code == 502


class TestExistingTurnkeyEndpointsStillWork:
    """Regression tests: ensure existing coinbase/moonpay paths are not broken."""

    def test_fund_coinbase_still_works(self, monkeypatch):
        """Coinbase via Turnkey path still works."""
        from sardis.services.turnkey_onramp import OnrampSession

        mock_session = OnrampSession(
            session_id="act_cb",
            onramp_url="https://onramp.example.com/cb",
            transaction_id="tx_cb",
            provider="coinbase",
            target_chain="base",
            target_token="USDC",
            wallet_address="0xabcdef1234567890abcdef1234567890abcdef12",
            amount_usd="100",
        )

        mock_svc = AsyncMock()
        mock_svc.create_onramp_session.return_value = mock_session

        with patch(
            "sardis.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test/fund",
                json={"amount": "100", "provider": "coinbase"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "coinbase"
        assert data["widget_url"] == "https://onramp.example.com/cb"

    def test_fund_moonpay_still_works(self, monkeypatch):
        """MoonPay via Turnkey path still works."""
        from sardis.services.turnkey_onramp import OnrampSession

        mock_session = OnrampSession(
            session_id="act_mp",
            onramp_url="https://onramp.example.com/mp",
            transaction_id="tx_mp",
            provider="moonpay",
            target_chain="ethereum",
            target_token="ETH",
            wallet_address="0x0000000000000000000000000000000000000001",
            amount_usd="50",
        )

        mock_svc = AsyncMock()
        mock_svc.create_onramp_session.return_value = mock_session

        with patch(
            "sardis.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ), patch(
            "sardis.routes.wallets.onramp._resolve_wallet_address",
            return_value="0x0000000000000000000000000000000000000001",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test/fund",
                json={
                    "amount": "50",
                    "provider": "moonpay",
                    "crypto_currency": "eth",
                    "network": "ethereum",
                },
            )

        assert resp.status_code == 201
        assert resp.json()["provider"] == "moonpay"

    def test_invalid_provider_rejected(self):
        """Invalid provider is rejected by Pydantic validation."""
        app = _build_app()
        client = TestClient(app)

        mock_svc = AsyncMock()
        with patch(
            "sardis.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ):
            resp = client.post(
                "/api/v2/wallets/wal_test/fund",
                json={"amount": "100", "provider": "stripe"},
            )
        assert resp.status_code == 422
