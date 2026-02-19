"""Authentication endpoints with JWT support (PyJWT)."""
from __future__ import annotations

import hmac
import logging
import os
import re
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, status, Form, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

_logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)

# JWT configuration - SECURITY CRITICAL
_jwt_secret_env = os.getenv("JWT_SECRET_KEY", "")
if not _jwt_secret_env:
    if os.getenv("SARDIS_ENVIRONMENT", "dev") in ("prod", "production", "staging"):
        raise RuntimeError(
            "CRITICAL: JWT_SECRET_KEY environment variable is not set. "
            "This is required for production deployments. "
            "Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    _logger.warning(
        "JWT_SECRET_KEY not set - generating random secret. "
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
    org_id: Optional[str] = None
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    jti: str  # JWT ID for revocation


class UserInfo(BaseModel):
    username: str
    role: str
    organization_id: Optional[str] = None


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


def create_jwt_token(payload: dict) -> str:
    """Create a JWT token using PyJWT with HMAC-SHA256."""
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify a JWT token and return its payload if valid.

    Returns None if token is invalid or expired.

    SECURITY: PyJWT's decode() enforces algorithm pinning via the
    `algorithms` parameter, preventing algorithm confusion attacks
    (e.g. alg:none, RS256 key confusion). Expiration is checked
    automatically when "exp" claim is present.
    """
    try:
        payload = pyjwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={
                "require": ["sub", "jti", "exp", "iat"],
            },
        )

        # Validate required claims are non-empty strings
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            return None
        if not isinstance(payload.get("jti"), str) or not payload["jti"]:
            return None

        return payload
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError, TypeError, ValueError):
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
        except (AttributeError, RuntimeError, ValueError, TypeError):
            # Fail-closed: if we cannot check revocation, treat token as invalid
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    token_org_id = payload.get("org_id") or payload.get("organization_id")
    organization_id = token_org_id if isinstance(token_org_id, str) and token_org_id.strip() else None

    return UserInfo(
        username=payload.get("sub", "unknown"),
        role=payload.get("role", "user"),
        organization_id=organization_id,
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
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    configured_org_id = os.getenv("SARDIS_DEFAULT_ORG_ID", "").strip()

    if env in ("prod", "production", "staging") and not configured_org_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT auth requires SARDIS_DEFAULT_ORG_ID in production/staging",
        )

    org_id = configured_org_id or ("org_demo" if env in ("dev", "test", "local") else "")

    payload = {
        "sub": username,
        "role": "admin",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_hex(16),
    }
    if org_id:
        payload["org_id"] = org_id

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
    if user.organization_id:
        payload["org_id"] = user.organization_id

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
        "organization_id": user.organization_id,
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
        except (RuntimeError, ConnectionError, TimeoutError, OSError):
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


# ---------------------------------------------------------------------------
# Public signup — test API key self-service
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


class SignupResponse(BaseModel):
    key: str
    key_id: str
    key_prefix: str
    organization_id: str
    scopes: list[str]
    rate_limit: int
    mode: str = "test"


# IP-based rate limiter: tracks (ip -> list of timestamps)
_signup_ip_timestamps: dict[str, list[float]] = defaultdict(list)
_SIGNUP_RATE_LIMIT = 5  # max signups per IP per hour
_SIGNUP_RATE_WINDOW = 3600  # 1 hour in seconds


def _check_signup_rate_limit(ip: str) -> None:
    """Raise 429 if this IP has exceeded the signup rate limit."""
    now = time.monotonic()
    timestamps = _signup_ip_timestamps[ip]
    # Prune expired entries
    _signup_ip_timestamps[ip] = [t for t in timestamps if now - t < _SIGNUP_RATE_WINDOW]
    if len(_signup_ip_timestamps[ip]) >= _SIGNUP_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signup requests. Try again later.",
        )


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: Request, body: SignupRequest):
    """
    Public signup endpoint — returns a test-mode API key (sk_test_ prefix).

    Gated behind SARDIS_ALLOW_PUBLIC_SIGNUP=1 environment variable.
    Test keys work only in simulated mode; no real money moves.
    """
    # Feature gate
    if os.getenv("SARDIS_ALLOW_PUBLIC_SIGNUP", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public signup is not enabled",
        )

    # Normalize email
    email = body.email.strip().lower()

    # Basic email format validation
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email address",
        )

    # IP rate limiting
    client_ip = request.client.host if request.client else "unknown"
    _check_signup_rate_limit(client_ip)

    from sardis_api.middleware.auth import get_api_key_manager

    manager = get_api_key_manager()

    # Duplicate check
    existing_org = await manager.find_org_by_email(email)
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Derive org external_id from email
    sanitized = re.sub(r"[^a-z0-9]", "_", email)
    org_id = f"org_{sanitized}"

    # Create org with email in settings (if postgres)
    if manager._use_postgres:
        import json

        pool = await manager._get_pool()
        async with pool.acquire() as conn:
            settings = json.dumps({"email": email, "signup_source": "public_api"})
            await conn.execute(
                """
                INSERT INTO organizations (external_id, name, settings)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (external_id) DO NOTHING
                """,
                org_id,
                email,
                settings,
            )

    # Create test API key
    full_key, api_key = await manager.create_key(
        organization_id=org_id,
        name=f"Test key for {email}",
        scopes=["read", "write"],
        rate_limit=30,
        test=True,
    )

    # Record the signup for rate limiting
    _signup_ip_timestamps[client_ip].append(time.monotonic())

    return SignupResponse(
        key=full_key,
        key_id=api_key.key_id,
        key_prefix=api_key.key_prefix,
        organization_id=api_key.organization_id,
        scopes=api_key.scopes,
        rate_limit=api_key.rate_limit,
        mode="test",
    )
