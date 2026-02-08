"""Authentication endpoints with JWT support."""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Form, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# JWT implementation using built-in modules (no external dependency)
import hashlib
import hmac
import json
import base64

router = APIRouter()
security = HTTPBearer(auto_error=False)

# JWT configuration - SECURITY CRITICAL
_jwt_secret_env = os.getenv("JWT_SECRET_KEY", "")
if not _jwt_secret_env:
    import logging
    _logger = logging.getLogger(__name__)
    if os.getenv("SARDIS_ENVIRONMENT", "dev") in ("prod", "production", "staging"):
        raise RuntimeError(
            "CRITICAL: JWT_SECRET_KEY environment variable is not set. "
            "This is required for production deployments. "
            "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    _logger.warning(
        "⚠️ JWT_SECRET_KEY not set - generating random secret. "
        "This will invalidate all tokens on restart. Set JWT_SECRET_KEY for persistent sessions."
    )
    _jwt_secret_env = secrets.token_hex(32)

JWT_SECRET = _jwt_secret_env
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    sub: str  # subject (user id)
    role: str
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    jti: str  # JWT ID for revocation


class UserInfo(BaseModel):
    username: str
    role: str


class BootstrapAPIKeyRequest(BaseModel):
    """Create an initial admin API key using an admin JWT (demo bootstrap)."""

    name: str = "Demo Admin Key"
    scopes: list[str] = Field(default_factory=lambda: ["admin", "*"])
    rate_limit: int = 100
    expires_in_days: Optional[int] = None
    organization_id: Optional[str] = None


class BootstrapAPIKeyResponse(BaseModel):
    key: str
    key_id: str
    key_prefix: str
    organization_id: str
    scopes: list[str]
    rate_limit: int
    expires_at: Optional[datetime]


def _base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    """Decode base64url string to bytes."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_jwt_token(payload: dict) -> str:
    """
    Create a JWT token using HMAC-SHA256.

    This is a minimal JWT implementation without external dependencies.
    For production with advanced features, consider using PyJWT.
    """
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{message}.{signature_b64}"


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify a JWT token and return its payload if valid.

    Returns None if token is invalid or expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # SECURITY: Validate header to prevent algorithm confusion attacks.
        # An attacker could craft a token with "alg":"none" and an empty
        # signature, or switch to an asymmetric algorithm if the secret
        # is a public key. We ONLY accept HS256.
        try:
            header = json.loads(_base64url_decode(header_b64))
        except Exception:
            return None
        if not isinstance(header, dict) or header.get("alg") != JWT_ALGORITHM:
            return None

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            JWT_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        actual_signature = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        # Decode payload
        payload = json.loads(_base64url_decode(payload_b64))

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None

        # SECURITY: Validate required claims exist
        if not isinstance(payload.get("sub"), str) or not payload.get("sub"):
            return None
        if not isinstance(payload.get("jti"), str) or not payload.get("jti"):
            return None

        return payload
    except Exception:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[UserInfo]:
    """
    Dependency to get the current authenticated user from JWT token.

    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_jwt_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Server-side revocation (logout) via cache-backed JTI blacklist
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    cache = getattr(request.app.state, "cache_service", None)
    if cache is not None:
        try:
            if await cache.is_jwt_jti_revoked(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception:
            # Fail-closed: if we cannot check revocation, treat token as invalid
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return UserInfo(
        username=payload.get("sub", "unknown"),
        role=payload.get("role", "user"),
    )


async def require_auth(
    user: Optional[UserInfo] = Depends(get_current_user),
) -> UserInfo:
    """
    Dependency that requires authentication.

    Raises HTTPException if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(
    user: UserInfo = Depends(require_auth),
) -> UserInfo:
    """
    Dependency that requires admin role.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Login with username and password.

    Returns a JWT access token on successful authentication.
    """
    admin_password = os.getenv("SARDIS_ADMIN_PASSWORD", "")
    allow_insecure_default = os.getenv("SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD", "").lower() in (
        "1",
        "true",
        "yes",
    )

    # SECURITY: Require explicit password in production
    if not admin_password:
        if allow_insecure_default and os.getenv("SARDIS_ENVIRONMENT", "dev") == "dev":
            # Explicitly opt-in only (dev convenience). Never default silently.
            import logging
            logging.getLogger(__name__).warning(
                "⚠️ SARDIS_ADMIN_PASSWORD not set - using insecure default 'change-me-immediately' "
                "because SARDIS_ALLOW_INSECURE_DEFAULT_ADMIN_PASSWORD is enabled. "
                "DO NOT use this outside local dev."
            )
            admin_password = "change-me-immediately"
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication not configured. Set SARDIS_ADMIN_PASSWORD.",
            )

    # Timing-safe comparison to prevent timing attacks
    valid_username = hmac.compare_digest(username, "admin")
    valid_password = hmac.compare_digest(password, admin_password)

    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "sub": username,
        "role": "admin",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
    }

    token = create_jwt_token(payload)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    user: UserInfo = Depends(require_auth),
):
    """
    Refresh the access token.

    Requires a valid (non-expired) token.
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "sub": user.username,
        "role": user.role,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
    }

    token = create_jwt_token(payload)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600,
    )


@router.get("/me")
async def get_me(user: UserInfo = Depends(require_auth)):
    """Get current user information."""
    return {
        "username": user.username,
        "role": user.role,
    }


@router.post("/logout")
async def logout(
    request: Request,
    user: UserInfo = Depends(require_auth),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Logout endpoint.

    Revokes the current JWT (by JTI) for the remainder of its lifetime.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_jwt_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not isinstance(jti, str) or not jti or not isinstance(exp, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl_seconds = max(0, exp - now_ts)

    cache = getattr(request.app.state, "cache_service", None)
    revoked = False
    if ttl_seconds > 0:
        if cache is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Logout temporarily unavailable",
            )
        try:
            revoked = await cache.revoke_jwt_jti(jti, ttl_seconds=ttl_seconds)
        except Exception:
            revoked = False
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Logout temporarily unavailable",
            )

    return {
        "message": "Successfully logged out",
        "revoked": revoked,
    }


@router.post("/bootstrap-api-key", response_model=BootstrapAPIKeyResponse)
async def bootstrap_api_key(
    request: Request,
    body: BootstrapAPIKeyRequest,
    user: UserInfo = Depends(require_admin),
):
    """
    Create the first admin API key using a dashboard JWT.

    This is meant for demo/dev bootstrapping, so that an operator can mint an
    API key without already having one.
    """
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").lower()
    if env in ("prod", "production") and os.getenv("SARDIS_ALLOW_BOOTSTRAP_API_KEYS", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap API keys are disabled in production",
        )

    from sardis_api.middleware.auth import get_api_key_manager

    org_id = body.organization_id or os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    manager = get_api_key_manager()
    full_key, api_key = await manager.create_key(
        organization_id=org_id,
        name=body.name,
        scopes=body.scopes,
        rate_limit=body.rate_limit,
        expires_at=expires_at,
    )

    return BootstrapAPIKeyResponse(
        key=full_key,
        key_id=api_key.key_id,
        key_prefix=api_key.key_prefix,
        organization_id=api_key.organization_id,
        scopes=api_key.scopes,
        rate_limit=api_key.rate_limit,
        expires_at=api_key.expires_at,
    )
