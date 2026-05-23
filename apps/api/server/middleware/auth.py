"""API Key authentication middleware.

Reads API keys from the ``ba_apikey`` table which is **shared** with the
better-auth api-key plugin running in the Next.js dashboard.  Both services
(FastAPI sardis-api and Next.js dashboard) connect to the same Neon PostgreSQL
database.  The dashboard writes keys via better-auth; this module validates
them on the FastAPI side by querying the same table directly.

Key hashing
-----------
better-auth's built-in api-key plugin uses plain SHA-256 by default.  We
keep HMAC-SHA256 as the *primary* hash for keys created via the FastAPI CRUD
endpoints (stronger against rainbow-table attacks), and fall back to plain
SHA-256 for keys created by the dashboard through better-auth.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger("server.api.auth")

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass
class APIKey:
    """API key data."""
    key_id: str
    key_prefix: str
    key_hash: str
    organization_id: str
    name: str
    scopes: list[str]
    rate_limit: int
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None
    environment: str = "test"

    @property
    def default_chain(self) -> str:
        """Resolve the default chain based on environment.

        - test → Base Sepolia (testnet)
        - live → Tempo (mainnet)
        """
        return _ENVIRONMENT_CHAIN_MAP.get(self.environment, "base_sepolia")


# Maps API key environment to the default chain for transaction routing.
_ENVIRONMENT_CHAIN_MAP: dict[str, str] = {
    "test": "base_sepolia",
    "live": "tempo",
}


@dataclass
class AuthContext:
    """Authentication context for a request."""
    api_key: APIKey
    organization_id: str
    scopes: list[str]
    is_authenticated: bool = True
    environment: str = "test"
    default_chain: str = "base_sepolia"


def _permissions_to_scopes(permissions: dict | list | str | None) -> list[str]:
    """Convert better-auth permissions JSONB to a flat scopes list.

    better-auth stores permissions as ``{"wallets": ["read","write"], ...}``.
    The legacy Sardis API uses flat scope strings like ``"read"``, ``"write"``,
    ``"admin"``, ``"*"``, or namespaced ``"api_keys:create"`` etc.

    This helper flattens the nested structure into a deduplicated list of
    simple scope strings that the existing permission-checking code expects.
    """
    if permissions is None:
        return ["read", "write"]

    if isinstance(permissions, str):
        try:
            permissions = json.loads(permissions)
        except (json.JSONDecodeError, TypeError):
            return ["read", "write"]

    if isinstance(permissions, list):
        return list(permissions) if permissions else ["read", "write"]

    if isinstance(permissions, dict):
        scopes: set[str] = set()
        for _resource, actions in permissions.items():
            if isinstance(actions, list):
                for a in actions:
                    scopes.add(str(a))
            elif isinstance(actions, str):
                scopes.add(actions)
        # If the permissions dict includes write for admin resource, grant admin
        if "write" in (permissions.get("admin") or []):
            scopes.add("admin")
        return sorted(scopes) if scopes else ["read", "write"]

    return ["read", "write"]


class APIKeyManager:
    """Manages API key validation and storage.

    Backs onto the ``ba_apikey`` table shared with better-auth.
    """

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pg_pool = None
        self._use_postgres = dsn.startswith("postgresql://") or dsn.startswith("postgres://")

        # In-memory cache for dev/testing when no Postgres DSN is provided
        self._keys: dict[str, APIKey] = {}
        self._key_to_id: dict[str, str] = {}  # prefix -> key_id

    async def _get_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None:
            from sardis.core.database import Database
            self._pg_pool = await Database.get_pool()
        return self._pg_pool

    @staticmethod
    def generate_api_key(*, test: bool = False) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            (full_key, prefix, hash)

        SECURITY: The hash MUST be produced by hash_key() (HMAC-SHA256 with prefix
        as salt) so that validate_key() can reproduce it. Previously this method
        used plain SHA-256 while validate_key used HMAC-SHA256, so newly created
        keys could never be validated — a critical inconsistency.
        """
        key_prefix = "sk_test_" if test else "sk_live_"
        full_key = f"{key_prefix}{secrets.token_urlsafe(32)}"
        prefix = full_key[:12]  # First 12 chars for lookup
        key_hash = APIKeyManager.hash_key(full_key)

        return full_key, prefix, key_hash

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for comparison using HMAC-SHA256 with the key prefix as salt.

        SECURITY: Plain SHA-256 without salt allows rainbow table attacks and
        means identical keys across orgs produce identical hashes. HMAC with
        the key prefix as salt mitigates both issues while remaining fast enough
        for API key validation (unlike bcrypt/argon2 which are designed for passwords).
        """
        prefix = key[:12] if len(key) >= 12 else key
        return hmac.new(prefix.encode(), key.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def get_prefix(key: str) -> str:
        """Get the prefix of an API key."""
        return key[:12] if len(key) >= 12 else key

    @staticmethod
    def resolve_environment(key_or_prefix: str) -> str:
        """Derive the environment from an API key or its stored prefix.

        Convention:
        - Keys starting with ``sk_live_`` → ``"live"``
        - Everything else (including ``sk_test_``) → ``"test"``
        """
        if key_or_prefix.startswith("sk_live_"):
            return "live"
        return "test"

    @staticmethod
    def _plain_sha256(key: str) -> str:
        """Plain SHA-256 hash — used by better-auth when creating keys.

        better-auth's built-in api-key plugin stores keys with plain SHA-256.
        This fallback ensures keys created via the dashboard can be validated
        here alongside HMAC-SHA256 hashes from FastAPI-created keys.
        """
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_key(
        self,
        organization_id: str,
        name: str,
        scopes: list[str] | None = None,
        rate_limit: int = 100,
        expires_at: datetime | None = None,
        *,
        test: bool = False,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key in the ba_apikey table.

        Returns:
            (full_key, api_key_record)

        Note: The full key is only returned once and should be shown to the user.
        """
        full_key, prefix, key_hash = self.generate_api_key(test=test)
        scopes = scopes or ["read", "write"]
        key_env = self.resolve_environment(full_key)
        config_id = key_env  # "test" or "live"

        key_id = f"key_{secrets.token_hex(8)}"

        # Build permissions JSONB from flat scopes for better-auth compatibility.
        # If scopes contain resource-specific permissions, nest them; otherwise
        # apply the same actions to all default resources.
        permissions_dict = self._scopes_to_permissions(scopes)

        api_key = APIKey(
            key_id=key_id,
            key_prefix=prefix,
            key_hash=key_hash,
            organization_id=organization_id,
            name=name,
            scopes=scopes,
            rate_limit=rate_limit,
            is_active=True,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
            last_used_at=None,
            environment=key_env,
        )

        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Resolve user_id from organization_id.
                # ba_apikey.user_id references ba_user.id.
                # We find the first user in that org (or fall back to org_id).
                user_id = await self._resolve_user_id(conn, organization_id)

                await conn.execute(
                    """
                    INSERT INTO ba_apikey (
                        id, key, name, prefix, user_id, config_id,
                        rate_limit_enabled, rate_limit_max, rate_limit_time_window,
                        enabled, expires_at, created_at, updated_at,
                        permissions, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6,
                        TRUE, $7, 3600000,
                        TRUE, $8, NOW(), NOW(),
                        $9, $10
                    )
                    """,
                    key_id,
                    key_hash,
                    name,
                    prefix,
                    user_id,
                    config_id,
                    rate_limit,
                    expires_at,
                    json.dumps(permissions_dict),
                    json.dumps({"org_id": organization_id, "source": "fastapi"}),
                )
        else:
            self._keys[key_id] = api_key
            self._key_to_id[prefix] = key_id

        return full_key, api_key

    @staticmethod
    def _scopes_to_permissions(scopes: list[str]) -> dict:
        """Convert flat scopes list to better-auth permissions JSONB format.

        Maps simple scope strings (read, write, admin, *) into the nested
        ``{"resource": ["action", ...]}`` structure that better-auth expects.
        """
        default_resources = ["wallets", "payments", "policies", "mandates", "agents"]

        if "*" in scopes or "admin" in scopes:
            perms = {r: ["read", "write"] for r in default_resources}
            perms["admin"] = ["read", "write"]
            return perms

        actions = set()
        for s in scopes:
            if s in ("read", "write"):
                actions.add(s)
        actions = sorted(actions) if actions else ["read"]
        return {r: list(actions) for r in default_resources}

    async def _resolve_user_id(self, conn, organization_id: str) -> str:
        """Resolve a ba_user.id from an organization external ID.

        The ba_apikey table references ba_user(id), not organizations.
        We find the first user associated with the org, or fall back
        to using organization_id directly (for bootstrapping scenarios).
        """
        row = await conn.fetchrow(
            "SELECT id FROM ba_user WHERE org_id = $1 LIMIT 1",
            organization_id,
        )
        if row:
            return str(row["id"])

        # Fallback: check if organization_id itself is a ba_user.id
        row = await conn.fetchrow(
            "SELECT id FROM ba_user WHERE id = $1",
            organization_id,
        )
        if row:
            return str(row["id"])

        # Last resort: use the org_id as-is (bootstrap/dev scenario).
        # This may violate FK if ba_user row doesn't exist yet,
        # but will work in dev/test where FK checks are relaxed.
        logger.warning(
            "No ba_user found for org_id=%s; using org_id as user_id fallback",
            organization_id,
        )
        return organization_id

    async def validate_key(self, key: str) -> APIKey | None:
        """
        Validate an API key against the ba_apikey table.

        Tries HMAC-SHA256 hash first (FastAPI-created keys), then falls back
        to plain SHA-256 (better-auth dashboard-created keys).

        Returns:
            APIKey if valid, None otherwise
        """
        if not key:
            return None

        prefix = self.get_prefix(key)
        key_hash = self.hash_key(key)
        # Also compute plain SHA-256 for keys created by better-auth dashboard
        plain_hash = self._plain_sha256(key)

        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Try HMAC-SHA256 hash first (keys created by FastAPI APIKeyManager)
                row = await conn.fetchrow(
                    """
                    SELECT ak.*, u.org_id AS user_org_id
                    FROM ba_apikey ak
                    LEFT JOIN ba_user u ON u.id = ak.user_id
                    WHERE ak.prefix = $1 AND ak.key = $2 AND ak.enabled = TRUE
                    """,
                    prefix,
                    key_hash,
                )
                # Fallback: plain SHA-256 (keys created by better-auth dashboard)
                if not row:
                    row = await conn.fetchrow(
                        """
                        SELECT ak.*, u.org_id AS user_org_id
                        FROM ba_apikey ak
                        LEFT JOIN ba_user u ON u.id = ak.user_id
                        WHERE ak.prefix = $1 AND ak.key = $2 AND ak.enabled = TRUE
                        """,
                        prefix,
                        plain_hash,
                    )
                    if row:
                        logger.info(
                            "API key '%s...' validated via plain SHA-256 "
                            "(better-auth dashboard key).",
                            prefix,
                        )

                if row:
                    # Check expiration
                    if row["expires_at"] and row["expires_at"] < datetime.now(UTC):
                        return None

                    # Update last request timestamp and request count
                    await conn.execute(
                        """
                        UPDATE ba_apikey
                        SET last_request = NOW(),
                            request_count = request_count + 1,
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                    )

                    env = row["config_id"] or self.resolve_environment(row["prefix"] or "")
                    org_id = row["user_org_id"] or row["user_id"]
                    permissions = row["permissions"]
                    scopes = _permissions_to_scopes(permissions)

                    return APIKey(
                        key_id=str(row["id"]),
                        key_prefix=row["prefix"] or "",
                        key_hash=row["key"],
                        organization_id=str(org_id),
                        name=row["name"] or "API Key",
                        scopes=scopes,
                        rate_limit=row["rate_limit_max"] or 100,
                        is_active=row["enabled"],
                        expires_at=row["expires_at"],
                        created_at=row["created_at"],
                        last_used_at=row["last_request"],
                        environment=env,
                    )

                # Legacy fallback: check old api_keys table for backward compat
                # during migration period. Remove after full migration.
                legacy_key = await self._check_legacy_api_keys(conn, prefix, key_hash, plain_hash)
                if legacy_key:
                    return legacy_key

                return None
        else:
            # In-memory lookup (dev/testing without Postgres)
            key_id = self._key_to_id.get(prefix)
            if not key_id:
                return None

            api_key = self._keys.get(key_id)
            if not api_key:
                return None

            # Verify hash
            if not hmac.compare_digest(api_key.key_hash, key_hash):
                return None

            # Check active and expiration
            if not api_key.is_active:
                return None
            if api_key.expires_at and api_key.expires_at < datetime.now(UTC):
                return None

            # Update last used
            api_key.last_used_at = datetime.now(UTC)

            return api_key

    async def _check_legacy_api_keys(
        self, conn, prefix: str, key_hash: str, plain_hash: str
    ) -> APIKey | None:
        """Check the legacy api_keys and user_api_keys tables.

        This provides backward compatibility during the migration period.
        Keys found here still work but callers should migrate to ba_apikey.
        """
        # Legacy api_keys table
        for hash_val in (key_hash, plain_hash):
            row = await conn.fetchrow(
                """
                SELECT k.*, o.external_id AS organization_external_id
                FROM api_keys k
                JOIN organizations o ON o.id = k.organization_id
                WHERE k.key_prefix = $1 AND k.key_hash = $2 AND k.is_active = TRUE
                """,
                prefix,
                hash_val,
            )
            if row:
                if hash_val == plain_hash:
                    logger.warning(
                        "API key '%s...' found in legacy api_keys table with "
                        "plain SHA-256. Migrate to ba_apikey table.",
                        prefix,
                    )
                else:
                    logger.info(
                        "API key '%s...' found in legacy api_keys table. "
                        "Migrate to ba_apikey table.",
                        prefix,
                    )

                if row["expires_at"] and row["expires_at"] < datetime.now(UTC):
                    return None

                await conn.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE key_prefix = $1",
                    prefix,
                )

                env = self.resolve_environment(row["key_prefix"])
                return APIKey(
                    key_id=str(row["id"]),
                    key_prefix=row["key_prefix"],
                    key_hash=row["key_hash"],
                    organization_id=str(row["organization_external_id"]),
                    name=row["name"],
                    scopes=row["scopes"],
                    rate_limit=row["rate_limit"],
                    is_active=row["is_active"],
                    expires_at=row["expires_at"],
                    created_at=row["created_at"],
                    last_used_at=row["last_used_at"],
                    environment=env,
                )

        # Legacy user_api_keys table
        for hash_val in (key_hash, plain_hash):
            user_row = await conn.fetchrow(
                """
                SELECT id, user_id, org_id, key_prefix, key_hash, name,
                       scopes, expires_at, created_at, last_used_at
                FROM user_api_keys
                WHERE key_hash = $1
                """,
                hash_val,
            )
            if user_row:
                if user_row["expires_at"] and user_row["expires_at"] < datetime.now(UTC):
                    return None
                await conn.execute(
                    "UPDATE user_api_keys SET last_used_at = NOW() WHERE id = $1",
                    user_row["id"],
                )
                user_env = self.resolve_environment(user_row["key_prefix"] or "")
                return APIKey(
                    key_id=str(user_row["id"]),
                    key_prefix=user_row["key_prefix"],
                    key_hash=user_row["key_hash"],
                    organization_id=str(user_row["org_id"]),
                    name=user_row["name"] or "default",
                    scopes=list(user_row["scopes"]) if user_row["scopes"] else ["*"],
                    rate_limit=100,
                    is_active=True,
                    expires_at=user_row["expires_at"],
                    created_at=user_row["created_at"],
                    last_used_at=user_row["last_used_at"],
                    environment=user_env,
                )

        return None

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by setting enabled=FALSE in ba_apikey."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE ba_apikey SET enabled = FALSE, updated_at = NOW() WHERE id = $1",
                    key_id,
                )
                return "UPDATE 1" in result
        else:
            if key_id in self._keys:
                self._keys[key_id].is_active = False
                return True
            return False

    async def list_keys(self, organization_id: str) -> list[APIKey]:
        """List all API keys for an organization from ba_apikey."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT ak.*, u.org_id AS user_org_id
                    FROM ba_apikey ak
                    LEFT JOIN ba_user u ON u.id = ak.user_id
                    WHERE u.org_id = $1 OR ak.user_id = $1
                    ORDER BY ak.created_at DESC
                    """,
                    organization_id,
                )
                return [
                    APIKey(
                        key_id=str(row["id"]),
                        key_prefix=row["prefix"] or "",
                        key_hash=row["key"],
                        organization_id=str(row["user_org_id"] or row["user_id"]),
                        name=row["name"] or "API Key",
                        scopes=_permissions_to_scopes(row["permissions"]),
                        rate_limit=row["rate_limit_max"] or 100,
                        is_active=row["enabled"],
                        expires_at=row["expires_at"],
                        created_at=row["created_at"],
                        last_used_at=row["last_request"],
                        environment=row["config_id"] or self.resolve_environment(row["prefix"] or ""),
                    )
                    for row in rows
                ]
        else:
            return [
                key for key in self._keys.values()
                if key.organization_id == organization_id
            ]

    async def get_key(self, key_id: str) -> APIKey | None:
        """Get an API key by ID from ba_apikey."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT ak.*, u.org_id AS user_org_id
                    FROM ba_apikey ak
                    LEFT JOIN ba_user u ON u.id = ak.user_id
                    WHERE ak.id = $1
                    """,
                    key_id,
                )
                if not row:
                    return None
                return APIKey(
                    key_id=str(row["id"]),
                    key_prefix=row["prefix"] or "",
                    key_hash=row["key"],
                    organization_id=str(row["user_org_id"] or row["user_id"]),
                    name=row["name"] or "API Key",
                    scopes=_permissions_to_scopes(row["permissions"]),
                    rate_limit=row["rate_limit_max"] or 100,
                    is_active=row["enabled"],
                    expires_at=row["expires_at"],
                    created_at=row["created_at"],
                    last_used_at=row["last_request"],
                    environment=row["config_id"] or self.resolve_environment(row["prefix"] or ""),
                )
        else:
            return self._keys.get(key_id)

    async def find_org_by_email(self, email: str) -> str | None:
        """Find an organization by email via ba_user table.

        Returns the org_id if found, None otherwise.
        """
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT org_id FROM ba_user WHERE email = $1 AND org_id IS NOT NULL",
                    email,
                )
                if row:
                    return str(row["org_id"])
                # Fallback: check legacy organizations table
                row = await conn.fetchrow(
                    "SELECT external_id FROM organizations WHERE settings->>'email' = $1",
                    email,
                )
                if row:
                    return str(row["external_id"])
                return None
        else:
            return None


# Global API key manager instance (set during app initialization)
_api_key_manager: APIKeyManager | None = None


def set_api_key_manager(manager: APIKeyManager):
    """Set the global API key manager."""
    global _api_key_manager
    _api_key_manager = manager


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager."""
    if _api_key_manager is None:
        raise RuntimeError("API key manager not initialized")
    return _api_key_manager


async def get_api_key(
    api_key: str = Security(api_key_header),
) -> APIKey | None:
    """
    Dependency to get and validate API key from request.

    Returns None if no key provided (for optional auth).
    Raises HTTPException if key is invalid.
    """
    if not api_key:
        return None

    manager = get_api_key_manager()
    validated_key = await manager.validate_key(api_key)

    if not validated_key:
        env = os.getenv("SARDIS_ENVIRONMENT", "").strip().lower()
        test_key = os.getenv("SARDIS_TEST_API_KEY", "")
        if test_key and env in {"dev", "test", "local"} and api_key == test_key:
            # Dev/test convenience key to keep local and CI integration tests
            # deterministic without explicit bootstrap.
            bootstrap_env = APIKeyManager.resolve_environment(test_key)
            return APIKey(
                key_id="key_test_bootstrap",
                key_prefix=test_key[:12],
                key_hash=APIKeyManager.hash_key(test_key),
                organization_id=os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo"),
                name="Test Bootstrap Key",
                scopes=["*"],
                rate_limit=1000,
                is_active=True,
                expires_at=None,
                created_at=datetime.now(UTC),
                last_used_at=datetime.now(UTC),
                environment=bootstrap_env,
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return validated_key


async def require_api_key(
    api_key: str = Security(api_key_header),
) -> APIKey:
    """
    Dependency that requires a valid API key.

    Raises HTTPException if no key or invalid key.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    validated_key = await get_api_key(api_key)
    if not validated_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return validated_key


def require_scope(required_scope: str):
    """
    Dependency factory that requires a specific scope.

    Usage:
        @router.post("/resource", dependencies=[Depends(require_scope("write"))])
    """
    async def check_scope(api_key: APIKey = Security(require_api_key)) -> APIKey:
        if required_scope not in api_key.scopes and "*" not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required",
            )
        return api_key

    return check_scope


def enforce_key_environment(api_key: APIKey, requested_mode: str | None = None) -> None:
    """Enforce that the API key environment matches the requested chain mode.

    Rules:
    - ``sk_test_`` keys (environment="test") can only use simulated chain mode.
      They must not execute real transactions on mainnet.
    - ``sk_live_`` keys (environment="live") can use live chain mode.

    Args:
        api_key: The validated API key.
        requested_mode: The chain mode requested by the caller.  If ``None``,
            the global ``SARDIS_CHAIN_MODE`` env var is used.

    Raises:
        HTTPException 403 if a test key attempts to use live chain mode.
    """
    effective_mode = (requested_mode or os.getenv("SARDIS_CHAIN_MODE", "simulated")).strip().lower()
    if api_key.environment == "test" and effective_mode == "live":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Test API keys (sk_test_) cannot execute live transactions. "
                "Create a live API key (sk_live_) to use live chain mode."
            ),
        )
