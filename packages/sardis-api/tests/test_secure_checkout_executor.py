from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import secure_checkout


class _WalletRepo:
    async def get(self, wallet_id: str):
        return SimpleNamespace(wallet_id=wallet_id, agent_id="agent_1")


class _AgentRepo:
    async def get(self, agent_id: str):
        return SimpleNamespace(agent_id=agent_id, owner_id="org_demo")


class _CardRepo:
    async def get_by_card_id(self, card_id: str):
        return {
            "card_id": card_id,
            "wallet_id": "wallet_1",
            "provider": "lithic",
            "provider_card_id": "provider_card_1",
            "card_number_last4": "4242",
            "expiry_month": 12,
            "expiry_year": 2030,
            "status": "active",
        }


class _CardProvider:
    async def reveal_card_details(self, card_id: str, *, reason: str = ""):
        assert card_id == "card_1"
        return {
            "pan": "4111111111111111",
            "cvv": "123",
            "exp_month": 12,
            "exp_year": 2030,
        }


class _ApprovalService:
    async def get_approval(self, approval_id: str):
        if approval_id == "appr_ok":
            return SimpleNamespace(
                id=approval_id,
                status="approved",
                wallet_id="wallet_1",
                organization_id="org_demo",
            )
        return None


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    store = secure_checkout.InMemorySecureCheckoutStore()
    app.dependency_overrides[secure_checkout.get_deps] = lambda: secure_checkout.SecureCheckoutDependencies(
        wallet_repo=_WalletRepo(),
        agent_repo=_AgentRepo(),
        card_repo=_CardRepo(),
        card_provider=_CardProvider(),
        policy_store=None,
        approval_service=_ApprovalService(),
        store=store,
    )
    app.include_router(secure_checkout.router, prefix="/api/v2/checkout")
    return app


def test_pan_entry_job_requires_approval(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    app = _build_app()
    client = TestClient(app)

    response = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "19.99",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["merchant_mode"] == "pan_entry"
    assert payload["status"] == "pending_approval"
    assert payload["approval_required"] is True


def test_pan_entry_execute_generates_secret_ref_without_exposing_pan(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    app = _build_app()
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "20.00",
            "currency": "USD",
            "intent_id": "intent_pan_1",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    denied = client.post(f"/api/v2/checkout/secure/jobs/{job_id}/execute", json={})
    assert denied.status_code == 403

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_id": "appr_ok"},
    )
    assert executed.status_code == 200
    payload = executed.json()
    assert payload["status"] == "dispatched"
    assert payload["secret_ref"]
    assert payload["executor_ref"].startswith("secret_ref:")
    # PAN must never be returned in the public job payload.
    assert "pan" not in payload

    secret_ref = payload["secret_ref"]
    consumed = client.post(
        f"/api/v2/checkout/secure/secrets/{secret_ref}/consume",
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert consumed.status_code == 200
    secret_payload = consumed.json()
    assert secret_payload["pan"] == "4111111111111111"
    assert secret_payload["cvv"] == "123"

    consumed_again = client.post(
        f"/api/v2/checkout/secure/secrets/{secret_ref}/consume",
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert consumed_again.status_code == 404


def test_tokenized_merchant_path_avoids_pan_secret(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_TOKENIZED_MERCHANTS", "api.payments.example.com")
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    app = _build_app()
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://api.payments.example.com/pay",
            "amount": "10.00",
            "currency": "USD",
            "intent_id": "intent_tokenized_1",
        },
    )
    assert created.status_code == 201
    create_payload = created.json()
    assert create_payload["merchant_mode"] == "tokenized_api"
    assert create_payload["status"] == "ready"
    assert create_payload["approval_required"] is False

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{create_payload['job_id']}/execute",
        json={},
    )
    assert executed.status_code == 200
    execute_payload = executed.json()
    assert execute_payload["status"] == "dispatched"
    assert execute_payload["executor_ref"].startswith("tokenized:")
    assert execute_payload["secret_ref"] is None
