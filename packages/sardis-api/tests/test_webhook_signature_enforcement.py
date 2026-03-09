"""Tests for webhook signature fail-closed enforcement.

Webhook endpoints must require signatures in ALL environments except
dev/development/local.  Previously only enforced in production.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.routers.cpn import (
    CPNDependencies,
    get_deps as cpn_get_deps,
    public_router as cpn_public_router,
)
from sardis_api.routers.treasury import (
    TreasuryDependencies,
    get_deps as treasury_get_deps,
    public_router as treasury_public_router,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeTreasuryRepo:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def record_treasury_webhook_event(self, **kwargs):
        self.events.append(kwargs)

    async def get_ach_payment(self, org_id, token):
        return {
            "organization_id": org_id,
            "payment_token": token,
            "external_bank_account_token": "eba_1",
            "status": "PENDING",
        }

    async def append_ach_events(self, org_id, token, events):
        pass

    async def update_ach_payment_status(self, org_id, token, status, **kw):
        pass


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_treasury_app(
    secret: str = "",
    env: str = "sandbox",
) -> FastAPI:
    deps = TreasuryDependencies(
        treasury_repo=_FakeTreasuryRepo(),
        lithic_client=None,
        lithic_webhook_secret=secret,
    )
    app = FastAPI()
    app.dependency_overrides[treasury_get_deps] = lambda: deps
    app.include_router(treasury_public_router, prefix="/api/v2/treasury")
    # Patch env for the webhook handler (it reads os.getenv)
    import os
    os.environ["SARDIS_ENVIRONMENT"] = env
    return app


def _build_cpn_app(
    secret: str = "",
    env: str = "sandbox",
) -> FastAPI:
    deps = CPNDependencies(
        treasury_repo=_FakeTreasuryRepo(),
        webhook_secret=secret,
        environment=env,
    )
    app = FastAPI()
    app.dependency_overrides[cpn_get_deps] = lambda: deps
    app.include_router(cpn_public_router, prefix="/api/v2")
    return app


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


_VALID_TREASURY_PAYLOAD = {
    "token": "evt_1",
    "event_type": "ACH_ORIGINATION_SETTLED",
    "payment_token": "pay_1",
    "data": {"token": "pay_1"},
}

_VALID_CPN_PAYLOAD = {
    "id": "evt_1",
    "type": "payment.updated",
    "payment_id": "cpn_pay_1",
    "status": "settled",
}


# ---------------------------------------------------------------------------
# Treasury webhook tests
# ---------------------------------------------------------------------------


class TestTreasuryWebhookSignatureEnforcement:
    """Treasury webhook must reject unsigned requests in non-dev envs."""

    @pytest.mark.parametrize("env", ["sandbox", "staging", "test"])
    def test_rejects_without_secret_in_non_dev_envs(self, env: str):
        """Returns 500 when secret not configured in sandbox/staging/test."""
        app = _build_treasury_app(secret="", env=env)
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/treasury/payments",
            content=json.dumps(_VALID_TREASURY_PAYLOAD),
        )

        assert response.status_code == 500
        assert "webhook secret not configured" in response.json()["detail"].lower()

    def test_rejects_without_secret_in_sandbox(self):
        """Explicit sandbox test — returns 500 when secret not configured."""
        app = _build_treasury_app(secret="", env="sandbox")
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/treasury/payments",
            content=json.dumps(_VALID_TREASURY_PAYLOAD),
        )

        assert response.status_code == 500

    def test_rejects_without_secret_in_production(self):
        """Still rejects in production (regression guard)."""
        app = _build_treasury_app(secret="", env="production")
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/treasury/payments",
            content=json.dumps(_VALID_TREASURY_PAYLOAD),
        )

        assert response.status_code == 500

    @pytest.mark.parametrize("env", ["dev", "development", "local"])
    def test_allows_missing_secret_in_dev(self, env: str):
        """No error when secret is missing in dev/development/local."""
        app = _build_treasury_app(secret="", env=env)
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/treasury/payments",
            content=json.dumps(_VALID_TREASURY_PAYLOAD),
        )

        # Should NOT be 500 — dev is the exception
        assert response.status_code != 500

    def test_valid_signature_accepted(self):
        """With a valid secret+signature, webhook processes normally."""
        secret = "treasury_webhook_secret"
        app = _build_treasury_app(secret=secret, env="sandbox")
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        body = json.dumps(_VALID_TREASURY_PAYLOAD).encode()
        sig = _sign(secret, body)

        response = client.post(
            "/api/v2/treasury/payments",
            content=body,
            headers={"x-lithic-hmac": sig},
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# CPN webhook tests
# ---------------------------------------------------------------------------


class TestCPNWebhookSignatureEnforcement:
    """CPN webhook must reject unsigned requests in non-dev envs."""

    @pytest.mark.parametrize("env", ["sandbox", "staging", "test"])
    def test_rejects_without_secret_in_non_dev_envs(self, env: str):
        """Returns 500 when secret not configured in sandbox/staging/test."""
        app = _build_cpn_app(secret="", env=env)
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/webhooks/cpn",
            content=json.dumps(_VALID_CPN_PAYLOAD),
        )

        assert response.status_code == 500
        assert "webhook secret not configured" in response.json()["detail"].lower()

    def test_rejects_without_secret_in_sandbox(self):
        """Explicit sandbox test — returns 500 when secret not configured."""
        app = _build_cpn_app(secret="", env="sandbox")
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/webhooks/cpn",
            content=json.dumps(_VALID_CPN_PAYLOAD),
        )

        assert response.status_code == 500

    def test_rejects_without_secret_in_production(self):
        """Still rejects in production (regression guard)."""
        app = _build_cpn_app(secret="", env="production")
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/webhooks/cpn",
            content=json.dumps(_VALID_CPN_PAYLOAD),
        )

        assert response.status_code == 500

    @pytest.mark.parametrize("env", ["dev", "development", "local"])
    def test_allows_missing_secret_in_dev(self, env: str):
        """No error when secret is missing in dev/development/local."""
        app = _build_cpn_app(secret="", env=env)
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        response = client.post(
            "/api/v2/webhooks/cpn",
            content=json.dumps(_VALID_CPN_PAYLOAD),
        )

        # Should NOT be 500 — dev is the exception
        assert response.status_code != 500

    def test_valid_signature_accepted(self):
        """With a valid secret+signature, webhook processes normally."""
        secret = "cpn_webhook_secret"
        app = _build_cpn_app(secret=secret, env="sandbox")
        app.state.cache_service = _FakeCacheService()
        client = TestClient(app)

        body = json.dumps(_VALID_CPN_PAYLOAD).encode()
        sig = _sign(secret, body)

        response = client.post(
            "/api/v2/webhooks/cpn",
            content=body,
            headers={"x-circle-signature": sig},
        )

        assert response.status_code == 200
