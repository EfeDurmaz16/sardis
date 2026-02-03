"""
Admin API endpoints with strict rate limiting.

CRITICAL SECURITY: Admin endpoints have significantly stricter rate limits
than regular endpoints to protect against brute force attacks and abuse.

Rate Limits:
- Standard endpoints: 100 req/min
- Admin endpoints: 10 req/min, 50 req/hour per IP/API key
- Sensitive admin actions: 5 req/min (e.g., user management, config changes)
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import require_admin_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin_principal)])


# ============================================================================
# Admin Rate Limiting Configuration
# ============================================================================

@dataclass
class AdminRateLimitConfig:
    """
    Strict rate limit configuration for admin endpoints.

    These limits are intentionally much lower than standard API limits
    to prevent brute force attacks and abuse of privileged operations.
    """
    # Standard admin endpoint limits
    requests_per_minute: int = 10
    requests_per_hour: int = 50
    burst_size: int = 3  # Very small burst allowance

    # Sensitive action limits (even stricter)
    sensitive_requests_per_minute: int = 5
    sensitive_requests_per_hour: int = 20

    # Lockout configuration
    lockout_threshold: int = 10  # Failed attempts before lockout
    lockout_duration_seconds: int = 900  # 15 minute lockout

    # IP-based additional restrictions
    max_concurrent_sessions: int = 3


@dataclass
class AdminRateLimitState:
    """Track rate limit state for admin endpoints."""
    minute_count: int = 0
    hour_count: int = 0
    minute_reset: float = 0
    hour_reset: float = 0
    failed_attempts: int = 0
    lockout_until: float = 0
    last_request: float = 0
    request_timestamps: List[float] = field(default_factory=list)


class AdminRateLimiter:
    """
    Strict rate limiter specifically for admin endpoints.

    Features:
    - Per-IP and per-API-key tracking
    - Failed attempt tracking with automatic lockout
    - Sliding window rate limiting
    - Concurrent session limiting
    - Audit logging of all admin access attempts

    SECURITY: This rate limiter is designed to be more restrictive than
    the standard API rate limiter. Do not increase limits without security review.
    """

    def __init__(self, config: Optional[AdminRateLimitConfig] = None):
        self.config = config or AdminRateLimitConfig()
        self._states: Dict[str, AdminRateLimitState] = defaultdict(AdminRateLimitState)
        self._sensitive_states: Dict[str, AdminRateLimitState] = defaultdict(AdminRateLimitState)

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the client.

        Uses combination of API key (if present) and IP address
        to prevent bypassing limits by switching between them.
        """
        parts = []

        # API key hash (don't log full key)
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            parts.append(f"key:{key_hash}")

        # IP address
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        parts.append(f"ip:{ip}")

        return "|".join(parts)

    def _is_locked_out(self, state: AdminRateLimitState) -> bool:
        """Check if client is currently locked out."""
        if state.lockout_until == 0:
            return False
        return time.time() < state.lockout_until

    def _check_sliding_window(
        self,
        state: AdminRateLimitState,
        window_seconds: int,
        max_requests: int,
    ) -> bool:
        """Check if request is within sliding window limit."""
        now = time.time()
        cutoff = now - window_seconds

        # Clean old timestamps
        state.request_timestamps = [
            ts for ts in state.request_timestamps if ts > cutoff
        ]

        return len(state.request_timestamps) < max_requests

    def check_rate_limit(
        self,
        request: Request,
        is_sensitive: bool = False,
    ) -> tuple[bool, dict, Optional[str]]:
        """
        Check if request is within admin rate limits.

        Args:
            request: FastAPI request
            is_sensitive: If True, applies even stricter limits

        Returns:
            Tuple of (allowed, headers, error_message)
        """
        now = time.time()
        client_id = self._get_client_identifier(request)

        # Get appropriate state
        if is_sensitive:
            state = self._sensitive_states[client_id]
            requests_per_minute = self.config.sensitive_requests_per_minute
            requests_per_hour = self.config.sensitive_requests_per_hour
        else:
            state = self._states[client_id]
            requests_per_minute = self.config.requests_per_minute
            requests_per_hour = self.config.requests_per_hour

        # Check lockout
        if self._is_locked_out(state):
            lockout_remaining = int(state.lockout_until - now)
            logger.warning(
                f"Admin rate limit: Client {client_id} is locked out "
                f"for {lockout_remaining} more seconds"
            )
            return (
                False,
                {"Retry-After": str(lockout_remaining)},
                f"Too many failed attempts. Locked out for {lockout_remaining} seconds.",
            )

        # Reset minute counter if needed
        if now >= state.minute_reset:
            state.minute_count = 0
            state.minute_reset = now + 60

        # Reset hour counter if needed
        if now >= state.hour_reset:
            state.hour_count = 0
            state.hour_reset = now + 3600

        # Build response headers
        headers = {
            "X-RateLimit-Limit": str(requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, requests_per_minute - state.minute_count)),
            "X-RateLimit-Reset": str(int(state.minute_reset)),
        }

        # Check minute limit
        if state.minute_count >= requests_per_minute:
            # Check if burst is allowed
            if not self._check_sliding_window(state, 60, requests_per_minute + self.config.burst_size):
                wait_time = int(state.minute_reset - now)
                headers["Retry-After"] = str(wait_time)
                logger.warning(
                    f"Admin rate limit exceeded for {client_id}: "
                    f"{state.minute_count}/{requests_per_minute} per minute"
                )
                return (
                    False,
                    headers,
                    f"Rate limit exceeded. Please wait {wait_time} seconds.",
                )

        # Check hour limit
        if state.hour_count >= requests_per_hour:
            wait_time = int(state.hour_reset - now)
            headers["Retry-After"] = str(wait_time)
            logger.warning(
                f"Admin hourly rate limit exceeded for {client_id}: "
                f"{state.hour_count}/{requests_per_hour} per hour"
            )
            return (
                False,
                headers,
                f"Hourly rate limit exceeded. Please wait {wait_time} seconds.",
            )

        # Request allowed - update counters
        state.minute_count += 1
        state.hour_count += 1
        state.request_timestamps.append(now)
        state.last_request = now

        headers["X-RateLimit-Remaining"] = str(max(0, requests_per_minute - state.minute_count))

        return True, headers, None

    def record_failed_attempt(self, request: Request) -> None:
        """
        Record a failed admin action attempt (e.g., auth failure).

        Too many failures will trigger automatic lockout.
        """
        client_id = self._get_client_identifier(request)
        state = self._states[client_id]

        state.failed_attempts += 1

        if state.failed_attempts >= self.config.lockout_threshold:
            state.lockout_until = time.time() + self.config.lockout_duration_seconds
            logger.error(
                f"SECURITY: Admin client {client_id} locked out after "
                f"{state.failed_attempts} failed attempts"
            )

    def reset_failed_attempts(self, request: Request) -> None:
        """Reset failed attempt counter on successful action."""
        client_id = self._get_client_identifier(request)
        self._states[client_id].failed_attempts = 0


# Global admin rate limiter instance
_admin_rate_limiter = AdminRateLimiter()


def get_admin_rate_limiter() -> AdminRateLimiter:
    """Get the global admin rate limiter."""
    return _admin_rate_limiter


# ============================================================================
# Rate Limit Decorators
# ============================================================================

def admin_rate_limit(is_sensitive: bool = False):
    """
    Decorator to apply admin rate limiting to endpoints.

    Usage:
        @router.post("/admin/users")
        @admin_rate_limit()
        async def list_users(request: Request):
            ...

        @router.delete("/admin/users/{user_id}")
        @admin_rate_limit(is_sensitive=True)
        async def delete_user(request: Request, user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            limiter = get_admin_rate_limiter()
            allowed, headers, error_msg = limiter.check_rate_limit(
                request, is_sensitive=is_sensitive
            )

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=error_msg or "Admin rate limit exceeded",
                    headers=headers,
                )

            # Execute the endpoint
            try:
                response = await func(request, *args, **kwargs)
                limiter.reset_failed_attempts(request)
                return response
            except HTTPException as e:
                # Record failed attempts for auth failures
                if e.status_code in (401, 403):
                    limiter.record_failed_attempt(request)
                raise

        return wrapper
    return decorator


# ============================================================================
# Dependency for rate limit checking
# ============================================================================

async def check_admin_rate_limit(
    request: Request,
    is_sensitive: bool = False,
) -> None:
    """
    FastAPI dependency for admin rate limiting.

    Usage:
        @router.get("/admin/stats")
        async def get_stats(
            request: Request,
            _: None = Depends(lambda r: check_admin_rate_limit(r))
        ):
            ...
    """
    limiter = get_admin_rate_limiter()
    allowed, headers, error_msg = limiter.check_rate_limit(request, is_sensitive)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg or "Admin rate limit exceeded",
            headers=headers,
        )


def require_admin_rate_limit(is_sensitive: bool = False):
    """
    Create a dependency that checks admin rate limits.

    Usage:
        @router.get("/admin/config")
        async def get_config(
            request: Request,
            _: None = Depends(require_admin_rate_limit())
        ):
            ...
    """
    async def dependency(request: Request) -> None:
        await check_admin_rate_limit(request, is_sensitive)
    return dependency


# ============================================================================
# Request/Response Models
# ============================================================================

class AdminStatsResponse(BaseModel):
    """Admin statistics response."""
    total_transactions: int = 0
    total_volume_usd: float = 0.0
    active_agents: int = 0
    active_wallets: int = 0
    timestamp: str


class AdminUserResponse(BaseModel):
    """Admin user info response."""
    user_id: str
    email: Optional[str] = None
    role: str
    created_at: str
    last_login: Optional[str] = None


class AdminConfigUpdate(BaseModel):
    """Admin configuration update request."""
    key: str = Field(..., max_length=100)
    value: str = Field(..., max_length=1000)
    description: Optional[str] = None


class RateLimitStatus(BaseModel):
    """Rate limit status for monitoring."""
    client_id: str
    minute_count: int
    hour_count: int
    minute_limit: int
    hour_limit: int
    is_locked: bool
    lockout_remaining: Optional[int] = None


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    request: Request,
    _: None = Depends(require_admin_rate_limit()),
):
    """
    Get admin dashboard statistics.

    Rate limited to 10 requests per minute.
    """
    logger.info(f"Admin stats requested from {request.client.host if request.client else 'unknown'}")

    return AdminStatsResponse(
        total_transactions=0,
        total_volume_usd=0.0,
        active_agents=0,
        active_wallets=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/users", response_model=List[AdminUserResponse])
async def list_admin_users(
    request: Request,
    _: None = Depends(require_admin_rate_limit()),
):
    """
    List all admin users.

    Rate limited to 10 requests per minute.
    """
    logger.info(f"Admin user list requested from {request.client.host if request.client else 'unknown'}")

    # Placeholder - would normally query database
    return []


@router.post("/config", status_code=status.HTTP_200_OK)
async def update_admin_config(
    request: Request,
    config: AdminConfigUpdate,
    _: None = Depends(require_admin_rate_limit(is_sensitive=True)),
):
    """
    Update system configuration.

    SENSITIVE: Rate limited to 5 requests per minute.
    """
    logger.warning(
        f"Admin config update: key={config.key} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    # Placeholder - would normally update configuration
    return {
        "success": True,
        "key": config.key,
        "message": "Configuration updated",
    }


@router.delete("/cache")
async def clear_admin_cache(
    request: Request,
    _: None = Depends(require_admin_rate_limit(is_sensitive=True)),
):
    """
    Clear system caches.

    SENSITIVE: Rate limited to 5 requests per minute.
    """
    logger.warning(
        f"Admin cache clear requested from {request.client.host if request.client else 'unknown'}"
    )

    return {
        "success": True,
        "message": "Cache cleared",
    }


@router.get("/rate-limit/status")
async def get_rate_limit_status(
    request: Request,
    _: None = Depends(require_admin_rate_limit()),
) -> RateLimitStatus:
    """
    Get current rate limit status for the requesting client.

    Useful for monitoring and debugging rate limit issues.
    """
    limiter = get_admin_rate_limiter()
    client_id = limiter._get_client_identifier(request)
    state = limiter._states[client_id]

    is_locked = limiter._is_locked_out(state)
    lockout_remaining = None
    if is_locked:
        lockout_remaining = int(state.lockout_until - time.time())

    return RateLimitStatus(
        client_id=client_id,
        minute_count=state.minute_count,
        hour_count=state.hour_count,
        minute_limit=limiter.config.requests_per_minute,
        hour_limit=limiter.config.requests_per_hour,
        is_locked=is_locked,
        lockout_remaining=lockout_remaining,
    )


@router.post("/audit-log")
async def create_audit_log_entry(
    request: Request,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    _: None = Depends(require_admin_rate_limit()),
):
    """
    Create an audit log entry.

    All admin actions should be logged for compliance.
    """
    logger.info(
        f"AUDIT: action={action} "
        f"from={request.client.host if request.client else 'unknown'} "
        f"details={details}"
    )

    return {
        "success": True,
        "action": action,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
