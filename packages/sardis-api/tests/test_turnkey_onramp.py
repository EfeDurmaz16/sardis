"""Tests for Turnkey native onramp service and wallet fund endpoints."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routes.wallets.onramp import router
from sardis_api.services.turnkey_onramp import (
    ACTIVITY_TYPE,
    CRYPTO_MAP,
    NETWORK_MAP,
    OnrampProvider,
    OnrampSession,
    OnrampTransactionStatus,
    TurnkeyOnrampService,
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
# Unit tests — TurnkeyOnrampService
# ---------------------------------------------------------------------------


class TestOnrampProvider:
    def test_coinbase_enum(self):
        p = OnrampProvider.coinbase
        assert p.turnkey_enum == "FIAT_ON_RAMP_PROVIDER_COINBASE"

    def test_moonpay_enum(self):
        p = OnrampProvider.moonpay
        assert p.turnkey_enum == "FIAT_ON_RAMP_PROVIDER_MOONPAY"


class TestNetworkAndCryptoMaps:
    def test_network_map_base(self):
        assert NETWORK_MAP["base"] == "BASE"

    def test_network_map_ethereum(self):
        assert NETWORK_MAP["ethereum"] == "ETHEREUM"

    def test_crypto_map_usdc(self):
        assert CRYPTO_MAP["usdc"] == "USDC"

    def test_crypto_map_eth(self):
        assert CRYPTO_MAP["eth"] == "ETH"


class TestTurnkeyOnrampServiceUnit:
    """Unit tests for TurnkeyOnrampService with mocked TurnkeyClient."""

    @pytest.fixture()
    def mock_client(self):
        client = AsyncMock()
        client.organization_id = "org_123"
        return client

    @pytest.fixture()
    def svc(self, mock_client):
        return TurnkeyOnrampService(turnkey_client=mock_client)

    @pytest.mark.asyncio
    async def test_create_session_coinbase(self, svc, mock_client):
        mock_client.post.return_value = {
            "activity": {
                "id": "act_abc",
                "result": {
                    "initFiatOnRampResult": {
                        "onRampUrl": "https://onramp.example.com/session/123",
                        "onRampTransactionId": "tx_onramp_001",
                    }
                },
            }
        }

        result = await svc.create_onramp_session(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            amount_usd="100",
            currency="USD",
            provider="coinbase",
            network="base",
            crypto_currency="usdc",
            sandbox=True,
        )

        assert isinstance(result, OnrampSession)
        assert result.session_id == "act_abc"
        assert result.onramp_url == "https://onramp.example.com/session/123"
        assert result.transaction_id == "tx_onramp_001"
        assert result.provider == "coinbase"
        assert result.target_chain == "base"
        assert result.target_token == "USDC"

        # Verify the Turnkey API call
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/public/v1/submit/init_fiat_on_ramp"
        body = call_args[0][1]
        assert body["type"] == ACTIVITY_TYPE
        assert body["organizationId"] == "org_123"
        params = body["parameters"]
        assert params["onrampProvider"] == "FIAT_ON_RAMP_PROVIDER_COINBASE"
        assert params["walletAddress"] == "0x1234567890abcdef1234567890abcdef12345678"
        assert params["network"] == "BASE"
        assert params["cryptoCurrencyCode"] == "USDC"
        assert params["fiatCurrencyAmount"] == "100"
        assert params["fiatCurrencyCode"] == "USD"
        assert params["sandboxMode"] is True

    @pytest.mark.asyncio
    async def test_create_session_moonpay(self, svc, mock_client):
        mock_client.post.return_value = {
            "activity": {
                "id": "act_moon",
                "result": {
                    "initFiatOnRampResult": {
                        "onRampUrl": "https://onramp.example.com/moonpay/456",
                        "onRampTransactionId": "tx_moon_002",
                    }
                },
            }
        }

        result = await svc.create_onramp_session(
            wallet_address="0xdeadbeef00000000000000000000000000000001",
            provider="moonpay",
            network="ethereum",
            crypto_currency="eth",
            sandbox=True,
        )

        assert result.provider == "moonpay"
        assert result.target_chain == "ethereum"
        assert result.target_token == "ETH"
        params = mock_client.post.call_args[0][1]["parameters"]
        assert params["onrampProvider"] == "FIAT_ON_RAMP_PROVIDER_MOONPAY"

    @pytest.mark.asyncio
    async def test_create_session_unsupported_provider(self, svc):
        with pytest.raises(ValueError, match="Unsupported onramp provider"):
            await svc.create_onramp_session(
                wallet_address="0x0000000000000000000000000000000000000001",
                provider="invalid_provider",
            )

    @pytest.mark.asyncio
    async def test_create_session_unsupported_network(self, svc):
        with pytest.raises(ValueError, match="Unsupported network"):
            await svc.create_onramp_session(
                wallet_address="0x0000000000000000000000000000000000000001",
                provider="coinbase",
                network="tempo",
            )

    @pytest.mark.asyncio
    async def test_create_session_unsupported_crypto(self, svc):
        with pytest.raises(ValueError, match="Unsupported crypto currency"):
            await svc.create_onramp_session(
                wallet_address="0x0000000000000000000000000000000000000001",
                provider="coinbase",
                crypto_currency="doge",
            )

    @pytest.mark.asyncio
    async def test_create_session_no_client(self):
        svc = TurnkeyOnrampService(turnkey_client=None)
        with pytest.raises(RuntimeError, match="Turnkey client not configured"):
            await svc.create_onramp_session(
                wallet_address="0x0000000000000000000000000000000000000001",
            )

    @pytest.mark.asyncio
    async def test_get_transaction_status(self, svc, mock_client):
        mock_client.post.return_value = {"transactionStatus": "completed"}

        result = await svc.get_transaction_status("tx_onramp_001")

        assert isinstance(result, OnrampTransactionStatus)
        assert result.transaction_id == "tx_onramp_001"
        assert result.status == "completed"

        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/public/v1/query/get_onramp_transaction_status"
        body = call_args[0][1]
        assert body["transactionId"] == "tx_onramp_001"
        assert body["organizationId"] == "org_123"

    @pytest.mark.asyncio
    async def test_get_transaction_status_with_refresh(self, svc, mock_client):
        mock_client.post.return_value = {"transactionStatus": "pending"}

        result = await svc.get_transaction_status("tx_002", refresh=True)
        body = mock_client.post.call_args[0][1]
        assert body["refresh"] is True
        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_get_status_no_client(self):
        svc = TurnkeyOnrampService(turnkey_client=None)
        with pytest.raises(RuntimeError, match="Turnkey client not configured"):
            await svc.get_transaction_status("tx_001")

    @pytest.mark.asyncio
    async def test_default_network_from_env(self, svc, mock_client, monkeypatch):
        monkeypatch.setenv("SARDIS_ONRAMP_DEFAULT_NETWORK", "ethereum")
        mock_client.post.return_value = {
            "activity": {
                "id": "act_eth",
                "result": {
                    "initFiatOnRampResult": {
                        "onRampUrl": "https://example.com/eth",
                        "onRampTransactionId": "tx_eth",
                    }
                },
            }
        }

        result = await svc.create_onramp_session(
            wallet_address="0x0000000000000000000000000000000000000001",
            provider="coinbase",
            sandbox=True,
        )
        assert result.target_chain == "ethereum"

    @pytest.mark.asyncio
    async def test_optional_amount_omitted(self, svc, mock_client):
        mock_client.post.return_value = {
            "activity": {
                "id": "act_noamount",
                "result": {
                    "initFiatOnRampResult": {
                        "onRampUrl": "https://example.com/noamt",
                        "onRampTransactionId": "tx_noamt",
                    }
                },
            }
        }

        await svc.create_onramp_session(
            wallet_address="0x0000000000000000000000000000000000000001",
            provider="coinbase",
            sandbox=True,
        )
        params = mock_client.post.call_args[0][1]["parameters"]
        assert "fiatCurrencyAmount" not in params

    @pytest.mark.asyncio
    async def test_country_code_params(self, svc, mock_client):
        mock_client.post.return_value = {
            "activity": {
                "id": "act_us",
                "result": {
                    "initFiatOnRampResult": {
                        "onRampUrl": "https://example.com/us",
                        "onRampTransactionId": "tx_us",
                    }
                },
            }
        }

        await svc.create_onramp_session(
            wallet_address="0x0000000000000000000000000000000000000001",
            provider="coinbase",
            country_code="US",
            country_subdivision_code="CA",
            sandbox=True,
        )
        params = mock_client.post.call_args[0][1]["parameters"]
        assert params["countryCode"] == "US"
        assert params["countrySubdivisionCode"] == "CA"


# ---------------------------------------------------------------------------
# Integration tests — Router endpoints
# ---------------------------------------------------------------------------


class TestWalletFundEndpoint:
    """Tests for ``POST /api/v2/wallets/{wallet_id}/fund``."""

    def test_fund_returns_503_when_turnkey_not_configured(self, monkeypatch):
        """When Turnkey env vars are missing, return 503."""
        monkeypatch.delenv("TURNKEY_API_KEY", raising=False)
        monkeypatch.delenv("TURNKEY_API_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("TURNKEY_API_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("TURNKEY_ORGANIZATION_ID", raising=False)

        with patch(
            "sardis_api.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_001/fund",
                json={"amount": "100", "currency": "USD", "provider": "coinbase"},
            )
        assert resp.status_code == 503
        assert "Turnkey onramp not configured" in resp.json()["detail"]

    def test_fund_success(self, monkeypatch):
        """Successful fund request with mocked TurnkeyOnrampService."""
        mock_session = OnrampSession(
            session_id="act_test",
            onramp_url="https://onramp.example.com/widget",
            transaction_id="tx_test",
            provider="coinbase",
            target_chain="base",
            target_token="USDC",
            wallet_address="0xabcdef1234567890abcdef1234567890abcdef12",
            amount_usd="100",
        )

        mock_svc = AsyncMock()
        mock_svc.create_onramp_session.return_value = mock_session

        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ), patch(
            "sardis_api.routes.wallets.onramp._resolve_wallet_address",
            return_value="0xabcdef1234567890abcdef1234567890abcdef12",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_001/fund",
                json={"amount": "100", "currency": "USD", "provider": "coinbase"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["session_id"] == "act_test"
        assert data["widget_url"] == "https://onramp.example.com/widget"
        assert data["transaction_id"] == "tx_test"
        assert data["provider"] == "coinbase"
        assert data["target_chain"] == "base"
        assert data["target_token"] == "USDC"
        assert data["wallet_id"] == "wal_test_001"
        assert data["status"] == "created"

    def test_fund_moonpay_provider(self, monkeypatch):
        """Fund with MoonPay provider."""
        mock_session = OnrampSession(
            session_id="act_moon",
            onramp_url="https://onramp.example.com/moonpay",
            transaction_id="tx_moon",
            provider="moonpay",
            target_chain="ethereum",
            target_token="ETH",
            wallet_address="0x0000000000000000000000000000000000000001",
            amount_usd="50",
        )

        mock_svc = AsyncMock()
        mock_svc.create_onramp_session.return_value = mock_session

        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ), patch(
            "sardis_api.routes.wallets.onramp._resolve_wallet_address",
            return_value="0x0000000000000000000000000000000000000001",
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_test_002/fund",
                json={
                    "amount": "50",
                    "currency": "EUR",
                    "provider": "moonpay",
                    "crypto_currency": "eth",
                    "network": "ethereum",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "moonpay"
        assert data["target_chain"] == "ethereum"

    def test_fund_wallet_not_found(self, monkeypatch):
        """When wallet address resolution fails, return 404."""
        mock_svc = AsyncMock()

        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ), patch(
            "sardis_api.routes.wallets.onramp._resolve_wallet_address",
            side_effect=ValueError("Wallet wal_gone not found"),
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.post(
                "/api/v2/wallets/wal_gone/fund",
                json={"amount": "100", "provider": "coinbase"},
            )

        assert resp.status_code == 404

    def test_fund_bad_provider_value(self):
        """Pydantic rejects invalid provider at the request validation level."""
        app = _build_app()
        client = TestClient(app)

        # Patch turnkey service so we don't get 503
        mock_svc = AsyncMock()
        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ):
            resp = client.post(
                "/api/v2/wallets/wal_test/fund",
                json={"amount": "100", "provider": "stripe"},
            )
        assert resp.status_code == 422  # Validation error


class TestWalletFundStatusEndpoint:
    """Tests for ``GET /api/v2/wallets/{wallet_id}/fund/status/{session_id}``."""

    def test_status_returns_503_when_turnkey_not_configured(self, monkeypatch):
        monkeypatch.delenv("TURNKEY_API_KEY", raising=False)
        monkeypatch.delenv("TURNKEY_API_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("TURNKEY_API_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("TURNKEY_ORGANIZATION_ID", raising=False)

        app = _build_app()
        client = TestClient(app)
        resp = client.get("/api/v2/wallets/wal_test/fund/status/tx_001")
        assert resp.status_code == 503

    def test_status_success(self):
        mock_status = OnrampTransactionStatus(
            transaction_id="tx_check",
            status="completed",
        )
        mock_svc = AsyncMock()
        mock_svc.get_transaction_status.return_value = mock_status

        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/api/v2/wallets/wal_test/fund/status/tx_check")

        assert resp.status_code == 200
        data = resp.json()
        assert data["transaction_id"] == "tx_check"
        assert data["status"] == "completed"
        assert data["wallet_id"] == "wal_test"
        assert data["session_id"] == "tx_check"

    def test_status_with_refresh_param(self):
        mock_status = OnrampTransactionStatus(
            transaction_id="tx_r",
            status="pending",
        )
        mock_svc = AsyncMock()
        mock_svc.get_transaction_status.return_value = mock_status

        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.get(
                "/api/v2/wallets/wal_test/fund/status/tx_r?refresh=true"
            )

        assert resp.status_code == 200
        mock_svc.get_transaction_status.assert_called_once_with(
            transaction_id="tx_r",
            refresh=True,
        )

    def test_status_upstream_error(self):
        mock_svc = AsyncMock()
        mock_svc.get_transaction_status.side_effect = RuntimeError("Turnkey down")

        with patch(
            "sardis_api.routes.wallets.onramp._get_turnkey_onramp_service",
            return_value=mock_svc,
        ):
            app = _build_app()
            client = TestClient(app)
            resp = client.get("/api/v2/wallets/wal_test/fund/status/tx_err")

        assert resp.status_code == 502


class TestLegacyOnrampEndpoint:
    """Ensure the original ``POST /onramp/session`` still works."""

    def test_legacy_coinbase_fallback(self, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        app = _build_app()
        client = TestClient(app)
        resp = client.post(
            "/api/v2/onramp/session",
            json={
                "wallet_address": "0x0000000000000000000000000000000000000001",
                "amount": "50",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "coinbase"
        assert data["session_id"].startswith("onramp_")
        assert "pay.coinbase.com" in data["url"]
