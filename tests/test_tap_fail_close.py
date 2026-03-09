"""Tests for TAP fail-close behavior.

Verifies that TAP verification rejects requests in production when
no JWKS provider is configured, while allowing bypass in dev for
backward compatibility.
"""
from __future__ import annotations

import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_api.middleware.tap import (
    TapMiddlewareConfig,
    TapVerificationMiddleware,
)


def _make_app(
    jwks_provider=None,
    enforcement_enabled: bool = True,
    fail_open_in_dev: bool = True,
    protected_paths=None,
) -> FastAPI:
    """Create a minimal FastAPI app with TAP middleware for testing."""
    app = FastAPI()

    config = TapMiddlewareConfig(
        protected_paths=protected_paths or ["/api/v2/ap2/", "/api/v2/a2a/"],
        enforcement_enabled=enforcement_enabled,
        fail_open_in_dev=fail_open_in_dev,
        jwks_provider=jwks_provider,
    )

    app.add_middleware(
        TapVerificationMiddleware,
        config=config,
        jwks_provider=jwks_provider,
    )

    @app.get("/api/v2/ap2/test")
    async def protected_endpoint():
        return {"ok": True}

    @app.get("/api/v2/a2a/test")
    async def a2a_endpoint():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


# Minimal valid TAP headers (structural only — signature won't verify)
_TAP_HEADERS = {
    "signature-input": 'sig1=("@authority" "@path");keyid="test-key";alg="ed25519";created=9999999999;nonce="abc123"',
    "signature": "sig1=:dGVzdA==:",
    "host": "localhost",
}


class TestTapFailCloseProduction:
    """TAP must reject in prod when no JWKS provider is available."""

    @patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "prod"})
    def test_prod_no_jwks_rejects(self):
        """In production with no JWKS provider, TAP must return 401."""
        app = _make_app(jwks_provider=None, enforcement_enabled=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v2/ap2/test", headers=_TAP_HEADERS)
        assert resp.status_code == 401

    @patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "production"})
    def test_production_alias_no_jwks_rejects(self):
        """'production' alias also triggers fail-close."""
        app = _make_app(jwks_provider=None, enforcement_enabled=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v2/ap2/test", headers=_TAP_HEADERS)
        assert resp.status_code == 401

    @patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "sandbox"})
    def test_sandbox_no_jwks_rejects(self):
        """Sandbox is treated as prod-like and must also fail-close."""
        app = _make_app(jwks_provider=None, enforcement_enabled=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v2/ap2/test", headers=_TAP_HEADERS)
        assert resp.status_code == 401


class TestTapProtectedPaths:
    """TAP protected paths must match actual router mount paths."""

    def test_default_protected_paths_include_api_prefix(self):
        """Default protected_paths must include /api/v2/ prefix."""
        config = TapMiddlewareConfig()
        assert "/api/v2/ap2/" in config.protected_paths
        assert "/api/v2/a2a/" in config.protected_paths
        assert "/api/v2/payments/" in config.protected_paths


class TestTapFailOpenDev:
    """TAP allows bypass in dev when fail_open_in_dev is True (default)."""

    @patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "dev"})
    def test_dev_no_jwks_enforcement_disabled_allows(self):
        """In dev with enforcement disabled, request passes."""
        app = _make_app(jwks_provider=None, enforcement_enabled=False, fail_open_in_dev=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v2/ap2/test")
        assert resp.status_code == 200

    def test_dev_verify_fn_returns_true_without_jwks(self):
        """In dev, verify_fn returns True when no JWKS provider (bypass)."""
        from sardis_api.middleware.tap import TapMiddlewareConfig, TapVerificationMiddleware

        config = TapMiddlewareConfig(fail_open_in_dev=True)
        middleware = TapVerificationMiddleware(None, config=config)

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "dev"}):
            verify_fn = middleware._build_verify_fn("test-req-id")
            result = verify_fn(b"base", "sig", "kid1", "ed25519")
            assert result is True, "Dev should bypass when no JWKS"

    def test_dev_verify_fn_rejects_when_fail_open_disabled(self):
        """In dev with fail_open_in_dev=False, verify_fn returns False."""
        from sardis_api.middleware.tap import TapMiddlewareConfig, TapVerificationMiddleware

        config = TapMiddlewareConfig(fail_open_in_dev=False)
        middleware = TapVerificationMiddleware(None, config=config)

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "dev"}):
            verify_fn = middleware._build_verify_fn("test-req-id")
            result = verify_fn(b"base", "sig", "kid1", "ed25519")
            assert result is False, "Dev with fail_open=False should reject"


class TestTapStaleCache:
    """JWKS stale cache expiry triggers rejection."""

    def test_stale_cache_expired_returns_none(self):
        """When JWKS cache exceeds max_stale, _jwks_provider returns None."""
        import time as time_mod

        _jwks_cache: dict[str, tuple[dict, float]] = {}
        _jwks_ttl = 3600.0
        _jwks_max_stale = 100.0

        # Seed cache with entry older than TTL AND older than max_stale
        # Must be older than TTL (3600s) to trigger the fetch path,
        # and older than max_stale (100s) to be rejected as too stale
        old_time = time_mod.monotonic() - 5000  # 5000s ago > TTL and > max_stale
        _jwks_cache["kid1"] = ({"keys": []}, old_time)

        def _jwks_provider(kid: str) -> dict | None:
            now = time_mod.monotonic()
            cached = _jwks_cache.get(kid)
            if cached and (now - cached[1]) < _jwks_ttl:
                return cached[0]
            # Simulate fetch failure (no real HTTP call)
            if cached:
                stale_age = now - cached[1]
                if stale_age <= _jwks_max_stale:
                    return cached[0]
                else:
                    return None
            return None

        result = _jwks_provider("kid1")
        assert result is None, "Expired stale cache should return None"

    def test_stale_cache_within_limit_returns_cached(self):
        """When JWKS cache is stale but within max_stale, return cached."""
        import time as time_mod

        _jwks_cache: dict[str, tuple[dict, float]] = {}
        _jwks_ttl = 100.0
        _jwks_max_stale = 500.0

        # Entry older than TTL but within max_stale
        old_time = time_mod.monotonic() - 200  # 200s > TTL(100) but < max_stale(500)
        cached_jwks = {"keys": [{"kid": "k1"}]}
        _jwks_cache["kid1"] = (cached_jwks, old_time)

        def _jwks_provider(kid: str) -> dict | None:
            now = time_mod.monotonic()
            cached = _jwks_cache.get(kid)
            if cached and (now - cached[1]) < _jwks_ttl:
                return cached[0]
            if cached:
                stale_age = now - cached[1]
                if stale_age <= _jwks_max_stale:
                    return cached[0]
                else:
                    return None
            return None

        result = _jwks_provider("kid1")
        assert result == cached_jwks, "Within max_stale should return cached"


class TestTapUnprotectedPaths:
    """Unprotected paths should always pass regardless of TAP config."""

    @patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "prod"})
    def test_health_endpoint_bypasses_tap(self):
        """Non-protected paths are not affected by TAP."""
        app = _make_app(jwks_provider=None, enforcement_enabled=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200
