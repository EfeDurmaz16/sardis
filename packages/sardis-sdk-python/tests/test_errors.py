"""Tests for error models."""
import pytest

from sardis_sdk.models.errors import (
    SardisError,
    APIError,
    ValidationError,
    InsufficientBalanceError,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
)


class TestSardisError:
    """Tests for base SardisError."""

    def test_basic_error(self):
        """Should create error with message only."""
        error = SardisError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.code == "SARDIS_ERROR"
        assert error.details == {}
        assert error.request_id is None

    def test_error_with_all_fields(self):
        """Should create error with all fields."""
        error = SardisError(
            message="Detailed error",
            code="CUSTOM_ERROR",
            details={"key": "value"},
            request_id="req_123",
        )
        assert error.message == "Detailed error"
        assert error.code == "CUSTOM_ERROR"
        assert error.details == {"key": "value"}
        assert error.request_id == "req_123"

    def test_str_representation(self):
        """Should format error as string."""
        error = SardisError("Test message", code="TEST_CODE")
        assert str(error) == "[TEST_CODE] Test message"

    def test_to_dict(self):
        """Should convert error to dictionary."""
        error = SardisError(
            message="Error message",
            code="ERROR_CODE",
            details={"field": "value"},
            request_id="req_456",
        )
        result = error.to_dict()
        assert result == {
            "error": {
                "code": "ERROR_CODE",
                "message": "Error message",
                "details": {"field": "value"},
                "request_id": "req_456",
            }
        }

    def test_inherits_from_exception(self):
        """Should be catchable as Exception."""
        with pytest.raises(Exception):
            raise SardisError("Test error")


class TestAPIError:
    """Tests for APIError."""

    def test_basic_api_error(self):
        """Should create API error with status code."""
        error = APIError("API failed", status_code=500)
        assert error.message == "API failed"
        assert error.status_code == 500
        assert error.code == "SARDIS_ERROR"

    def test_api_error_with_all_fields(self):
        """Should create API error with all fields."""
        error = APIError(
            message="Not authorized",
            status_code=401,
            code="UNAUTHORIZED",
            details={"reason": "expired_token"},
            request_id="req_789",
        )
        assert error.message == "Not authorized"
        assert error.status_code == 401
        assert error.code == "UNAUTHORIZED"
        assert error.details == {"reason": "expired_token"}
        assert error.request_id == "req_789"

    def test_from_response_with_error_dict(self):
        """Should create APIError from response with error object."""
        body = {
            "error": {
                "message": "Resource not found",
                "code": "NOT_FOUND",
                "details": {"id": "123"},
                "request_id": "req_abc",
            }
        }
        error = APIError.from_response(404, body)
        assert error.message == "Resource not found"
        assert error.status_code == 404
        assert error.code == "NOT_FOUND"
        assert error.details == {"id": "123"}
        assert error.request_id == "req_abc"

    def test_from_response_with_string_error(self):
        """Should create APIError from response with string error."""
        body = {"error": "Something went wrong"}
        error = APIError.from_response(500, body)
        assert error.message == "Something went wrong"
        assert error.status_code == 500
        assert error.code == "API_ERROR"

    def test_from_response_with_string_detail(self):
        """Should create APIError from response with string detail."""
        body = {"detail": "Validation failed"}
        error = APIError.from_response(400, body)
        assert error.message == "Validation failed"
        assert error.status_code == 400
        assert error.code == "API_ERROR"

    def test_from_response_with_validation_errors_list(self):
        """Should create APIError from response with validation errors list."""
        body = {
            "detail": [
                {"loc": ["body", "amount"], "msg": "field required"},
                {"loc": ["body", "merchant"], "msg": "field required"},
            ]
        }
        error = APIError.from_response(422, body)
        assert error.message == "Validation Error"
        assert error.status_code == 422
        assert error.code == "VALIDATION_ERROR"
        assert "errors" in error.details

    def test_from_response_with_empty_body(self):
        """Should create APIError from response with empty error object."""
        body = {"error": {}}
        error = APIError.from_response(500, body)
        assert error.message == "Unknown error"
        assert error.code == "API_ERROR"

    def test_inherits_from_sardis_error(self):
        """Should be catchable as SardisError."""
        with pytest.raises(SardisError):
            raise APIError("Test", status_code=500)


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_validation_error(self):
        """Should create validation error with message."""
        error = ValidationError("Invalid input")
        assert error.message == "Invalid input"
        assert error.code == "VALIDATION_ERROR"
        assert error.field is None
        assert error.details == {"field": None}

    def test_validation_error_with_field(self):
        """Should create validation error with field."""
        error = ValidationError("Amount must be positive", field="amount")
        assert error.message == "Amount must be positive"
        assert error.field == "amount"
        assert error.details == {"field": "amount"}

    def test_inherits_from_sardis_error(self):
        """Should be catchable as SardisError."""
        with pytest.raises(SardisError):
            raise ValidationError("Test")


class TestInsufficientBalanceError:
    """Tests for InsufficientBalanceError."""

    def test_insufficient_balance_error(self):
        """Should create insufficient balance error."""
        error = InsufficientBalanceError(
            message="Insufficient funds",
            required="100.00",
            available="50.00",
            currency="USDC",
        )
        assert error.message == "Insufficient funds"
        assert error.code == "INSUFFICIENT_BALANCE"
        assert error.required == "100.00"
        assert error.available == "50.00"
        assert error.currency == "USDC"
        assert error.details == {
            "required": "100.00",
            "available": "50.00",
            "currency": "USDC",
        }

    def test_inherits_from_sardis_error(self):
        """Should be catchable as SardisError."""
        with pytest.raises(SardisError):
            raise InsufficientBalanceError(
                message="Not enough",
                required="100",
                available="50",
                currency="USDC",
            )


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_basic_rate_limit_error(self):
        """Should create rate limit error."""
        error = RateLimitError("Too many requests")
        assert error.message == "Too many requests"
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self):
        """Should create rate limit error with retry_after."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert error.message == "Rate limited"
        assert error.retry_after == 60

    def test_inherits_from_sardis_error(self):
        """Should be catchable as SardisError."""
        with pytest.raises(SardisError):
            raise RateLimitError("Test")


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_default_authentication_error(self):
        """Should create authentication error with default message."""
        error = AuthenticationError()
        assert error.message == "Invalid or missing API key"
        assert error.code == "AUTHENTICATION_ERROR"

    def test_custom_authentication_error(self):
        """Should create authentication error with custom message."""
        error = AuthenticationError("Token expired")
        assert error.message == "Token expired"
        assert error.code == "AUTHENTICATION_ERROR"

    def test_inherits_from_sardis_error(self):
        """Should be catchable as SardisError."""
        with pytest.raises(SardisError):
            raise AuthenticationError()


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_not_found_error(self):
        """Should create not found error."""
        error = NotFoundError("Wallet", "wallet_123")
        assert error.message == "Wallet not found: wallet_123"
        assert error.code == "NOT_FOUND"
        assert error.resource_type == "Wallet"
        assert error.resource_id == "wallet_123"
        assert error.details == {
            "resource_type": "Wallet",
            "resource_id": "wallet_123",
        }

    def test_different_resource_types(self):
        """Should work with different resource types."""
        agent_error = NotFoundError("Agent", "agent_456")
        assert agent_error.message == "Agent not found: agent_456"

        payment_error = NotFoundError("Payment", "pay_789")
        assert payment_error.message == "Payment not found: pay_789"

    def test_inherits_from_sardis_error(self):
        """Should be catchable as SardisError."""
        with pytest.raises(SardisError):
            raise NotFoundError("Resource", "id")
