"""Tests for dual-path JWT validation (HS256 + JWKS).

Covers:
- Valid HS256 JWT → authenticated payload returned
- Expired JWT → None
- Invalid signature → None
- Missing JWT → 401 via get_current_user
- JWT with wrong/missing required claims → None
- HS256 secret shorter than 32 chars in prod → RuntimeError
- Valid JWKS path → payload returned (mock the JWKS endpoint)
- JWKS endpoint unreachable → fallback returns None
"""
from __future__ import annotations

import importlib
import os
import secrets
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Ensure package sources are on sys.path
_root = Path(__file__).parent.parent
_pkgs = _root / "packages"
for _pkg in ("sardis-core", "server-api"):
    _p = _pkgs / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_SECRET = "a" * 64  # well above 32-char minimum


def _make_hs256_token(
    sub: str = "user_123",
    role: str = "admin",
    org_id: str = "org_456",
    exp: int | None = None,
    iat: int | None = None,
    jti: str | None = None,
    secret: str = _TEST_SECRET,
    **extra,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": role,
        "org_id": org_id,
        "exp": exp if exp is not None else now + 3600,
        "iat": iat if iat is not None else now,
        "jti": jti if jti is not None else secrets.token_hex(16),
        **extra,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# Test: verify_jwt_token — HS256 path
# ---------------------------------------------------------------------------


class TestVerifyJwtTokenHS256:
    """Unit tests for the HS256 leg of verify_jwt_token."""

    def _import_auth(self, secret: str = _TEST_SECRET, env: str = "dev"):
        """Import auth module with a specific JWT_SECRET and environment."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": secret,
            "SARDIS_ENVIRONMENT": env,
            "BETTER_AUTH_JWKS_URL": "",
        }):
            # Reload so module-level env reads pick up the new values.
            import sardis_server.routes.accounts.auth as _auth_mod
            importlib.reload(_auth_mod)
            return _auth_mod

    def test_valid_token_returns_payload(self):
        auth = self._import_auth()
        token = _make_hs256_token(secret=_TEST_SECRET)
        payload = auth.verify_jwt_token(token)

        assert payload is not None
        assert payload["sub"] == "user_123"
        assert payload["role"] == "admin"
        assert payload["org_id"] == "org_456"
        assert isinstance(payload["jti"], str) and len(payload["jti"]) > 0

    def test_expired_token_returns_none(self):
        auth = self._import_auth()
        token = _make_hs256_token(
            exp=int(time.time()) - 3600,
            iat=int(time.time()) - 7200,
            secret=_TEST_SECRET,
        )
        assert auth.verify_jwt_token(token) is None

    def test_wrong_secret_returns_none(self):
        auth = self._import_auth()
        wrong_secret = "b" * 64
        token = _make_hs256_token(secret=wrong_secret)
        assert auth.verify_jwt_token(token) is None

    def test_garbage_token_returns_none(self):
        auth = self._import_auth()
        assert auth.verify_jwt_token("not.a.jwt") is None

    def test_missing_sub_returns_none(self):
        """Token without `sub` claim must be rejected."""
        auth = self._import_auth()
        now = int(time.time())
        payload = {
            "role": "admin",
            "exp": now + 3600,
            "iat": now,
            "jti": secrets.token_hex(16),
        }
        token = pyjwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        assert auth.verify_jwt_token(token) is None

    def test_empty_sub_returns_none(self):
        """Token with empty string `sub` must be rejected."""
        auth = self._import_auth()
        token = _make_hs256_token(sub="", secret=_TEST_SECRET)
        assert auth.verify_jwt_token(token) is None

    def test_missing_jti_returns_none(self):
        """Token without `jti` claim must be rejected (required claim)."""
        auth = self._import_auth()
        now = int(time.time())
        payload = {
            "sub": "user_123",
            "role": "admin",
            "exp": now + 3600,
            "iat": now,
            # no jti
        }
        token = pyjwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        assert auth.verify_jwt_token(token) is None

    def test_empty_jti_returns_none(self):
        """Token with empty jti must be rejected."""
        auth = self._import_auth()
        token = _make_hs256_token(jti="", secret=_TEST_SECRET)
        assert auth.verify_jwt_token(token) is None


# ---------------------------------------------------------------------------
# Test: JWT_SECRET_KEY short key in prod → RuntimeError
# ---------------------------------------------------------------------------


class TestJwtSecretSecurityCheck:
    """Module-level secret validation tests."""

    def test_short_secret_in_prod_raises(self):
        """HS256 secret shorter than 32 chars in prod must raise RuntimeError."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": "too-short",
            "SARDIS_ENVIRONMENT": "production",
            "BETTER_AUTH_JWKS_URL": "",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            with pytest.raises(RuntimeError, match="too short"):
                importlib.reload(_auth_mod)

    def test_missing_secret_in_prod_raises(self):
        """Missing JWT_SECRET_KEY in prod must raise RuntimeError."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": "",
            "SARDIS_ENVIRONMENT": "prod",
            "BETTER_AUTH_JWKS_URL": "",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                importlib.reload(_auth_mod)

    def test_short_secret_in_dev_warns_but_works(self):
        """Short key in dev should not raise — just warn."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": "short",
            "SARDIS_ENVIRONMENT": "dev",
            "BETTER_AUTH_JWKS_URL": "",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            # Should not raise
            importlib.reload(_auth_mod)
            assert _auth_mod.JWT_SECRET == "short"


# ---------------------------------------------------------------------------
# Test: JWKS path (mock PyJWKClient)
# ---------------------------------------------------------------------------


class TestVerifyJwtTokenJWKS:
    """Tests for the JWKS (better-auth EdDSA/ES256) validation path."""

    def test_jwks_valid_token_returns_payload(self):
        """When HS256 fails and JWKS succeeds, payload is returned."""
        now = int(time.time())
        expected_payload = {
            "sub": "ba_user_42",
            "exp": now + 3600,
            "iat": now,
            "aud": "sardis-api",
        }

        mock_signing_key = MagicMock()
        mock_signing_key.key = "fake-jwks-key"

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": _TEST_SECRET,
            "SARDIS_ENVIRONMENT": "dev",
            "BETTER_AUTH_JWKS_URL": "https://auth.sardis.sh/.well-known/jwks.json",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            importlib.reload(_auth_mod)

            # Inject the mock JWKS client after reload
            original_client = _auth_mod._jwks_client
            _auth_mod._jwks_client = mock_jwks_client

            try:
                # Mock pyjwt.decode to return expected payload for JWKS path.
                # The first call (HS256) will fail naturally since we pass a
                # non-HS256-signed token.  The second call (JWKS) we intercept.
                original_decode = pyjwt.decode
                call_count = [0]

                def mock_decode(token, key, algorithms, **kwargs):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        # HS256 path — let it fail
                        raise pyjwt.InvalidTokenError("not HS256")
                    # JWKS path — return payload
                    return expected_payload

                with patch.object(pyjwt, "decode", side_effect=mock_decode):
                    result = _auth_mod.verify_jwt_token("fake.jwks.token")

                assert result is not None
                assert result["sub"] == "ba_user_42"
                # jti should be synthesized for better-auth tokens
                assert result["jti"].startswith("ba_")
            finally:
                _auth_mod._jwks_client = original_client

    def test_jwks_unreachable_returns_none(self):
        """When HS256 fails and JWKS client raises, verify returns None."""
        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = Exception(
            "JWKS endpoint unreachable"
        )

        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": _TEST_SECRET,
            "SARDIS_ENVIRONMENT": "dev",
            "BETTER_AUTH_JWKS_URL": "https://auth.sardis.sh/.well-known/jwks.json",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            importlib.reload(_auth_mod)

            original_client = _auth_mod._jwks_client
            _auth_mod._jwks_client = mock_jwks_client

            try:
                # Token that fails HS256 and also fails JWKS lookup
                result = _auth_mod.verify_jwt_token("bad.token.for.jwks")
                assert result is None
            finally:
                _auth_mod._jwks_client = original_client

    def test_jwks_disabled_when_url_not_set(self):
        """When BETTER_AUTH_JWKS_URL is empty, JWKS path is skipped entirely."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": _TEST_SECRET,
            "SARDIS_ENVIRONMENT": "dev",
            "BETTER_AUTH_JWKS_URL": "",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            importlib.reload(_auth_mod)
            assert _auth_mod._jwks_client is None

            # Non-HS256 token should just return None (no JWKS fallback)
            result = _auth_mod.verify_jwt_token("some.random.token")
            assert result is None


# ---------------------------------------------------------------------------
# Test: get_current_user dependency (HTTP-level)
# ---------------------------------------------------------------------------


class TestGetCurrentUserEndpoint:
    """Integration tests for the /auth/me endpoint via get_current_user."""

    @pytest.fixture
    def auth_app(self):
        """Minimal app with auth router for HTTP testing."""
        with patch.dict(os.environ, {
            "JWT_SECRET_KEY": _TEST_SECRET,
            "SARDIS_ENVIRONMENT": "dev",
            "BETTER_AUTH_JWKS_URL": "",
        }):
            import sardis_server.routes.accounts.auth as _auth_mod
            importlib.reload(_auth_mod)

            app = FastAPI()
            app.include_router(_auth_mod.router, prefix="/api/v2/auth")
            return app

    @pytest.mark.asyncio
    async def test_valid_bearer_returns_user(self, auth_app):
        token = _make_hs256_token(secret=_TEST_SECRET)
        transport = ASGITransport(app=auth_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "user_123"
        assert body["role"] == "admin"
        assert body["organization_id"] == "org_456"

    @pytest.mark.asyncio
    async def test_missing_bearer_returns_401(self, auth_app):
        transport = ASGITransport(app=auth_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v2/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_bearer_returns_401(self, auth_app):
        transport = ASGITransport(app=auth_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/auth/me",
                headers={"Authorization": "Bearer garbage.token.here"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_bearer_returns_401(self, auth_app):
        token = _make_hs256_token(
            exp=int(time.time()) - 100,
            iat=int(time.time()) - 7200,
            secret=_TEST_SECRET,
        )
        transport = ASGITransport(app=auth_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v2/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 401
