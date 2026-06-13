"""Structural tests for the Anthropic-compatible error hierarchy.

The official Anthropic Python SDK exposes a layered exception tree
(``APIError`` -> ``APIStatusError`` -> ``BadRequestError`` / ``RateLimitError``
/ ...). Agent developers migrating from ``anthropic`` reuse those names and
``except`` clauses verbatim, so we assert the same shape and the same
top-level re-exports here.
"""

from __future__ import annotations

import sardis
from sardis.models.errors import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SardisError,
    ServerError,
    TimeoutError,
    UnprocessableEntityError,
    ValidationError,
)


class TestHierarchy:
    def test_api_status_error_subclasses_api_error(self) -> None:
        assert issubclass(APIStatusError, APIError)
        assert issubclass(APIError, SardisError)

    def test_status_errors_are_api_status_errors(self) -> None:
        for cls in (
            BadRequestError,
            AuthenticationError,
            PermissionDeniedError,
            NotFoundError,
            ConflictError,
            UnprocessableEntityError,
            RateLimitError,
            InternalServerError,
        ):
            assert issubclass(cls, APIStatusError), cls

    def test_backwards_compatible_subclassing(self) -> None:
        # 403 used to raise AuthenticationError; 422 used to raise
        # ValidationError. The new specific classes keep those parents so old
        # except clauses still catch them.
        assert issubclass(PermissionDeniedError, AuthenticationError)
        assert issubclass(UnprocessableEntityError, ValidationError)

    def test_internal_server_error_is_server_error_alias(self) -> None:
        assert InternalServerError is ServerError

    def test_connection_and_timeout_aliases(self) -> None:
        assert APIConnectionError is NetworkError
        assert APITimeoutError is TimeoutError
        # Transport errors are NOT status errors.
        assert not issubclass(APIConnectionError, APIStatusError)


class TestStatusCodes:
    def test_default_status_codes(self) -> None:
        assert BadRequestError().status_code == 400
        assert AuthenticationError().status_code == 401
        assert PermissionDeniedError().status_code == 403
        assert NotFoundError().status_code == 404
        assert ConflictError().status_code == 409
        assert UnprocessableEntityError().status_code == 422
        assert RateLimitError().status_code == 429
        assert InternalServerError().status_code == 500


class TestTopLevelExports:
    def test_errors_exposed_at_package_root(self) -> None:
        # anthropic.RateLimitError -> sardis.RateLimitError
        for name in (
            "SardisError",
            "APIError",
            "APIStatusError",
            "APIConnectionError",
            "APITimeoutError",
            "BadRequestError",
            "AuthenticationError",
            "PermissionDeniedError",
            "NotFoundError",
            "ConflictError",
            "UnprocessableEntityError",
            "RateLimitError",
            "InternalServerError",
            "ValidationError",
        ):
            assert hasattr(sardis, name), name

    def test_root_export_identity(self) -> None:
        assert sardis.RateLimitError is RateLimitError
        assert sardis.BadRequestError is BadRequestError
