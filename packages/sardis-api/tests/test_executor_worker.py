from __future__ import annotations

import hmac
import hashlib
import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from sardis_api.executor_worker import (
    SecureCheckoutCompletionClient,
    canonical_dispatch_payload_bytes,
    create_executor_worker_app,
)


def _sample_payload() -> dict:
    return {
        "job_id": "scj_worker_1",
        "intent_id": "intent_worker_1",
        "wallet_id": "wallet_1",
        "card_id": "card_1",
        "merchant_origin": "https://www.amazon.com",
        "merchant_mode": "pan_entry",
        "amount": "10.00",
        "currency": "USD",
        "purpose": "agent_checkout",
        "options": {"trace": False},
        "secret_ref": "sec_123",
        "secret_expires_at": "2030-01-01T00:00:00+00:00",
    }


def _signed_headers(payload: dict, *, path: str = "/internal/executor/jobs") -> dict[str, str]:
    token = "dispatch_secret"
    signing_key = "dispatch_sign_key"
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex
    payload_hash = hashlib.sha256(canonical_dispatch_payload_bytes(payload)).hexdigest()
    canonical = "\n".join(["POST", path, ts, nonce, payload_hash])
    signature = hmac.new(
        signing_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Authorization": f"Bearer {token}",
        "X-Sardis-Timestamp": ts,
        "X-Sardis-Nonce": nonce,
        "X-Sardis-Signature": signature,
    }


def test_worker_accepts_valid_signed_dispatch(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_TOKEN", "dispatch_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_SIGNING_KEY", "dispatch_sign_key")
    monkeypatch.setenv("SARDIS_EXECUTOR_ENFORCE_SIGNED_DISPATCH", "1")
    app = create_executor_worker_app()
    client = TestClient(app)

    payload = _sample_payload()
    response = client.post(
        "/internal/executor/jobs",
        content=canonical_dispatch_payload_bytes(payload),
        headers={**_signed_headers(payload), "Content-Type": "application/json"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["duplicate"] is False
    assert body["execution_id"].startswith("exec_")
    assert body["job_id"] == payload["job_id"]


def test_worker_dispatch_idempotency_by_job_id(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_TOKEN", "dispatch_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_SIGNING_KEY", "dispatch_sign_key")
    monkeypatch.setenv("SARDIS_EXECUTOR_ENFORCE_SIGNED_DISPATCH", "1")
    app = create_executor_worker_app()
    client = TestClient(app)

    payload = _sample_payload()
    first = client.post(
        "/internal/executor/jobs",
        content=canonical_dispatch_payload_bytes(payload),
        headers={**_signed_headers(payload), "Content-Type": "application/json"},
    )
    second = client.post(
        "/internal/executor/jobs",
        content=canonical_dispatch_payload_bytes(payload),
        headers={**_signed_headers(payload), "Content-Type": "application/json"},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["execution_id"] == second.json()["execution_id"]
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True


def test_worker_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_TOKEN", "dispatch_secret")
    monkeypatch.setenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_SIGNING_KEY", "dispatch_sign_key")
    monkeypatch.setenv("SARDIS_EXECUTOR_ENFORCE_SIGNED_DISPATCH", "1")
    app = create_executor_worker_app()
    client = TestClient(app)

    payload = _sample_payload()
    headers = _signed_headers(payload)
    headers["X-Sardis-Signature"] = "deadbeef"

    response = client.post(
        "/internal/executor/jobs",
        content=canonical_dispatch_payload_bytes(payload),
        headers={**headers, "Content-Type": "application/json"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "dispatch_signature_invalid"


async def test_completion_client_retries_and_succeeds():
    completion_client = SecureCheckoutCompletionClient(
        callback_base_url="https://api.sardis.sh",
        executor_token="exec_secret",
        timeout_seconds=1.0,
        max_attempts=3,
        backoff_seconds=0.01,
    )

    mock_http = AsyncMock()
    mock_http.post.side_effect = [
        Exception("timeout"),
        SimpleNamespace(status_code=502),
        SimpleNamespace(status_code=200),
    ]
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_http
    mock_cm.__aexit__.return_value = None

    with patch("sardis_api.executor_worker.httpx.AsyncClient", return_value=mock_cm):
        result = await completion_client.complete_job(
            job_id="scj_worker_1",
            status_value="completed",
            executor_ref="exec_1",
        )

    assert result.delivered is True
    assert result.attempts == 3
    assert result.status_code == 200
    assert mock_http.post.call_count == 3


async def test_completion_client_returns_failure_after_retries():
    completion_client = SecureCheckoutCompletionClient(
        callback_base_url="https://api.sardis.sh",
        executor_token="exec_secret",
        timeout_seconds=1.0,
        max_attempts=2,
        backoff_seconds=0.01,
    )

    mock_http = AsyncMock()
    mock_http.post.side_effect = [
        SimpleNamespace(status_code=503),
        SimpleNamespace(status_code=503),
    ]
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_http
    mock_cm.__aexit__.return_value = None

    with patch("sardis_api.executor_worker.httpx.AsyncClient", return_value=mock_cm):
        result = await completion_client.complete_job(
            job_id="scj_worker_1",
            status_value="failed",
            failure_reason="browser_error",
        )

    assert result.delivered is False
    assert result.attempts == 2
    assert result.status_code == 503
