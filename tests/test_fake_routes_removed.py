"""Verify that formerly-fake API routers now return proper error codes.

These routers previously returned 200 with hardcoded fabricated data.
After remediation they must return:
- 501 Not Implemented for unimplemented integrations
- 503 Service Unavailable when a required module is missing
- 422 when chain mode prevents execution
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 1. Lightspark Grid — all endpoints → 501
# ---------------------------------------------------------------------------

class TestLightsparkGrid:
    @pytest.fixture
    def client(self):
        from sardis_api.routers.lightspark import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def test_create_uma_returns_501(self, client):
        resp = client.post("/grid/uma/create", json={
            "wallet_id": "w_1", "agent_id": "a_1",
        })
        assert resp.status_code == 501
        body = resp.json()["detail"]
        assert body["error"] == "not_implemented"
        assert "SARDIS_LIGHTSPARK_API_KEY" in body["message"]

    def test_get_uma_returns_501(self, client):
        resp = client.get("/grid/uma/w_1")
        assert resp.status_code == 501

    def test_send_uma_returns_501(self, client):
        resp = client.post("/grid/uma/send", json={
            "from_wallet_id": "w_1", "to_address": "$a@sardis.sh",
            "amount_cents": 100,
        })
        assert resp.status_code == 501

    def test_create_payout_returns_501(self, client):
        resp = client.post("/grid/payouts", json={
            "wallet_id": "w_1", "amount_cents": 1000,
        })
        assert resp.status_code == 501

    def test_fx_quote_returns_501(self, client):
        resp = client.post("/grid/fx/quote", json={
            "from_currency": "USD", "to_currency": "EUR", "amount_cents": 1000,
        })
        assert resp.status_code == 501

    def test_plaid_link_returns_501(self, client):
        resp = client.post("/grid/plaid/link-token", json={
            "customer_id": "cust_1",
        })
        assert resp.status_code == 501

    def test_webhook_returns_501(self, client):
        resp = client.post("/grid/webhooks", content=b'{}',
                           headers={"X-Grid-Signature": "abc123"})
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# 2. Striga — all endpoints → 501
# ---------------------------------------------------------------------------

class TestStriga:
    @pytest.fixture
    def client(self):
        from sardis_api.routers.striga import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def test_create_viban_returns_501(self, client):
        resp = client.post("/striga/vibans", json={
            "wallet_id": "w_1",
        })
        assert resp.status_code == 501
        body = resp.json()["detail"]
        assert body["error"] == "not_implemented"
        assert "SARDIS_STRIGA_API_KEY" in body["message"]

    def test_get_viban_returns_501(self, client):
        resp = client.get("/striga/vibans/w_1")
        assert resp.status_code == 501

    def test_create_card_returns_501(self, client):
        resp = client.post("/striga/cards", json={
            "wallet_id": "w_1",
        })
        assert resp.status_code == 501

    def test_sepa_payout_returns_501(self, client):
        resp = client.post("/striga/sepa/payout", json={
            "wallet_id": "w_1", "amount": 100.0, "iban": "DE89370400440532013000",
        })
        assert resp.status_code == 501

    def test_webhook_returns_501(self, client):
        resp = client.post("/striga/webhooks", content=b'{}',
                           headers={"X-Striga-Signature": "abc123"})
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# 3. Currency — all endpoints → 501
# ---------------------------------------------------------------------------

class TestCurrency:
    @pytest.fixture
    def client(self):
        from sardis_api.routers.currency import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def test_convert_returns_501(self, client):
        resp = client.post("/currency/convert", json={
            "from_currency": "USDC", "to_currency": "EUR", "amount_cents": 10000,
        })
        assert resp.status_code == 501
        body = resp.json()["detail"]
        assert body["error"] == "not_implemented"

    def test_balance_returns_501(self, client):
        resp = client.get("/currency/balance/w_1")
        assert resp.status_code == 501

    def test_rates_returns_501(self, client):
        """Previously returned fabricated rates like USD_EUR=0.92."""
        resp = client.get("/currency/rates")
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# 4. Fiat Rails — all endpoints → 501
# ---------------------------------------------------------------------------

class TestFiatRails:
    @pytest.fixture
    def client(self):
        from sardis_api.routers.fiat_rails import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app, raise_server_exceptions=False)

    def test_payout_returns_501(self, client):
        resp = client.post("/fiat-rails/payout", json={
            "wallet_id": "w_1", "amount_cents": 1000, "currency": "USD",
            "rail": "ach", "destination": {"account_id": "123"},
        })
        assert resp.status_code == 501
        body = resp.json()["detail"]
        assert body["error"] == "not_implemented"

    def test_quote_returns_501(self, client):
        """Previously returned hardcoded fee quotes."""
        resp = client.post("/fiat-rails/quote", json={
            "amount_cents": 1000, "currency": "USD", "rail": "ach",
        })
        assert resp.status_code == 501

    def test_list_rails_returns_501(self, client):
        """Previously returned a static list of rails."""
        resp = client.get("/fiat-rails/rails")
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# 5. Counterparties — trust profile → 501 (no real scoring)
# ---------------------------------------------------------------------------

class TestCounterpartyTrustProfile:
    @pytest.fixture
    def client(self):
        from sardis_api.routers.counterparties import router
        app = FastAPI()
        app.include_router(router, prefix="/api/v2/counterparties")

        from sardis_api.authz import Principal, require_principal
        app.dependency_overrides[require_principal] = lambda: Principal(
            kind="api_key",
            organization_id="test_org",
            scopes=["*"],
        )
        return TestClient(app, raise_server_exceptions=False)

    def test_trust_profile_returns_501_for_existing_counterparty(self, client):
        """Previously returned hardcoded trust scores (0.85/0.50/0.10)."""
        # Create a counterparty first
        create_resp = client.post("/api/v2/counterparties/", json={
            "name": "Test Vendor",
            "identifier": "0xabc",
            "trust_status": "approved",
        })
        assert create_resp.status_code == 201
        cpty_id = create_resp.json()["id"]

        # Trust profile should return 501
        resp = client.get(f"/api/v2/counterparties/{cpty_id}/trust-profile")
        assert resp.status_code == 501
        body = resp.json()["detail"]
        assert body["error"] == "not_implemented"
        assert "trust scoring" in body["message"].lower()

    def test_trust_profile_returns_404_for_missing_counterparty(self, client):
        resp = client.get("/api/v2/counterparties/cpty_nonexistent/trust-profile")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Ramp — bridge ImportError → 503, withdraw non-live → 422
# ---------------------------------------------------------------------------

class TestRampBridgeFallback:
    @pytest.fixture
    def mock_deps(self):
        wallet_repo = AsyncMock()
        wallet = MagicMock()
        wallet.wallet_id = "w_1"
        wallet.agent_id = "a_1"
        wallet.get_address.return_value = "0xabc123"
        wallet.addresses = {"base": "0xabc123", "tempo": "0xabc123"}
        wallet_repo.get.return_value = wallet

        agent_repo = AsyncMock()
        agent = MagicMock()
        agent.agent_id = "a_1"
        agent.owner_id = "org_demo"
        agent_repo.get.return_value = agent

        offramp_service = AsyncMock()

        from sardis_api.routers.ramp import RampDependencies
        return RampDependencies(
            wallet_repo=wallet_repo,
            agent_repo=agent_repo,
            offramp_service=offramp_service,
        )

    @pytest.fixture
    def client(self, mock_deps):
        from sardis_api.routers.ramp import get_deps
        from sardis_api.routers.ramp import router as ramp_router

        app = FastAPI()
        app.dependency_overrides[get_deps] = lambda: mock_deps

        from sardis_api.authz import Principal, require_principal
        app.dependency_overrides[require_principal] = lambda: Principal(
            kind="api_key",
            organization_id="org_demo",
            scopes=["*"],
        )

        app.include_router(ramp_router, prefix="/ramp")
        return TestClient(app, raise_server_exceptions=False)

    def test_bridge_returns_503_when_module_unavailable(self, client):
        """Previously returned fake 'queued' response on ImportError."""
        with patch.dict("sys.modules", {"sardis_chain": None, "sardis_chain.bridge": None}):
            resp = client.post("/ramp/bridge", json={
                "wallet_id": "w_1",
                "source_chain": "base",
                "destination_chain": "tempo",
                "amount": 100,
                "token": "USDC",
            })
            assert resp.status_code == 503
            body = resp.json()["detail"]
            assert body["error"] == "service_unavailable"
            assert "bridge" in body["message"].lower()

    def test_withdraw_crypto_returns_422_in_simulated_mode(self, client):
        """Previously returned fake 'pending' response in non-live mode."""
        import os
        os.environ["SARDIS_CHAIN_MODE"] = "simulated"

        resp = client.post("/ramp/withdraw-crypto", json={
            "wallet_id": "w_1",
            "destination_address": "0xdef456",
            "amount": 50,
            "chain": "tempo",
            "token": "USDC",
        })
        assert resp.status_code == 422
        body = resp.json()["detail"]
        assert body["error"] == "chain_mode_not_live"
        assert "SARDIS_CHAIN_MODE=live" in body["message"]
