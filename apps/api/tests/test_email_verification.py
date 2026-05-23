"""Tests for the email verification flow."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def fake_email_verification_db(monkeypatch):
    """Provide the DB-backed token store expected by the router."""
    token_rows: dict[str, dict] = {}

    class FakeConnection:
        async def execute(self, sql: str, *args):
            if "INSERT INTO email_verification_tokens" in sql:
                user_id, token_hash, expires_at = args
                token_rows[token_hash] = {
                    "user_id": user_id,
                    "expires_at": expires_at,
                    "used_at": None,
                }
            elif "UPDATE email_verification_tokens SET used_at" in sql:
                token_rows[args[0]]["used_at"] = True

        async def fetchrow(self, _sql: str, token_hash: str):
            return token_rows.get(token_hash)

    class FakeAcquire:
        async def __aenter__(self):
            return FakeConnection()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakePool:
        def acquire(self):
            return FakeAcquire()

    async def fake_get_pool():
        return FakePool()

    from sardis.core.database import Database

    monkeypatch.setattr(Database, "get_pool", fake_get_pool)
    yield token_rows


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
async def test_confirm_with_valid_token(client, fake_email_verification_db):
    """A token written directly into the DB store can be confirmed successfully."""
    import hashlib
    import secrets
    from datetime import UTC, datetime, timedelta

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    fake_email_verification_db[token_hash] = {
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
async def test_confirm_with_expired_token_returns_400(client, fake_email_verification_db):
    """Confirming an expired token returns 400."""
    import hashlib
    import secrets
    from datetime import UTC, datetime, timedelta

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    fake_email_verification_db[token_hash] = {
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
async def test_confirm_already_used_token_returns_400(client, fake_email_verification_db):
    """Confirming a token that was already used returns 400."""
    import hashlib
    import secrets
    from datetime import UTC, datetime, timedelta

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    fake_email_verification_db[token_hash] = {
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
