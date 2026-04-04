"""Tests for Batch Payment API (atomic multi-transfer via Tempo type 0x76).

Covers:
- Create batch with valid transfers -> 201 success
- Non-tempo chain -> 422
- Empty batch -> 422 (pydantic min_length=1)
- Batch exceeding max size -> 422 (pydantic max_length=50)
- Authentication required -> 401 without auth (non-anon mode)
- Mandate validation: active mandate not found -> 404
- Mandate validation: total exceeds per-tx limit -> 422
- Token not available on Tempo -> 422
"""
from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.batch_payments import (
    BatchPaymentRequest,
    BatchPaymentResponse,
    TransferItem,
    router,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_principal(**overrides) -> Principal:
    defaults = dict(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )
    defaults.update(overrides)
    return Principal(**defaults)


def _valid_batch_body(num_transfers: int = 2, chain: str = "tempo") -> dict:
    transfers = [
        {"to": f"0x{'ab' * 20}", "amount": "10.00", "token": "USDC"}
        for _ in range(num_transfers)
    ]
    return {"transfers": transfers, "chain": chain}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_principal():
    return _make_principal()


@pytest.fixture
def mock_tempo_executor():
    executor = AsyncMock()
    receipt = MagicMock()
    receipt.tx_hash = "0xdeadbeef1234567890"
    receipt.status = True
    executor.execute_batch_transfers = AsyncMock(return_value=receipt)
    return executor


@pytest.fixture
def mock_token_registry():
    """Mock TOKEN_REGISTRY so token lookup succeeds without real config."""
    token_meta = MagicMock()
    token_meta.contract_addresses = {"tempo": "0xUSDC_TEMPO_ADDR"}
    token_meta.to_raw_amount = MagicMock(side_effect=lambda d: int(d * 10**6))
    return {"USDC": token_meta}


@pytest.fixture
def app(mock_principal, mock_tempo_executor, mock_token_registry):
    app = FastAPI()

    async def override_principal():
        return mock_principal

    app.dependency_overrides[require_principal] = override_principal
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBatchPaymentValidation:
    def test_empty_batch_returns_422(self, client):
        body = {"transfers": [], "chain": "tempo"}
        resp = client.post("/payments/batch", json=body)
        assert resp.status_code == 422

    def test_batch_exceeding_max_returns_422(self, client):
        body = _valid_batch_body(num_transfers=51)
        resp = client.post("/payments/batch", json=body)
        assert resp.status_code == 422

    def test_non_tempo_chain_returns_422(self, client):
        body = _valid_batch_body(chain="base")
        resp = client.post("/payments/batch", json=body)
        assert resp.status_code == 422
        assert "Tempo" in resp.json()["detail"]

    def test_negative_amount_returns_422(self, client):
        body = {
            "transfers": [{"to": "0x" + "ab" * 20, "amount": "-5", "token": "USDC"}],
            "chain": "tempo",
        }
        resp = client.post("/payments/batch", json=body)
        assert resp.status_code == 422

    def test_zero_amount_returns_422(self, client):
        body = {
            "transfers": [{"to": "0x" + "ab" * 20, "amount": "0", "token": "USDC"}],
            "chain": "tempo",
        }
        resp = client.post("/payments/batch", json=body)
        assert resp.status_code == 422


class TestBatchPaymentSuccess:
    def test_valid_batch_returns_201(self, client, mock_tempo_executor, mock_token_registry):
        with patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body(num_transfers=3)
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 201
        data = resp.json()
        assert data["tx_hash"] == "0xdeadbeef1234567890"
        assert data["chain"] == "tempo"
        assert data["transfer_count"] == 3
        assert data["status"] == "confirmed"
        assert len(data["transfers"]) == 3
        for i, t in enumerate(data["transfers"]):
            assert t["index"] == i
            assert t["status"] == "included"
            assert t["token"] == "USDC"

    def test_single_transfer_batch_succeeds(self, client, mock_tempo_executor, mock_token_registry):
        with patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body(num_transfers=1)
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 201
        assert resp.json()["transfer_count"] == 1

    def test_max_size_batch_succeeds(self, client, mock_tempo_executor, mock_token_registry):
        with patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body(num_transfers=50)
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 201
        assert resp.json()["transfer_count"] == 50

    def test_failed_receipt_returns_failed_status(self, client, mock_tempo_executor, mock_token_registry):
        mock_tempo_executor.execute_batch_transfers.return_value.status = False
        with patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body(num_transfers=2)
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 201
        assert resp.json()["status"] == "failed"

    def test_total_amount_is_sum_of_transfers(self, client, mock_tempo_executor, mock_token_registry):
        with patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = {
                "transfers": [
                    {"to": "0x" + "ab" * 20, "amount": "25.50", "token": "USDC"},
                    {"to": "0x" + "cd" * 20, "amount": "14.50", "token": "USDC"},
                ],
                "chain": "tempo",
            }
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 201
        assert resp.json()["total_amount"] == "40.00"


class TestBatchPaymentTokenValidation:
    def test_token_not_on_tempo_returns_422(self, client):
        """PYUSD is a valid TokenType but may not have a Tempo address."""
        # Mock registry to return a token with no Tempo address
        token_meta = MagicMock()
        token_meta.contract_addresses = {}  # no tempo address
        mock_registry = {MagicMock(): token_meta}  # keyed by TokenType enum

        # Patch TOKEN_REGISTRY.get to always return token_meta (has no tempo addr)
        with patch("sardis_v2_core.tokens.TOKEN_REGISTRY") as mock_reg:
            mock_reg.get = MagicMock(return_value=token_meta)
            body = {
                "transfers": [{"to": "0x" + "ab" * 20, "amount": "10", "token": "USDC"}],
                "chain": "tempo",
            }
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 422
        assert "not available" in resp.json()["detail"]


class TestBatchPaymentMandateValidation:
    def _patch_inline_imports(self, mock_db, mock_tempo_executor, mock_token_registry):
        """Context manager stack for inline imports in batch_payment handler."""
        import contextlib
        import sys

        db_module = MagicMock()
        db_module.Database = mock_db

        tempo_module = MagicMock()
        tempo_module.TempoExecutor = MagicMock(return_value=mock_tempo_executor)

        tokens_module = sys.modules.get("sardis_v2_core.tokens")

        return contextlib.ExitStack()

    def test_mandate_not_found_returns_404(self, client, mock_tempo_executor, mock_token_registry):
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value=None)

        with patch("sardis_v2_core.database.Database", mock_db, create=True), \
             patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body()
            body["mandate_id"] = "mnd_nonexistent"
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 404
        assert "mandate" in resp.json()["detail"].lower()

    def test_mandate_exceeds_per_tx_limit_returns_422(self, client, mock_tempo_executor, mock_token_registry):
        mock_mandate = {"amount_per_tx": Decimal("5.00")}  # limit is 5, batch total = 20
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value=mock_mandate)

        with patch("sardis_v2_core.database.Database", mock_db, create=True), \
             patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body(num_transfers=2)  # 2 * 10 = 20 > 5
            body["mandate_id"] = "mnd_strict"
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 422
        assert "exceeds" in resp.json()["detail"].lower()

    def test_mandate_within_limit_succeeds(self, client, mock_tempo_executor, mock_token_registry):
        mock_mandate = {"amount_per_tx": Decimal("100.00")}
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value=mock_mandate)

        with patch("sardis_v2_core.database.Database", mock_db, create=True), \
             patch("sardis_chain.tempo.executor.TempoExecutor", return_value=mock_tempo_executor), \
             patch("sardis_v2_core.tokens.TOKEN_REGISTRY", mock_token_registry):
            body = _valid_batch_body(num_transfers=2)  # 2 * 10 = 20 <= 100
            body["mandate_id"] = "mnd_ok"
            resp = client.post("/payments/batch", json=body)

        assert resp.status_code == 201


class TestBatchPaymentAuth:
    def test_unauthenticated_request_returns_401(self):
        """When SARDIS_ALLOW_ANON is off, unauthenticated requests must be rejected."""
        os.environ["SARDIS_ALLOW_ANON"] = "0"
        os.environ["SARDIS_ENVIRONMENT"] = "production"

        app = FastAPI()
        app.include_router(router)
        c = TestClient(app, raise_server_exceptions=False)
        body = _valid_batch_body()
        resp = c.post("/payments/batch", json=body)
        # Either 401 or 403 is acceptable -- the point is it's not 2xx
        assert resp.status_code in (401, 403)

        # Restore
        os.environ["SARDIS_ALLOW_ANON"] = "1"
        os.environ["SARDIS_ENVIRONMENT"] = "dev"
