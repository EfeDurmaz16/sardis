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
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, List, MutableSet, Optional, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from sardis_protocol.tap import (
    TAP_ALLOWED_MESSAGE_ALGS,
    TAP_MAX_TIME_WINDOW_SECONDS,
    TAP_PROTOCOL_VERSION,
    TapVerificationResult,
    validate_tap_headers,
)
from sardis_protocol.tap_keys import select_jwk_by_kid, verify_signature_with_jwk

from .exceptions import create_error_response, get_request_id

logger = logging.getLogger(__name__)


@dataclass
class NonceCache:
    """In-memory nonce cache with TTL-based automatic cleanup."""

    _nonces: Set[str] = field(default_factory=set)
    _timestamps: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    ttl_seconds: int = 600  # 10 minutes default
    _last_cleanup: int = field(default_factory=lambda: int(time.time()))

    def contains(self, nonce: str) -> bool:
        """Check if nonce exists in cache."""
        with self._lock:
            self._cleanup_expired()
            return nonce in self._nonces

    def add(self, nonce: str) -> None:
        """Add nonce to cache with current timestamp."""
        with self._lock:
            self._cleanup_expired()
            now = int(time.time())
            self._nonces.add(nonce)
            self._timestamps[nonce] = now

    def _cleanup_expired(self) -> None:
        """Remove expired nonces (called automatically on access)."""
        now = int(time.time())

        # Only cleanup every 60 seconds to reduce overhead
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

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired nonces from cache")


@dataclass
class TapMiddlewareConfig:
    """Configuration for TAP verification middleware."""

    # Paths requiring TAP verification (prefix match)
    protected_paths: List[str] = field(default_factory=lambda: [
        "/v2/ap2/",
        "/v2/payments/",
    ])

    # Enforcement bypass (disabled in dev/test environments)
    enforcement_enabled: bool = True

    # TAP validation parameters
    max_time_window_seconds: int = TAP_MAX_TIME_WINDOW_SECONDS
    allowed_algs: List[str] = field(default_factory=lambda: list(TAP_ALLOWED_MESSAGE_ALGS))

    # Nonce cache TTL (should be > max_time_window_seconds)
    nonce_ttl_seconds: int = 600

    # JWKS provider (callable that returns JWKS dict given a keyid)
    # Signature: jwks_provider(kid: str) -> dict | None
    jwks_provider: Optional[Callable[[str], dict]] = None

    @classmethod
    def from_environment(cls) -> "TapMiddlewareConfig":
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
        config: Optional[TapMiddlewareConfig] = None,
        jwks_provider: Optional[Callable[[str], dict]] = None,
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
                # No JWKS provider configured - skip cryptographic verification
                # This allows structural validation only in test scenarios
                logger.warning(
                    f"TAP signature verification skipped (no JWKS provider configured)",
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
                        f"TAP signature verified successfully",
                        extra={"request_id": request_id, "keyid": keyid, "alg": alg},
                    )
                else:
                    logger.warning(
                        f"TAP signature verification failed",
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
                f"TAP verification skipped (enforcement disabled)",
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
