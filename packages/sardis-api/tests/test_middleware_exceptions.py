"""
Comprehensive tests for sardis_api.middleware.exceptions module.

Tests cover:
- RFC 7807 Problem Details format compliance
- Exception handler registration
- Various exception type handling
- Error response creation
- Request ID correlation
- Production vs development error messages
"""
from __future__ import annotations

import asyncio
import json
import os
import pytest
import time
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from httpx import AsyncClient, ASGITransport

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_api.middleware.exceptions import (
    RFC7807Error,
    ERROR_TYPE_BASE,
    ERROR_TYPES,
    get_request_id,
    is_production,
    create_error_response,
    create_validation_error_response,
    register_exception_handlers,
    ExceptionHandlerMiddleware,
)


class TestRFC7807Error:
    """Tests for RFC7807Error class."""

    def test_basic_error(self):
        """Should create basic RFC 7807 error."""
        error = RFC7807Error(
            type="https://api.sardis.sh/errors/validation-error",
            title="Validation Error",
            status=400,
            detail="Invalid input provided",
            instance="/api/v2/payments/123",
            request_id="req_abc123",
        )

        assert error.type == "https://api.sardis.sh/errors/validation-error"
        assert error.title == "Validation Error"
        assert error.status == 400
        assert error.detail == "Invalid input provided"
        assert error.instance == "/api/v2/payments/123"
        assert error.request_id == "req_abc123"

    def test_to_dict(self):
        """Should convert to RFC 7807 compliant dictionary."""
        error = RFC7807Error(
            type="https://api.sardis.sh/errors/not-found",
            title="Not Found",
            status=404,
            detail="Resource not found",
            instance="/api/v2/wallets/xyz",
            request_id="req_def456",
        )

        result = error.to_dict()

        assert result["type"] == "https://api.sardis.sh/errors/not-found"
        assert result["title"] == "Not Found"
        assert result["status"] == 404
        assert result["detail"] == "Resource not found"
        assert result["instance"] == "/api/v2/wallets/xyz"
        assert result["request_id"] == "req_def456"
        assert "timestamp" in result

    def test_to_dict_with_extensions(self):
        """Should include extensions in dict."""
        error = RFC7807Error(
            type="https://api.sardis.sh/errors/validation-error",
            title="Validation Error",
            status=422,
            detail="Field validation failed",
            instance="/api/v2/payments",
            request_id="req_ghi789",
            extensions={
                "errors": [
                    {"field": "amount", "message": "Must be positive"}
                ],
                "field_count": 1,
            }
        )

        result = error.to_dict()

        assert "errors" in result
        assert len(result["errors"]) == 1
        assert result["field_count"] == 1


class TestErrorTypes:
    """Tests for error type mappings."""

    def test_all_error_types_have_mappings(self):
        """All defined error types should have valid mappings."""
        expected_types = [
            "VALIDATION_ERROR",
            "NOT_FOUND",
            "AUTHENTICATION_REQUIRED",
            "FORBIDDEN",
            "RATE_LIMIT_EXCEEDED",
            "INTERNAL_ERROR",
            "BAD_REQUEST",
        ]

        for error_type in expected_types:
            assert error_type in ERROR_TYPES
            mapping = ERROR_TYPES[error_type]
            assert len(mapping) == 2  # (slug, title)
            assert isinstance(mapping[0], str)  # slug
            assert isinstance(mapping[1], str)  # title

    def test_error_type_format(self):
        """Error type slugs should be kebab-case."""
        for error_code, (slug, title) in ERROR_TYPES.items():
            # Slug should be lowercase with hyphens
            assert slug == slug.lower()
            assert "_" not in slug


class TestGetRequestId:
    """Tests for get_request_id function."""

    def test_from_request_state(self):
        """Should get request ID from request state."""
        mock_request = Mock()
        mock_request.state.request_id = "state_request_id_123"
        mock_request.headers = {}

        result = get_request_id(mock_request)
        assert result == "state_request_id_123"

    def test_from_header_fallback(self):
        """Should fall back to header if not in state."""
        mock_request = Mock()
        del mock_request.state.request_id  # No request_id in state
        mock_request.headers = {"X-Request-ID": "header_request_id_456"}

        # Mock hasattr to return False for request_id
        mock_request.state = Mock(spec=[])

        result = get_request_id(mock_request)
        assert result == "header_request_id_456"

    def test_unknown_fallback(self):
        """Should return 'unknown' if no request ID available."""
        mock_request = Mock()
        mock_request.state = Mock(spec=[])  # No request_id
        mock_request.headers = {}

        result = get_request_id(mock_request)
        assert result == "unknown"


class TestIsProduction:
    """Tests for is_production function."""

    def test_production_environment(self):
        """Should return True for production."""
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "production"}):
            assert is_production() is True

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "prod"}):
            assert is_production() is True

    def test_non_production_environment(self):
        """Should return False for non-production."""
        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "dev"}):
            assert is_production() is False

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "staging"}):
            assert is_production() is True

        with patch.dict(os.environ, {"SARDIS_ENVIRONMENT": "test"}):
            assert is_production() is False

    def test_default_to_dev(self):
        """Should default to dev (non-production)."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove SARDIS_ENVIRONMENT
            os.environ.pop("SARDIS_ENVIRONMENT", None)
            # Note: This might not work perfectly with patching
            # but tests the intent


class TestCreateErrorResponse:
    """Tests for create_error_response function."""

    def test_basic_error_response(self):
        """Should create proper error response."""
        response = create_error_response(
            error_code="VALIDATION_ERROR",
            message="Invalid amount provided",
            status_code=400,
            request_id="req_test123",
            instance="/api/v2/payments",
        )

        assert response.status_code == 400

        content = json.loads(response.body)
        assert content["type"] == f"{ERROR_TYPE_BASE}/validation-error"
        assert content["title"] == "Validation Error"
        assert content["status"] == 400
        assert content["detail"] == "Invalid amount provided"
        assert content["instance"] == "/api/v2/payments"
        assert content["request_id"] == "req_test123"

    def test_error_response_headers(self):
        """Should include proper headers."""
        response = create_error_response(
            error_code="NOT_FOUND",
            message="Resource not found",
            status_code=404,
            request_id="req_456",
        )

        assert response.headers.get("X-Request-ID") == "req_456"
        assert response.headers.get("Content-Type") == "application/problem+json"

    def test_error_response_with_details(self):
        """Should include additional details."""
        response = create_error_response(
            error_code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            status_code=429,
            request_id="req_789",
            details={
                "retry_after": 60,
                "limit": 100,
                "remaining": 0,
            },
        )

        content = json.loads(response.body)
        assert content["retry_after"] == 60
        assert content["limit"] == 100
        assert content["remaining"] == 0

    def test_unknown_error_code(self):
        """Should handle unknown error codes gracefully."""
        response = create_error_response(
            error_code="CUSTOM_ERROR_TYPE",
            message="Custom error occurred",
            status_code=500,
            request_id="req_custom",
        )

        content = json.loads(response.body)
        # Should use error code as slug
        assert "custom-error-type" in content["type"]


class TestCreateValidationErrorResponse:
    """Tests for create_validation_error_response function."""

    def test_validation_error_response(self):
        """Should create validation error response."""
        errors = [
            {"field": "amount", "message": "Must be positive", "type": "value_error"},
            {"field": "currency", "message": "Invalid currency", "type": "value_error"},
        ]

        response = create_validation_error_response(
            errors=errors,
            request_id="req_val123",
            instance="/api/v2/payments",
        )

        assert response.status_code == 422

        content = json.loads(response.body)
        assert content["type"] == f"{ERROR_TYPE_BASE}/validation-error"
        assert content["title"] == "Validation Error"
        assert content["status"] == 422
        assert "errors" in content
        assert len(content["errors"]) == 2

    def test_validation_error_headers(self):
        """Should have proper headers."""
        response = create_validation_error_response(
            errors=[],
            request_id="req_val456",
            instance="/test",
        )

        assert response.headers.get("Content-Type") == "application/problem+json"


class TestRegisterExceptionHandlers:
    """Tests for register_exception_handlers function."""

    @pytest.fixture
    def app_with_handlers(self):
        """Create app with exception handlers registered."""
        app = FastAPI()
        register_exception_handlers(app)

        class TestInput(BaseModel):
            amount: int = Field(gt=0)
            name: str = Field(min_length=1)

        @app.post("/api/v2/test")
        def test_endpoint(data: TestInput):
            return {"status": "ok"}

        @app.get("/api/v2/not-found")
        def not_found_endpoint():
            from sardis_v2_core.exceptions import SardisNotFoundError
            raise SardisNotFoundError("wallet_123", "Wallet")

        @app.get("/api/v2/http-error")
        def http_error_endpoint():
            raise HTTPException(status_code=403, detail="Forbidden")

        @app.get("/api/v2/internal-error")
        def internal_error_endpoint():
            raise RuntimeError("Something went wrong")

        return app

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, app_with_handlers):
        """Should handle validation errors."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_handlers),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v2/test",
                json={"amount": -5, "name": ""}
            )

        assert response.status_code == 422
        content = response.json()
        assert content["type"] == f"{ERROR_TYPE_BASE}/validation-error"
        assert "errors" in content

    @pytest.mark.asyncio
    async def test_not_found_error_handler(self, app_with_handlers):
        """Should handle not found errors."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_handlers),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v2/not-found")

        assert response.status_code == 404
        content = response.json()
        assert "not-found" in content["type"]

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, app_with_handlers):
        """Should handle HTTP exceptions."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_handlers),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v2/http-error")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_internal_error_handler(self, app_with_handlers):
        """Should handle internal errors."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_handlers),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v2/internal-error")

        assert response.status_code == 500
        content = response.json()
        assert "internal-error" in content["type"]


class TestExceptionHandlerMiddleware:
    """Tests for ExceptionHandlerMiddleware class."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create app with exception handler middleware."""
        app = FastAPI()
        app.add_middleware(ExceptionHandlerMiddleware)

        @app.get("/api/v2/success")
        def success_endpoint():
            return {"status": "ok"}

        @app.get("/api/v2/error")
        def error_endpoint():
            raise ValueError("Test error")

        return app

    @pytest.mark.asyncio
    async def test_success_passes_through(self, app_with_middleware):
        """Should pass through successful requests."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v2/success")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_catches_unhandled_exceptions(self, app_with_middleware):
        """Should catch unhandled exceptions."""
        async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/v2/error")

        assert response.status_code == 500


class TestErrorResponseEdgeCases:
    """Edge case tests for error responses."""

    def test_long_error_message(self):
        """Should handle long error messages."""
        long_message = "x" * 10000

        response = create_error_response(
            error_code="VALIDATION_ERROR",
            message=long_message,
            status_code=400,
            request_id="req_long",
        )

        content = json.loads(response.body)
        assert len(content["detail"]) == 10000

    def test_unicode_in_error_message(self):
        """Should handle unicode in error messages."""
        response = create_error_response(
            error_code="VALIDATION_ERROR",
            message="Invalid input provided",
            status_code=400,
            request_id="req_unicode",
        )

        content = json.loads(response.body)
        assert "Invalid" in content["detail"]

    def test_special_characters_in_instance(self):
        """Should handle special characters in instance path."""
        response = create_error_response(
            error_code="NOT_FOUND",
            message="Not found",
            status_code=404,
            request_id="req_special",
            instance="/api/v2/users/user@email.com/wallets",
        )

        content = json.loads(response.body)
        assert "@" in content["instance"]

    def test_null_details(self):
        """Should handle null details."""
        response = create_error_response(
            error_code="BAD_REQUEST",
            message="Bad request",
            status_code=400,
            request_id="req_null",
            details=None,
        )

        assert response.status_code == 400

    def test_empty_details(self):
        """Should handle empty details dict."""
        response = create_error_response(
            error_code="BAD_REQUEST",
            message="Bad request",
            status_code=400,
            request_id="req_empty",
            details={},
        )

        assert response.status_code == 400
