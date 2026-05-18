from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_server.authz import Principal, require_admin_principal, require_principal
from sardis_server.routes.agents import agent_events
from sardis_server.routes.money_movement import holds


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_test_001",
        scopes=["*"],
    )


class _FakeAcquire:
    def __init__(self, conn) -> None:
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEventsConn:
    async def fetch(self, query, *params):
        assert "FROM agent_events" in query
        assert params[0] == "org_test_001"
        assert params[1] == "agent_123"
        return [
            {
                "id": 7,
                "agent_id": "agent_123",
                "session_id": "sess_1",
                "event_type": "tool_call",
                "event_data": {"tool": "pay"},
                "sdk_timestamp": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
                "created_at": datetime(2026, 1, 2, 3, 4, 6, tzinfo=UTC),
            }
        ]


class _FakeEventsPool:
    def acquire(self):
        return _FakeAcquire(_FakeEventsConn())


class _FakeEventsDeps:
    async def _get_pool(self):
        return _FakeEventsPool()


class _FakeHold:
    def __init__(self) -> None:
        self.hold_id = "hold_123"
        self.wallet_id = "wallet_123"
        self.merchant_id = "merchant_123"
        self.amount = 25
        self.token = "USDC"
        self.status = "active"
        self.purpose = "hotel"
        self.created_at = datetime(2026, 1, 2, 3, 4, 5)
        self.expires_at = datetime(2026, 1, 9, 3, 4, 5)
        self.captured_amount = None
        self.captured_at = None
        self.voided_at = None


class _FakeHoldsRepo:
    async def get(self, hold_id: str):
        if hold_id == "hold_123":
            return _FakeHold()
        return None


def _build_agent_events_app(*, with_state: bool) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    if with_state:
        app.state.agent_events_deps = _FakeEventsDeps()
    app.include_router(agent_events.router)
    return app


def _build_holds_app(*, with_state: bool) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    app.dependency_overrides[require_admin_principal] = _principal
    if with_state:
        app.state.holds_repo = _FakeHoldsRepo()
    app.include_router(holds.router, prefix="/holds")
    return app


def test_agent_events_requires_truthful_wiring_when_not_configured() -> None:
    with TestClient(_build_agent_events_app(with_state=False)) as client:
        response = client.get("/agent_123/events")

    assert response.status_code == 501, response.text
    assert "app.state.agent_events_deps" in response.json()["detail"]


def test_agent_events_reads_from_app_state_wiring() -> None:
    with TestClient(_build_agent_events_app(with_state=True)) as client:
        response = client.get("/agent_123/events")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == 1
    assert payload["events"][0]["agent_id"] == "agent_123"
    assert payload["events"][0]["event_type"] == "tool_call"


def test_holds_requires_truthful_wiring_when_not_configured() -> None:
    with TestClient(_build_holds_app(with_state=False)) as client:
        response = client.get("/holds/hold_123")

    assert response.status_code == 501, response.text
    assert "app.state.holds_deps or app.state.holds_repo" in response.json()["detail"]


def test_holds_reads_from_app_state_repo_wiring() -> None:
    with TestClient(_build_holds_app(with_state=True)) as client:
        response = client.get("/holds/hold_123")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["hold_id"] == "hold_123"
    assert payload["wallet_id"] == "wallet_123"
    assert payload["status"] == "active"
