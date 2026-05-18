"""Tests for admin login fail-open removal (S2 security fix).

Validates that:
- Primary auth failure returns 401 and does NOT silently fall through to legacy auth
- Default admin password only works in dev environments with explicit opt-in
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_api.routers import auth


@pytest.fixture
def app():
    """Create a test FastAPI app with the auth router."""
    test_app = FastAPI()
    test_app.include_router(auth.router, prefix="/api/v2/auth")
    # Simulate having a database_url so the primary auth path is attempted
    test_app.state.database_url = "postgresql://fake:fake@localhost/fake"
    return test_app


@pytest.fixture
def transport(app):
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_admin_login_rejects_on_primary_auth_failure(transport):
    """Primary auth error returns 401 and does NOT fall through to legacy admin password.

    When AuthService.login() raises a non-ValueError exception (e.g. a DB
    connection error), the endpoint must return 401 with a logged warning
    instead of silently falling through to legacy shared password auth.
    """
    env_vars = {
        "SARDIS_ADMIN_PASSWORD": "super-secret",
        "SARDIS_ENVIRONMENT": "dev",
        "SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD": "true",
    }

    mock_auth_svc = AsyncMock()
    # Simulate a non-ValueError failure (e.g. DB connection error)
    mock_auth_svc.login.side_effect = RuntimeError("DB connection failed")

    mock_auth_cls = MagicMock(return_value=mock_auth_svc)

    with (
        patch.dict(os.environ, env_vars, clear=False),
        patch("sardis_api.services.auth_service.AuthService", mock_auth_cls),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/auth/login",
                data={"username": "user@example.com", "password": "super-secret"},
            )

    # Must be 401, not a successful fallthrough to legacy admin auth
    assert resp.status_code == 401, (
        f"Expected 401 on primary auth failure, got {resp.status_code}: {resp.text}. "
        "The endpoint may be silently falling through to legacy admin password."
    )
    body = resp.json()
    assert body["detail"] == "authentication_failed"


@pytest.mark.asyncio
async def test_admin_login_no_default_password_in_non_dev(transport):
    """Default admin password must fail in non-dev environments.

    Even with SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD=true, the
    default password 'change-me-immediately' must not work in sandbox,
    staging, or production.
    """
    for env_name in ("sandbox", "staging", "prod", "production"):
        env_vars = {
            "SARDIS_ADMIN_PASSWORD": "",  # No real password set
            "SARDIS_ENVIRONMENT": env_name,
            "SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD": "true",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v2/auth/login",
                    data={
                        "username": "admin",
                        "password": "change-me-immediately",
                    },
                )

        # Must NOT succeed — default password must be rejected in non-dev envs
        assert resp.status_code in (401, 503), (
            f"Expected 401 or 503 for default password in {env_name} env, "
            f"got {resp.status_code}: {resp.text}"
        )


@pytest.mark.asyncio
async def test_admin_login_default_password_works_in_dev(transport):
    """Default admin password works in dev with explicit opt-in.

    This is the happy path: dev environment + explicit allow flag.
    """
    env_vars = {
        "SARDIS_ADMIN_PASSWORD": "",  # No real password set
        "SARDIS_ENVIRONMENT": "dev",
        "SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD": "true",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/auth/login",
                data={
                    "username": "admin",
                    "password": "change-me-immediately",
                },
            )

    assert resp.status_code == 200, (
        f"Expected 200 for default password in dev with opt-in, "
        f"got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "access_token" in body


@pytest.mark.asyncio
async def test_admin_login_default_password_fails_without_optin(transport):
    """Default admin password fails in dev without explicit opt-in flag."""
    env_vars = {
        "SARDIS_ADMIN_PASSWORD": "",  # No real password set
        "SARDIS_ENVIRONMENT": "dev",
        "SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD": "",  # Not opted in
    }

    with patch.dict(os.environ, env_vars, clear=False):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v2/auth/login",
                data={
                    "username": "admin",
                    "password": "change-me-immediately",
                },
            )

    assert resp.status_code == 503, (
        f"Expected 503 when admin password not configured and no opt-in, "
        f"got {resp.status_code}: {resp.text}"
    )
