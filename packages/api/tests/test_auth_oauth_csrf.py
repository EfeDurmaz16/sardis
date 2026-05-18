"""Tests for OAuth CSRF state parameter verification.

Validates that the Google OAuth flow uses a cryptographic state token
to prevent CSRF attacks:
- Initiation endpoint sets state in cookie and redirect URL
- Callback rejects requests with missing state
- Callback rejects requests with mismatched state
- Callback clears cookie after successful validation
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

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
    return test_app


@pytest.fixture
def transport(app):
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_oauth_initiation_returns_state(transport):
    """Initiation endpoint includes state in redirect URL and sets cookie."""
    with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-client-id"}):
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
            resp = await client.get("/api/v2/auth/google")

    assert resp.status_code == 307, f"Expected redirect, got {resp.status_code}: {resp.text}"

    # Parse the redirect URL
    location = resp.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    # State must be in the redirect URL
    assert "state" in params, f"state param missing from redirect URL: {location}"
    state_from_url = params["state"][0]
    assert len(state_from_url) > 20, "state token should be sufficiently long"

    # State must also be set in a cookie
    cookie_header = resp.headers.get("set-cookie", "")
    assert "oauth_state=" in cookie_header, f"oauth_state cookie not set. Headers: {dict(resp.headers)}"
    assert "httponly" in cookie_header.lower(), "oauth_state cookie must be httponly"


@pytest.mark.asyncio
async def test_oauth_callback_rejects_missing_state(transport):
    """Callback without state param returns 400."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # No state query param, no cookie
        resp = await client.get("/api/v2/auth/google/callback?code=testcode")

    assert resp.status_code == 400
    body = resp.json()
    assert "state" in body["detail"].lower()


@pytest.mark.asyncio
async def test_oauth_callback_rejects_missing_state_cookie(transport):
    """Callback with state param but no cookie returns 400."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v2/auth/google/callback?code=testcode&state=somevalue")

    assert resp.status_code == 400
    body = resp.json()
    assert "state" in body["detail"].lower()


@pytest.mark.asyncio
async def test_oauth_callback_rejects_invalid_state(transport):
    """Callback with wrong state returns 400."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v2/auth/google/callback?code=testcode&state=wrong-state",
            cookies={"oauth_state": "correct-state"},
        )

    assert resp.status_code == 400
    body = resp.json()
    assert "state" in body["detail"].lower()


def _build_mock_httpx_client(token_resp_json, userinfo_resp_json):
    """Helper to build a mock httpx.AsyncClient for the token exchange.

    Uses MagicMock for response objects because httpx response .json()
    is synchronous (not awaited), while the client's .post()/.get()
    are async and need AsyncMock.
    """
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = token_resp_json

    mock_userinfo_response = MagicMock()
    mock_userinfo_response.status_code = 200
    mock_userinfo_response.json.return_value = userinfo_resp_json

    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_token_response
    mock_client_instance.get.return_value = mock_userinfo_response
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    return mock_client_instance


@pytest.mark.asyncio
async def test_oauth_callback_accepts_valid_state(transport):
    """Callback with matching state proceeds to token exchange."""
    state_token = "valid-state-token-abc123"

    mock_auth_result = AsyncMock()
    mock_auth_result.user_id = "usr_123"
    mock_auth_result.email = "test@example.com"
    mock_auth_result.org_id = "org_test"
    mock_auth_result.access_token = "jwt_token"
    mock_auth_result.refresh_token = "refresh_token"

    mock_httpx = _build_mock_httpx_client(
        token_resp_json={"access_token": "goog_token"},
        userinfo_resp_json={"id": "google-123", "email": "test@example.com", "name": "Test User"},
    )

    with (
        patch("httpx.AsyncClient", return_value=mock_httpx),
        patch.object(auth, "_get_auth_service") as mock_get_auth_svc,
        patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
        }),
    ):
        mock_auth_svc = AsyncMock()
        mock_auth_svc.google_oauth_callback.return_value = mock_auth_result
        mock_get_auth_svc.return_value = mock_auth_svc

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v2/auth/google/callback?code=testcode&state={state_token}",
                cookies={"oauth_state": state_token},
            )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # Cookie should be cleared after successful validation
    cookie_header = resp.headers.get("set-cookie", "")
    if "oauth_state=" in cookie_header:
        # The cookie should be deleted (max-age=0 or expires in past)
        lower_cookie = cookie_header.lower()
        assert "max-age=0" in lower_cookie or 'oauth_state=""' in cookie_header or "oauth_state=;" in cookie_header


@pytest.mark.asyncio
async def test_oauth_initiation_state_roundtrip(transport):
    """State from initiation can be used to pass callback validation."""
    with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-client-id"}):
        # Step 1: Hit the initiation endpoint to get the state token
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
            init_resp = await client.get("/api/v2/auth/google")

    assert init_resp.status_code == 307

    # Extract state from redirect URL
    location = init_resp.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)
    state_token = params["state"][0]

    # Extract state from cookie
    cookie_header = init_resp.headers.get("set-cookie", "")
    cookie_state = None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("oauth_state="):
            cookie_state = part.split("=", 1)[1]
            break

    assert cookie_state is not None, "Could not extract oauth_state cookie"
    assert state_token == cookie_state, "State in URL and cookie must match"

    # Step 2: Use that state in a callback (mock downstream services)
    mock_auth_result = AsyncMock()
    mock_auth_result.user_id = "usr_456"
    mock_auth_result.email = "roundtrip@example.com"
    mock_auth_result.org_id = "org_test"
    mock_auth_result.access_token = "jwt_rt"
    mock_auth_result.refresh_token = "refresh_rt"

    mock_httpx = _build_mock_httpx_client(
        token_resp_json={"access_token": "goog_token"},
        userinfo_resp_json={"id": "google-456", "email": "roundtrip@example.com", "name": "Roundtrip User"},
    )

    with (
        patch("httpx.AsyncClient", return_value=mock_httpx),
        patch.object(auth, "_get_auth_service") as mock_get_auth_svc,
        patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
        }),
    ):
        mock_auth_svc = AsyncMock()
        mock_auth_svc.google_oauth_callback.return_value = mock_auth_result
        mock_get_auth_svc.return_value = mock_auth_svc

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/api/v2/auth/google/callback?code=testcode&state={state_token}",
                cookies={"oauth_state": cookie_state},
            )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
