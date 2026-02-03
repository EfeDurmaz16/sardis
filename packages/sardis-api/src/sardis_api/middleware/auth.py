"""API Key authentication middleware."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger("sardis.api.auth")

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
    scopes: List[str]
    rate_limit: int
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]


@dataclass
class AuthContext:
    """Authentication context for a request."""
    api_key: APIKey
    organization_id: str
    scopes: List[str]
    is_authenticated: bool = True


class APIKeyManager:
    """Manages API key validation and storage."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pg_pool = None
        self._use_postgres = dsn.startswith("postgresql://") or dsn.startswith("postgres://")
        
        # In-memory cache for dev/testing
        self._keys: Dict[str, APIKey] = {}
        self._key_to_id: Dict[str, str] = {}  # prefix -> key_id

    async def _get_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None and self._use_postgres:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pg_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pg_pool

    async def _ensure_org_uuid(self, conn, organization_external_id: str) -> str:
        row = await conn.fetchrow(
            "SELECT id FROM organizations WHERE external_id = $1",
            organization_external_id,
        )
        if row:
            return str(row["id"])
        created = await conn.fetchrow(
            """
            INSERT INTO organizations (external_id, name, settings)
            VALUES ($1, $2, '{}'::jsonb)
            RETURNING id
            """,
            organization_external_id,
            organization_external_id,
        )
        return str(created["id"])

    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """
        Generate a new API key.
        
        Returns:
            (full_key, prefix, hash)
        """
        # Generate 32 random bytes = 256 bits of entropy
        key_bytes = secrets.token_bytes(32)
        full_key = f"sk_live_{secrets.token_urlsafe(32)}"
        prefix = full_key[:12]  # First 12 chars for lookup
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        
        return full_key, prefix, key_hash

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def get_prefix(key: str) -> str:
        """Get the prefix of an API key."""
        return key[:12] if len(key) >= 12 else key

    async def create_key(
        self,
        organization_id: str,
        name: str,
        scopes: List[str] = None,
        rate_limit: int = 100,
        expires_at: Optional[datetime] = None,
    ) -> tuple[str, APIKey]:
        """
        Create a new API key.
        
        Returns:
            (full_key, api_key_record)
            
        Note: The full key is only returned once and should be shown to the user.
        """
        full_key, prefix, key_hash = self.generate_api_key()
        scopes = scopes or ["read", "write"]
        
        key_id = f"key_{secrets.token_hex(8)}"
        
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
            created_at=datetime.now(timezone.utc),
            last_used_at=None,
        )
        
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                org_uuid = await self._ensure_org_uuid(conn, organization_id)
                await conn.execute(
                    """
                    INSERT INTO api_keys (
                        key_prefix, key_hash, organization_id, name,
                        scopes, rate_limit, is_active, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    prefix,
                    key_hash,
                    org_uuid,
                    name,
                    scopes,
                    rate_limit,
                    True,
                    expires_at,
                )
        else:
            self._keys[key_id] = api_key
            self._key_to_id[prefix] = key_id
        
        return full_key, api_key

    async def validate_key(self, key: str) -> Optional[APIKey]:
        """
        Validate an API key.
        
        Returns:
            APIKey if valid, None otherwise
        """
        if not key:
            return None
        
        prefix = self.get_prefix(key)
        key_hash = self.hash_key(key)
        
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT k.*, o.external_id AS organization_external_id
                    FROM api_keys k
                    JOIN organizations o ON o.id = k.organization_id
                    WHERE k.key_prefix = $1 AND k.key_hash = $2 AND k.is_active = TRUE
                    """,
                    prefix,
                    key_hash,
                )
                
                if not row:
                    return None
                
                # Check expiration
                if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
                    return None
                
                # Update last used
                await conn.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE key_prefix = $1",
                    prefix,
                )
                
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
                )
        else:
            # In-memory lookup
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
            if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
                return None
            
            # Update last used
            api_key.last_used_at = datetime.now(timezone.utc)
            
            return api_key

    async def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE api_keys SET is_active = FALSE WHERE id = $1",
                    key_id,
                )
                return "UPDATE 1" in result
        else:
            if key_id in self._keys:
                self._keys[key_id].is_active = False
                return True
            return False

    async def list_keys(self, organization_id: str) -> List[APIKey]:
        """List all API keys for an organization."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT k.*, o.external_id AS organization_external_id
                    FROM api_keys k
                    JOIN organizations o ON o.id = k.organization_id
                    WHERE o.external_id = $1
                    ORDER BY k.created_at DESC
                    """,
                    organization_id,
                )
                return [
                    APIKey(
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
                    )
                    for row in rows
                ]
        else:
            return [
                key for key in self._keys.values()
                if key.organization_id == organization_id
            ]

    async def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get an API key by ID."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT k.*, o.external_id AS organization_external_id
                    FROM api_keys k
                    JOIN organizations o ON o.id = k.organization_id
                    WHERE k.id = $1
                    """,
                    key_id,
                )
                if not row:
                    return None
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
                )
        else:
            return self._keys.get(key_id)


# Global API key manager instance (set during app initialization)
_api_key_manager: Optional[APIKeyManager] = None


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
) -> Optional[APIKey]:
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
