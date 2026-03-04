from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.routers.cpn import CPNDependencies, get_deps, public_router


class _FakeTreasuryRepo:
    def __init__(self) -> None:
        self.events = []

    async def record_treasury_webhook_event(self, **kwargs):
        self.events.append(kwargs)


class _FakeCacheService:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._locks: dict[str, str] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value: str, ttl: int = 0):
        self._store[key] = value

    async def acquire_lock(self, resource: str, ttl_seconds: int = 30):
        owner = f"lock:{resource}"
        if resource in self._locks:
            return None
        self._locks[resource] = owner
        return owner

    async def release_lock(self, resource: str, owner: str):
        current = self._locks.get(resource)
        if current == owner:
            self._locks.pop(resource, None)


def _build_app(deps: CPNDependencies) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: deps
    app.include_router(public_router, prefix="/api/v2")
    return app


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_cpn_webhook_rejects_invalid_signature_in_production():
    deps = CPNDependencies(
        treasury_repo=_FakeTreasuryRepo(),
        webhook_secret="cpn_secret",
        environment="prod",
    )
    app = _build_app(deps)
    client = TestClient(app)

    payload = {"id": "evt_1", "type": "payment.updated", "status": "processed"}
    response = client.post(
        "/api/v2/webhooks/cpn",
        content=json.dumps(payload),
        headers={"x-circle-signature": "bad"},
    )

    assert response.status_code == 401


def test_cpn_webhook_duplicate_event_is_idempotent():
    repo = _FakeTreasuryRepo()
    deps = CPNDependencies(
        treasury_repo=repo,
        webhook_secret="cpn_secret",
        environment="prod",
    )
    app = _build_app(deps)
    app.state.cache_service = _FakeCacheService()
    client = TestClient(app)

    payload = {
        "id": "evt_dup_1",
        "type": "payment.updated",
        "payment_id": "cpn_pay_1",
        "status": "settled",
    }
    body = json.dumps(payload).encode("utf-8")
    sig = _sign("cpn_secret", body)

    first = client.post(
        "/api/v2/webhooks/cpn",
        content=body,
        headers={"x-circle-signature": sig},
    )
    second = client.post(
        "/api/v2/webhooks/cpn",
        content=body,
        headers={"x-circle-signature": sig},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "received"
    assert second.json()["status"] == "received"
    assert len(repo.events) == 1
    assert repo.events[0]["provider"] == "circle_cpn"
