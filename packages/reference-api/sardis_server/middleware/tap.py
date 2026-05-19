"""TAP (Trust Anchor Protocol) verification middleware for FastAPI.

Validates TAP message signatures on incoming requests to AP2 and payment endpoints.
Enforces cryptographic verification of agent identity using Ed25519/ECDSA-P256 signatures.

Key features:
- RFC 9421-like Signature-Input/Signature header validation
- Timestamp validation with configurable max window (default 8 minutes)
- Nonce replay prevention with TTL-based in-memory cache
- Configurable path prefixes requiring TAP verification
- Environment-based enforcement bypass for dev/test
- RFC 7807 error responses on verification failure
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, MutableSet
from dataclasses import dataclass, field
from threading import Lock

from fastapi import Request, Response
from sardis_protocol.tap import (
    TAP_ALLOWED_MESSAGE_ALGS,
    TAP_MAX_TIME_WINDOW_SECONDS,
    TAP_PROTOCOL_VERSION,
    TapVerificationResult,
    validate_tap_headers,
)
from sardis_protocol.tap_keys import select_jwk_by_kid, verify_signature_with_jwk
from starlette.middleware.base import BaseHTTPMiddleware

from .exceptions import create_error_response, get_request_id

logger = logging.getLogger(__name__)


class NonceCache:
    """Nonce cache with Redis backend for multi-instance deployments.

    Falls back to in-memory when Redis is unavailable.
    Uses Redis SISMEMBER/SADD for O(1) replay detection with per-nonce TTL.
    """

    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl_seconds = ttl_seconds
        self._redis = None
        self._redis_available = False
        self._init_redis()
        # In-memory fallback
        self._nonces: set[str] = set()
        self._timestamps: dict[str, int] = {}
        self._lock = Lock()
        self._last_cleanup: int = int(time.time())

    def _init_redis(self) -> None:
        redis_url = (
            os.getenv("SARDIS_REDIS_URL")
            or os.getenv("REDIS_URL")
            or os.getenv("UPSTASH_REDIS_URL")
            or ""
        )
        if redis_url:
            try:
                import redis as redis_sync
                self._redis = redis_sync.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                self._redis_available = True
                logger.info("TAP nonce cache using Redis backend")
            except Exception as e:
                logger.warning("Redis TAP nonce cache failed (%s), using in-memory", e)
                self._redis = None
                self._redis_available = False

    def contains(self, nonce: str) -> bool:
        """Check if nonce exists in cache."""
        if self._redis_available and self._redis:
            try:
                return bool(self._redis.sismember("sardis:tap:nonces", nonce))
            except Exception:
                pass
        with self._lock:
            self._cleanup_expired()
            return nonce in self._nonces

    def add(self, nonce: str) -> None:
        """Add nonce to cache with TTL."""
        if self._redis_available and self._redis:
            try:
                # Use a per-nonce key with TTL for automatic expiry
                pipe = self._redis.pipeline()
                pipe.sadd("sardis:tap:nonces", nonce)
                pipe.set(f"sardis:tap:nonce:{nonce}", "1", ex=self.ttl_seconds)
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            self._cleanup_expired()
            now = int(time.time())
            self._nonces.add(nonce)
            self._timestamps[nonce] = now

    def _cleanup_expired(self) -> None:
        """Remove expired nonces from in-memory fallback."""
        now = int(time.time())
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        expired = {
            nonce
            for nonce, timestamp in self._timestamps.items()
            if now - timestamp > self.ttl_seconds
        }
        for nonce in expired:
            self._nonces.discard(nonce)
            self._timestamps.pop(nonce, None)


@dataclass
class TapMiddlewareConfig:
    """Configuration for TAP verification middleware."""

    # Paths requiring TAP verification (prefix match)
    # Must match actual mount paths from main.py (e.g. /api/v2/ap2/, /api/v2/a2a/)
    protected_paths: list[str] = field(default_factory=lambda: [
        "/api/v2/ap2/",
        "/api/v2/a2a/",
        "/api/v2/payments/",
    ])

    # Enforcement bypass (disabled in dev/test environments)
    enforcement_enabled: bool = True

    # TAP validation parameters
    max_time_window_seconds: int = TAP_MAX_TIME_WINDOW_SECONDS
    allowed_algs: list[str] = field(default_factory=lambda: list(TAP_ALLOWED_MESSAGE_ALGS))

    # Nonce cache TTL (should be > max_time_window_seconds)
    nonce_ttl_seconds: int = 600

    # JWKS provider (callable that returns JWKS dict given a keyid)
    # Signature: jwks_provider(kid: str) -> dict | None
    jwks_provider: Callable[[str], dict] | None = None

    # When True (default), dev/test environments bypass signature verification
    # when no JWKS provider is configured. In prod, verification always fails
    # without a JWKS provider regardless of this setting.
    fail_open_in_dev: bool = True

    @classmethod
    def from_environment(cls) -> TapMiddlewareConfig:
        """Load TAP middleware configuration from environment."""
        enforcement = os.getenv("SARDIS_TAP_ENFORCEMENT", "true").lower() == "true"
        env = os.getenv("SARDIS_ENVIRONMENT", "dev")

        # Disable enforcement in dev/test by default
        if env in ("dev", "development", "test") and enforcement:
            logger.warning(
                f"TAP enforcement enabled in {env} environment. "
                "Set SARDIS_TAP_ENFORCEMENT=false to disable."
            )

        return cls(
            enforcement_enabled=enforcement,
            max_time_window_seconds=int(
                os.getenv("SARDIS_TAP_MAX_TIME_WINDOW", str(TAP_MAX_TIME_WINDOW_SECONDS))
            ),
            nonce_ttl_seconds=int(
                os.getenv("SARDIS_TAP_NONCE_TTL", "600")
            ),
        )


class TapVerificationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates TAP message signatures on protected endpoints.

    Verification flow:
    1. Check if request path requires TAP (prefix match against protected_paths)
    2. Extract Signature-Input and Signature headers
    3. Build signature base from @authority and @path
    4. Validate timestamps, nonce, and cryptographic signature
    5. On success: inject TapVerificationResult into request.state.tap_result
    6. On failure: return HTTP 401 with RFC 7807 error body

    Configuration via environment:
    - SARDIS_TAP_ENFORCEMENT: Enable/disable enforcement (default: true)
    - SARDIS_TAP_MAX_TIME_WINDOW: Max allowed time window in seconds
    - SARDIS_TAP_NONCE_TTL: Nonce cache TTL in seconds
    """

    def __init__(
        self,
        app,
        config: TapMiddlewareConfig | None = None,
        jwks_provider: Callable[[str], dict] | None = None,
    ):
        super().__init__(app)
        self.config = config or TapMiddlewareConfig.from_environment()
        self.nonce_cache = NonceCache(ttl_seconds=self.config.nonce_ttl_seconds)
        self.jwks_provider = jwks_provider or self.config.jwks_provider

        logger.info(
            f"TAP verification middleware initialized "
            f"(enforcement={'enabled' if self.config.enforcement_enabled else 'disabled'}, "
            f"protected_paths={self.config.protected_paths})"
        )

    def _requires_tap_verification(self, path: str) -> bool:
        """Check if request path requires TAP verification."""
        return any(path.startswith(prefix) for prefix in self.config.protected_paths)

    def _get_authority(self, request: Request) -> str:
        """Extract authority (host:port) from request."""
        # Prefer forwarded host headers for proxy scenarios
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        return host

    def _build_verify_fn(self, request_id: str) -> Callable:
        """
        Build signature verification function that integrates with JWKS provider.

        Signature: verify_fn(signature_base: bytes, signature_b64: str, keyid: str, alg: str) -> bool
        """
        def verify_fn(
            signature_base: bytes,
            signature_b64: str,
            keyid: str,
            alg: str,
        ) -> bool:
            if not self.jwks_provider:
                # Fail-close in production: reject when no JWKS provider
                env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
                is_prod = env in ("prod", "production", "sandbox")

                if is_prod or not self.config.fail_open_in_dev:
                    logger.error(
                        "TAP signature verification REJECTED (no JWKS provider in %s)",
                        env,
                        extra={"request_id": request_id, "keyid": keyid},
                    )
                    return False

                # Dev/test: bypass with warning (backward compat)
                logger.warning(
                    "TAP signature verification skipped (no JWKS provider in %s)",
                    env,
                    extra={"request_id": request_id, "keyid": keyid},
                )
                return True

            try:
                # Fetch JWKS for this key ID
                jwks = self.jwks_provider(keyid)
                if not jwks:
                    logger.warning(
                        f"JWKS not found for keyid={keyid}",
                        extra={"request_id": request_id},
                    )
                    return False

                # Select specific JWK by kid
                jwk = select_jwk_by_kid(jwks, keyid)
                if not jwk:
                    logger.warning(
                        f"JWK not found in JWKS for keyid={keyid}",
                        extra={"request_id": request_id},
                    )
                    return False

                # Verify signature using JWK
                verified = verify_signature_with_jwk(
                    signature_base=signature_base,
                    signature_b64=signature_b64,
                    jwk=jwk,
                    alg=alg,
                )

                if verified:
                    logger.info(
                        "TAP signature verified successfully",
                        extra={"request_id": request_id, "keyid": keyid, "alg": alg},
                    )
                else:
                    logger.warning(
                        "TAP signature verification failed",
                        extra={"request_id": request_id, "keyid": keyid, "alg": alg},
                    )

                return verified

            except Exception as exc:
                logger.error(
                    f"TAP signature verification error: {exc}",
                    extra={"request_id": request_id, "keyid": keyid},
                    exc_info=True,
                )
                return False

        return verify_fn

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with TAP verification if required."""
        path = request.url.path

        # Skip verification if path not protected
        if not self._requires_tap_verification(path):
            return await call_next(request)

        # Skip verification if enforcement disabled
        if not self.config.enforcement_enabled:
            logger.debug(
                "TAP verification skipped (enforcement disabled)",
                extra={"path": path},
            )
            # Still inject empty result for downstream handlers
            request.state.tap_result = TapVerificationResult(
                accepted=True,
                reason="enforcement_disabled",
            )
            return await call_next(request)

        request_id = get_request_id(request)

        # Extract TAP headers
        signature_input_header = request.headers.get("signature-input", "")
        signature_header = request.headers.get("signature", "")
        tap_version = request.headers.get("tap-version", TAP_PROTOCOL_VERSION)

        if not signature_input_header or not signature_header:
            logger.warning(
                "TAP verification failed: missing required headers",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "has_signature_input": bool(signature_input_header),
                    "has_signature": bool(signature_header),
                },
            )
            return create_error_response(
                error_code="AUTHENTICATION_REQUIRED",
                message="TAP signature headers required (Signature-Input, Signature)",
                status_code=401,
                request_id=request_id,
                instance=path,
                details={
                    "tap_protocol_version": TAP_PROTOCOL_VERSION,
                    "required_headers": ["Signature-Input", "Signature"],
                },
            )

        # Get authority and path for signature base
        authority = self._get_authority(request)
        if not authority:
            logger.warning(
                "TAP verification failed: missing Host header",
                extra={"request_id": request_id, "path": path},
            )
            return create_error_response(
                error_code="BAD_REQUEST",
                message="Host header required for TAP verification",
                status_code=400,
                request_id=request_id,
                instance=path,
            )

        # Convert nonce cache to set interface for validate_tap_headers
        nonce_set = _NonceSetAdapter(self.nonce_cache)

        # Build verification function
        verify_fn = self._build_verify_fn(request_id)

        # Validate TAP headers
        result = validate_tap_headers(
            signature_input_header=signature_input_header,
            signature_header=signature_header,
            authority=authority,
            path=path,
            max_time_window_seconds=self.config.max_time_window_seconds,
            allowed_algs=self.config.allowed_algs,
            nonce_cache=nonce_set,
            verify_signature_fn=verify_fn,
            tap_version=tap_version,
        )

        if not result.accepted:
            logger.warning(
                f"TAP verification failed: {result.reason}",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "reason": result.reason,
                    "tap_version": tap_version,
                },
            )
            return create_error_response(
                error_code="INVALID_CREDENTIALS",
                message=f"TAP signature verification failed: {result.reason}",
                status_code=401,
                request_id=request_id,
                instance=path,
                details={
                    "tap_error": result.reason,
                    "tap_protocol_version": tap_version,
                },
            )

        # Inject verification result into request state
        request.state.tap_result = result

        logger.info(
            "TAP verification successful",
            extra={
                "request_id": request_id,
                "path": path,
                "keyid": result.signature_input.keyid if result.signature_input else None,
                "alg": result.signature_input.alg if result.signature_input else None,
                "tag": result.signature_input.tag if result.signature_input else None,
            },
        )

        return await call_next(request)


class _NonceSetAdapter(MutableSet[str]):
    """Adapter to make NonceCache compatible with MutableSet[str] interface."""

    def __init__(self, cache: NonceCache):
        self._cache = cache

    def __contains__(self, nonce: object) -> bool:
        return self._cache.contains(str(nonce)) if isinstance(nonce, str) else False

    def __iter__(self):
        # Not needed for TAP validation, but required by MutableSet protocol
        return iter(self._cache._nonces)

    def __len__(self) -> int:
        return len(self._cache._nonces)

    def add(self, nonce: str) -> None:
        self._cache.add(nonce)

    def discard(self, nonce: str) -> None:
        # Not used by TAP validation
        pass


__all__ = [
    "TapVerificationMiddleware",
    "TapMiddlewareConfig",
    "NonceCache",
]
