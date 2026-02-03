from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_login_requires_admin_password(test_client):
    resp = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "anything"},
    )
    assert resp.status_code == 503


@pytest.mark.anyio
async def test_logout_revokes_token(test_client, monkeypatch):
    monkeypatch.setenv("SARDIS_ADMIN_PASSWORD", "super-secret-password")

    login = await test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "super-secret-password"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    me1 = await test_client.get("/api/v1/auth/me", headers=headers)
    assert me1.status_code == 200, me1.text
    assert me1.json()["username"] == "admin"

    logout = await test_client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200, logout.text
    assert logout.json().get("revoked") is True

    me2 = await test_client.get("/api/v1/auth/me", headers=headers)
    assert me2.status_code == 401
    assert me2.json()["detail"] == "Token revoked"

