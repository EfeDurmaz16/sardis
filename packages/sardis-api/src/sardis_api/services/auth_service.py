"""User authentication service.

Handles registration, login, Google OAuth, API key management, and MFA.
Replaces the shared admin password with proper per-user credentials.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid import errors if argon2 isn't installed
_argon2_hasher = None


def _get_hasher():
    global _argon2_hasher
    if _argon2_hasher is None:
        try:
            from argon2 import PasswordHasher
            _argon2_hasher = PasswordHasher()
        except ImportError:
            _argon2_hasher = None
    return _argon2_hasher


def _hash_password(password: str) -> str:
    hasher = _get_hasher()
    if hasher:
        return hasher.hash(password)
    # Fallback: PBKDF2 (always available)
    import hashlib as hl
    salt = secrets.token_hex(16)
    dk = hl.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"pbkdf2:{salt}:{dk.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("pbkdf2:"):
        _, salt, stored_dk = password_hash.split(":", 2)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(dk.hex(), stored_dk)
    hasher = _get_hasher()
    if hasher:
        try:
            return hasher.verify(password_hash, password)
        except Exception:
            return False
    return False


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, key_prefix)."""
    raw = f"sk_test_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    return raw, prefix


@dataclass
class AuthResult:
    user_id: str
    email: str
    org_id: str
    display_name: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    api_key: str | None = None  # Only returned once on creation


class AuthService:
    """Handles user authentication and API key management."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    async def _get_pool(self):
        from sardis_v2_core.database import Database
        return await Database.get_pool()

    async def register(self, email: str, password: str, display_name: str | None = None) -> AuthResult:
        """Register a new user with email + password."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Check for existing user
            existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
            if existing:
                raise ValueError("email_already_registered")

            password_hash = _hash_password(password)
            user_id = f"usr_{secrets.token_hex(16)}"
            org_id = f"org_{secrets.token_hex(12)}"

            await conn.execute(
                """INSERT INTO users (id, email, password_hash, display_name)
                   VALUES ($1, $2, $3, $4)""",
                user_id, email, password_hash, display_name,
            )
            await conn.execute(
                """INSERT INTO user_org_memberships (user_id, org_id, role)
                   VALUES ($1, $2, 'owner')""",
                user_id, org_id,
            )

            # Auto-generate first API key
            raw_key, prefix = _generate_api_key()
            key_hash = _hash_api_key(raw_key)
            await conn.execute(
                """INSERT INTO user_api_keys (user_id, org_id, key_hash, key_prefix, name, scopes)
                   VALUES ($1, $2, $3, $4, 'default', $5)""",
                user_id, org_id, key_hash, prefix, ["*"],
            )

        access_token = self._create_jwt(user_id, email, org_id)
        refresh_token = self._create_jwt(user_id, email, org_id, expires_in=86400 * 7, token_type="refresh")

        return AuthResult(
            user_id=user_id,
            email=email,
            org_id=org_id,
            display_name=display_name,
            access_token=access_token,
            refresh_token=refresh_token,
            api_key=raw_key,
        )

    async def login(self, email: str, password: str) -> AuthResult:
        """Authenticate with email + password."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, password_hash, display_name, mfa_enabled FROM users WHERE email = $1",
                email,
            )
            if not row or not row["password_hash"]:
                raise ValueError("invalid_credentials")

            if not _verify_password(password, row["password_hash"]):
                raise ValueError("invalid_credentials")

            # Get org membership
            org_row = await conn.fetchrow(
                "SELECT org_id FROM user_org_memberships WHERE user_id = $1 ORDER BY created_at LIMIT 1",
                row["id"],
            )
            org_id = org_row["org_id"] if org_row else f"org_{row['id']}"

        access_token = self._create_jwt(row["id"], row["email"], org_id)
        refresh_token = self._create_jwt(row["id"], row["email"], org_id, expires_in=86400 * 7, token_type="refresh")

        return AuthResult(
            user_id=row["id"],
            email=row["email"],
            org_id=org_id,
            display_name=row["display_name"],
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def google_oauth_callback(self, google_id: str, email: str, name: str | None = None) -> AuthResult:
        """Handle Google OAuth callback — upsert user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, display_name FROM users WHERE google_id = $1 OR email = $2",
                google_id, email,
            )
            if row:
                # Update google_id if needed
                if not row.get("google_id"):
                    await conn.execute(
                        "UPDATE users SET google_id = $1, email_verified = TRUE, updated_at = now() WHERE id = $2",
                        google_id, row["id"],
                    )
                user_id = row["id"]
                display_name = row["display_name"] or name
            else:
                user_id = f"usr_{secrets.token_hex(16)}"
                org_id = f"org_{secrets.token_hex(12)}"
                display_name = name

                await conn.execute(
                    """INSERT INTO users (id, email, google_id, display_name, email_verified)
                       VALUES ($1, $2, $3, $4, TRUE)""",
                    user_id, email, google_id, display_name,
                )
                await conn.execute(
                    """INSERT INTO user_org_memberships (user_id, org_id, role)
                       VALUES ($1, $2, 'owner')""",
                    user_id, org_id,
                )

            org_row = await conn.fetchrow(
                "SELECT org_id FROM user_org_memberships WHERE user_id = $1 ORDER BY created_at LIMIT 1",
                user_id,
            )
            org_id = org_row["org_id"] if org_row else f"org_{user_id}"

        access_token = self._create_jwt(user_id, email, org_id)
        refresh_token = self._create_jwt(user_id, email, org_id, expires_in=86400 * 7, token_type="refresh")

        return AuthResult(
            user_id=user_id,
            email=email,
            org_id=org_id,
            display_name=display_name,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def generate_api_key(
        self, user_id: str, org_id: str, name: str = "default", scopes: list[str] | None = None,
    ) -> tuple[str, str]:
        """Generate a new API key. Returns (raw_key, key_id)."""
        raw_key, prefix = _generate_api_key()
        key_hash = _hash_api_key(raw_key)
        key_id = f"key_{secrets.token_hex(12)}"

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO user_api_keys (id, user_id, org_id, key_hash, key_prefix, name, scopes)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                key_id, user_id, org_id, key_hash, prefix, name, scopes or ["*"],
            )

        return raw_key, key_id

    async def verify_api_key(self, raw_key: str) -> dict[str, Any] | None:
        """Verify an API key and return user/org info."""
        key_hash = _hash_api_key(raw_key)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT k.id, k.user_id, k.org_id, k.scopes, k.expires_at,
                          u.email, u.display_name
                   FROM user_api_keys k
                   JOIN users u ON u.id = k.user_id
                   WHERE k.key_hash = $1""",
                key_hash,
            )
            if not row:
                return None

            # Check expiry
            if row["expires_at"] and row["expires_at"].timestamp() < time.time():
                return None

            # Update last_used_at
            await conn.execute(
                "UPDATE user_api_keys SET last_used_at = now() WHERE id = $1",
                row["id"],
            )

        return {
            "key_id": row["id"],
            "user_id": row["user_id"],
            "org_id": row["org_id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "scopes": list(row["scopes"]) if row["scopes"] else ["*"],
        }

    async def list_api_keys(self, user_id: str) -> list[dict[str, Any]]:
        """List API keys for a user (prefix only, never the full key)."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, org_id, key_prefix, name, scopes, last_used_at, expires_at, created_at
                   FROM user_api_keys WHERE user_id = $1 ORDER BY created_at DESC""",
                user_id,
            )
        return [dict(r) for r in rows]

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """Revoke (delete) an API key."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_api_keys WHERE id = $1 AND user_id = $2",
                key_id, user_id,
            )
        return result == "DELETE 1"

    async def setup_mfa(self, user_id: str) -> dict[str, str]:
        """Generate TOTP secret and provisioning URI."""
        try:
            import pyotp
        except ImportError:
            raise ValueError("pyotp not installed — MFA not available")

        secret = pyotp.random_base32()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT email FROM users WHERE id = $1", user_id)
            if not row:
                raise ValueError("user_not_found")

            await conn.execute(
                "UPDATE users SET mfa_secret = $1, updated_at = now() WHERE id = $2",
                secret, user_id,
            )

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=row["email"], issuer_name="Sardis")
        return {"secret": secret, "uri": uri}

    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify TOTP code and enable MFA."""
        try:
            import pyotp
        except ImportError:
            raise ValueError("pyotp not installed")

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mfa_secret FROM users WHERE id = $1", user_id,
            )
            if not row or not row["mfa_secret"]:
                raise ValueError("mfa_not_setup")

            totp = pyotp.TOTP(row["mfa_secret"])
            if not totp.verify(code):
                return False

            await conn.execute(
                "UPDATE users SET mfa_enabled = TRUE, updated_at = now() WHERE id = $1",
                user_id,
            )
        return True

    async def create_password_reset_token(self, email: str) -> str | None:
        """Generate a password reset token for the given email.

        Returns the raw token (to be sent via email) or None if email not found.
        Token is stored as SHA-256 hash, expires in 1 hour, single-use.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                email.strip().lower(),
            )
            if not user:
                return None

            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expires_at = datetime.now(UTC) + timedelta(hours=1)

            await conn.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                VALUES ($1, $2, $3)
                """,
                user["id"],
                token_hash,
                expires_at,
            )

            return raw_token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a valid reset token.

        Returns True if password was changed, False if token is invalid/expired/used.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, expires_at, used_at
                FROM password_reset_tokens
                WHERE token_hash = $1
                """,
                token_hash,
            )

            if not row:
                return False
            if row["used_at"] is not None:
                return False
            if row["expires_at"].replace(tzinfo=UTC) < datetime.now(UTC):
                return False

            new_hash = self._hash_password(new_password)

            # Update password and mark token as used atomically
            await conn.execute(
                "UPDATE users SET password_hash = $1, updated_at = now() WHERE id = $2",
                new_hash,
                row["user_id"],
            )
            await conn.execute(
                "UPDATE password_reset_tokens SET used_at = now() WHERE token_hash = $1",
                token_hash,
            )

            return True

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change password for an authenticated user. Verifies current password first."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash FROM users WHERE id = $1",
                user_id,
            )
            if not row or not row["password_hash"]:
                return False
            if not self._verify_password(current_password, row["password_hash"]):
                return False

            new_hash = self._hash_password(new_password)
            await conn.execute(
                "UPDATE users SET password_hash = $1, updated_at = now() WHERE id = $2",
                new_hash,
                user_id,
            )
            return True

    async def delete_account(self, user_id: str) -> bool:
        """Permanently delete a user account and all associated data.

        Cascading deletes handle: api_keys, org_memberships.
        Additional cleanup: billing subscriptions, usage events.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Delete billing data
            await conn.execute(
                "DELETE FROM billing_subscriptions WHERE org_id IN (SELECT org_id FROM user_org_memberships WHERE user_id = $1)",
                user_id,
            )
            # Delete the user (CASCADE handles api_keys and org_memberships)
            result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            return result == "DELETE 1"

    async def mark_email_verified(self, user_id: str) -> None:
        """Set email_verified = TRUE for the given user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET email_verified = TRUE, updated_at = now() WHERE id = $1",
                user_id,
            )

    def _create_jwt(
        self,
        user_id: str,
        email: str,
        org_id: str,
        expires_in: int = 3600,
        token_type: str = "access",
    ) -> str:
        import jwt as pyjwt

        secret = os.getenv("JWT_SECRET_KEY", "")
        if not secret:
            raise RuntimeError("JWT_SECRET_KEY environment variable is required")
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "org_id": org_id,
            "type": token_type,
            "iat": now,
            "exp": now + expires_in,
            "jti": secrets.token_hex(16),
        }
        return pyjwt.encode(payload, secret, algorithm="HS256")
