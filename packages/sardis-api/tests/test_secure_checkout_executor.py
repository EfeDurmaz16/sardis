from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from decimal import Decimal
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
    status_updates: list[tuple[str, str]] = []

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

    async def update_status(self, card_id: str, status_value: str):
        self.__class__.status_updates.append((card_id, status_value))
        row = await self.get_by_card_id(card_id)
        row["status"] = status_value
        return row


class _CardProvider:
    freeze_calls: list[str] = []

    async def reveal_card_details(self, card_id: str, *, reason: str = ""):
        assert card_id == "card_1"
        return {
            "pan": "4111111111111111",
            "cvv": "123",
            "exp_month": 12,
            "exp_year": 2030,
        }

    async def freeze_card(self, provider_card_id: str):
        self.__class__.freeze_calls.append(provider_card_id)
        return {"provider_card_id": provider_card_id, "status": "frozen"}


class _InvalidRevealCardProvider(_CardProvider):
    async def reveal_card_details(self, card_id: str, *, reason: str = ""):
        _ = reason
        assert card_id == "card_1"
        return {
            "pan": "not-a-pan",
            "cvv": "12",
            "exp_month": 0,
            "exp_year": 1999,
        }


class _LeakErrorCardProvider(_CardProvider):
    async def reveal_card_details(self, card_id: str, *, reason: str = ""):
        _ = reason
        assert card_id == "card_1"
        raise RuntimeError("provider leaked pan 4111111111111111 while failing")


class _ApprovalService:
    async def get_approval(self, approval_id: str):
        approvals = {
            "appr_ok": SimpleNamespace(
                id="appr_ok",
                status="approved",
                wallet_id="wallet_1",
                organization_id="org_demo",
                reviewed_by="reviewer_a",
            ),
            "appr_ok_2": SimpleNamespace(
                id="appr_ok_2",
                status="approved",
                wallet_id="wallet_1",
                organization_id="org_demo",
                reviewed_by="reviewer_b",
            ),
            "appr_same_a": SimpleNamespace(
                id="appr_same_a",
                status="approved",
                wallet_id="wallet_1",
                organization_id="org_demo",
                reviewed_by="reviewer_same",
            ),
            "appr_same_b": SimpleNamespace(
                id="appr_same_b",
                status="approved",
                wallet_id="wallet_1",
                organization_id="org_demo",
                reviewed_by="reviewer_same",
            ),
        }
        if approval_id in approvals:
            return approvals[approval_id]
        if approval_id == "appr_legacy_ok":
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


class _PolicySnapshot:
    max_per_tx = Decimal("250")
    max_daily = Decimal("1000")
    max_monthly = Decimal("10000")
    approval_threshold = Decimal("150")

    def validate_payment(self, *, amount: Decimal, fee: Decimal, mcc_code=None, merchant_category=None):
        _ = fee, mcc_code, merchant_category
        if amount > self.max_per_tx:
            return False, "per_tx_limit_exceeded"
        return True, "OK"


class _PolicyStoreWithSnapshot:
    async def fetch_policy(self, agent_id: str):
        _ = agent_id
        return _PolicySnapshot()


class _AuditSink:
    def __init__(self):
        self.events: list[dict] = []

    async def record_event(self, event: dict):
        self.events.append(event)


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["*"],
        api_key=None,
    )


def _non_admin_principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_demo",
        scopes=["read"],
        api_key=None,
    )


def _build_app(*, policy_store=None, audit_sink=None, card_provider=None, principal_factory=_principal) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_principal] = principal_factory
    store = secure_checkout.InMemorySecureCheckoutStore()
    app.dependency_overrides[secure_checkout.get_deps] = lambda: secure_checkout.SecureCheckoutDependencies(
        wallet_repo=_WalletRepo(),
        agent_repo=_AgentRepo(),
        card_repo=_CardRepo(),
        card_provider=card_provider or _CardProvider(),
        policy_store=policy_store,
        approval_service=_ApprovalService(),
        audit_sink=audit_sink,
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


def test_pan_entry_quorum_requires_two_approvals_when_configured(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_MIN_APPROVALS", "2")
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_DISTINCT_APPROVAL_REVIEWERS", "1")
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
            "intent_id": "intent_pan_quorum_1",
            "approval_id": "appr_ok",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "pending_approval"
    assert payload["approval_quorum_required"] == 2

    insufficient = client.post(
        f"/api/v2/checkout/secure/jobs/{payload['job_id']}/execute",
        json={"approval_id": "appr_ok"},
    )
    assert insufficient.status_code == 403
    assert insufficient.json()["detail"] == "approval_quorum_not_met:1/2"

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{payload['job_id']}/execute",
        json={"approval_ids": ["appr_ok", "appr_ok_2"]},
    )
    assert executed.status_code == 200
    execute_payload = executed.json()
    assert execute_payload["status"] == "dispatched"
    assert execute_payload["approval_id"] == "appr_ok"
    assert execute_payload["approval_ids"] == ["appr_ok", "appr_ok_2"]


def test_pan_entry_quorum_requires_distinct_reviewers(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_MIN_APPROVALS", "2")
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_DISTINCT_APPROVAL_REVIEWERS", "1")
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
            "intent_id": "intent_pan_distinct_1",
            "approval_ids": ["appr_same_a", "appr_same_b"],
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "pending_approval"

    denied = client.post(
        f"/api/v2/checkout/secure/jobs/{payload['job_id']}/execute",
        json={"approval_ids": ["appr_same_a", "appr_same_b"]},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "approval_distinct_reviewer_quorum_not_met:1/2"


def test_pan_entry_execute_fail_closed_on_invalid_revealed_card_details(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    app = _build_app(card_provider=_InvalidRevealCardProvider())
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "20.00",
            "currency": "USD",
            "intent_id": "intent_pan_invalid_reveal_1",
            "approval_id": "appr_ok",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_id": "appr_ok"},
    )
    assert executed.status_code == 503
    assert executed.json()["detail"] == "card_details_invalid"


def test_pan_entry_reveal_failure_redacts_sensitive_error(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    app = _build_app(card_provider=_LeakErrorCardProvider())
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "20.00",
            "currency": "USD",
            "intent_id": "intent_pan_redaction_1",
            "approval_id": "appr_ok",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_id": "appr_ok"},
    )
    assert executed.status_code == 503
    assert executed.json()["detail"] == "card_details_reveal_failed"

    fetched = client.get(f"/api/v2/checkout/secure/jobs/{job_id}")
    assert fetched.status_code == 200
    payload = fetched.json()
    assert payload["error_code"] == "card_details_reveal_failed"
    assert "4111111111111111" not in (payload["error"] or "")
    assert "[REDACTED_PAN]" in (payload["error"] or "")


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
    assert tokenized_payload["pan_compliance_ready"] is True

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
    assert pan_payload["pan_compliance_ready"] is True


def test_security_policy_endpoint_returns_runtime_guardrails(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS", "www.amazon.com,checkout.stripe.com")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_FREEZE_ON_SECURITY_INCIDENT", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_ROTATE_ON_SECURITY_INCIDENT", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_ROTATE_SEVERITIES", "high,critical")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_ON_SECURITY_INCIDENT", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_OPS_APPROVED", "0")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_ALLOWED_SEVERITIES", "low,medium")
    monkeypatch.setenv("SARDIS_CHECKOUT_INCIDENT_COOLDOWN_MEDIUM_SECONDS", "120")
    app = _build_app(policy_store=_PolicyStore())
    client = TestClient(app)

    response = client.get("/api/v2/checkout/secure/security-policy")
    assert response.status_code == 200
    payload = response.json()
    assert payload["pan_execution_enabled"] is True
    assert payload["require_shared_secret_store"] is True
    assert payload["shared_secret_store_configured"] is False
    assert payload["production_pan_entry_requires_allowlist"] is True
    assert payload["pan_entry_break_glass_only"] is True
    assert payload["pan_boundary_mode"] == "issuer_hosted_iframe_plus_enclave_break_glass"
    assert payload["issuer_hosted_reveal_preferred"] is True
    assert payload["recommended_default_mode"] == "embedded_iframe"
    assert payload["pan_entry_allowlist"] == ["checkout.stripe.com", "www.amazon.com"]
    assert payload["supported_merchant_modes"] == ["tokenized_api", "embedded_iframe", "pan_entry", "blocked"]
    assert payload["auto_freeze_on_security_incident"] is True
    assert payload["auto_rotate_on_security_incident"] is True
    assert payload["auto_rotate_severities"] == ["critical", "high"]
    assert payload["auto_unfreeze_on_security_incident"] is True
    assert payload["auto_unfreeze_ops_approved"] is False
    assert payload["auto_unfreeze_allowed_severities"] == ["low", "medium"]
    assert payload["min_approvals"] == 1
    assert payload["pan_min_approvals"] == 2
    assert payload["require_distinct_approval_reviewers"] is True
    assert payload["incident_cooldown_seconds"]["medium"] == 120


def test_security_policy_endpoint_requires_admin():
    app = _build_app(policy_store=_PolicyStore(), principal_factory=_non_admin_principal)
    client = TestClient(app)

    response = client.get("/api/v2/checkout/secure/security-policy")
    assert response.status_code == 403
    assert response.json()["detail"] == "admin_required"


def test_prod_pan_entry_requires_allowlist(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_QSA_CONTACT", "qsa@sardis.example")
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
    monkeypatch.setenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_QSA_CONTACT", "qsa@sardis.example")
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


def test_prod_pan_execute_requires_dispatch_runtime_readiness(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_SECRET_STORE", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_QSA_CONTACT", "qsa@sardis.example")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS", "www.amazon.com")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    monkeypatch.delenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_URL", raising=False)
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
            "intent_id": "intent_prod_runtime_ready_1",
            "approval_ids": ["appr_ok", "appr_ok_2"],
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_ids": ["appr_ok", "appr_ok_2"]},
    )
    assert executed.status_code == 503
    assert executed.json()["detail"] == "executor_dispatch_url_not_configured"


def test_prod_pan_execute_requires_shared_secret_store(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "1")
    monkeypatch.delenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_SECRET_STORE", raising=False)
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_QSA_CONTACT", "qsa@sardis.example")
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
            "intent_id": "intent_prod_shared_secret_store_required_1",
            "approval_ids": ["appr_ok", "appr_ok_2"],
        },
    )
    assert created.status_code == 201
    job_id = created.json()["job_id"]

    executed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/execute",
        json={"approval_ids": ["appr_ok", "appr_ok_2"]},
    )
    assert executed.status_code == 503
    assert executed.json()["detail"] == "secure_secret_store_not_configured"


def test_prod_pan_entry_requires_pci_attestation(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS", "www.amazon.com")
    monkeypatch.delenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", raising=False)
    monkeypatch.delenv("SARDIS_CHECKOUT_QSA_CONTACT", raising=False)
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
            "intent_id": "intent_prod_pan_attestation_required_1",
        },
    )
    assert created.status_code == 403
    assert created.json()["detail"] == "pan_compliance_not_attested"


def test_prod_requires_persistent_secure_checkout_store(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.delenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", raising=False)
    app = _build_app(policy_store=_PolicyStore())
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://api.payments.example.com/pay",
            "amount": "12.00",
            "currency": "USD",
            "intent_id": "intent_prod_store_required_1",
        },
    )
    assert created.status_code == 503
    assert created.json()["detail"] == "secure_checkout_persistent_store_required"


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


def test_completion_callback_is_idempotent_with_idempotency_key(monkeypatch):
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
            "intent_id": "intent_complete_idempotent_1",
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

    headers = {
        "X-Sardis-Executor-Token": "exec_secret",
        "X-Sardis-Completion-Idempotency-Key": "comp_key_1",
    }
    first = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/complete",
        json={"status": "completed", "executor_ref": "exec_done_idempotent"},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["status"] == "completed"

    second = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/complete",
        json={"status": "completed", "executor_ref": "exec_done_idempotent"},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["status"] == "completed"


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


def test_secure_checkout_emits_audit_events_without_pan_fields(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    sink = _AuditSink()
    app = _build_app(audit_sink=sink)
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "23.00",
            "currency": "USD",
            "intent_id": "intent_audit_1",
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
    secret_ref = dispatch_payload["secret_ref"]
    assert secret_ref

    consumed = client.post(
        f"/api/v2/checkout/secure/secrets/{secret_ref}/consume",
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert consumed.status_code == 200

    completed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/complete",
        json={"status": "completed", "executor_ref": "exec_done_audit"},
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert completed.status_code == 200

    event_types = [event["event_type"] for event in sink.events]
    assert "secure_checkout.job_created" in event_types
    assert "secure_checkout.job_dispatched" in event_types
    assert "secure_checkout.secret_consumed" in event_types
    assert "secure_checkout.job_finalized" in event_types

    serialized = json.dumps(sink.events)
    assert "4111111111111111" not in serialized
    assert "\"cvv\"" not in serialized


def test_secure_checkout_job_evidence_export_returns_integrity_bundle(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    sink = _AuditSink()
    app = _build_app(audit_sink=sink, policy_store=_PolicyStoreWithSnapshot())
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "24.00",
            "currency": "USD",
            "intent_id": "intent_evidence_1",
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
    assert secret_ref

    consumed = client.post(
        f"/api/v2/checkout/secure/secrets/{secret_ref}/consume",
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert consumed.status_code == 200

    completed = client.post(
        f"/api/v2/checkout/secure/jobs/{job_id}/complete",
        json={"status": "completed", "executor_ref": "exec_done_evidence"},
        headers={"X-Sardis-Executor-Token": "exec_secret"},
    )
    assert completed.status_code == 200

    evidence = client.get(f"/api/v2/checkout/secure/jobs/{job_id}/evidence")
    assert evidence.status_code == 200
    payload = evidence.json()

    assert payload["job"]["job_id"] == job_id
    assert payload["job"]["status"] == "completed"
    assert payload["approvals"]
    assert payload["approvals"][0]["approval_id"] == "appr_ok"
    assert payload["policy"]["policy_present"] is True
    assert payload["policy"]["policy_hash"]
    assert payload["integrity"]["digest_sha256"]
    assert payload["integrity"]["hash_chain_entries"] >= 1
    assert payload["integrity"]["event_count"] >= 3
    assert payload["generated_at"]
    assert payload["scope_window"]["job_created_at"]
    assert payload["scope_window"]["job_updated_at"]

    serialized = json.dumps(payload)
    assert "4111111111111111" not in serialized
    assert "\"cvv\"" not in serialized


def test_secure_checkout_job_evidence_export_requires_existing_job():
    app = _build_app()
    client = TestClient(app)
    response = client.get("/api/v2/checkout/secure/jobs/scj_missing/evidence")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_attestation_failure_triggers_auto_freeze(monkeypatch):
    _CardProvider.freeze_calls = []
    _CardRepo.status_updates = []
    monkeypatch.setenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "exec_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY", "attest_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_FREEZE_ON_SECURITY_INCIDENT", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_DISPATCH_SECURITY_ALERTS", "0")
    app = _build_app()
    client = TestClient(app)

    created = client.post(
        "/api/v2/checkout/secure/jobs",
        json={
            "wallet_id": "wallet_1",
            "card_id": "card_1",
            "merchant_url": "https://www.amazon.com/checkout",
            "amount": "25.00",
            "currency": "USD",
            "intent_id": "intent_attestation_freeze_1",
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

    complete_path = f"/api/v2/checkout/secure/jobs/{job_id}/complete"
    body = json.dumps({"status": "completed", "executor_ref": "exec_fail"}).encode("utf-8")
    headers = _executor_attestation_headers(
        path=complete_path,
        body=body,
    )
    headers["X-Sardis-Executor-Signature"] = "deadbeef"
    failed = client.post(
        complete_path,
        content=body,
        headers={**headers, "Content-Type": "application/json"},
    )
    assert failed.status_code == 401
    assert failed.json()["detail"] == "executor_attestation_invalid_signature"

    assert "provider_card_1" in _CardProvider.freeze_calls
    assert ("card_1", "frozen") in _CardRepo.status_updates


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
