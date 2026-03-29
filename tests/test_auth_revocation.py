from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_login_requires_valid_credentials(test_client):
    """Shared admin password was removed. Login with invalid credentials returns 401."""
    resp = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_admin_password_removed(test_client, monkeypatch):
    """Even with SARDIS_ADMIN_PASSWORD set, shared admin login is no longer supported."""
    monkeypatch.setenv("SARDIS_ADMIN_PASSWORD", "super-secret-password")

    login = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "super-secret-password"},
    )
    # Shared admin password was removed — always returns 401
    assert login.status_code == 401
