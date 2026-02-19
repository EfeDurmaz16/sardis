"""
Tests for the public signup endpoint (POST /auth/signup).

Tests cover:
- Successful signup returns 201 + sk_test_ key
- Duplicate email returns 409
- Invalid email returns 422
- Feature gate disabled returns 403
- Case-insensitive email dedup
- IP rate limit enforcement (6th signup -> 429)
- generate_api_key(test=True) produces sk_test_ prefix
- generate_api_key() still produces sk_live_ (backward compat)
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Direct module loading — bypasses sardis_api.__init__ which imports main.py
# and pulls in the full (heavy) dependency tree.
# ---------------------------------------------------------------------------
_src_dir = Path(__file__).parent.parent / "src"
_packages_dir = Path(__file__).parent.parent.parent

# Ensure sardis-core src is importable (needed by some transitive imports)
for pkg in ["sardis-core"]:
    pkg_path = _packages_dir / pkg / "src"
    if pkg_path.exists() and str(pkg_path) not in sys.path:
        sys.path.insert(0, str(pkg_path))


def _load_module(name: str, file_path: Path) -> types.ModuleType:
    """Load a Python module from file without triggering package __init__."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Register a stub sardis_api package so sub-module imports resolve
# without executing the real __init__.py.
_stub_pkg = types.ModuleType("sardis_api")
_stub_pkg.__path__ = [str(_src_dir / "sardis_api")]
_stub_pkg.__package__ = "sardis_api"
sys.modules.setdefault("sardis_api", _stub_pkg)

# Stub out the middleware sub-package as well
_stub_mw = types.ModuleType("sardis_api.middleware")
_stub_mw.__path__ = [str(_src_dir / "sardis_api" / "middleware")]
_stub_mw.__package__ = "sardis_api.middleware"
sys.modules.setdefault("sardis_api.middleware", _stub_mw)

# Stub out the routers sub-package
_stub_rt = types.ModuleType("sardis_api.routers")
_stub_rt.__path__ = [str(_src_dir / "sardis_api" / "routers")]
_stub_rt.__package__ = "sardis_api.routers"
sys.modules.setdefault("sardis_api.routers", _stub_rt)

# Now load the actual modules we need
_auth_middleware = _load_module(
    "sardis_api.middleware.auth",
    _src_dir / "sardis_api" / "middleware" / "auth.py",
)
APIKeyManager = _auth_middleware.APIKeyManager
set_api_key_manager = _auth_middleware.set_api_key_manager

_auth_router_mod = _load_module(
    "sardis_api.routers.auth",
    _src_dir / "sardis_api" / "routers" / "auth.py",
)
router = _auth_router_mod.router
_signup_ip_timestamps = _auth_router_mod._signup_ip_timestamps


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with the auth router for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/auth")

    manager = APIKeyManager(dsn="memory://")
    set_api_key_manager(manager)

    return app


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    """Clear IP rate limit state between tests."""
    _signup_ip_timestamps.clear()
    yield
    _signup_ip_timestamps.clear()


# ---------------------------------------------------------------------------
# Unit tests for generate_api_key
# ---------------------------------------------------------------------------


class TestGenerateAPIKey:
    def test_default_produces_sk_live(self):
        """generate_api_key() without test flag produces sk_live_ prefix."""
        full_key, prefix, key_hash = APIKeyManager.generate_api_key()
        assert full_key.startswith("sk_live_")
        assert prefix == full_key[:12]
        assert key_hash  # non-empty

    def test_test_flag_produces_sk_test(self):
        """generate_api_key(test=True) produces sk_test_ prefix."""
        full_key, prefix, key_hash = APIKeyManager.generate_api_key(test=True)
        assert full_key.startswith("sk_test_")
        assert prefix == full_key[:12]
        assert key_hash  # non-empty

    def test_live_flag_explicit(self):
        """generate_api_key(test=False) explicitly produces sk_live_."""
        full_key, _prefix, _hash = APIKeyManager.generate_api_key(test=False)
        assert full_key.startswith("sk_live_")


# ---------------------------------------------------------------------------
# Integration tests for POST /auth/signup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSignupEndpoint:
    async def _post_signup(self, client: AsyncClient, email: str) -> object:
        return await client.post("/auth/signup", json={"email": email})

    async def test_feature_gate_disabled(self):
        """Should return 403 when SARDIS_ALLOW_PUBLIC_SIGNUP is not set."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": ""}, clear=False):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._post_signup(client, "dev@example.com")
                assert resp.status_code == 403

    async def test_successful_signup(self):
        """Should return 201 with sk_test_ key on valid signup."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": "1"}, clear=False):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._post_signup(client, "dev@example.com")
                assert resp.status_code == 201
                data = resp.json()
                assert data["key"].startswith("sk_test_")
                assert data["mode"] == "test"
                assert data["scopes"] == ["read", "write"]
                assert data["rate_limit"] == 30
                assert data["key_id"]
                assert data["key_prefix"]
                assert data["organization_id"]

    async def test_invalid_email(self):
        """Should return 422 for invalid email format."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": "1"}, clear=False):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._post_signup(client, "not-an-email")
                assert resp.status_code == 422

    async def test_email_too_short(self):
        """Should return 422 for email shorter than 5 chars."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": "1"}, clear=False):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._post_signup(client, "a@b")
                assert resp.status_code == 422

    async def test_duplicate_email(self):
        """Should return 409 when email already registered."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": "1"}, clear=False):
            manager = APIKeyManager(dsn="memory://")
            manager.find_org_by_email = AsyncMock(return_value="org_existing")
            set_api_key_manager(manager)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await self._post_signup(client, "dup@example.com")
                assert resp.status_code == 409

    async def test_case_insensitive_email(self):
        """Should normalize email to lowercase for dedup."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": "1"}, clear=False):
            manager = APIKeyManager(dsn="memory://")
            calls = []

            async def _mock_find(email):
                calls.append(email)
                return None

            manager.find_org_by_email = _mock_find
            set_api_key_manager(manager)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await self._post_signup(client, "Dev@Example.COM")
                assert calls[-1] == "dev@example.com"

    async def test_ip_rate_limit(self):
        """6th signup from same IP within an hour should return 429."""
        app = _make_app()
        with patch.dict(os.environ, {"SARDIS_ALLOW_PUBLIC_SIGNUP": "1"}, clear=False):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for i in range(5):
                    resp = await self._post_signup(client, f"user{i}@example.com")
                    assert resp.status_code == 201, f"Request {i+1} should succeed"

                resp = await self._post_signup(client, "user5@example.com")
                assert resp.status_code == 429
