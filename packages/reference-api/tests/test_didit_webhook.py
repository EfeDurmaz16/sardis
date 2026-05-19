"""Tests for the Didit KYC webhook endpoint (POST /api/v2/kyc/webhook).

Covers:
- Valid HMAC-SHA256 signature -> 200 + correct processing
- Invalid signature -> 401
- Expired timestamp -> 401
- Missing signature header -> 401
- Missing webhook secret -> 401
- Idempotent reprocessing (same session_id + status returns already_processed)
- All Didit status mappings (Approved, Declined, In Review, In Progress, Abandoned, Expired)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_webhook_secret_for_didit_hmac_verification"


def _sign_payload(payload: dict, secret: str = WEBHOOK_SECRET) -> str:
    """Compute the HMAC-SHA256 signature that Didit would send.

    Didit canonicalises via sorted-keys compact JSON before signing.
    """
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_didit_payload(
    session_id: str = "ses_test_001",
    status: str = "Approved",
    vendor_data: str = "user_abc",
) -> dict:
    """Build a minimal Didit webhook payload."""
    return {
        "session_id": session_id,
        "status": status,
        "vendor_data": vendor_data,
        "workflow_id": "wf_test",
    }


# ---------------------------------------------------------------------------
# Test: valid signature -> 200 + DB update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_valid_signature_approved(app, monkeypatch):
    """POST /api/v2/kyc/webhook with valid sig + Approved status returns 200."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    # Clear the in-memory idempotency cache between tests
    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(
        session_id="ses_approved_001",
        status="Approved",
        vendor_data="user_kyc_test",
    )
    signature = _sign_payload(payload)
    ts = str(int(time.time()))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                "X-Timestamp": ts,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processed"
    assert body["session_id"] == "ses_approved_001"
    assert body["kyc_status"] == "approved"


@pytest.mark.asyncio
async def test_webhook_stores_safe_metadata_without_raw_payload(app, monkeypatch):
    """KYC webhook metadata must not persist raw provider PII/document payloads."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance import kyc_onboarding

    kyc_onboarding._idempotency_cache.clear()
    updates: list[dict] = []

    async def fake_update_kyc_status(**kwargs):
        updates.append(kwargs)

    async def fake_on_kyc_approved(user_id: str, organization_id: str | None) -> None:
        return None

    monkeypatch.setattr(kyc_onboarding, "_update_kyc_status", fake_update_kyc_status)
    monkeypatch.setattr(kyc_onboarding, "_on_kyc_approved", fake_on_kyc_approved)

    payload = {
        **_build_didit_payload(
            session_id="ses_safe_metadata",
            status="Approved",
            vendor_data="user_safe_metadata",
        ),
        "document_number": "123456789",
        "first_name": "Sensitive",
        "data": {
            "id": "ses_safe_metadata",
            "status": "Approved",
            "document_number": "987654321",
            "workflow_id": "wf_nested",
        },
    }
    signature = _sign_payload(payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                "X-Timestamp": str(int(time.time())),
            },
        )

    assert resp.status_code == 200
    assert updates
    metadata = updates[0]["metadata"]
    assert metadata["provider"] == "didit"
    assert metadata["payload_hash"]
    assert metadata["session_id"] == "ses_safe_metadata"
    assert metadata["workflow_id"] == "wf_test"
    assert "document_number" not in metadata
    assert "first_name" not in metadata
    assert "data" not in metadata


@pytest.mark.asyncio
async def test_webhook_valid_signature_declined(app, monkeypatch):
    """POST /api/v2/kyc/webhook with Declined status processes correctly."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(
        session_id="ses_declined_001",
        status="Declined",
        vendor_data="user_declined",
    )
    signature = _sign_payload(payload)
    ts = str(int(time.time()))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                "X-Timestamp": ts,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processed"
    assert body["kyc_status"] == "declined"


@pytest.mark.asyncio
async def test_webhook_valid_signature_in_review(app, monkeypatch):
    """POST /api/v2/kyc/webhook with 'In Review' status maps to pending_review."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(
        session_id="ses_review_001",
        status="In Review",
    )
    signature = _sign_payload(payload)
    ts = str(int(time.time()))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                "X-Timestamp": ts,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["kyc_status"] == "pending_review"


# ---------------------------------------------------------------------------
# Test: invalid signature -> 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_invalid_signature_returns_401(app, monkeypatch):
    """POST /api/v2/kyc/webhook with wrong signature returns 401."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(session_id="ses_bad_sig")
    bad_signature = "deadbeef" * 8  # 64-char hex but wrong

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": bad_signature,
                "X-Timestamp": str(int(time.time())),
            },
        )

    assert resp.status_code == 401
    assert "Invalid webhook signature" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# Test: missing signature header -> 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_missing_signature_returns_401(app, monkeypatch):
    """POST /api/v2/kyc/webhook without X-Signature-V2 header returns 401."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    payload = _build_didit_payload()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 401
    assert "Missing webhook signature" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# Test: missing webhook secret env var -> 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_no_secret_configured_returns_401(app, monkeypatch):
    """POST /api/v2/kyc/webhook returns 401 when DIDIT_WEBHOOK_SECRET is unset."""
    monkeypatch.delenv("DIDIT_WEBHOOK_SECRET", raising=False)

    payload = _build_didit_payload()
    signature = _sign_payload(payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
            },
        )

    assert resp.status_code == 401
    assert "not configured" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# Test: expired timestamp -> 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_expired_timestamp_returns_401(app, monkeypatch):
    """POST /api/v2/kyc/webhook with a timestamp > 300s old returns 401."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    payload = _build_didit_payload(session_id="ses_old_ts")
    signature = _sign_payload(payload)
    old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                "X-Timestamp": old_timestamp,
            },
        )

    assert resp.status_code == 401
    assert "timestamp" in resp.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_webhook_future_timestamp_returns_401(app, monkeypatch):
    """POST /api/v2/kyc/webhook with a timestamp > 300s in the future returns 401."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    payload = _build_didit_payload(session_id="ses_future_ts")
    signature = _sign_payload(payload)
    future_timestamp = str(int(time.time()) + 600)  # 10 minutes from now

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                "X-Timestamp": future_timestamp,
            },
        )

    assert resp.status_code == 401
    assert "timestamp" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# Test: idempotent reprocessing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_idempotent_reprocessing(app, monkeypatch):
    """Sending the same (session_id, status) twice returns already_processed on the second call."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(
        session_id="ses_idempotent_001",
        status="Approved",
        vendor_data="user_idem",
    )
    signature = _sign_payload(payload)
    ts = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "X-Signature-V2": signature,
        "X-Timestamp": ts,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # First call: should process
        resp1 = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers=headers,
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "processed"

        # Second call (same payload): should be idempotent
        resp2 = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers=headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "already_processed"
        assert resp2.json()["session_id"] == "ses_idempotent_001"


# ---------------------------------------------------------------------------
# Test: different statuses for same session are NOT treated as duplicates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_different_status_same_session_is_processed(app, monkeypatch):
    """Same session_id with different status should be processed (not deduped)."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    ts = str(int(time.time()))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # First: In Progress
        payload1 = _build_didit_payload(
            session_id="ses_multi_status",
            status="In Progress",
        )
        resp1 = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload1),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": _sign_payload(payload1),
                "X-Timestamp": ts,
            },
        )
        assert resp1.status_code == 200
        assert resp1.json()["kyc_status"] == "in_progress"

        # Second: Approved (same session, different status)
        payload2 = _build_didit_payload(
            session_id="ses_multi_status",
            status="Approved",
        )
        resp2 = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload2),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": _sign_payload(payload2),
                "X-Timestamp": ts,
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "processed"
        assert resp2.json()["kyc_status"] == "approved"


# ---------------------------------------------------------------------------
# Test: no timestamp header is acceptable (optional)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_no_timestamp_header_still_works(app, monkeypatch):
    """When X-Timestamp is absent, the request should still be processed."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(
        session_id="ses_no_ts_001",
        status="Expired",
    )
    signature = _sign_payload(payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
                # No X-Timestamp header
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["kyc_status"] == "expired"


# ---------------------------------------------------------------------------
# Test: status mapping for Abandoned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_abandoned_status(app, monkeypatch):
    """Abandoned status is correctly mapped."""
    monkeypatch.setenv("DIDIT_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from sardis_server.routes.compliance.kyc_onboarding import _idempotency_cache
    _idempotency_cache.clear()

    payload = _build_didit_payload(
        session_id="ses_abandoned_001",
        status="Abandoned",
    )
    signature = _sign_payload(payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/v2/kyc/webhook",
            content=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "X-Signature-V2": signature,
            },
        )

    assert resp.status_code == 200
    assert resp.json()["kyc_status"] == "abandoned"
