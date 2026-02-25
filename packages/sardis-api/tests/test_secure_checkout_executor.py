from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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


class _PolicyStore:
    async def fetch_policy(self, agent_id: str):
        _ = agent_id
        return None


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _build_app(*, policy_store=None) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = _principal
    store = secure_checkout.InMemorySecureCheckoutStore()
    app.dependency_overrides[secure_checkout.get_deps] = lambda: secure_checkout.SecureCheckoutDependencies(
        wallet_repo=_WalletRepo(),
        agent_repo=_AgentRepo(),
        card_repo=_CardRepo(),
        card_provider=_CardProvider(),
        policy_store=policy_store,
        approval_service=_ApprovalService(),
        store=store,
    )
    app.include_router(secure_checkout.router, prefix="/api/v2/checkout")
    return app


def _executor_attestation_headers(
    *,
    path: str,
    method: str = "POST",
    token: str = "exec_secret",
    key: str = "attest_secret",
    body: bytes = b"",
    nonce: str | None = None,
    timestamp: int | None = None,
) -> dict[str, str]:
    nonce_value = nonce or uuid.uuid4().hex
    ts_value = str(timestamp or int(time.time()))
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join([method.upper(), path, ts_value, nonce_value, body_hash])
    signature = hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-Sardis-Executor-Token": token,
        "X-Sardis-Executor-Timestamp": ts_value,
        "X-Sardis-Executor-Nonce": nonce_value,
        "X-Sardis-Executor-Signature": signature,
    }


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


def test_embedded_iframe_merchant_path_avoids_pan_secret(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_EMBEDDED_IFRAME_MERCHANTS", "checkout.issuer-elements.example.com")
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    app = _build_app()
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://checkout.issuer-elements.example.com/start",
            "amount": "9.00",
            "currency": "USD",
            "intent_id": "intent_embedded_1",
        },
    )
    assert created.status_code == 201
    create_payload = created.json()
    assert create_payload["merchant_mode"] == "embedded_iframe"
    assert create_payload["status"] == "ready"
    assert create_payload["approval_required"] is False

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{create_payload['job_id']}/execute",
        json={},
    )
    assert executed.status_code == 200
    execute_payload = executed.json()
    assert execute_payload["status"] == "dispatched"
    assert execute_payload["executor_ref"].startswith("embedded_iframe:")
    assert execute_payload["secret_ref"] is None


def test_merchant_capability_endpoint(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_TOKENIZED_MERCHANTS", "api.payments.example.com")
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    app = _build_app()
    client = TestClient(app)

    tokenized = client.post(
        "/api/v2/checkout/secure/merchant-capability",
        json={
            "merchant_url": "https://api.payments.example.com/pay",
            "amount": "10.00",
            "currency": "USD",
        },
    )
    assert tokenized.status_code == 200
    tokenized_payload = tokenized.json()
    assert tokenized_payload["merchant_mode"] == "tokenized_api"
    assert tokenized_payload["approval_likely_required"] is False
    assert tokenized_payload["pan_allowed_for_merchant"] is True

    pan_entry = client.post(
        "/api/v2/checkout/secure/merchant-capability",
        json={
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "50.00",
            "currency": "USD",
        },
    )
    assert pan_entry.status_code == 200
    pan_payload = pan_entry.json()
    assert pan_payload["merchant_mode"] == "pan_entry"
    assert pan_payload["approval_likely_required"] is True
    assert pan_payload["pan_allowed_for_merchant"] is True


def test_prod_pan_entry_requires_allowlist(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.delenv("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS", raising=False)
    app = _build_app(policy_store=_PolicyStore())
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "20.00",
            "currency": "USD",
            "intent_id": "intent_prod_pan_blocked_1",
        },
    )
    assert created.status_code == 403
    assert created.json()["detail"] == "pan_entry_not_allowlisted"


def test_prod_pan_entry_allowlisted_is_permitted(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS", "www.amazon.com")
    app = _build_app(policy_store=_PolicyStore())
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "20.00",
            "currency": "USD",
            "intent_id": "intent_prod_pan_allow_1",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["merchant_mode"] == "pan_entry"
    assert payload["status"] == "pending_approval"


def test_execute_dispatches_to_external_worker_when_configured(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_URL", "https://executor.example.internal/jobs")
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
            "intent_id": "intent_dispatch_1",
            "approval_id": "appr_ok",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    mock_response = SimpleNamespace(
        status_code=200,
        json=lambda: {"execution_id": "exec_123"},
    )
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = mock_response

    with patch("sardis_api.routers.secure_checkout.httpx.AsyncClient", return_value=mock_client):
        executed = client.post(
            f"/api/v2/checkout/secure/jobs/{job_id}/execute",
            json={"approval_id": "appr_ok"},
        )

    assert executed.status_code == 200
    payload = executed.json()
    assert payload["status"] == "dispatched"
    assert payload["executor_ref"] == "exec_123"


def test_executor_can_complete_dispatched_job_and_revoke_secret(monkeypatch):
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
            "amount": "22.00",
            "currency": "USD",
            "intent_id": "intent_complete_1",
            "approval_id": "appr_ok",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_id": "appr_ok"},
    )
    assert executed.status_code == 200
    dispatch_payload = executed.json()
    assert dispatch_payload["status"] == "dispatched"
    assert dispatch_payload["secret_ref"]
    secret_ref = dispatch_payload["secret_ref"]

    completed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/complete",
        json={"status": "completed", "executor_ref": "exec_done_1"},
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert completed.status_code == 200
    done_payload = completed.json()
    assert done_payload["status"] == "completed"
    assert done_payload["executor_ref"] == "exec_done_1"
    assert done_payload["secret_ref"] is None

    consumed = client.post(
        f"/api/v2/checkout/secure/secrets/{secret_ref}/consume",
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert consumed.status_code == 404


def test_consume_secret_requires_attestation_when_enabled(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY", "attest_secret")
    app = _build_app()
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "22.00",
            "currency": "USD",
            "intent_id": "intent_attest_consume_1",
            "approval_id": "appr_ok",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_id": "appr_ok"},
    )
    assert executed.status_code == 200
    secret_ref = executed.json()["secret_ref"]

    missing = client.post(
        f"/api/v2/checkout/secure/secrets/{secret_ref}/consume",
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert missing.status_code == 401
    assert missing.json()["detail"] == "executor_attestation_missing"

    consume_path = f"/api/v2/checkout/secure/secrets/{secret_ref}/consume"
    headers = _executor_attestation_headers(path=consume_path)
    consumed = client.post(consume_path, headers=headers)
    assert consumed.status_code == 200
    payload = consumed.json()
    assert payload["pan"] == "4111111111111111"


def test_executor_attestation_replay_is_rejected(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY", "attest_secret")
    app = _build_app()
    client = TestClient(app)

    created_1 = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "20.00",
            "currency": "USD",
            "intent_id": "intent_attest_replay_1",
            "approval_id": "appr_ok",
        },
    )
    created_2 = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "21.00",
            "currency": "USD",
            "intent_id": "intent_attest_replay_2",
            "approval_id": "appr_ok",
        },
    )
    assert created_1.status_code == 201
    assert created_2.status_code == 201
    job_1 = created_1.json()["job_id"]
    job_2 = created_2.json()["job_id"]

    exec_1 = client.post(f"/api/v2/checkout/secure/jobs/{job_1}/execute", json={"approval_id": "appr_ok"})
    exec_2 = client.post(f"/api/v2/checkout/secure/jobs/{job_2}/execute", json={"approval_id": "appr_ok"})
    assert exec_1.status_code == 200
    assert exec_2.status_code == 200

    nonce = "replay_nonce_1"
    ts = int(time.time())
    body_1 = json.dumps({"status": "completed", "executor_ref": "exec_done_1"}).encode("utf-8")
    complete_1_path = f"/api/v2/checkout/secure/jobs/{job_1}/complete"
    headers_1 = _executor_attestation_headers(path=complete_1_path, nonce=nonce, timestamp=ts, body=body_1)
    completed = client.post(
        complete_1_path,
        content=body_1,
        headers={**headers_1, "Content-Type": "application/json"},
    )
    assert completed.status_code == 200

    body_2 = json.dumps({"status": "completed", "executor_ref": "exec_done_2"}).encode("utf-8")
    complete_2_path = f"/api/v2/checkout/secure/jobs/{job_2}/complete"
    headers_2 = _executor_attestation_headers(path=complete_2_path, nonce=nonce, timestamp=ts, body=body_2)
    replayed = client.post(
        complete_2_path,
        content=body_2,
        headers={**headers_2, "Content-Type": "application/json"},
    )
    assert replayed.status_code == 401
    assert replayed.json()["detail"] == "executor_attestation_replay"
