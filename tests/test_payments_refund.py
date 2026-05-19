"""Tests for Refund API endpoints (full and partial refunds).

Covers:
- Full refund -> 201 success
- Partial refund -> 201 with correct amount
- Refund exceeding original amount -> 422
- Refund of already-refunded payment -> 409
- Payment not found -> 404
- Payment not completed -> 400
- Get refund status -> 200
- Get refund for non-existent payment -> 404
- Authentication required -> 401
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from server.authz import Principal, require_principal
from server.routes.money_movement.payments_refund import router
from sardis_v2_core.refund import Refund, RefundService, RefundStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_principal(**overrides) -> Principal:
    defaults = {
        "kind": "api_key",
        "organization_id": "org_test_001",
        "scopes": ["*"],
    }
    defaults.update(overrides)
    return Principal(**defaults)


def _make_refund(
    payment_id: str = "pay_001",
    amount: Decimal = Decimal("100.00"),
    status: RefundStatus = RefundStatus.COMPLETED,
    **kwargs,
) -> Refund:
    defaults = {
        "refund_id": "rfd_test001",
        "payment_id": payment_id,
        "org_id": "org_test_001",
        "amount": amount,
        "currency": "USDC",
        "reason": "Customer request",
        "status": status,
        "reverse_tx_hash": "0xsim_abc123",
        "error": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return Refund(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_principal():
    return _make_principal()


@pytest.fixture
def mock_refund_service():
    svc = AsyncMock(spec=RefundService)
    return svc


@pytest.fixture
def app(mock_principal, mock_refund_service):
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
# POST /{payment_id}/refund
# ---------------------------------------------------------------------------


class TestInitiateRefund:
    def _patch_refund_service(self, mock_svc):
        """Return a context manager that patches the RefundService constructor."""
        return patch(
            "sardis_v2_core.refund.RefundService",
            return_value=mock_svc,
        )

    def test_full_refund_returns_201(self, client, mock_refund_service):
        refund = _make_refund(amount=Decimal("100.00"))
        mock_refund_service.initiate_refund = AsyncMock(return_value=refund)

        with self._patch_refund_service(mock_refund_service):
            resp = client.post(
                "/pay_001/refund",
                json={"reason": "Customer request"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["refund_id"] == "rfd_test001"
        assert data["payment_id"] == "pay_001"
        assert data["amount"] == "100.00"
        assert data["status"] == "completed"
        assert data["reverse_tx_hash"] == "0xsim_abc123"
        assert data["error"] is None

    def test_partial_refund_returns_201(self, client, mock_refund_service):
        refund = _make_refund(amount=Decimal("30.00"))
        mock_refund_service.initiate_refund = AsyncMock(return_value=refund)

        with self._patch_refund_service(mock_refund_service):
            resp = client.post(
                "/pay_001/refund",
                json={"reason": "Partial return", "amount": "30.00"},
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == "30.00"

    def test_payment_not_found_returns_404(self, client, mock_refund_service):
        mock_refund_service.initiate_refund = AsyncMock(
            side_effect=ValueError("Payment pay_999 not found")
        )

        with self._patch_refund_service(mock_refund_service):
            resp = client.post(
                "/pay_999/refund",
                json={"reason": "Test"},
            )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_already_refunded_returns_409(self, client, mock_refund_service):
        mock_refund_service.initiate_refund = AsyncMock(
            side_effect=ValueError("Payment pay_001 has already been refunded")
        )

        with self._patch_refund_service(mock_refund_service):
            resp = client.post(
                "/pay_001/refund",
                json={"reason": "Double refund attempt"},
            )

        assert resp.status_code == 409
        assert "already been refunded" in resp.json()["detail"]

    def test_amount_exceeds_original_returns_422(self, client, mock_refund_service):
        mock_refund_service.initiate_refund = AsyncMock(
            side_effect=ValueError("Refund amount 500 exceeds original payment amount 100")
        )

        with self._patch_refund_service(mock_refund_service):
            resp = client.post(
                "/pay_001/refund",
                json={"reason": "Over-refund", "amount": "500.00"},
            )

        assert resp.status_code == 422
        assert "exceeds" in resp.json()["detail"]

    def test_payment_not_completed_returns_400(self, client, mock_refund_service):
        mock_refund_service.initiate_refund = AsyncMock(
            side_effect=ValueError("Payment pay_001 status is 'pending', only completed payments can be refunded")
        )

        with self._patch_refund_service(mock_refund_service):
            resp = client.post(
                "/pay_001/refund",
                json={"reason": "Premature refund"},
            )

        assert resp.status_code == 400

    def test_missing_reason_returns_422(self, client):
        """Pydantic requires 'reason' field with min_length=1."""
        resp = client.post("/pay_001/refund", json={})
        assert resp.status_code == 422

    def test_empty_reason_returns_422(self, client):
        resp = client.post("/pay_001/refund", json={"reason": ""})
        assert resp.status_code == 422

    def test_negative_amount_returns_422(self, client):
        resp = client.post(
            "/pay_001/refund",
            json={"reason": "test", "amount": "-10"},
        )
        assert resp.status_code == 422

    def test_zero_amount_returns_422(self, client):
        resp = client.post(
            "/pay_001/refund",
            json={"reason": "test", "amount": "0"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /{payment_id}/refund
# ---------------------------------------------------------------------------


class TestGetRefundStatus:
    def test_refund_found_returns_200(self, client, mock_refund_service):
        refund = _make_refund()
        mock_refund_service.get_refund = AsyncMock(return_value=refund)

        with patch("sardis_v2_core.refund.RefundService", return_value=mock_refund_service):
            resp = client.get("/pay_001/refund")

        assert resp.status_code == 200
        data = resp.json()
        assert data["refund_id"] == "rfd_test001"
        assert data["status"] == "completed"

    def test_refund_not_found_returns_404(self, client, mock_refund_service):
        mock_refund_service.get_refund = AsyncMock(return_value=None)

        with patch("sardis_v2_core.refund.RefundService", return_value=mock_refund_service):
            resp = client.get("/pay_999/refund")

        assert resp.status_code == 404
        assert "No refund found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestRefundAuth:
    def test_unauthenticated_request_returns_401(self):
        os.environ["SARDIS_ALLOW_ANON"] = "0"
        os.environ["SARDIS_ENVIRONMENT"] = "production"

        app = FastAPI()
        app.include_router(router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/pay_001/refund", json={"reason": "test"})
        assert resp.status_code in (401, 403)

        os.environ["SARDIS_ALLOW_ANON"] = "1"
        os.environ["SARDIS_ENVIRONMENT"] = "dev"
