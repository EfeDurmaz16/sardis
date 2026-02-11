"""Comprehensive security middleware for Sardis API.

Provides production-grade security headers and request validation:
- Content Security Policy (CSP)
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- Request body size limits
- API versioning headers
- Request ID tracking
- Webhook signature verification
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

logger = logging.getLogger("sardis.api.security")

# API Version
API_VERSION = "2.0.0"


@dataclass
class SecurityConfig:
    """Configuration for security middleware."""

    # HSTS settings
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False

    # CSP settings
    csp_default_src: str = "'self'"
    csp_script_src: str = "'self'"
    csp_style_src: str = "'self' 'unsafe-inline'"
    csp_img_src: str = "'self' data: https:"
    csp_connect_src: str = "'self'"
    csp_frame_ancestors: str = "'none'"
    csp_form_action: str = "'self'"
    csp_report_uri: Optional[str] = None

    # Request limits
    max_body_size_bytes: int = 10 * 1024 * 1024  # 10MB default
    max_body_size_webhook: int = 1 * 1024 * 1024  # 1MB for webhooks

    # Paths to exclude from certain security headers
    exclude_csp_paths: List[str] = field(default_factory=lambda: [
        "/api/v2/docs",
        "/api/v2/openapi.json",
    ])

    @classmethod
    def from_environment(cls) -> "SecurityConfig":
        """Load security configuration from environment."""
        return cls(
            hsts_max_age=int(os.getenv("SECURITY_HSTS_MAX_AGE", "31536000")),
            hsts_include_subdomains=os.getenv("SECURITY_HSTS_SUBDOMAINS", "true").lower() == "true",
            hsts_preload=os.getenv("SECURITY_HSTS_PRELOAD", "false").lower() == "true",
            max_body_size_bytes=int(os.getenv("SECURITY_MAX_BODY_SIZE", str(10 * 1024 * 1024))),
            csp_report_uri=os.getenv("SECURITY_CSP_REPORT_URI"),
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds comprehensive security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - X-API-Version
    - Cache-Control (for API responses)
    """

    def __init__(
        self,
        app,
        config: Optional[SecurityConfig] = None,
    ):
        super().__init__(app)
        self.config = config or SecurityConfig.from_environment()
        self._csp_header = self._build_csp_header()

    def _build_csp_header(self) -> str:
        """Build the Content-Security-Policy header value."""
        directives = [
            f"default-src {self.config.csp_default_src}",
            f"script-src {self.config.csp_script_src}",
            f"style-src {self.config.csp_style_src}",
            f"img-src {self.config.csp_img_src}",
            f"connect-src {self.config.csp_connect_src}",
            f"frame-ancestors {self.config.csp_frame_ancestors}",
            f"form-action {self.config.csp_form_action}",
            "base-uri 'self'",
            "object-src 'none'",
        ]

        if self.config.csp_report_uri:
            directives.append(f"report-uri {self.config.csp_report_uri}")

        return "; ".join(directives)

    def _build_hsts_header(self) -> str:
        """Build the Strict-Transport-Security header value."""
        parts = [f"max-age={self.config.hsts_max_age}"]

        if self.config.hsts_include_subdomains:
            parts.append("includeSubDomains")

        if self.config.hsts_preload:
            parts.append("preload")

        return "; ".join(parts)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)

        # HSTS - only for HTTPS or non-development environments
        is_secure = request.url.scheme == "https" or os.getenv("SARDIS_ENVIRONMENT") not in ("dev", "development")
        if is_secure:
            response.headers["Strict-Transport-Security"] = self._build_hsts_header()

        # CSP - exclude docs paths that need inline scripts
        if request.url.path not in self.config.exclude_csp_paths:
            response.headers["Content-Security-Policy"] = self._csp_header

        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), ambient-light-sensor=(), autoplay=(), "
            "battery=(), camera=(), cross-origin-isolated=(), display-capture=(), "
            "document-domain=(), encrypted-media=(), execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), fullscreen=(), geolocation=(), "
            "gyroscope=(), keyboard-map=(), magnetometer=(), microphone=(), "
            "midi=(), navigation-override=(), payment=(), picture-in-picture=(), "
            "publickey-credentials-get=(), screen-wake-lock=(), sync-xhr=(), "
            "usb=(), web-share=(), xr-spatial-tracking=()"
        )

        # API versioning header
        response.headers["X-API-Version"] = API_VERSION

        # Cache control for API responses (except health checks)
        if request.url.path.startswith("/api/") and "/health" not in request.url.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces request body size limits.

    Prevents resource exhaustion attacks by rejecting oversized requests
    before they are fully read into memory.

    Features:
    - Configurable default size limit
    - Per-path limit overrides
    - Streaming check to avoid memory issues
    """

    def __init__(
        self,
        app,
        default_limit: int = 10 * 1024 * 1024,  # 10MB
        path_limits: Optional[Dict[str, int]] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.path_limits = path_limits or {
            "/api/v2/webhooks": 1 * 1024 * 1024,  # 1MB for webhook callbacks
            "/api/v2/checkout": 512 * 1024,  # 512KB for checkout
        }
        self.exclude_paths = set(exclude_paths or ["/", "/health", "/api/v2/health"])

    def _get_limit_for_path(self, path: str) -> int:
        """Get the body size limit for a specific path."""
        for prefix, limit in self.path_limits.items():
            if path.startswith(prefix):
                return limit
        return self.default_limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check content-length and enforce body size limits.

        SECURITY: Checks both Content-Length header AND actual streamed body size.
        Without streaming check, chunked Transfer-Encoding bypasses the limit
        because chunked requests omit Content-Length.
        """
        # Skip for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Skip for methods that don't have bodies
        if request.method in ("GET", "HEAD", "OPTIONS", "DELETE"):
            return await call_next(request)

        # Get the limit for this path
        limit = self._get_limit_for_path(request.url.path)

        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > limit:
                    logger.warning(
                        f"Request body too large: {length} bytes (limit: {limit})",
                        extra={
                            "path": request.url.path,
                            "content_length": length,
                            "limit": limit,
                        }
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "type": "https://api.sardis.sh/errors/request-entity-too-large",
                            "title": "Request Entity Too Large",
                            "status": 413,
                            "detail": f"Request body exceeds maximum size of {limit} bytes",
                            "instance": request.url.path,
                        },
                        headers={"X-Max-Body-Size": str(limit)},
                    )
            except ValueError:
                pass

        # SECURITY: Also enforce limit on the actual streamed body.
        # Chunked Transfer-Encoding omits Content-Length, so we must count
        # bytes as they arrive. This prevents resource exhaustion via chunked requests.
        transfer_encoding = request.headers.get("transfer-encoding", "").lower()
        if "chunked" in transfer_encoding or not content_length:
            body = await request.body()
            if len(body) > limit:
                logger.warning(
                    f"Chunked/streamed body too large: {len(body)} bytes (limit: {limit})",
                    extra={
                        "path": request.url.path,
                        "body_size": len(body),
                        "limit": limit,
                    }
                )
                return JSONResponse(
                    status_code=413,
                    content={
                        "type": "https://api.sardis.sh/errors/request-entity-too-large",
                        "title": "Request Entity Too Large",
                        "status": 413,
                        "detail": f"Request body exceeds maximum size of {limit} bytes",
                        "instance": request.url.path,
                    },
                    headers={"X-Max-Body-Size": str(limit)},
                )

        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request has a unique request ID.

    Features:
    - Accepts X-Request-ID from client for distributed tracing
    - Generates unique ID if not provided
    - Stores ID in request.state for access in handlers
    - Adds ID to response headers
    """

    REQUEST_ID_HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Ensure request has an ID and propagate to response."""
        # Get existing ID or generate new one
        request_id = request.headers.get(self.REQUEST_ID_HEADER)

        if not request_id:
            # Generate a unique request ID with timestamp prefix for ordering
            timestamp = int(time.time() * 1000) % 1000000
            unique_part = uuid.uuid4().hex[:12]
            request_id = f"req_{timestamp:06d}_{unique_part}"

        # Store in request state for access by handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers[self.REQUEST_ID_HEADER] = request_id

        return response


class WebhookSignatureVerifier:
    """
    Utility class for webhook signature verification.

    Provides HMAC-SHA256 signature generation and verification
    compatible with Stripe's webhook signature format.

    Usage:
        verifier = WebhookSignatureVerifier()

        # Generate signature for outbound webhook
        signature = verifier.sign(payload, secret)

        # Verify inbound webhook
        if not verifier.verify(payload, signature, secret):
            raise HTTPException(400, "Invalid signature")
    """

    SIGNATURE_HEADER = "X-Sardis-Signature"
    TIMESTAMP_HEADER = "X-Sardis-Timestamp"
    TOLERANCE_SECONDS = 300  # 5 minute tolerance for replay protection

    def __init__(
        self,
        secret: Optional[str] = None,
        tolerance_seconds: int = TOLERANCE_SECONDS,
    ):
        """Initialize verifier for instance-style usage."""
        self._secret = secret
        self._tolerance_seconds = tolerance_seconds

    @staticmethod
    def sign(payload: bytes, secret: str, timestamp: Optional[int] = None) -> str:
        """
        Generate an HMAC-SHA256 signature for a payload.

        Args:
            payload: The raw request body bytes
            secret: The webhook signing secret
            timestamp: Unix timestamp (current time if not provided)

        Returns:
            Signature string in format "t=<timestamp>,v1=<signature>"
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Create signed payload: timestamp.payload
        signed_payload = f"{timestamp}.".encode() + payload

        # Compute HMAC-SHA256
        signature = hmac.new(
            secret.encode(),
            signed_payload,
            hashlib.sha256
        ).hexdigest()

        return f"t={timestamp},v1={signature}"

    @classmethod
    def verify_signature(
        cls,
        payload: bytes,
        signature_header: str,
        secret: str,
        tolerance: Optional[int] = None,
    ) -> bool:
        """
        Verify a webhook signature.

        Args:
            payload: The raw request body bytes
            signature_header: The X-Sardis-Signature header value
            secret: The webhook signing secret
            tolerance: Timestamp tolerance in seconds (default: 300)

        Returns:
            True if signature is valid, False otherwise
        """
        if tolerance is None:
            tolerance = cls.TOLERANCE_SECONDS

        try:
            # Parse signature header: t=<timestamp>,v1=<signature>
            parts = {}
            for part in signature_header.split(","):
                key, _, value = part.partition("=")
                parts[key.strip()] = value.strip()

            timestamp = int(parts.get("t", 0))
            expected_signature = parts.get("v1", "")

            if not timestamp or not expected_signature:
                return False

            # Check timestamp is within tolerance
            current_time = int(time.time())
            if abs(current_time - timestamp) > tolerance:
                logger.warning(
                    f"Webhook timestamp out of tolerance: {current_time - timestamp}s",
                    extra={"timestamp": timestamp, "current_time": current_time}
                )
                return False

            # Compute expected signature
            signed_payload = f"{timestamp}.".encode() + payload
            computed_signature = hmac.new(
                secret.encode(),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            # Constant-time comparison
            return hmac.compare_digest(expected_signature, computed_signature)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    def generate_signature(self, timestamp: str | int, payload: bytes) -> str:
        """
        Generate signature using the instance secret.

        This preserves backwards compatibility with tests and older integrations
        that instantiate the verifier with a secret.
        """
        if not self._secret:
            raise ValueError("Webhook secret is required to generate signatures")
        return self.sign(payload, self._secret, int(timestamp))

    def verify(self, signature_header: str, payload: bytes) -> bool:
        """Verify signature using the instance secret and tolerance."""
        if not self._secret:
            return False
        return self.verify_signature(
            payload=payload,
            signature_header=signature_header,
            secret=self._secret,
            tolerance=self._tolerance_seconds,
        )

    @classmethod
    def get_signing_headers(
        cls,
        payload: bytes,
        secret: str,
    ) -> Dict[str, str]:
        """
        Generate headers for signing an outbound webhook.

        Args:
            payload: The webhook payload bytes
            secret: The signing secret

        Returns:
            Dictionary of headers to add to the request
        """
        timestamp = int(time.time())
        signature = cls.sign(payload, secret, timestamp)

        return {
            cls.SIGNATURE_HEADER: signature,
            cls.TIMESTAMP_HEADER: str(timestamp),
            "Content-Type": "application/json",
        }


def verify_webhook_signature(
    signature_or_payload: str | bytes,
    payload_or_request: bytes | Request,
    secret: Optional[str] = None,
) -> bool | None:
    """
    FastAPI dependency for verifying webhook signatures.

    Raises HTTPException if signature is invalid.

    Usage:
        @router.post("/webhook")
        async def handle_webhook(
            request: Request,
            body: bytes = Body(...),
        ):
            verify_webhook_signature(body, request, WEBHOOK_SECRET)
            ...
    """
    # Mode 1 (bool helper): verify_webhook_signature(signature_header, payload, secret?)
    if isinstance(signature_or_payload, str) and isinstance(payload_or_request, (bytes, bytearray)):
        resolved_secret = secret or os.getenv("WEBHOOK_SECRET")
        if not resolved_secret:
            return False
        return WebhookSignatureVerifier.verify_signature(
            payload=bytes(payload_or_request),
            signature_header=signature_or_payload,
            secret=resolved_secret,
        )

    # Mode 2 (FastAPI dependency): verify_webhook_signature(payload, request, secret?)
    if isinstance(signature_or_payload, (bytes, bytearray)) and isinstance(payload_or_request, Request):
        payload = bytes(signature_or_payload)
        request = payload_or_request
        resolved_secret = secret or os.getenv("WEBHOOK_SECRET")
        if not resolved_secret:
            raise HTTPException(
                status_code=500,
                detail={
                    "type": "https://api.sardis.sh/errors/webhook-secret-missing",
                    "title": "Webhook Secret Not Configured",
                    "status": 500,
                    "detail": "WEBHOOK_SECRET is not configured",
                },
            )

        signature = request.headers.get(WebhookSignatureVerifier.SIGNATURE_HEADER)
        if not signature:
            raise HTTPException(
                status_code=400,
                detail={
                    "type": "https://api.sardis.sh/errors/missing-signature",
                    "title": "Missing Webhook Signature",
                    "status": 400,
                    "detail": f"Missing required header: {WebhookSignatureVerifier.SIGNATURE_HEADER}",
                },
            )

        if not WebhookSignatureVerifier.verify_signature(payload, signature, resolved_secret):
            raise HTTPException(
                status_code=401,
                detail={
                    "type": "https://api.sardis.sh/errors/invalid-signature",
                    "title": "Invalid Webhook Signature",
                    "status": 401,
                    "detail": "The webhook signature is invalid or expired",
                },
            )
        return None

    raise TypeError(
        "verify_webhook_signature expects either "
        "(signature_header: str, payload: bytes, secret?: str) or "
        "(payload: bytes, request: Request, secret?: str)"
    )


# Constants for common security configurations
SECURITY_HEADERS_PERMISSIVE = SecurityConfig(
    csp_script_src="'self' 'unsafe-inline' 'unsafe-eval'",
    csp_style_src="'self' 'unsafe-inline'",
    hsts_max_age=86400,  # 1 day for development
)

SECURITY_HEADERS_STRICT = SecurityConfig(
    csp_default_src="'none'",
    csp_script_src="'self'",
    csp_style_src="'self'",
    csp_img_src="'self'",
    csp_connect_src="'self'",
    csp_frame_ancestors="'none'",
    hsts_max_age=63072000,  # 2 years
    hsts_preload=True,
)
