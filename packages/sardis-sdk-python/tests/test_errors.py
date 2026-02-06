"""Tests for sardis_sdk.models.errors."""

from __future__ import annotations

import pytest

from sardis_sdk.models.errors import (
    APIError,
    AuthenticationError,
    ErrorCode,
    InsufficientBalanceError,
    NotFoundError,
    RateLimitError,
    SardisError,
    ValidationError,
)


class TestSardisError:
    def test_defaults(self):
        err = SardisError("boom")
        assert err.message == "boom"
        assert err.code == ErrorCode.UNKNOWN_ERROR.value
        assert err.details == {}
        assert err.request_id is None

    def test_to_dict_shape(self):
        err = SardisError(
            message="m",
            code="CUSTOM",
            details={"k": "v"},
            request_id="req_1",
        )
        as_dict = err.to_dict()
        assert as_dict["error"]["code"] == "CUSTOM"
        assert as_dict["error"]["message"] == "m"
        assert as_dict["error"]["details"] == {"k": "v"}
        assert as_dict["error"]["request_id"] == "req_1"


class TestAPIError:
    def test_from_response_with_error_object(self):
        err = APIError.from_response(
            404,
            {"error": {"message": "Not found", "code": "NOT_FOUND", "details": {"id": "x"}, "request_id": "r"}},
        )
        assert isinstance(err, NotFoundError)
        assert err.status_code == 404
        assert err.message == "Not found"
        assert err.code == "NOT_FOUND"
        assert err.details["id"] == "x"
        assert err.details["resource_type"] == "Resource"
        assert err.details["resource_id"] == ""
        assert err.request_id == "r"

    def test_from_response_with_string_detail(self):
        err = APIError.from_response(500, {"detail": "oops"})
        assert err.status_code == 500
        assert err.message == "oops"

    def test_from_response_with_validation_errors_list(self):
        err = APIError.from_response(422, {"detail": [{"loc": ["body", "x"], "msg": "missing"}]})
        assert isinstance(err, ValidationError)
        assert err.code == ErrorCode.VALIDATION_ERROR.value
        assert "errors" in err.details


class TestAuthenticationError:
    def test_defaults(self):
        err = AuthenticationError()
        assert err.status_code == 401
        assert err.code == ErrorCode.AUTHENTICATION_ERROR.value


class TestNotFoundError:
    def test_message_and_details(self):
        err = NotFoundError(resource_type="Wallet", resource_id="wallet_123")
        assert err.status_code == 404
        assert err.code == ErrorCode.NOT_FOUND.value
        assert "Wallet not found" in err.message
        assert err.details["resource_type"] == "Wallet"
        assert err.details["resource_id"] == "wallet_123"


class TestRateLimitError:
    def test_retryable(self):
        err = RateLimitError(retry_after=12)
        assert err.status_code == 429
        assert err.retryable is True
        assert err.details["retry_after"] == 12


class TestInsufficientBalanceError:
    def test_balance_details(self):
        err = InsufficientBalanceError(required="100.00", available="50.00", currency="USDC")
        assert err.code == ErrorCode.INSUFFICIENT_BALANCE.value
        assert err.details["required"] == "100.00"
        assert err.details["available"] == "50.00"
        assert err.details["currency"] == "USDC"


class TestExceptionCatching:
    def test_inherits_exception(self):
        with pytest.raises(SardisError):
            raise ValidationError("bad input")
