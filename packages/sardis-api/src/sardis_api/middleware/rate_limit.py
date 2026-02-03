"""Rate limiting middleware for Sardis API."""
from __future__ import annotations

import inspect
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    burst_size: int = 20  # Allow short bursts


@dataclass
class RateLimitState:
    """Track rate limit state for a client."""
    minute_count: int = 0
    hour_count: int = 0
    minute_reset: float = 0
    hour_reset: float = 0
    tokens: float = 0  # Token bucket for burst handling
    last_update: float = 0


class RedisRateLimiter:
    """Production-ready Redis-backed rate limiter using sliding window."""

    def __init__(self, config: RateLimitConfig, redis_url: str):
        self.config = config
        self._redis_url = redis_url
        self._redis = None

    def _get_redis(self):
        """Lazy Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
            except ImportError:
                raise RuntimeError(
                    "redis package required for RedisRateLimiter. "
                    "Install with: pip install redis"
                )
        return self._redis

    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client."""
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"rl:key:{api_key[:8]}"
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"rl:ip:{forwarded.split(',')[0].strip()}"
        client_host = request.client.host if request.client else "unknown"
        return f"rl:ip:{client_host}"

    async def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """Check rate limit using Redis sliding window."""
        now = time.time()
        client_key = self._get_client_key(request)
        redis_client = self._get_redis()

        # Sliding window keys
        minute_key = f"{client_key}:minute"
        hour_key = f"{client_key}:hour"

        # Use pipeline for atomic operations
        pipe = redis_client.pipeline()

        # Clean old entries and count current
        minute_cutoff = now - 60
        hour_cutoff = now - 3600

        # Minute window
        pipe.zremrangebyscore(minute_key, 0, minute_cutoff)
        pipe.zcard(minute_key)
        pipe.zadd(minute_key, {str(now): now})
        pipe.expire(minute_key, 120)

        # Hour window
        pipe.zremrangebyscore(hour_key, 0, hour_cutoff)
        pipe.zcard(hour_key)
        pipe.zadd(hour_key, {str(now): now})
        pipe.expire(hour_key, 7200)

        results = await pipe.execute()
        minute_count = results[1]
        hour_count = results[5]

        headers = {
            "X-RateLimit-Limit": str(self.config.requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, self.config.requests_per_minute - minute_count)),
            "X-RateLimit-Reset": str(int(now + 60)),
        }

        # Check limits
        if minute_count > self.config.requests_per_minute:
            headers["Retry-After"] = "60"
            return False, headers

        if hour_count > self.config.requests_per_hour:
            headers["Retry-After"] = "3600"
            return False, headers

        headers["X-RateLimit-Remaining"] = str(max(0, self.config.requests_per_minute - minute_count))
        return True, headers


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using token bucket algorithm.

    ⚠️ WARNING: This is single-instance only. For multi-instance deployments,
    use RedisRateLimiter by setting REDIS_URL environment variable.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._states: dict[str, RateLimitState] = defaultdict(RateLimitState)
    
    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client."""
        # Try to get API key first
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return f"key:{api_key[:8]}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is within rate limits.
        
        Returns:
            Tuple of (allowed, headers) where headers contain rate limit info.
        """
        now = time.time()
        client_key = self._get_client_key(request)
        state = self._states[client_key]
        
        # Reset minute counter if needed
        if now >= state.minute_reset:
            state.minute_count = 0
            state.minute_reset = now + 60
        
        # Reset hour counter if needed
        if now >= state.hour_reset:
            state.hour_count = 0
            state.hour_reset = now + 3600
        
        # Token bucket refill
        time_passed = now - state.last_update if state.last_update else 0
        state.tokens = min(
            self.config.burst_size,
            state.tokens + time_passed * (self.config.requests_per_minute / 60)
        )
        state.last_update = now
        
        # Check limits
        headers = {
            "X-RateLimit-Limit": str(self.config.requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, self.config.requests_per_minute - state.minute_count)),
            "X-RateLimit-Reset": str(int(state.minute_reset)),
        }
        
        # Check if over limit
        if state.minute_count >= self.config.requests_per_minute:
            if state.tokens < 1:
                headers["Retry-After"] = str(int(state.minute_reset - now))
                return False, headers
        
        if state.hour_count >= self.config.requests_per_hour:
            headers["Retry-After"] = str(int(state.hour_reset - now))
            return False, headers
        
        # Consume a token and increment counters
        state.tokens -= 1
        state.minute_count += 1
        state.hour_count += 1
        
        headers["X-RateLimit-Remaining"] = str(max(0, self.config.requests_per_minute - state.minute_count))
        
        return True, headers


def create_rate_limiter(config: RateLimitConfig):
    """Factory to create appropriate rate limiter based on environment."""
    import os
    import logging

    logger = logging.getLogger(__name__)
    redis_url = (
        os.getenv("SARDIS_REDIS_URL")
        or os.getenv("REDIS_URL")
        or os.getenv("UPSTASH_REDIS_URL")
        or ""
    )
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()

    if redis_url:
        try:
            limiter = RedisRateLimiter(config, redis_url)
            logger.info("Using Redis-backed rate limiter for multi-instance support")
            return limiter
        except Exception as e:
            logger.warning(f"Redis rate limiter failed ({e}), falling back to in-memory")

    if env in ("prod", "production"):
        raise RuntimeError(
            "CRITICAL: Redis is required for production rate limiting. "
            "Set SARDIS_REDIS_URL (preferred), REDIS_URL, or UPSTASH_REDIS_URL."
        )

    return InMemoryRateLimiter(config)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.limiter = create_rate_limiter(config or RateLimitConfig())
        self.exclude_paths = exclude_paths or ["/health", "/", "/api/v2/docs", "/api/v2/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Check rate limit
        check = getattr(self.limiter, "check_rate_limit", None)
        if check is None:
            allowed, headers = True, {}
        elif inspect.iscoroutinefunction(check):
            allowed, headers = await check(request)
        else:
            allowed, headers = check(request)
        
        if not allowed:
            import json
            import time
            # RFC 7807 Problem Details format
            error_content = {
                "type": "https://api.sardis.io/errors/rate-limit-exceeded",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": "Too many requests. Please wait before making another request.",
                "instance": request.url.path,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            if "Retry-After" in headers:
                error_content["retry_after_seconds"] = int(headers["Retry-After"])

            headers["Content-Type"] = "application/problem+json"
            return Response(
                content=json.dumps(error_content),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
                media_type="application/problem+json",
            )
        
        # Process request and add rate limit headers to response
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


def rate_limit(requests_per_minute: int = 100):
    """
    Decorator for rate limiting specific endpoints.
    
    Usage:
        @app.get("/api/expensive")
        @rate_limit(requests_per_minute=10)
        async def expensive_endpoint():
            ...
    """
    limiter = InMemoryRateLimiter(RateLimitConfig(requests_per_minute=requests_per_minute))
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            allowed, headers = limiter.check_rate_limit(request)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers=headers,
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
