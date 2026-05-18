from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets

import pytest
from httpx import ASGITransport, AsyncClient

from sardis.routes.accounts.auth import create_jwt_token


@pytest.mark.asyncio
async def test_logout_revokes_token(app):
    now = datetime.now(UTC)
    token = create_jwt_token({
        "sub": "user_logout_test",
        "role": "admin",
        "org_id": "org_logout_test",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        me1 = await client.get("/api/v2/auth/me", headers=headers)
        assert me1.status_code == 200

        logout = await client.post("/api/v2/auth/logout", headers=headers)
        assert logout.status_code == 200

        me2 = await client.get("/api/v2/auth/me", headers=headers)
        assert me2.status_code == 401
