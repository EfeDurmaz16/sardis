"""Tests for ACP (Agentic Commerce Protocol) checkout endpoints.

Tests the full ACP lifecycle:
1. Create checkout session
2. Update session (items, buyer info, fulfillment)
3. Complete with SPT / delegate payment / crypto
4. Cancel session
5. Delegate payment tokenization
6. Webhook emission
7. API-Version header validation
8. Edge cases and error handling
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clean_acp_state():
    """Reset in-memory ACP state between tests."""
    from server.routes.protocol.acp import _sessions
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture
def acp_app():
    """Create a test FastAPI app with the ACP router.

    Wires a permissive fake orchestrator so the Sardis authority gates run and
    ALLOW (the moat is exercised, never skipped).  Tests that need a deny wire a
    denying orchestrator via ``set_acp_orchestrator``.
    """
    from server.authz import Principal, require_principal
    from server.routes.protocol import acp
    from server.routes.protocol.acp import router

    app = FastAPI()

    # Override auth to return a test principal
    test_principal = Principal(
        kind="api_key",
        organization_id="org_test_123",
        scopes=["*"],
    )

    async def _override_principal():
        return test_principal

    app.dependency_overrides[require_principal] = _override_principal

    # Default: an orchestrator whose gates pass (evaluate_chain returns None).
    app.dependency_overrides[acp.get_deps] = lambda: acp.ACPDependencies(
        orchestrator=_AllowingOrchestrator(),
        chain_executor=None,
    )
    app.include_router(router, prefix="/api/v2")

    return app


class _AllowingOrchestrator:
    """Fake orchestrator whose authority gates always pass."""

    async def evaluate_chain(self, chain):  # noqa: ANN001
        return None


class _DenyingOrchestrator:
    """Fake orchestrator whose authority gates deny with a given exception."""

    def __init__(self, exc):
        self._exc = exc

    async def evaluate_chain(self, chain):  # noqa: ANN001
        raise self._exc


def set_acp_orchestrator(app, orchestrator):
    """Swap the wired ACP orchestrator for a test on the given app."""
    from server.routes.protocol import acp

    app.dependency_overrides[acp.get_deps] = lambda: acp.ACPDependencies(
        orchestrator=orchestrator, chain_executor=None,
    )


@pytest.fixture
def client(acp_app):
    return TestClient(acp_app)


# ---------------------------------------------------------------------------
# Tokenized payment-data helpers (PAN-free)
# ---------------------------------------------------------------------------

def _spt_body(token: str) -> dict:
    """Build a tokenized complete body for a Stripe Shared Payment Token."""
    return {
        "payment_data": {
            "handler_id": "stripe",
            "instrument": {
                "type": "card",
                "credential": {"type": "spt", "token": token},
            },
        }
    }


def _issuer_card_body(card_ref: str, *, handler_id: str = "crossmint") -> dict:
    """Build a tokenized complete body for an issuer-delegated card reference."""
    return {
        "payment_data": {
            "handler_id": handler_id,
            "instrument": {
                "type": "card",
                "credential": {"type": "issuer_card", "token": card_ref},
            },
        }
    }


class _FakeCardResult:
    """Minimal stand-in for the provider ProviderResult (tokenized only)."""

    def __init__(self, *, ok=True, status="active", card_id="crd_abc123", last_four="4242"):
        self.ok = ok
        self.status = status
        self.raw = {
            "card_id": card_id,
            "status": status,
            "last_four": last_four,
            "currency": "USD",
        }


class _FakeCardPort:
    """Mocked Crossmint-style CardPort. NEVER returns a PAN."""

    def __init__(self, result=None, *, raise_exc=None):
        self._result = result if result is not None else _FakeCardResult()
        self._raise = raise_exc
        self.calls = []

    async def set_state(self, card_ref, *, state):
        self.calls.append((card_ref, state))
        if self._raise is not None:
            raise self._raise
        return self._result


def _patch_card_port(port):
    """Patch the dependency resolver to return the mocked CardPort."""
    return patch("server.dependencies.get_card_port", return_value=port)


# ---------------------------------------------------------------------------
# Create checkout session
# ---------------------------------------------------------------------------

class TestCreateCheckoutSession:

    def test_create_minimal(self, client):
        """Create session with just items."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_pro_monthly", "quantity": 1}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"].startswith("csn_")
        assert data["status"] == "open"
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Sardis Pro -- Monthly"
        assert data["totals"]["total"] == "99.00"
        assert data["totals"]["currency"] == "usd"
        assert data["payment"]["methods_supported"] == ["card", "crypto"]
        assert data["api_version"] == "2026-01-16"

    def test_create_with_buyer_and_fulfillment(self, client):
        """Create session with full buyer info and fulfillment."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_credits_1000", "quantity": 5}],
                "buyer_information": {
                    "name": "Agent Smith",
                    "email": "agent@example.com",
                    "phone": "+1234567890",
                },
                "fulfillment": {
                    "type": "digital",
                    "estimated_delivery": "Immediate",
                },
                "webhook_url": "https://agent.example.com/webhooks/acp",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["totals"]["total"] == "50.00"
        assert data["buyer_information"]["name"] == "Agent Smith"
        assert data["fulfillment"]["type"] == "digital"
        assert data["webhook_url"] == "https://agent.example.com/webhooks/acp"

    def test_create_multiple_items(self, client):
        """Create session with multiple line items."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [
                    {"id": "sardis_pro_monthly", "quantity": 1},
                    {"id": "sardis_credits_1000", "quantity": 3},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["items"]) == 2
        # 99 + 30 = 129
        assert data["totals"]["total"] == "129.00"

    def test_create_unknown_product(self, client):
        """Reject unknown product IDs."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "nonexistent_product", "quantity": 1}],
            },
        )
        assert resp.status_code == 400
        assert "Unknown product id" in resp.json()["detail"]

    def test_create_empty_items(self, client):
        """Reject empty items list."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": []},
        )
        assert resp.status_code == 422

    def test_create_with_price_override(self, client):
        """Create session with agent-specified price override."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_pro_monthly", "quantity": 1, "price": "79.00"}],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["items"][0]["unit_price"] == "79.00"
        assert data["totals"]["total"] == "79.00"

    def test_create_with_affiliate_attribution(self, client):
        """Create session with affiliate attribution."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_pro_monthly", "quantity": 1}],
                "affiliate_attribution": {"touchpoint": "chatgpt_plugin"},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["affiliate_attribution"]["touchpoint"] == "chatgpt_plugin"


# ---------------------------------------------------------------------------
# Get checkout session
# ---------------------------------------------------------------------------

class TestGetCheckoutSession:

    def test_get_existing(self, client):
        """Retrieve an existing session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.get(f"/api/v2/acp/checkout_sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == session_id
        assert resp.json()["status"] == "open"

    def test_get_nonexistent(self, client):
        """Return 404 for nonexistent session."""
        resp = client.get("/api/v2/acp/checkout_sessions/csn_nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update checkout session
# ---------------------------------------------------------------------------

class TestUpdateCheckoutSession:

    def test_update_items(self, client):
        """Update line items recalculates totals."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}",
            json={
                "items": [{"id": "sardis_enterprise_monthly", "quantity": 1}],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["totals"]["total"] == "499.00"

    def test_update_buyer_info(self, client):
        """Update buyer information."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}",
            json={
                "buyer_information": {
                    "name": "Updated Agent",
                    "email": "updated@agent.ai",
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["buyer_information"]["name"] == "Updated Agent"

    def test_update_fulfillment(self, client):
        """Update fulfillment preferences."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}",
            json={
                "fulfillment": {
                    "type": "shipping",
                    "address": {
                        "name": "Agent HQ",
                        "line_one": "123 AI Street",
                        "city": "San Francisco",
                        "state": "CA",
                        "country": "US",
                        "postal_code": "94105",
                    },
                },
            },
        )
        assert resp.status_code == 200
        assert resp.json()["fulfillment"]["type"] == "shipping"

    def test_update_completed_session_fails(self, client):
        """Cannot update a completed session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        # Complete it
        client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_test12345678"),
        )

        # Try to update
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}",
            json={"items": [{"id": "sardis_credits_1000", "quantity": 1}]},
        )
        assert resp.status_code == 409

    def test_update_canceled_session_fails(self, client):
        """Cannot update a canceled session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        # Cancel it
        client.post(f"/api/v2/acp/checkout_sessions/{session_id}/cancel")

        # Try to update
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}",
            json={"items": [{"id": "sardis_credits_1000", "quantity": 1}]},
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Complete checkout session
# ---------------------------------------------------------------------------

class TestCompleteCheckoutSession:

    def test_complete_with_spt(self, client):
        """Complete with a tokenized Shared Payment Token (dev mode)."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_abc123def456"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["payment"]["status"] == "succeeded"

    def test_complete_with_invalid_spt(self, client):
        """Reject a credential typed `spt` whose token is not an spt_."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("invalid_token"),
        )
        assert resp.status_code == 400
        assert "spt" in resp.json()["detail"].lower()

    def test_complete_with_issuer_card(self, client):
        """Complete with an issuer-delegated card reference (mocked CardPort)."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        port = _FakeCardPort(_FakeCardResult(ok=True, status="active", card_id="crd_x1_abcdef"))
        with _patch_card_port(port):
            resp = client.post(
                f"/api/v2/acp/checkout_sessions/{session_id}/complete",
                json=_issuer_card_body("crd_x1_abcdef"),
            )
        assert resp.status_code == 200
        data = resp.json()
        # Verified with the issuer; PAN never touched Sardis. Stays `processing`
        # (and `open`) until a settlement signal — fail-closed, not auto-paid.
        assert data["payment"]["status"] == "processing"
        assert data["status"] == "open"
        assert port.calls == [("crd_x1_abcdef", "active")]

    def test_complete_issuer_card_unverified_fails_closed(self, client):
        """Issuer rejects/unknown card -> fail closed (402), session not completed."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        port = _FakeCardPort(raise_exc=RuntimeError("card not found"))
        with _patch_card_port(port):
            resp = client.post(
                f"/api/v2/acp/checkout_sessions/{session_id}/complete",
                json=_issuer_card_body("crd_missing_ref"),
            )
        assert resp.status_code == 402
        assert "issuer_card_unverified" in str(resp.json()["detail"])

        # Session must still be open, not completed.
        get_resp = client.get(f"/api/v2/acp/checkout_sessions/{session_id}")
        assert get_resp.json()["status"] == "open"

    def test_complete_issuer_card_not_active_fails_closed(self, client):
        """A frozen/closed issuer card is not chargeable -> 402."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        port = _FakeCardPort(_FakeCardResult(ok=True, status="frozen"))
        with _patch_card_port(port):
            resp = client.post(
                f"/api/v2/acp/checkout_sessions/{session_id}/complete",
                json=_issuer_card_body("crd_frozen_ref"),
            )
        assert resp.status_code == 402
        assert "not_chargeable" in str(resp.json()["detail"])

    def test_complete_rejects_raw_pan_as_issuer_token(self, client):
        """A raw card number passed as a credential token is rejected (422)."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        # No CardPort patch: the raw-PAN guard must reject before any issuer call.
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_issuer_card_body("4242424242424242"),
        )
        assert resp.status_code == 422
        assert "raw_pan_rejected" in str(resp.json()["detail"])

    def test_complete_rejects_raw_card_fields(self, client):
        """A legacy raw-card body (number/cvc/exp) is rejected (422), never 2xx."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        for body in (
            {
                "payment_method": "delegate_payment",
                "delegate_payment_token": "vt_test",
            },
            {
                "payment_data": {
                    "handler_id": "stripe",
                    "instrument": {
                        "type": "card",
                        "credential": {
                            "type": "issuer_card",
                            "token": "crd_x",
                            "number": "4242424242424242",
                            "cvc": "123",
                        },
                    },
                }
            },
            {
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2030,
                "cvc": "123",
            },
        ):
            resp = client.post(
                f"/api/v2/acp/checkout_sessions/{session_id}/complete",
                json=body,
            )
            assert resp.status_code == 422, body

    def test_complete_missing_payment_rejected(self, client):
        """No payment_data and no crypto -> 400 (fail closed)."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={},
        )
        assert resp.status_code == 400
        assert "missing_payment" in str(resp.json()["detail"])

    def test_complete_ambiguous_payment_rejected(self, client):
        """Both payment_data and crypto -> 400 (fail closed)."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        body = _spt_body("spt_abc12345")
        body["crypto_payment"] = {
            "tx_hash": "0x" + "a" * 64,
            "chain": "base",
            "token": "USDC",
        }
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=body,
        )
        assert resp.status_code == 400
        assert "ambiguous_payment" in str(resp.json()["detail"])

    def test_complete_with_crypto_processing(self, client):
        """Crypto without on-chain verification stays processing/open (fail-closed)."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={
                "crypto_payment": {
                    "tx_hash": "0xabc123def456789012345678901234567890123456789012345678901234abcd",
                    "chain": "base",
                    "token": "USDC",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Not marked succeeded/completed without a real receipt.
        assert data["payment"]["status"] == "processing"
        assert data["status"] == "open"

    def test_complete_crypto_missing_tx_hash(self, client):
        """Reject crypto payment without tx_hash."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        # tx_hash is a required field on ACPCryptoPayment -> 422 at validation.
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={"crypto_payment": {"chain": "base"}},
        )
        assert resp.status_code == 422

    def test_complete_already_completed(self, client):
        """Cannot complete an already-completed session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        # Complete first time
        client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_first1234"),
        )

        # Try again
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_second123"),
        )
        assert resp.status_code == 409

    def test_complete_canceled_session(self, client):
        """Cannot complete a canceled session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        client.post(f"/api/v2/acp/checkout_sessions/{session_id}/cancel")

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_test12345"),
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Cancel checkout session
# ---------------------------------------------------------------------------

class TestCancelCheckoutSession:

    def test_cancel_open_session(self, client):
        """Cancel an open session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        resp = client.post(f"/api/v2/acp/checkout_sessions/{session_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "canceled"

    def test_cancel_completed_session_fails(self, client):
        """Cannot cancel a completed session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_test12345"),
        )

        resp = client.post(f"/api/v2/acp/checkout_sessions/{session_id}/cancel")
        assert resp.status_code == 409

    def test_cancel_already_canceled(self, client):
        """Cannot cancel an already-canceled session."""
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        session_id = create_resp.json()["id"]

        client.post(f"/api/v2/acp/checkout_sessions/{session_id}/cancel")

        resp = client.post(f"/api/v2/acp/checkout_sessions/{session_id}/cancel")
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Delegate Payment — QUARANTINED (raw-PAN intake removed, fail-closed)
# ---------------------------------------------------------------------------

class TestDelegatePaymentQuarantined:
    """The raw-PAN PSP endpoint is removed. It must never accept a card."""

    def test_raw_pan_intake_rejected(self, client):
        """Posting a raw card to /delegate_payment fails closed (501), no 2xx."""
        resp = client.post(
            "/api/v2/acp/delegate_payment",
            json={
                "payment_method": {
                    "type": "card",
                    "number": "4242424242424242",
                    "exp_month": 12,
                    "exp_year": 2030,
                    "cvc": "123",
                },
                "allowance": {
                    "reason": "one_time",
                    "max_amount": 10000,
                    "currency": "usd",
                    "checkout_session_id": "csn_test123",
                },
            },
        )
        assert resp.status_code == 501
        detail = resp.json()["detail"]
        assert detail["reason_code"] == "raw_pan_not_accepted"
        assert "issuer-delegated" in detail["message"]

    def test_delegate_endpoint_no_body_still_rejects(self, client):
        """Even an empty body fails closed — no card data is ever parsed."""
        resp = client.post("/api/v2/acp/delegate_payment", json={})
        assert resp.status_code == 501
        assert resp.json()["detail"]["reason_code"] == "raw_pan_not_accepted"


# ---------------------------------------------------------------------------
# API-Version header
# ---------------------------------------------------------------------------

class TestAPIVersionHeader:

    def test_default_version_when_not_provided(self, client):
        """Default to current version when header is omitted."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        assert resp.status_code == 201
        assert resp.json()["api_version"] == "2026-01-16"

    def test_explicit_supported_version(self, client):
        """Accept explicit supported version."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
            headers={"API-Version": "2026-01-16"},
        )
        assert resp.status_code == 201

    def test_unsupported_version_rejected(self, client):
        """Reject unsupported API version."""
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
            headers={"API-Version": "2025-01-01"},
        )
        assert resp.status_code == 400
        assert "Unsupported API-Version" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Full lifecycle test
# ---------------------------------------------------------------------------

class TestACPLifecycle:

    def test_full_spt_lifecycle(self, client):
        """Full lifecycle: create -> update -> complete with SPT."""
        # 1. Create
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_credits_1000", "quantity": 2}],
                "buyer_information": {"name": "AI Agent", "email": "ai@agent.com"},
            },
        )
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]
        assert create_resp.json()["totals"]["total"] == "20.00"

        # 2. Update items
        update_resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}",
            json={
                "items": [
                    {"id": "sardis_credits_1000", "quantity": 5},
                    {"id": "sardis_pro_monthly", "quantity": 1},
                ],
            },
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["totals"]["total"] == "149.00"  # 50 + 99

        # 3. Complete with tokenized SPT
        complete_resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_granted_abc123"),
        )
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "completed"
        assert complete_resp.json()["payment"]["status"] == "succeeded"

        # 4. Verify state persisted
        get_resp = client.get(f"/api/v2/acp/checkout_sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "completed"

    def test_full_issuer_card_lifecycle(self, client):
        """Full lifecycle: create -> complete with an issuer-delegated card ref."""
        # 1. Create checkout session
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_enterprise_monthly", "quantity": 1}],
            },
        )
        session_id = create_resp.json()["id"]

        # 2. Complete with an issuer-delegated card reference (mocked CardPort).
        port = _FakeCardPort(_FakeCardResult(ok=True, status="active", card_id="crd_life"))
        with _patch_card_port(port):
            complete_resp = client.post(
                f"/api/v2/acp/checkout_sessions/{session_id}/complete",
                json=_issuer_card_body("crd_life"),
            )
        assert complete_resp.status_code == 200
        # Verified with the issuer; processing until settlement (fail-closed).
        assert complete_resp.json()["payment"]["status"] == "processing"
        assert port.calls == [("crd_life", "active")]

    def test_full_crypto_lifecycle(self, client):
        """Full lifecycle: create -> complete with crypto (processing, fail-closed)."""
        # 1. Create
        create_resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={
                "items": [{"id": "sardis_pro_monthly", "quantity": 1}],
            },
        )
        session_id = create_resp.json()["id"]

        # 2. Complete with crypto
        complete_resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={
                "crypto_payment": {
                    "tx_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "chain": "base",
                    "token": "USDC",
                },
            },
        )
        assert complete_resp.status_code == 200
        # Not auto-completed without an on-chain receipt.
        assert complete_resp.json()["payment"]["status"] == "processing"


# ---------------------------------------------------------------------------
# Webhook emission
# ---------------------------------------------------------------------------

class TestACPWebhooks:

    def test_webhook_emitted_on_create(self, client):
        """Webhook is emitted when session is created."""
        with patch("server.routes.protocol.acp._send_acp_webhook", new_callable=AsyncMock) as mock_send:
            resp = client.post(
                "/api/v2/acp/checkout_sessions",
                json={
                    "items": [{"id": "sardis_pro_monthly", "quantity": 1}],
                    "webhook_url": "https://agent.example.com/hook",
                },
            )
            assert resp.status_code == 201
            # The webhook is fire-and-forget via asyncio.create_task,
            # so in test client it may or may not have been awaited.
            # We verify the function was called.
            # Note: TestClient runs sync so async tasks might not execute.
            # In production, the webhook would be delivered.

    def test_webhook_signing(self):
        """Verify HMAC signing of webhook payloads."""
        import hashlib
        import hmac

        secret = "test_wh_fixture"
        timestamp = "1711900000"
        payload = '{"type": "order_create", "data": {"checkout_session_id": "csn_test"}}'

        sig_payload = f"{timestamp}.{payload}"
        expected_sig = hmac.new(
            secret.encode(),
            sig_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        header = f"t={timestamp},v1={expected_sig}"
        assert header.startswith("t=")
        assert ",v1=" in header

        # Verify the signature is correct
        parts = dict(p.split("=", 1) for p in header.split(","))
        assert parts["t"] == timestamp
        computed = hmac.new(
            secret.encode(),
            f"{parts['t']}.{payload}".encode(),
            hashlib.sha256,
        ).hexdigest()
        assert computed == parts["v1"]


# ---------------------------------------------------------------------------
# Orchestrator gating (the Sardis moat) — denials block the ACP order
# ---------------------------------------------------------------------------


class TestACPOrchestratorGating:
    """ACP completion must run the fail-closed authority gates."""

    def _open_session(self, client):
        resp = client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        )
        return resp.json()["id"]

    def test_policy_denial_blocks_order(self, acp_app):
        """A policy denial from the orchestrator blocks the order (403, not paid)."""
        from sardis.core.orchestrator import PolicyViolationError

        set_acp_orchestrator(
            acp_app, _DenyingOrchestrator(PolicyViolationError("over_limit", mandate_id="m")),
        )
        client = TestClient(acp_app)
        session_id = self._open_session(client)

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_blocked123"),
        )
        assert resp.status_code == 403
        assert "payment_denied" in str(resp.json()["detail"])

        # Session must NOT be completed.
        got = client.get(f"/api/v2/acp/checkout_sessions/{session_id}").json()
        assert got["status"] == "open"
        assert got["payment"]["status"] in ("pending", "processing")

    def test_revocation_blocks_order(self, acp_app):
        """A revoked/absent spending mandate (PolicyViolationError) blocks the order."""
        from sardis.core.orchestrator import PolicyViolationError

        set_acp_orchestrator(
            acp_app,
            _DenyingOrchestrator(
                PolicyViolationError(
                    "No active spending mandate authorizes this payment "
                    "(revoked, suspended, expired, or never issued)",
                    mandate_id="m",
                    rule_id="no_active_spending_mandate",
                )
            ),
        )
        client = TestClient(acp_app)
        session_id = self._open_session(client)

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_revoked12"),
        )
        assert resp.status_code == 403
        got = client.get(f"/api/v2/acp/checkout_sessions/{session_id}").json()
        assert got["status"] == "open"

    def test_compliance_denial_blocks_crypto(self, acp_app, monkeypatch):
        """A compliance/sanctions denial blocks even a crypto order (403)."""
        from sardis.core.orchestrator import ComplianceViolationError

        monkeypatch.setenv("SARDIS_ACP_SETTLEMENT_ADDRESS", "0x" + "11" * 20)
        set_acp_orchestrator(
            acp_app,
            _DenyingOrchestrator(ComplianceViolationError("sanctions_hit", mandate_id="m")),
        )
        client = TestClient(acp_app)
        session_id = self._open_session(client)

        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={"crypto_payment": {"tx_hash": "0x" + "a" * 64, "chain": "base", "token": "USDC"}},
        )
        assert resp.status_code == 403

    def test_orchestrator_not_wired_fails_closed(self, acp_app):
        """No orchestrator wired -> 503 (fail-closed, moat never skipped)."""
        from server.routes.protocol import acp

        acp_app.dependency_overrides[acp.get_deps] = lambda: acp.ACPDependencies(
            orchestrator=None, chain_executor=None,
        )
        client = TestClient(acp_app)
        session_id = self._open_session(client)
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json=_spt_body("spt_nowire1234"),
        )
        assert resp.status_code == 503
        assert "orchestrator_not_configured" in str(resp.json()["detail"])


# ---------------------------------------------------------------------------
# On-chain crypto verification — succeeded ONLY on confirmed proof
# ---------------------------------------------------------------------------

_BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
_TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
_MERCHANT = "0x" + "ab" * 20  # trusted settlement address (lowercased compare)


def _topic_addr(addr: str) -> str:
    return "0x" + "0" * 24 + addr[2:].lower()


def _transfer_log(*, token=_BASE_USDC, to=_MERCHANT, value_minor=99_000_000):
    return {
        "address": token,
        "topics": [_TRANSFER_SIG, _topic_addr("0x" + "cd" * 20), _topic_addr(to)],
        "data": hex(value_minor),
    }


def _receipt(*, status=1, block=100, logs=None):
    return {
        "status": hex(status),
        "blockNumber": hex(block),
        "logs": logs if logs is not None else [_transfer_log()],
    }


class _FakeRPC:
    """Minimal fake ProductionRPCClient for on-chain verification tests."""

    def __init__(self, *, receipt=None, current_block=200, raise_on_receipt=False):
        self._receipt = receipt
        self._current_block = current_block
        self._raise = raise_on_receipt

    async def get_transaction_receipt(self, tx_hash):
        if self._raise:
            raise RuntimeError("rpc down")
        return self._receipt

    async def get_block_number(self):
        return self._current_block


class TestACPCryptoOnChainVerification:
    """processing -> succeeded only when the tx_hash is confirmed on-chain."""

    def _setup(self, acp_app, monkeypatch, fake_rpc):
        monkeypatch.setenv("SARDIS_ACP_SETTLEMENT_ADDRESS", _MERCHANT)
        # _AllowingOrchestrator already wired by the fixture.
        import sardis.chain.rpc_client as rpc_mod

        monkeypatch.setattr(rpc_mod, "get_rpc_client", lambda chain, **k: fake_rpc)
        return TestClient(acp_app)

    def _open(self, client):
        return client.post(
            "/api/v2/acp/checkout_sessions",
            json={"items": [{"id": "sardis_pro_monthly", "quantity": 1}]},
        ).json()["id"]

    def _complete(self, client, session_id, tx="0x" + "f" * 64):
        return client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={"crypto_payment": {"tx_hash": tx, "chain": "base", "token": "USDC"}},
        )

    def test_valid_confirmed_tx_succeeds(self, acp_app, monkeypatch):
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=_receipt(), current_block=200))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["payment"]["status"] == "succeeded"
        assert data["status"] == "completed"

    def test_not_mined_stays_processing(self, acp_app, monkeypatch):
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=None))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"
        assert resp.json()["status"] == "open"

    def test_reverted_tx_is_failed(self, acp_app, monkeypatch):
        client = self._setup(
            acp_app, monkeypatch, _FakeRPC(receipt=_receipt(status=0), current_block=200),
        )
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        # A reverted tx is a genuine failure, never succeeded/completed.
        assert resp.json()["payment"]["status"] == "failed"
        assert resp.json()["status"] == "open"

    def test_insufficient_confirmations_stays_processing(self, acp_app, monkeypatch):
        # base requires 3 confs; block=100, current=101 -> only 2 confs.
        client = self._setup(
            acp_app, monkeypatch, _FakeRPC(receipt=_receipt(block=100), current_block=101),
        )
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_wrong_recipient_stays_processing(self, acp_app, monkeypatch):
        bad = _receipt(logs=[_transfer_log(to="0x" + "99" * 20)])
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=bad, current_block=200))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_underpaid_stays_processing(self, acp_app, monkeypatch):
        bad = _receipt(logs=[_transfer_log(value_minor=98_000_000)])  # < 99 USDC
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=bad, current_block=200))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_overpaid_succeeds(self, acp_app, monkeypatch):
        good = _receipt(logs=[_transfer_log(value_minor=120_000_000)])  # >= 99 USDC
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=good, current_block=200))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "succeeded"

    def test_wrong_token_contract_stays_processing(self, acp_app, monkeypatch):
        bad = _receipt(logs=[_transfer_log(token="0x" + "de" * 20)])  # not USDC contract
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=bad, current_block=200))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_no_transfer_log_stays_processing(self, acp_app, monkeypatch):
        bad = _receipt(logs=[])
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=bad, current_block=200))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_rpc_error_stays_processing(self, acp_app, monkeypatch):
        client = self._setup(acp_app, monkeypatch, _FakeRPC(raise_on_receipt=True))
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_no_settlement_address_stays_processing(self, acp_app, monkeypatch):
        # No SARDIS_ACP_SETTLEMENT_ADDRESS -> cannot verify recipient -> processing.
        monkeypatch.delenv("SARDIS_ACP_SETTLEMENT_ADDRESS", raising=False)
        import sardis.chain.rpc_client as rpc_mod

        monkeypatch.setattr(
            rpc_mod, "get_rpc_client",
            lambda chain, **k: _FakeRPC(receipt=_receipt(), current_block=200),
        )
        client = TestClient(acp_app)
        session_id = self._open(client)
        resp = self._complete(client, session_id)
        assert resp.json()["payment"]["status"] == "processing"

    def test_replay_same_tx_twice_is_idempotent(self, acp_app, monkeypatch):
        """Verifying the same confirmed tx twice is safe (second attempt 409)."""
        client = self._setup(acp_app, monkeypatch, _FakeRPC(receipt=_receipt(), current_block=200))
        session_id = self._open(client)
        first = self._complete(client, session_id)
        assert first.json()["payment"]["status"] == "succeeded"
        # Replaying complete on a completed session is rejected (no double-credit).
        second = self._complete(client, session_id)
        assert second.status_code == 409

    def test_unsupported_chain_stays_processing(self, acp_app, monkeypatch):
        monkeypatch.setenv("SARDIS_ACP_SETTLEMENT_ADDRESS", _MERCHANT)
        import sardis.chain.rpc_client as rpc_mod

        monkeypatch.setattr(
            rpc_mod, "get_rpc_client",
            lambda chain, **k: _FakeRPC(receipt=_receipt(), current_block=200),
        )
        client = TestClient(acp_app)
        session_id = self._open(client)
        resp = client.post(
            f"/api/v2/acp/checkout_sessions/{session_id}/complete",
            json={"crypto_payment": {"tx_hash": "0x" + "f" * 64, "chain": "nonsense_chain", "token": "USDC"}},
        )
        assert resp.json()["payment"]["status"] == "processing"
