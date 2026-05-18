from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_logout_revokes_token(app, monkeypatch):
    monkeypatch.setenv("SARDIS_ADMIN_PASSWORD", "demo-password")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post(
            "/api/v2/auth/login",
            data={"username": "admin", "password": "demo-password"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        me1 = await client.get("/api/v2/auth/me", headers=headers)
        assert me1.status_code == 200

        logout = await client.post("/api/v2/auth/logout", headers=headers)
        assert logout.status_code == 200

        me2 = await client.get("/api/v2/auth/me", headers=headers)
        assert me2.status_code == 401

