"""Tests for the email verification flow."""
from __future__ import annotations

import pytest

from sardis_api.routers.email_verification import _token_store


@pytest.fixture(autouse=True)
def clear_token_store():
    """Reset in-memory token store between tests."""
    _token_store.clear()
    yield
    _token_store.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_auth_token(client) -> str:
    """Obtain a JWT for the test admin user."""
    resp = await client.post(
        "/api/v2/auth/login",
        data={"username": "admin", "password": "change-me-immediately"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code != 200:
        pytest.skip("Could not obtain auth token — admin login unavailable in this env")
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_verification_email_returns_200(client):
    """POST /auth/verify-email/send with a valid bearer token returns 200."""
    token = await _get_auth_token(client)

    resp = await client.post(
        "/api/v2/auth/verify-email/send",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert "message" in body


@pytest.mark.asyncio
async def test_send_requires_authentication(client):
    """POST /auth/verify-email/send without a bearer token returns 401 or 403."""
    resp = await client.post("/api/v2/auth/verify-email/send")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_confirm_with_valid_token(client):
    """A token written directly into the store can be confirmed successfully."""
    import hashlib
    import secrets
    from datetime import UTC, datetime, timedelta

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    _token_store[token_hash] = {
        "user_id": "usr_test_abc123",
        "expires_at": datetime.now(UTC) + timedelta(hours=24),
        "used_at": None,
    }

    resp = await client.post(
        "/api/v2/auth/verify-email/confirm",
        json={"token": raw_token},
    )
    assert resp.status_code == 200
    assert resp.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_confirm_with_expired_token_returns_400(client):
    """Confirming an expired token returns 400."""
    import hashlib
    import secrets
    from datetime import UTC, datetime, timedelta

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    _token_store[token_hash] = {
        "user_id": "usr_test_expired",
        "expires_at": datetime.now(UTC) - timedelta(seconds=1),  # already expired
        "used_at": None,
    }

    resp = await client.post(
        "/api/v2/auth/verify-email/confirm",
        json={"token": raw_token},
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_confirm_with_invalid_token_returns_400(client):
    """Confirming a completely unknown token returns 400."""
    resp = await client.post(
        "/api/v2/auth/verify-email/confirm",
        json={"token": "this-token-does-not-exist"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_confirm_already_used_token_returns_400(client):
    """Confirming a token that was already used returns 400."""
    import hashlib
    import secrets
    from datetime import UTC, datetime, timedelta

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    _token_store[token_hash] = {
        "user_id": "usr_test_used",
        "expires_at": datetime.now(UTC) + timedelta(hours=24),
        "used_at": datetime.now(UTC),  # already used
    }

    resp = await client.post(
        "/api/v2/auth/verify-email/confirm",
        json={"token": raw_token},
    )
    assert resp.status_code == 400
    assert "already been used" in resp.json()["detail"].lower()
