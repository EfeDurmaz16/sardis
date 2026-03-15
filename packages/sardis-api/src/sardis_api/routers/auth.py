"""Authentication endpoints with JWT support (PyJWT)."""
from __future__ import annotations

import hmac
import logging
import os
import re
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
    org_id: str | None = None
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    jti: str  # JWT ID for revocation


class UserInfo(BaseModel):
    username: str
    role: str
    organization_id: str | None = None


class BootstrapAPIKeyRequest(BaseModel):
    """Create an initial admin API key using an admin JWT (demo bootstrap)."""

    name: str = "Demo Admin Key"
    scopes: list[str] = Field(default_factory=lambda: ["admin", "*"])
    rate_limit: int = 100
    expires_in_days: int | None = None
    organization_id: str | None = None


class BootstrapAPIKeyResponse(BaseModel):
    key: str
    key_id: str
    key_prefix: str
    organization_id: str
    scopes: list[str]
    rate_limit: int
    expires_at: datetime | None


def create_jwt_token(payload: dict) -> str:
    """Create a JWT token using PyJWT with HMAC-SHA256."""
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict | None:
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
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserInfo | None:
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
    user: UserInfo | None = Depends(get_current_user),
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
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    Login with username/email and password.

    Tries user auth (from users table) first, then falls back to
    shared admin password for backward compatibility (with deprecation warning).
    """
    # Try user-based auth first
    database_url = getattr(getattr(request.app, "state", None), "database_url", None)
    if database_url and username != "admin":
        try:
            from sardis_api.services.auth_service import AuthService
            auth_svc = AuthService(dsn=database_url)
            result = await auth_svc.login(email=username, password=password)
            return TokenResponse(
                access_token=result.access_token,
                token_type="bearer",
                expires_in=3600,
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as exc:
            _logger.warning(
                "Primary auth failed for user %r: %s: %s",
                username,
                type(exc).__name__,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication_failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Shared admin password was removed. Use per-user accounts.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials. Register at POST /auth/register or reset password at POST /auth/forgot-password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    user: UserInfo = Depends(require_auth),
):
    """
    Refresh the access token.

    Requires a valid (non-expired) token.
    """
    now = datetime.now(UTC)
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
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
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

    now_ts = int(datetime.now(UTC).timestamp())
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
        expires_at = datetime.now(UTC) + timedelta(days=body.expires_in_days)

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


# ---------------------------------------------------------------------------
# User-based authentication endpoints (Phase 2)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = None


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    org_id: str
    access_token: str
    api_key: str


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserLoginResponse(BaseModel):
    user_id: str
    email: str
    org_id: str
    access_token: str
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    name: str = "default"
    scopes: list[str] = Field(default_factory=lambda: ["*"])


class APIKeyResponse(BaseModel):
    key: str | None = None  # Only in create response
    key_id: str
    key_prefix: str
    org_id: str
    name: str
    scopes: list[str]


class MFASetupResponse(BaseModel):
    secret: str
    uri: str


class MFAVerifyRequest(BaseModel):
    code: str


# IP-based rate limiter for register endpoint: tracks (ip -> list of timestamps)
_register_ip_timestamps: dict[str, list[float]] = defaultdict(list)
_REGISTER_RATE_LIMIT = 5  # max registrations per IP per hour
_REGISTER_RATE_WINDOW = 3600  # 1 hour in seconds


def _check_register_rate_limit(ip: str) -> None:
    """Raise 429 if this IP has exceeded the register rate limit."""
    now = time.monotonic()
    timestamps = _register_ip_timestamps[ip]
    # Prune expired entries
    _register_ip_timestamps[ip] = [t for t in timestamps if now - t < _REGISTER_RATE_WINDOW]
    if len(_register_ip_timestamps[ip]) >= _REGISTER_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration requests. Try again later.",
        )


def _get_auth_service(request: Request):
    database_url = getattr(getattr(request.app, "state", None), "database_url", None)
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User authentication requires a database. Set DATABASE_URL.",
        )
    from sardis_api.services.auth_service import AuthService
    return AuthService(dsn=database_url)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: Request, body: RegisterRequest):
    """Register a new user account with email + password."""
    # IP rate limiting
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    # x-forwarded-for may be a comma-separated list; take the first (original client) IP
    client_ip = client_ip.split(",")[0].strip()
    _check_register_rate_limit(client_ip)

    auth_svc = _get_auth_service(request)
    try:
        result = await auth_svc.register(
            email=body.email.strip().lower(),
            password=body.password,
            display_name=body.display_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # Record the registration for rate limiting
    _register_ip_timestamps[client_ip].append(time.monotonic())

    # Analytics: identify and track signup (fire-and-forget, never blocks the request)
    from sardis_api.analytics.posthog_tracker import SIGNUP_COMPLETED, identify_user, track_event
    identify_user(result.user_id, {"email": result.email, "plan": "free"})
    track_event(result.user_id, SIGNUP_COMPLETED, {"method": "email"})

    return RegisterResponse(
        user_id=result.user_id,
        email=result.email,
        org_id=result.org_id,
        access_token=result.access_token,
        api_key=result.api_key,
    )


@router.get("/google")
async def google_oauth_redirect():
    """Initiate Google OAuth redirect.

    Generates a cryptographic state token for CSRF protection,
    stores it in a signed httponly cookie, and includes it in the
    Google redirect URL.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID.",
        )
    redirect_uri = os.getenv("SARDIS_GOOGLE_REDIRECT_URI", "https://api.sardis.sh/api/v2/auth/google/callback")
    scope = "openid email profile"

    # Generate CSRF state token
    state_token = secrets.token_urlsafe(32)

    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&redirect_uri={redirect_uri}"
        f"&response_type=code&scope={scope}&access_type=offline"
        f"&state={state_token}"
    )
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url=url)
    response.set_cookie(
        key="oauth_state",
        value=state_token,
        httponly=True,
        secure=os.getenv("SARDIS_ENVIRONMENT", "dev") != "dev",
        samesite="lax",
        max_age=600,  # 10 minutes — generous for the OAuth round-trip
    )
    return response


@router.get("/google/callback")
async def google_oauth_callback(request: Request, code: str):
    """Handle Google OAuth callback.

    Validates the CSRF state parameter before exchanging the
    authorization code for tokens.
    """
    import httpx

    # --- CSRF state validation ---------------------------------------------------
    state_param = request.query_params.get("state")
    state_cookie = request.cookies.get("oauth_state")

    if not state_param or not state_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state parameter — possible CSRF attack",
        )

    if not hmac.compare_digest(state_param, state_cookie):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state parameter — possible CSRF attack",
        )
    # -----------------------------------------------------------------------------

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.getenv("SARDIS_GOOGLE_REDIRECT_URI", "https://api.sardis.sh/api/v2/auth/google/callback")

    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange OAuth code")

        tokens = token_resp.json()
        # Get user info
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        userinfo = userinfo_resp.json()

    auth_svc = _get_auth_service(request)
    result = await auth_svc.google_oauth_callback(
        google_id=userinfo["id"],
        email=userinfo["email"],
        name=userinfo.get("name"),
    )

    from fastapi.responses import JSONResponse

    response = JSONResponse(content=UserLoginResponse(
        user_id=result.user_id,
        email=result.email,
        org_id=result.org_id,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    ).model_dump())

    # Clear the oauth_state cookie now that it has been consumed
    response.delete_cookie(key="oauth_state")

    return response


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(request: Request, user: UserInfo = Depends(require_auth)):
    """Generate TOTP secret and provisioning URI for MFA setup."""
    auth_svc = _get_auth_service(request)
    result = await auth_svc.setup_mfa(user_id=user.username)
    return MFASetupResponse(**result)


@router.post("/mfa/verify")
async def verify_mfa(request: Request, body: MFAVerifyRequest, user: UserInfo = Depends(require_auth)):
    """Verify TOTP code to enable MFA."""
    auth_svc = _get_auth_service(request)
    valid = await auth_svc.verify_mfa(user_id=user.username, code=body.code)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    return {"mfa_enabled": True}


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    body: APIKeyCreateRequest,
    user: UserInfo = Depends(require_auth),
):
    """Generate a new API key for the authenticated user."""
    auth_svc = _get_auth_service(request)
    org_id = user.organization_id or "org_demo"
    raw_key, key_id = await auth_svc.generate_api_key(
        user_id=user.username,
        org_id=org_id,
        name=body.name,
        scopes=body.scopes,
    )
    return APIKeyResponse(
        key=raw_key,
        key_id=key_id,
        key_prefix=raw_key[:12],
        org_id=org_id,
        name=body.name,
        scopes=body.scopes,
    )


@router.get("/api-keys")
async def list_api_keys(request: Request, user: UserInfo = Depends(require_auth)):
    """List API keys for the authenticated user (prefix only)."""
    auth_svc = _get_auth_service(request)
    keys = await auth_svc.list_api_keys(user_id=user.username)
    return {"keys": keys}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    request: Request,
    key_id: str,
    user: UserInfo = Depends(require_auth),
):
    """Revoke an API key."""
    auth_svc = _get_auth_service(request)
    deleted = await auth_svc.revoke_api_key(key_id=key_id, user_id=user.username)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"revoked": True}


# ---------------------------------------------------------------------------
# Password reset (self-serve account recovery)
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


# Per-IP rate limiting for forgot-password (3 per hour to prevent enumeration)
_forgot_ip_timestamps: dict[str, list[float]] = defaultdict(list)


def _check_forgot_rate_limit(ip: str) -> None:
    now = time.monotonic()
    _forgot_ip_timestamps[ip] = [t for t in _forgot_ip_timestamps[ip] if now - t < 3600]
    if len(_forgot_ip_timestamps[ip]) >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Try again later.",
        )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """Request a password reset email.

    Always returns 200 regardless of whether the email exists (prevents enumeration).
    Rate limited to 3 requests per IP per hour.
    """
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    client_ip = client_ip.split(",")[0].strip()
    _check_forgot_rate_limit(client_ip)
    _forgot_ip_timestamps[client_ip].append(time.monotonic())

    auth_svc = _get_auth_service(request)
    token = await auth_svc.create_password_reset_token(body.email)

    if token:
        from sardis_api.email_templates import send_password_reset_email
        await send_password_reset_email(body.email.strip().lower(), token)

    # Always return success to prevent email enumeration
    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: Request, body: ResetPasswordRequest):
    """Reset password using a valid reset token from email."""
    auth_svc = _get_auth_service(request)
    success = await auth_svc.reset_password(body.token, body.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token. Please request a new one.",
        )

    return {"message": "Password has been reset successfully. You can now log in."}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(request: Request, body: ChangePasswordRequest, user: UserInfo = Depends(require_auth)):
    """Change password for an authenticated user. Requires current password."""
    auth_svc = _get_auth_service(request)
    success = await auth_svc.change_password(user.username, body.current_password, body.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    return {"message": "Password changed successfully."}


# ---------------------------------------------------------------------------
# Account deletion (GDPR Art. 17 — right to erasure)
# ---------------------------------------------------------------------------

@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(request: Request, user: UserInfo = Depends(require_auth)):
    """Permanently delete the authenticated user's account and all associated data.

    This action is irreversible. All wallets, agents, API keys, policies,
    transaction history, and billing data will be permanently removed.
    """
    auth_svc = _get_auth_service(request)
    deleted = await auth_svc.delete_account(user.username)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please contact support.",
        )

    # Revoke the current JWT so it can't be used after deletion
    from sardis_api.analytics.posthog_tracker import track_event
    track_event(user.username, "ACCOUNT_DELETED", {})

    return {"message": "Account has been permanently deleted."}
