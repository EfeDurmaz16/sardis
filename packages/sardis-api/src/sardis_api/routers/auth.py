"""Authentication endpoints with JWT support."""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

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

        return payload
    except Exception:
        return None


async def get_current_user(
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

    # SECURITY: Require explicit password in production
    if not admin_password:
        if os.getenv("SARDIS_ENVIRONMENT", "dev") in ("prod", "production", "staging"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication not configured. Set SARDIS_ADMIN_PASSWORD.",
            )
        # Dev mode: use insecure default but warn
        import logging
        logging.getLogger(__name__).warning(
            "⚠️ SARDIS_ADMIN_PASSWORD not set - using insecure default 'change-me-immediately'. "
            "DO NOT use this in production!"
        )
        admin_password = "change-me-immediately"

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
async def logout(user: UserInfo = Depends(require_auth)):
    """
    Logout endpoint.

    Note: For stateless JWT, actual token invalidation requires
    implementing a token blacklist or using short-lived tokens.
    This endpoint is provided for API completeness.
    """
    return {
        "message": "Successfully logged out",
        "note": "Please discard your token client-side",
    }
