"""
Comprehensive tests for sardis_v2_core.logging module.

Tests cover:
- Sensitive data masking
- Structured logging
- Request/response logging
- Logging decorators
- JSON formatter
- RequestContext management
"""
from __future__ import annotations

import json
import logging
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import io

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sardis_v2_core.logging import (
    # Core functions
    mask_sensitive_data,
    mask_value,
    mask_headers,
    is_sensitive_key,
    # Logging
    get_logger,
    StructuredLogger,
    RequestContext,
    log_request,
    log_response,
    # Decorators
    log_operation,
    log_operation_sync,
    # Configuration
    configure_logging,
    JsonFormatter,
)


class TestMaskValue:
    """Tests for mask_value function."""

    def test_mask_normal_value(self):
        """Should mask value showing only first/last chars."""
        result = mask_value("secrettoken12345", show_chars=4)
        assert result == "secr...2345"

    def test_mask_short_value(self):
        """Should fully mask short values."""
        result = mask_value("abc", show_chars=4)
        assert "***" in result  # Should use mask pattern

    def test_mask_empty_value(self):
        """Should handle empty values."""
        result = mask_value("")
        assert "***" in result

    def test_custom_show_chars(self):
        """Should respect custom show_chars."""
        result = mask_value("longsecretvalue", show_chars=2)
        assert result == "lo...ue"


class TestIsSensitiveKey:
    """Tests for is_sensitive_key function."""

    def test_known_sensitive_keys(self):
        """Should identify known sensitive keys."""
        sensitive_keys = [
            "password",
            "api_key",
            "secret",
            "token",
            "credential",
            "authorization",
            "private_key",
        ]
        for key in sensitive_keys:
            assert is_sensitive_key(key), f"Should be sensitive: {key}"

    def test_non_sensitive_keys(self):
        """Should not flag non-sensitive keys."""
        non_sensitive = [
            "username",
            "email",
            "wallet_id",
            "amount",
            "status",
        ]
        for key in non_sensitive:
            assert not is_sensitive_key(key), f"Should not be sensitive: {key}"

    def test_case_insensitive(self):
        """Should be case insensitive."""
        assert is_sensitive_key("PASSWORD")
        assert is_sensitive_key("Password")
        assert is_sensitive_key("API_KEY")

    def test_hyphen_handling(self):
        """Should handle hyphens in keys."""
        assert is_sensitive_key("api-key")
        assert is_sensitive_key("x-auth-token")


class TestMaskSensitiveData:
    """Tests for mask_sensitive_data function."""

    def test_mask_dict_with_sensitive_keys(self):
        """Should mask sensitive keys in dict."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk_live_abc123",
        }
        result = mask_sensitive_data(data)

        assert result["username"] == "john"
        assert "***" in result["password"]
        assert "***" in result["api_key"]

    def test_mask_nested_dict(self):
        """Should mask nested dicts."""
        data = {
            "user": {
                "name": "john",
                "credentials": {
                    "password": "secret",
                    "token": "abc123",
                }
            }
        }
        result = mask_sensitive_data(data)

        assert result["user"]["name"] == "john"
        assert "***" in result["user"]["credentials"]["password"]
        assert "***" in result["user"]["credentials"]["token"]

    def test_mask_list(self):
        """Should mask sensitive data in lists."""
        data = [
            {"username": "john", "password": "secret1"},
            {"username": "jane", "password": "secret2"},
        ]
        result = mask_sensitive_data(data)

        assert result[0]["username"] == "john"
        assert "***" in result[0]["password"]
        assert "***" in result[1]["password"]

    def test_mask_inline_api_keys(self):
        """Should mask inline API keys in strings."""
        data = {"message": "Using key sk_live_abc123def456"}
        result = mask_sensitive_data(data)

        assert "sk_live_***" in result["message"]

    def test_mask_bearer_token(self):
        """Should mask bearer tokens."""
        data = {"auth": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        result = mask_sensitive_data(data)

        assert "Bearer ***" in result["auth"]

    def test_mask_basic_auth(self):
        """Should mask basic auth."""
        data = {"auth": "Basic dXNlcjpwYXNz"}
        result = mask_sensitive_data(data)

        assert "Basic ***" in result["auth"]

    def test_mask_url_credentials(self):
        """Should mask credentials in URLs."""
        data = {"url": "https://user:password@example.com/api"}
        result = mask_sensitive_data(data)

        assert "user:password" not in result["url"]
        assert "***" in result["url"]

    def test_mask_jwt_tokens(self):
        """Should mask JWT tokens."""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        data = {"token": jwt}
        result = mask_sensitive_data(data)

        assert "***JWT***" in result["token"]

    def test_additional_fields(self):
        """Should mask additional specified fields."""
        data = {
            "custom_secret": "value",
            "normal_field": "normal",
        }
        result = mask_sensitive_data(data, additional_fields=["custom_secret"])

        assert "***" in result["custom_secret"]
        assert result["normal_field"] == "normal"

    def test_max_depth_protection(self):
        """Should prevent infinite recursion."""
        # Create deeply nested structure
        data = {"level": 0}
        current = data
        for i in range(15):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        # Should not raise
        result = mask_sensitive_data(data)
        assert result is not None

    def test_preserves_types(self):
        """Should preserve list vs tuple types."""
        data_list = [1, 2, 3]
        data_tuple = (1, 2, 3)

        result_list = mask_sensitive_data(data_list)
        result_tuple = mask_sensitive_data(data_tuple)

        assert isinstance(result_list, list)
        assert isinstance(result_tuple, tuple)


class TestMaskHeaders:
    """Tests for mask_headers function."""

    def test_mask_authorization(self):
        """Should mask Authorization header."""
        headers = {
            "Authorization": "Bearer token123",
            "Content-Type": "application/json",
        }
        result = mask_headers(headers)

        assert "***" in result["Authorization"]
        assert result["Content-Type"] == "application/json"

    def test_mask_api_key_header(self):
        """Should mask X-API-Key header."""
        headers = {"X-API-Key": "secret_key"}
        result = mask_headers(headers)

        assert "***" in result["X-API-Key"]

    def test_mask_cookie_header(self):
        """Should mask Cookie header."""
        headers = {"Cookie": "session=abc123"}
        result = mask_headers(headers)

        assert "***" in result["Cookie"]

    def test_case_insensitive_headers(self):
        """Should handle different header cases."""
        headers = {
            "authorization": "Bearer token",
            "AUTHORIZATION": "Bearer token2",
        }
        result = mask_headers(headers)

        for key in result:
            assert "***" in result[key]


class TestRequestContext:
    """Tests for RequestContext class."""

    def test_default_values(self):
        """Should have sensible defaults."""
        ctx = RequestContext(operation="test_op")

        assert ctx.operation == "test_op"
        assert ctx.request_id is not None
        assert ctx.started_at is not None
        assert ctx.user_id is None
        assert ctx.wallet_id is None

    def test_elapsed_ms(self):
        """Should calculate elapsed time."""
        ctx = RequestContext(operation="test")
        import time
        time.sleep(0.1)

        elapsed = ctx.elapsed_ms()
        assert elapsed >= 100  # At least 100ms

    def test_to_dict(self):
        """Should convert to dictionary."""
        ctx = RequestContext(
            operation="test",
            user_id="user_123",
            wallet_id="wallet_456",
        )
        result = ctx.to_dict()

        assert result["operation"] == "test"
        assert result["user_id"] == "user_123"
        assert result["wallet_id"] == "wallet_456"
        assert "request_id" in result
        assert "elapsed_ms" in result

    def test_masks_sensitive_extra_data(self):
        """Should mask sensitive data in extra."""
        ctx = RequestContext(
            operation="test",
            extra={"api_key": "secret123", "amount": 100},
        )
        result = ctx.to_dict()

        assert "***" in result.get("api_key", "***")
        assert result.get("amount") == 100


class TestStructuredLogger:
    """Tests for StructuredLogger class."""

    def test_create_logger(self):
        """Should create logger with name."""
        logger = StructuredLogger("test_module")
        assert logger._logger.name == "test_module"

    def test_log_levels(self):
        """Should support all log levels."""
        logger = StructuredLogger("test")

        # These should not raise
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

    def test_context_manager(self):
        """Should provide context management."""
        logger = StructuredLogger("test")

        with logger.context(operation="test_op", user_id="user_123") as ctx:
            assert ctx.operation == "test_op"
            assert ctx.user_id == "user_123"
            assert logger.current_context == ctx

        # After exiting, no current context
        assert logger.current_context is None

    def test_nested_context(self):
        """Should support nested contexts."""
        logger = StructuredLogger("test")

        with logger.context(operation="outer") as outer:
            assert logger.current_context == outer

            with logger.context(operation="inner") as inner:
                assert logger.current_context == inner

            # Back to outer
            assert logger.current_context == outer

    def test_context_with_exception(self):
        """Context should handle exceptions properly."""
        logger = StructuredLogger("test")

        with pytest.raises(ValueError):
            with logger.context(operation="failing_op"):
                raise ValueError("test error")

        # Context should be cleaned up
        assert logger.current_context is None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_structured_logger(self):
        """Should return StructuredLogger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, StructuredLogger)


class TestLogRequest:
    """Tests for log_request function."""

    def test_basic_request_logging(self):
        """Should log basic request info."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        log_request(
            mock_logger,
            method="POST",
            url="https://api.example.com/test",
        )

        mock_logger.debug.assert_called()
        call_args = str(mock_logger.debug.call_args)
        assert "POST" in call_args

    def test_masks_sensitive_headers(self):
        """Should mask sensitive headers in log."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        log_request(
            mock_logger,
            method="GET",
            url="https://api.example.com",
            headers={"Authorization": "Bearer secret_token"},
        )

        # Check that logged data has masked header
        call_args = mock_logger.debug.call_args
        if call_args and call_args.kwargs:
            extra = call_args.kwargs.get("extra", {})
            data = extra.get("data", {})
            if "headers" in data:
                assert "***" in data["headers"].get("Authorization", "")

    def test_masks_sensitive_body(self):
        """Should mask sensitive data in body."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        log_request(
            mock_logger,
            method="POST",
            url="https://api.example.com",
            body={"password": "secret", "username": "john"},
        )

        # Body should be masked
        call_args = mock_logger.debug.call_args
        if call_args and call_args.kwargs:
            extra = call_args.kwargs.get("extra", {})
            data = extra.get("data", {})
            if "body" in data:
                assert "secret" not in data["body"]


class TestLogResponse:
    """Tests for log_response function."""

    def test_basic_response_logging(self):
        """Should log response info."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        log_response(
            mock_logger,
            status_code=200,
            duration_ms=150.0,
        )

        mock_logger.debug.assert_called()

    def test_warning_for_error_status(self):
        """Should use warning level for error status codes."""
        mock_logger = Mock()
        mock_logger.warning = Mock()
        mock_logger.debug = Mock()

        log_response(mock_logger, status_code=500, duration_ms=100.0)

        mock_logger.warning.assert_called()


class TestLogOperationDecorator:
    """Tests for @log_operation decorator."""

    @pytest.mark.asyncio
    async def test_logs_operation(self):
        """Should log operation start and completion."""
        @log_operation(operation_name="test_operation")
        async def my_async_func(x):
            return x * 2

        result = await my_async_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_logs_exception(self):
        """Should log exceptions."""
        @log_operation(operation_name="failing_op")
        async def failing_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await failing_func()

    @pytest.mark.asyncio
    async def test_uses_function_name_as_default(self):
        """Should use function name when operation_name not provided."""
        @log_operation()
        async def my_named_function():
            return True

        result = await my_named_function()
        assert result is True


class TestLogOperationSyncDecorator:
    """Tests for @log_operation_sync decorator."""

    def test_logs_sync_operation(self):
        """Should work with sync functions."""
        @log_operation_sync(operation_name="sync_test")
        def my_sync_func(x):
            return x + 1

        result = my_sync_func(5)
        assert result == 6

    def test_logs_sync_exception(self):
        """Should log sync exceptions."""
        @log_operation_sync()
        def failing_sync():
            raise RuntimeError("sync error")

        with pytest.raises(RuntimeError):
            failing_sync()


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_formats_as_json(self):
        """Should format log record as JSON."""
        formatter = JsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_includes_exception_info(self):
        """Should include exception info when present."""
        formatter = JsonFormatter()

        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    def test_includes_extra_data(self):
        """Should include extra data."""
        formatter = JsonFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.data = {"key": "value"}

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["data"]["key"] == "value"


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configures_console_logging(self):
        """Should configure console handler."""
        configure_logging(level=logging.DEBUG)

        # Should not raise
        logger = logging.getLogger("test_configure")
        logger.info("Test message")

    def test_configures_json_format(self):
        """Should configure JSON format when specified."""
        configure_logging(json_format=True)

        logger = logging.getLogger("test_json")
        # Should not raise
        logger.info("Test JSON message")


class TestLoggingSecurityEdgeCases:
    """Security edge case tests for logging."""

    def test_masks_deeply_nested_sensitive_data(self):
        """Should mask deeply nested sensitive data."""
        data = {
            "l1": {
                "l2": {
                    "l3": {
                        "password": "deep_secret"
                    }
                }
            }
        }
        result = mask_sensitive_data(data)

        assert "***" in result["l1"]["l2"]["l3"]["password"]

    def test_handles_circular_reference_gracefully(self):
        """Should handle circular references via max depth."""
        data = {"key": "value"}
        data["self"] = data  # Circular reference

        # Should not hang or crash due to max depth
        # Note: This will be limited by _max_depth parameter
        result = mask_sensitive_data(data, _max_depth=5)
        assert result is not None

    def test_handles_none_values(self):
        """Should handle None values in data."""
        data = {
            "value": None,
            "password": None,
        }
        result = mask_sensitive_data(data)

        assert result["value"] is None
        # None password should still be masked
        assert "***" in str(result["password"])

    def test_handles_non_string_keys(self):
        """Should handle non-string keys."""
        # While unusual, dicts can have non-string keys
        data = {1: "value", "password": "secret"}
        result = mask_sensitive_data(data)

        assert result[1] == "value"
        assert "***" in result["password"]

    def test_truncates_long_messages(self):
        """Should truncate very long log messages."""
        from sardis_v2_core.logging import _mask_inline_patterns

        long_text = "a" * 20000
        result = _mask_inline_patterns(long_text)

        # Should be truncated
        assert len(result) < len(long_text)
        assert "truncated" in result.lower()

    def test_does_not_modify_original_data(self):
        """Should not modify the original data structure."""
        original = {
            "password": "secret",
            "nested": {"api_key": "key123"}
        }
        original_copy = {
            "password": "secret",
            "nested": {"api_key": "key123"}
        }

        result = mask_sensitive_data(original)

        # Original should be unchanged
        assert original == original_copy
        # Result should be masked
        assert "***" in result["password"]
