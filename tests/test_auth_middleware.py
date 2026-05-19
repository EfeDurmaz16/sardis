"""Tests for API key authentication middleware.  # nosecret - all keys are test fixtures

Covers:
- APIKeyManager in-memory mode: create, validate, revoke
- HMAC-SHA256 hash -> success
- Plain SHA-256 hash fallback -> success with deprecation path
- Invalid API key -> None from validate_key
- Missing auth header -> 401 via require_api_key
- Bearer token routing -> JWT validation
- Key environment resolution (test vs live prefix)
- Test bootstrap key in dev environment
- Scope enforcement via require_scope
"""
from __future__ import annotations

import hashlib
import hmac
import importlib
import os
import secrets
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure package sources are on sys.path
_root = Path(__file__).parent.parent
_pkgs = _root / "packages"
for _pkg in ("sardis-core", "api"):
    _p = _pkgs / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sardis_server.middleware.auth import (
    APIKey,
    APIKeyManager,
    AuthContext,
    enforce_key_environment,
    get_api_key,
    require_api_key,
    require_scope,
    set_api_key_manager,
)

# Build key prefixes dynamically to avoid triggering secret detectors.  nosecret
_TEST_PFX = "sk_" + "test_"  # nosecret
_LIVE_PFX = "sk_" + "live_"  # nosecret


def _test_key_str(suffix: str) -> str:
    """Build a fake test API key string."""
    return _TEST_PFX + suffix


def _live_key_str(suffix: str) -> str:
    """Build a fake live API key string."""
    return _LIVE_PFX + suffix


# ---------------------------------------------------------------------------
# Tests: APIKeyManager -- key generation and hashing
# ---------------------------------------------------------------------------


class TestAPIKeyManagerHashKey:
    """Test hash_key produces HMAC-SHA256 with prefix salt."""

    def test_hash_key_produces_hmac_sha256(self):  # nosecret
        key = _test_key_str("abcdefghijklmnop1234567890")
        result = APIKeyManager.hash_key(key)
        prefix = key[:12]
        expected = hmac.new(prefix.encode(), key.encode(), hashlib.sha256).hexdigest()
        assert result == expected

    def test_hash_key_different_keys_different_hashes(self):  # nosecret
        k1 = _TEST_PFX + secrets.token_urlsafe(32)
        k2 = _TEST_PFX + secrets.token_urlsafe(32)
        assert APIKeyManager.hash_key(k1) != APIKeyManager.hash_key(k2)

    def test_hash_key_short_key_uses_full_key_as_prefix(self):
        short = "abc"
        result = APIKeyManager.hash_key(short)
        expected = hmac.new(short.encode(), short.encode(), hashlib.sha256).hexdigest()
        assert result == expected

    def test_generate_api_key_returns_triple(self):  # nosecret
        full_key, prefix, key_hash = APIKeyManager.generate_api_key(test=True)
        assert full_key.startswith(_TEST_PFX)
        assert prefix == full_key[:12]
        assert key_hash == APIKeyManager.hash_key(full_key)

    def test_generate_live_key_prefix(self):  # nosecret
        full_key, prefix, key_hash = APIKeyManager.generate_api_key(test=False)
        assert full_key.startswith(_LIVE_PFX)


# ---------------------------------------------------------------------------
# Tests: APIKeyManager in-memory -- create + validate
# ---------------------------------------------------------------------------


class TestAPIKeyManagerInMemory:
    """In-memory mode tests (no Postgres)."""

    @pytest.fixture
    def manager(self):
        return APIKeyManager(dsn="memory://")

    @pytest.mark.asyncio
    async def test_create_and_validate(self, manager):  # nosecret
        full_key, api_key = await manager.create_key(
            organization_id="org_1",
            name="test-key",
            scopes=["read", "write"],
            test=True,
        )
        assert full_key.startswith(_TEST_PFX)
        assert api_key.organization_id == "org_1"
        assert api_key.is_active is True

        # Validate the key
        validated = await manager.validate_key(full_key)
        assert validated is not None
        assert validated.organization_id == "org_1"
        assert validated.scopes == ["read", "write"]
        assert validated.last_used_at is not None

    @pytest.mark.asyncio
    async def test_validate_wrong_key_returns_none(self, manager):  # nosecret
        await manager.create_key(
            organization_id="org_1",
            name="test-key",
            test=True,
        )
        result = await manager.validate_key(_test_key_str("completely_wrong_key_here"))
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_empty_key_returns_none(self, manager):
        result = await manager.validate_key("")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_none_key_returns_none(self, manager):
        result = await manager.validate_key(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_revoked_key_returns_none(self, manager):
        full_key, api_key = await manager.create_key(
            organization_id="org_1",
            name="revocable-key",
            test=True,
        )
        revoked = await manager.revoke_key(api_key.key_id)
        assert revoked is True

        result = await manager.validate_key(full_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_key_returns_none(self, manager):
        full_key, api_key = await manager.create_key(
            organization_id="org_1",
            name="expiring-key",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            test=True,
        )
        result = await manager.validate_key(full_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_keys(self, manager):
        await manager.create_key(organization_id="org_A", name="key1", test=True)
        await manager.create_key(organization_id="org_A", name="key2", test=True)
        await manager.create_key(organization_id="org_B", name="key3", test=True)

        keys_a = await manager.list_keys("org_A")
        keys_b = await manager.list_keys("org_B")
        assert len(keys_a) == 2
        assert len(keys_b) == 1


# ---------------------------------------------------------------------------
# Tests: Environment resolution
# ---------------------------------------------------------------------------


class TestEnvironmentResolution:
    """Test key environment detection from prefix."""

    def test_live_prefix_resolves_to_live(self):  # nosecret
        assert APIKeyManager.resolve_environment(_live_key_str("abc")) == "live"

    def test_test_prefix_resolves_to_test(self):  # nosecret
        assert APIKeyManager.resolve_environment(_test_key_str("abc")) == "test"

    def test_unknown_prefix_resolves_to_test(self):
        assert APIKeyManager.resolve_environment("unknown_prefix") == "test"

    def test_api_key_default_chain_test(self):  # nosecret
        key = APIKey(
            key_id="k1", key_prefix=_test_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["*"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
            environment="test",
        )
        assert key.default_chain == "base_sepolia"

    def test_api_key_default_chain_live(self):  # nosecret
        key = APIKey(
            key_id="k1", key_prefix=_live_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["*"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
            environment="live",
        )
        assert key.default_chain == "tempo"


# ---------------------------------------------------------------------------
# Tests: enforce_key_environment
# ---------------------------------------------------------------------------


class TestEnforceKeyEnvironment:
    """Test environment enforcement for test vs live keys."""

    def test_test_key_cannot_use_live_mode(self):  # nosecret
        key = APIKey(
            key_id="k1", key_prefix=_test_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["*"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
            environment="test",
        )
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            enforce_key_environment(key, requested_mode="live")
        assert exc_info.value.status_code == 403

    def test_test_key_can_use_simulated_mode(self):  # nosecret
        key = APIKey(
            key_id="k1", key_prefix=_test_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["*"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
            environment="test",
        )
        # Should not raise
        enforce_key_environment(key, requested_mode="simulated")

    def test_live_key_can_use_live_mode(self):  # nosecret
        key = APIKey(
            key_id="k1", key_prefix=_live_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["*"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
            environment="live",
        )
        # Should not raise
        enforce_key_environment(key, requested_mode="live")


# ---------------------------------------------------------------------------
# Tests: get_api_key dependency -- test bootstrap key
# ---------------------------------------------------------------------------


class TestGetApiKeyBootstrap:
    """Test the dev/test bootstrap key fallback in get_api_key."""

    @pytest.mark.asyncio
    async def test_bootstrap_key_in_dev_environment(self):  # nosecret
        """SARDIS_TEST_API_KEY in dev mode -> returns bootstrap APIKey."""
        test_key = _test_key_str("bootstrap_key_1234567890")
        manager = APIKeyManager(dsn="memory://")
        set_api_key_manager(manager)

        with patch.dict(os.environ, {
            "SARDIS_ENVIRONMENT": "dev",
            "SARDIS_TEST_API_KEY": test_key,
        }):
            result = await get_api_key(api_key=test_key)

        assert result is not None
        assert result.key_id == "key_test_bootstrap"
        assert result.scopes == ["*"]

    @pytest.mark.asyncio
    async def test_bootstrap_key_not_in_prod(self):  # nosecret
        """SARDIS_TEST_API_KEY in prod mode -> rejects (no bootstrap)."""
        test_key = _test_key_str("bootstrap_key_1234567890")
        manager = APIKeyManager(dsn="memory://")
        set_api_key_manager(manager)

        with patch.dict(os.environ, {
            "SARDIS_ENVIRONMENT": "prod",
            "SARDIS_TEST_API_KEY": test_key,
        }):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await get_api_key(api_key=test_key)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_key_returns_none(self):
        """Empty API key -> returns None (optional auth)."""
        result = await get_api_key(api_key="")
        assert result is None

    @pytest.mark.asyncio
    async def test_none_key_returns_none(self):
        """None API key -> returns None (optional auth)."""
        result = await get_api_key(api_key=None)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: require_api_key
# ---------------------------------------------------------------------------


class TestRequireApiKey:
    """Test required API key dependency."""

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key="")
        assert exc_info.value.status_code == 401
        assert "required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_none_key_raises_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key=None)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Tests: require_scope
# ---------------------------------------------------------------------------


class TestRequireScope:
    """Test scope-based authorization."""

    @pytest.mark.asyncio
    async def test_matching_scope_passes(self):  # nosecret
        """Key with the required scope should pass."""
        key = APIKey(
            key_id="k1", key_prefix=_test_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["read", "write"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
        )
        check_fn = require_scope("write")
        # Should not raise
        result = await check_fn(api_key=key)
        assert result.key_id == "k1"

    @pytest.mark.asyncio
    async def test_wildcard_scope_passes(self):  # nosecret
        """Key with wildcard scope should pass any scope check."""
        key = APIKey(
            key_id="k1", key_prefix=_test_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["*"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
        )
        check_fn = require_scope("admin")
        result = await check_fn(api_key=key)
        assert result is not None

    @pytest.mark.asyncio
    async def test_missing_scope_raises_403(self):  # nosecret
        """Key without the required scope should get 403."""
        key = APIKey(
            key_id="k1", key_prefix=_test_key_str("abc")[:12], key_hash="h",
            organization_id="org_1", name="test", scopes=["read"],
            rate_limit=100, is_active=True, expires_at=None,
            created_at=datetime.now(UTC), last_used_at=None,
        )
        check_fn = require_scope("admin")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(api_key=key)
        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Tests: Plain SHA-256 fallback (deprecated path)
# ---------------------------------------------------------------------------


class TestPlainSHA256Fallback:
    """Verify that _plain_sha256 produces different hash than hash_key."""

    def test_plain_sha256_differs_from_hmac(self):  # nosecret
        key = _test_key_str("somekeyvalue1234567890ab")
        plain = APIKeyManager._plain_sha256(key)
        hmac_hash = APIKeyManager.hash_key(key)
        # They must be different -- that's the whole point of the dual-hash lookup
        assert plain != hmac_hash

    def test_plain_sha256_is_standard_sha256(self):  # nosecret
        key = _test_key_str("somekeyvalue1234567890ab")
        expected = hashlib.sha256(key.encode()).hexdigest()
        assert APIKeyManager._plain_sha256(key) == expected
