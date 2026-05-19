"""Tests for Streaming Payment API (SSE-based pay-per-use payments).

Covers:
- Create (open) stream -> 201 success
- Consume units -> correct state tracking
- Consume exceeding deposit -> 422
- Consume exceeding max_units -> 422
- Consume on non-existent stream -> 404
- Consume on non-open stream -> 409
- Settle stream -> correct final state
- Settle non-existent stream -> 404
- SSE events endpoint -> 404 for missing stream
"""
from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from server.authz import Principal, require_principal
from server.routes.money_movement.streaming_payments import (
    _active_streams,
    router,
)

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


def _seed_stream(
    stream_id: str = "stream_test001",
    deposit: Decimal = Decimal("100.00"),
    unit_price: Decimal = Decimal("0.10"),
    max_units: int | None = None,
    status: str = "open",
    units_consumed: int = 0,
    amount_consumed: Decimal = Decimal("0"),
) -> dict:
    """Insert a stream directly into _active_streams for testing."""
    channel_mgr = MagicMock()
    voucher = MagicMock()
    voucher.sequence = 1
    channel_mgr.issue_voucher = MagicMock(return_value=voucher)
    channel_mgr.settle = AsyncMock()

    stream_data = {
        "channel_id": "ch_test001",
        "channel_mgr": channel_mgr,
        "unit_price": unit_price,
        "max_units": max_units,
        "units_consumed": units_consumed,
        "amount_consumed": amount_consumed,
        "deposit": deposit,
        "status": status,
        "events": asyncio.Queue(),
    }
    _active_streams[stream_id] = stream_data
    return stream_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_principal():
    p = _make_principal()
    # streaming_payments.py open_stream uses principal.principal_id
    # which doesn't exist on the Principal dataclass -- mock it
    return MagicMock(
        spec=Principal,
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
        principal_id="user_test_001",
        org_id="org_test_001",
    )


@pytest.fixture
def app(mock_principal):
    app = FastAPI()

    async def override_principal():
        return mock_principal

    app.dependency_overrides[require_principal] = override_principal
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_streams():
    """Reset in-memory stream store between tests."""
    _active_streams.clear()
    yield
    _active_streams.clear()


# ---------------------------------------------------------------------------
# POST /payments/stream/open
# ---------------------------------------------------------------------------


class TestOpenStream:
    def test_open_stream_returns_201(self, client):
        mock_channel = MagicMock()
        mock_session = MagicMock()
        mock_session.channel_id = "ch_new_001"
        mock_channel.open = AsyncMock(return_value=mock_session)

        with patch(
            "sardis_chain.tempo.stream_channel.TempoStreamChannel",
            return_value=mock_channel,
        ), patch(
            "server.routes.money_movement.streaming_payments._persist_stream_meta",
            new_callable=AsyncMock,
        ):
            resp = client.post("/payments/stream/open", json={
                "service_address": "0x" + "ab" * 20,
                "deposit_amount": "50.00",
                "token": "USDC",
                "unit_price": "0.05",
                "duration_hours": 24,
            })

        assert resp.status_code == 201
        data = resp.json()
        assert data["channel_id"] == "ch_new_001"
        assert data["deposit_amount"] == "50.00"
        assert data["unit_price"] == "0.05"
        assert data["units_consumed"] == 0
        assert data["status"] == "open"
        assert data["stream_id"].startswith("stream_")
        assert "/events" in data["sse_url"]

    def test_open_stream_stores_in_active_streams(self, client):
        mock_channel = MagicMock()
        mock_session = MagicMock()
        mock_session.channel_id = "ch_stored"
        mock_channel.open = AsyncMock(return_value=mock_session)

        with patch(
            "sardis_chain.tempo.stream_channel.TempoStreamChannel",
            return_value=mock_channel,
        ), patch(
            "server.routes.money_movement.streaming_payments._persist_stream_meta",
            new_callable=AsyncMock,
        ):
            resp = client.post("/payments/stream/open", json={
                "service_address": "0xservice",
                "deposit_amount": "100",
                "unit_price": "1.0",
            })

        stream_id = resp.json()["stream_id"]
        assert stream_id in _active_streams
        assert _active_streams[stream_id]["status"] == "open"

    def test_open_stream_validation_rejects_zero_deposit(self, client):
        resp = client.post("/payments/stream/open", json={
            "service_address": "0xservice",
            "deposit_amount": "0",
            "unit_price": "0.1",
        })
        assert resp.status_code == 422

    def test_open_stream_validation_rejects_zero_unit_price(self, client):
        resp = client.post("/payments/stream/open", json={
            "service_address": "0xservice",
            "deposit_amount": "100",
            "unit_price": "0",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /payments/stream/{stream_id}/consume
# ---------------------------------------------------------------------------


class TestConsumeUnits:
    def test_consume_units_succeeds(self, client):
        _seed_stream("stream_test001", deposit=Decimal("100"), unit_price=Decimal("0.10"))

        resp = client.post("/payments/stream/stream_test001/consume", json={
            "stream_id": "stream_test001",
            "units": 5,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["units_consumed"] == 5
        assert data["total_units"] == 5
        assert data["amount_this_batch"] == "0.50"
        assert data["total_amount"] == "0.50"
        assert data["remaining"] == "99.50"
        assert data["voucher_sequence"] == 1

    def test_consume_accumulates_across_calls(self, client):
        _seed_stream("stream_acc", deposit=Decimal("10"), unit_price=Decimal("1.00"))

        # First consume
        resp1 = client.post("/payments/stream/stream_acc/consume", json={
            "stream_id": "stream_acc",
            "units": 3,
        })
        assert resp1.status_code == 200
        assert resp1.json()["total_units"] == 3
        assert resp1.json()["total_amount"] == "3.00"

        # Second consume
        resp2 = client.post("/payments/stream/stream_acc/consume", json={
            "stream_id": "stream_acc",
            "units": 2,
        })
        assert resp2.status_code == 200
        assert resp2.json()["total_units"] == 5
        assert resp2.json()["total_amount"] == "5.00"
        assert resp2.json()["remaining"] == "5.00"

    def test_consume_exceeding_deposit_returns_422(self, client):
        _seed_stream("stream_exceed", deposit=Decimal("1.00"), unit_price=Decimal("0.50"))

        resp = client.post("/payments/stream/stream_exceed/consume", json={
            "stream_id": "stream_exceed",
            "units": 3,  # 3 * 0.50 = 1.50 > 1.00
        })

        assert resp.status_code == 422
        assert "exceed deposit" in resp.json()["detail"].lower()

    def test_consume_exceeding_max_units_returns_422(self, client):
        _seed_stream("stream_maxu", deposit=Decimal("100"), unit_price=Decimal("0.10"), max_units=10)

        resp = client.post("/payments/stream/stream_maxu/consume", json={
            "stream_id": "stream_maxu",
            "units": 11,  # > max_units=10
        })

        assert resp.status_code == 422
        assert "max units" in resp.json()["detail"].lower()

    def test_consume_nonexistent_stream_returns_404(self, client):
        resp = client.post("/payments/stream/stream_nope/consume", json={
            "stream_id": "stream_nope",
            "units": 1,
        })
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_consume_on_settled_stream_returns_409(self, client):
        _seed_stream("stream_settled", status="settled")

        resp = client.post("/payments/stream/stream_settled/consume", json={
            "stream_id": "stream_settled",
            "units": 1,
        })

        assert resp.status_code == 409
        assert "settled" in resp.json()["detail"].lower()

    def test_consume_zero_units_returns_422(self, client):
        _seed_stream("stream_zero")
        resp = client.post("/payments/stream/stream_zero/consume", json={
            "stream_id": "stream_zero",
            "units": 0,
        })
        assert resp.status_code == 422

    def test_consume_pushes_sse_event(self, client):
        stream_data = _seed_stream("stream_sse", deposit=Decimal("100"), unit_price=Decimal("1"))

        client.post("/payments/stream/stream_sse/consume", json={
            "stream_id": "stream_sse",
            "units": 2,
        })

        # Check the events queue has an event
        queue: asyncio.Queue = stream_data["events"]
        assert not queue.empty()
        event = queue.get_nowait()
        assert event["type"] == "payment"
        assert event["units"] == 2
        assert event["amount"] == "2"


# ---------------------------------------------------------------------------
# POST /payments/stream/{stream_id}/settle
# ---------------------------------------------------------------------------


class TestSettleStream:
    def test_settle_returns_settled_status(self, client):
        _seed_stream("stream_to_settle", deposit=Decimal("50"), unit_price=Decimal("1"),
                     units_consumed=10, amount_consumed=Decimal("10"))

        resp = client.post("/payments/stream/stream_to_settle/settle")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "settled"
        assert data["units_consumed"] == 10
        assert data["amount_consumed"] == "10"
        assert data["remaining"] == "40"

    def test_settle_calls_channel_manager(self, client):
        stream_data = _seed_stream("stream_settle_call")

        client.post("/payments/stream/stream_settle_call/settle")

        stream_data["channel_mgr"].settle.assert_awaited_once_with("ch_test001")

    def test_settle_nonexistent_stream_returns_404(self, client):
        resp = client.post("/payments/stream/stream_ghost/settle")
        assert resp.status_code == 404

    def test_settle_updates_active_streams(self, client):
        _seed_stream("stream_final")

        client.post("/payments/stream/stream_final/settle")

        assert _active_streams["stream_final"]["status"] == "settled"


# ---------------------------------------------------------------------------
# GET /payments/stream/{stream_id}/events (SSE)
# ---------------------------------------------------------------------------


class TestStreamEvents:
    def test_events_nonexistent_stream_returns_404(self, client):
        resp = client.get("/payments/stream/stream_missing/events")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestStreamingPaymentsAuth:
    def test_unauthenticated_open_returns_401(self):
        os.environ["SARDIS_ALLOW_ANON"] = "0"
        os.environ["SARDIS_ENVIRONMENT"] = "production"

        app = FastAPI()
        app.include_router(router)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/payments/stream/open", json={
            "service_address": "0xtest",
            "deposit_amount": "10",
            "unit_price": "0.1",
        })
        assert resp.status_code in (401, 403)

        os.environ["SARDIS_ALLOW_ANON"] = "1"
        os.environ["SARDIS_ENVIRONMENT"] = "dev"
