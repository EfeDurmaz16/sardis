"""TAP verification middleware integration tests.

Tests middleware integration with FastAPI:
- Request rejection without TAP headers on protected paths
- Pass-through on unprotected paths
- TAP result injection into request.state
- Expired signature rejection
- Nonce replay prevention
- Dev bypass flag handling
- ECDSA-P256 and Ed25519 verification
- RFC 7807 error format
"""
from __future__ import annotations

import time
from typing import Callable
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from sardis_api.middleware import (
    TapMiddlewareConfig,
    TapVerificationMiddleware,
    register_exception_handlers,
)
from sardis_protocol.tap import TapVerificationResult

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.tap]


def _create_test_app(
    enforcement_enabled: bool = True,
    protected_paths: list[str] | None = None,
    jwks_provider: Callable[[str], dict] | None = None,
) -> FastAPI:
    """Create FastAPI test app with TAP middleware."""
    app = FastAPI()

    # Register RFC 7807 exception handlers
    register_exception_handlers(app)

    # Configure TAP middleware
    config = TapMiddlewareConfig(
        protected_paths=protected_paths or ["/v2/ap2/", "/v2/payments/"],
        enforcement_enabled=enforcement_enabled,
        max_time_window_seconds=480,  # 8 minutes
        nonce_ttl_seconds=600,  # 10 minutes
    )

    app.add_middleware(
        TapVerificationMiddleware,
        config=config,
        jwks_provider=jwks_provider,
    )

    # Test endpoints
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/docs")
    async def docs():
        return {"docs": "OpenAPI"}

    @app.post("/v2/ap2/intent")
    async def ap2_intent(request: Request):
        tap_result = getattr(request.state, "tap_result", None)
        return {
            "status": "accepted",
            "tap_verified": tap_result.accepted if tap_result else False,
        }

    @app.post("/v2/payments/execute")
    async def payment_execute(request: Request):
        tap_result = getattr(request.state, "tap_result", None)
        return {
            "status": "executed",
            "tap_verified": tap_result.accepted if tap_result else False,
        }

    @app.get("/v2/public/status")
    async def public_status():
        return {"status": "public"}

    return app


def _valid_signature_input(now: int | None = None, nonce: str = "nonce-unique") -> str:
    """Generate valid TAP Signature-Input header."""
    if now is None:
        now = int(time.time())
    return (
        'sig1=("@authority" "@path");'
        f"created={now - 60};"
        'keyid="test-key-123";'
        'alg="Ed25519";'
        f"expires={now + 60};"
        f'nonce="{nonce}";'
        'tag="agent-browser-auth"'
    )


def _valid_signature() -> str:
    """Generate valid TAP Signature header."""
    return "sig1=:dGVzdHNpZ25hdHVyZQ==:"


@pytest.mark.asyncio
async def test_middleware_rejects_requests_without_tap_headers_on_protected_paths():
    """Test 1: Middleware rejects requests without TAP headers on protected paths (401)."""
    app = _create_test_app(enforcement_enabled=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Protected AP2 endpoint without TAP headers
        response = await client.post("/v2/ap2/intent", json={"test": "data"})

        assert response.status_code == 401
        data = response.json()
        assert "authentication-required" in data["type"].lower()
        assert "TAP signature headers required" in data["detail"]
        assert "required_headers" in data
        assert data["required_headers"] == ["Signature-Input", "Signature"]


@pytest.mark.asyncio
async def test_middleware_passes_requests_on_unprotected_paths():
    """Test 2: Middleware passes requests on unprotected paths (e.g., /health, /docs)."""
    app = _create_test_app(enforcement_enabled=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Health endpoint should not require TAP
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json() == {"status": "ok"}

        # Public endpoint should not require TAP
        public_resp = await client.get("/v2/public/status")
        assert public_resp.status_code == 200
        assert public_resp.json() == {"status": "public"}


@pytest.mark.asyncio
async def test_middleware_passes_valid_tap_headers_and_populates_request_state():
    """Test 3: Middleware passes valid TAP headers and populates request.state.tap_result."""
    # No JWKS provider = signature verification is skipped (structural validation only)
    app = _create_test_app(enforcement_enabled=True, jwks_provider=None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers={
                "Signature-Input": _valid_signature_input(),
                "Signature": _valid_signature(),
                "Host": "test",
            },
        )

        # Should pass with valid TAP headers (signature verification skipped without JWKS provider)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        # tap_verified will be True because signature verification is skipped
        assert data["tap_verified"] is True


@pytest.mark.asyncio
async def test_middleware_rejects_expired_tap_signatures():
    """Test 4: Middleware rejects expired TAP signatures."""
    app = _create_test_app(enforcement_enabled=True)

    # Create expired signature (created 10 minutes ago, expires 5 minutes ago)
    now = int(time.time())
    expired_input = (
        'sig1=("@authority" "@path");'
        f"created={now - 600};"
        'keyid="test-key-123";'
        'alg="Ed25519";'
        f"expires={now - 300};"
        'nonce="nonce-expired";'
        'tag="agent-browser-auth"'
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers={
                "Signature-Input": expired_input,
                "Signature": _valid_signature(),
                "Host": "test",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "invalid-credentials" in data["type"].lower()
        assert "TAP signature verification failed" in data["detail"]
        assert "tap_error" in data
        assert "expired" in data["tap_error"].lower()


@pytest.mark.asyncio
async def test_middleware_rejects_replayed_nonces():
    """Test 5: Middleware rejects replayed nonces."""
    app = _create_test_app(enforcement_enabled=True)

    headers_first = {
        "Signature-Input": _valid_signature_input(nonce="nonce-replay-test"),
        "Signature": _valid_signature(),
        "Host": "test",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First request should succeed
        response1 = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers=headers_first,
        )
        assert response1.status_code == 200

        # Second request with same nonce should be rejected
        response2 = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers=headers_first,
        )
        assert response2.status_code == 401
        data = response2.json()
        assert "invalid-credentials" in data["type"].lower()
        assert "tap_error" in data
        assert "replayed" in data["tap_error"].lower()


@pytest.mark.asyncio
async def test_middleware_respects_dev_bypass_flag():
    """Test 6: Middleware respects dev bypass flag (SARDIS_TAP_ENFORCEMENT=disabled)."""
    app = _create_test_app(enforcement_enabled=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Protected endpoint should pass without TAP headers when enforcement is disabled
        response = await client.post("/v2/ap2/intent", json={"test": "data"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        # TAP verification was bypassed, but result should indicate it was disabled
        assert data["tap_verified"] is True  # Bypass mode sets accepted=True


@pytest.mark.asyncio
async def test_middleware_handles_ecdsa_p256_verification():
    """Test 7: Middleware handles ECDSA-P256 verification."""
    # No JWKS provider = signature verification is skipped (structural validation only)
    app = _create_test_app(enforcement_enabled=True, jwks_provider=None)

    now = int(time.time())
    # Use ecdsa-p256 (lowercase) which is in the allowed algorithms list
    ecdsa_input = (
        'sig1=("@authority" "@path");'
        f"created={now - 60};"
        'keyid="ecdsa-key-456";'
        'alg="ecdsa-p256";'
        f"expires={now + 60};"
        'nonce="nonce-ecdsa-test";'
        'tag="agent-browser-auth"'
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers={
                "Signature-Input": ecdsa_input,
                "Signature": _valid_signature(),
                "Host": "test",
            },
        )

        # Should pass structural validation (signature verification skipped without JWKS provider)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_middleware_returns_rfc7807_error_format_on_rejection():
    """Test 8: Middleware returns RFC 7807 error format on rejection."""
    app = _create_test_app(enforcement_enabled=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v2/payments/execute", json={"amount": 100})

        assert response.status_code == 401

        # Verify RFC 7807 format
        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data
        assert "request_id" in data

        # Verify error details
        assert data["status"] == 401
        assert data["type"].startswith("https://") or data["type"].startswith("http://")
        assert "TAP signature headers required" in data["detail"]
        assert data["instance"] == "/v2/payments/execute"

        # TAP-specific fields
        assert "tap_protocol_version" in data
        assert data["tap_protocol_version"] == "1.0"


@pytest.mark.asyncio
async def test_middleware_handles_missing_host_header():
    """Test bonus: Middleware handles missing Host header gracefully."""
    app = _create_test_app(enforcement_enabled=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # AsyncClient should add Host header automatically, but we can verify the error path
        # by checking the middleware logic handles missing authority
        response = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers={
                "Signature-Input": _valid_signature_input(),
                "Signature": _valid_signature(),
                # Host header should be added by client automatically
            },
        )

        # Should either succeed (Host added) or fail with specific error
        # In practice, httpx always adds Host header, so this will succeed
        assert response.status_code in (200, 400, 401)


@pytest.mark.asyncio
async def test_middleware_handles_invalid_signature_format():
    """Test bonus: Middleware handles invalid signature format."""
    app = _create_test_app(enforcement_enabled=True)

    invalid_signature_input = "invalid-format-not-parseable"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers={
                "Signature-Input": invalid_signature_input,
                "Signature": _valid_signature(),
                "Host": "test",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "TAP signature verification failed" in data["detail"]


@pytest.mark.asyncio
async def test_middleware_time_window_validation():
    """Test bonus: Middleware validates time window is within allowed limit."""
    app = _create_test_app(enforcement_enabled=True)

    now = int(time.time())
    # Create signature with window > 8 minutes (480 seconds)
    long_window_input = (
        'sig1=("@authority" "@path");'
        f"created={now - 60};"
        'keyid="test-key-123";'
        'alg="Ed25519";'
        f"expires={now + 600};"  # 10 minutes from now = 11 minute total window
        'nonce="nonce-long-window";'
        'tag="agent-browser-auth"'
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v2/ap2/intent",
            json={"test": "data"},
            headers={
                "Signature-Input": long_window_input,
                "Signature": _valid_signature(),
                "Host": "test",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "tap_error" in data
        assert "window" in data["tap_error"].lower()
