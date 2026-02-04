"""
Tests for SardisClient
"""
import pytest
from sardis_sdk import AsyncSardisClient, SardisClient
from sardis_sdk.client import RetryConfig
from sardis_sdk.models.errors import APIError, AuthenticationError, ConnectionError, RateLimitError, TimeoutError


class TestClientInitialization:
    """Tests for client initialization."""

    def test_create_client_with_api_key(self, api_key, base_url):
        """Should create client with required API key."""
        client = SardisClient(api_key=api_key, base_url=base_url)
        assert client is not None

    def test_raise_error_without_api_key(self, base_url):
        """Should raise ValueError when API key is missing."""
        with pytest.raises(ValueError, match="API key is required"):
            SardisClient(base_url=base_url)

    def test_initialize_all_resources(self, api_key, base_url):
        """Should initialize all resource classes."""
        client = SardisClient(api_key=api_key, base_url=base_url)

        assert hasattr(client, "payments")
        assert hasattr(client, "holds")
        assert hasattr(client, "webhooks")
        assert hasattr(client, "marketplace")
        assert hasattr(client, "transactions")
        assert hasattr(client, "ledger")
        assert hasattr(client, "wallets")
        assert hasattr(client, "agents")

    def test_accept_custom_timeout(self, api_key, base_url):
        """Should accept custom timeout."""
        client = SardisClient(api_key=api_key, base_url=base_url, timeout=60)
        assert client._timeout.connect == 60.0
        assert client._timeout.read == 60.0
        assert client._timeout.write == 60.0

    def test_accept_custom_max_retries(self, api_key, base_url):
        """Should accept custom max retries."""
        from sardis_sdk.client import RetryConfig
        retry_config = RetryConfig(max_retries=5)
        client = SardisClient(api_key=api_key, base_url=base_url, retry=retry_config)
        assert client._retry.max_retries == 5

    def test_strip_trailing_slash_from_base_url(self, api_key):
        """Should strip trailing slash from base URL."""
        client = SardisClient(api_key=api_key, base_url="https://api.example.com/")
        assert client._base_url == "https://api.example.com"


class TestHealthCheck:
    """Tests for health check."""

    async def test_return_health_status(self, client, mock_health_response):
        """Should return health status."""
        health = await client.health()

        assert health["status"] == "healthy"
        assert health["version"] == "0.3.0"


class TestContextManager:
    """Tests for async context manager."""

    async def test_use_as_context_manager(self, api_key, base_url, mock_health_response):
        """Should work as async context manager."""
        async with AsyncSardisClient(api_key=api_key, base_url=base_url) as client:
            health = await client.health()
            assert health["status"] == "healthy"

    async def test_close_client_on_exit(self, api_key, base_url, mock_health_response):
        """Should close client on context exit."""
        async with AsyncSardisClient(api_key=api_key, base_url=base_url) as client:
            await client.health()

        # Client should be closed after context exit
        assert client._client is None or client._client.is_closed


class TestErrorHandling:
    """Tests for error handling."""

    async def test_raise_authentication_error_on_401(self, client, httpx_mock):
        """Should raise AuthenticationError on 401."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/error/401",
            method="GET",
            status_code=401,
            json={"error": "Unauthorized"},
        )

        with pytest.raises(AuthenticationError):
            await client._request("GET", "/v1/error/401")

    async def test_raise_rate_limit_error_on_429(self, api_key, base_url, httpx_mock):
        """Should raise RateLimitError on 429."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/error/429",
            method="GET",
            status_code=429,
            headers={"Retry-After": "5"},
            json={"error": "Rate limit exceeded"},
        )

        # Use retry=RetryConfig(max_retries=1) to avoid retries for this test
        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=1))
        try:
            with pytest.raises(RateLimitError):
                await client._request("GET", "/v1/error/429")
        finally:
            await client.close()

    async def test_raise_api_error_on_500(self, api_key, base_url, httpx_mock):
        """Should raise APIError on 500."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/error/500",
            method="GET",
            status_code=500,
            json={"error": "Internal server error"},
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=1))
        try:
            with pytest.raises(APIError):
                await client._request("GET", "/v1/error/500")
        finally:
            await client.close()


class TestRetryLogic:
    """Tests for retry logic."""

    async def test_client_supports_retries(self, api_key, base_url):
        """Should support configurable retry count."""
        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=3))
        assert client._retry.max_retries == 3
        await client.close()

    async def test_retry_on_rate_limit_then_succeed(self, api_key, base_url, httpx_mock):
        """Should retry on 429 and succeed on next attempt."""
        # First request returns 429, second succeeds
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/retry-test",
            method="GET",
            status_code=429,
            headers={"Retry-After": "0"},
            json={"error": "Rate limit"},
        )
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/retry-test",
            method="GET",
            status_code=200,
            json={"success": True},
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=2))
        try:
            result = await client._request("GET", "/v1/retry-test")
            assert result["success"] is True
        finally:
            await client.close()

    async def test_retry_on_timeout_then_succeed(self, api_key, base_url, httpx_mock):
        """Should retry on timeout and succeed on next attempt."""
        import httpx

        # First request times out, second succeeds
        httpx_mock.add_exception(
            httpx.TimeoutException("Connection timed out"),
            url="https://api.sardis.network/v1/timeout-test",
            method="GET",
        )
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/timeout-test",
            method="GET",
            status_code=200,
            json={"success": True},
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=2))
        try:
            result = await client._request("GET", "/v1/timeout-test")
            assert result["success"] is True
        finally:
            await client.close()

    async def test_retry_on_connection_error_then_succeed(self, api_key, base_url, httpx_mock):
        """Should retry on connection error and succeed on next attempt."""
        import httpx

        # First request has connection error, second succeeds
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="https://api.sardis.network/v1/connect-test",
            method="GET",
        )
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/connect-test",
            method="GET",
            status_code=200,
            json={"success": True},
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=2))
        try:
            result = await client._request("GET", "/v1/connect-test")
            assert result["success"] is True
        finally:
            await client.close()

    async def test_raise_timeout_after_max_retries(self, api_key, base_url, httpx_mock):
        """Should raise timeout error after exhausting retries."""
        import httpx

        # All requests timeout
        httpx_mock.add_exception(
            httpx.TimeoutException("Connection timed out"),
            url="https://api.sardis.network/v1/timeout-fail",
            method="GET",
        )
        httpx_mock.add_exception(
            httpx.TimeoutException("Connection timed out"),
            url="https://api.sardis.network/v1/timeout-fail",
            method="GET",
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=2))
        try:
            with pytest.raises(TimeoutError):
                await client._request("GET", "/v1/timeout-fail")
        finally:
            await client.close()

    async def test_raise_connection_error_after_max_retries(self, api_key, base_url, httpx_mock):
        """Should raise connection error after exhausting retries."""
        import httpx

        # All requests fail with connection error
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="https://api.sardis.network/v1/connect-fail",
            method="GET",
        )
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="https://api.sardis.network/v1/connect-fail",
            method="GET",
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=2))
        try:
            with pytest.raises(ConnectionError):
                await client._request("GET", "/v1/connect-fail")
        finally:
            await client.close()


class TestRequestMethod:
    """Tests for request method."""

    async def test_make_get_request_with_params(self, client, httpx_mock):
        """Should make GET request with params."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/test?foo=bar",
            method="GET",
            json={"param": "bar"},
        )

        result = await client._request("GET", "/v1/test", params={"foo": "bar"})
        assert result["param"] == "bar"

    async def test_make_post_request_with_json(self, client, httpx_mock):
        """Should make POST request with JSON body."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/test",
            method="POST",
            json={"received": True},
        )

        result = await client._request("POST", "/v1/test", json={"foo": "bar"})
        assert result["received"] is True

    async def test_handle_error_with_list_body(self, api_key, base_url, httpx_mock):
        """Should handle error response with list body."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/validation-error",
            method="POST",
            status_code=422,
            json=[
                {"loc": ["body", "amount"], "msg": "field required"},
                {"loc": ["body", "merchant"], "msg": "field required"},
            ],
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=1))
        try:
            with pytest.raises(APIError) as exc_info:
                await client._request("POST", "/v1/validation-error")
            # The list should be wrapped in {"detail": list}
            assert exc_info.value.code == "VALIDATION_ERROR"
        finally:
            await client.close()

    async def test_handle_error_with_non_json_body(self, api_key, base_url, httpx_mock):
        """Should handle error response with non-JSON body."""
        httpx_mock.add_response(
            url="https://api.sardis.network/v1/html-error",
            method="GET",
            status_code=500,
            content=b"<html>Internal Server Error</html>",
        )

        client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=1))
        try:
            with pytest.raises(APIError) as exc_info:
                await client._request("GET", "/v1/html-error")
            # Should contain the text content
            assert "Internal Server Error" in str(exc_info.value.details) or "Internal Server Error" in exc_info.value.message
        finally:
            await client.close()


class TestLegacyMethods:
    """Tests for legacy methods."""

    async def test_execute_payment_legacy(self, client, httpx_mock):
        """Should execute payment using legacy method."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/mandates/execute",
            method="POST",
            json={
                "payment_id": "pay_123",
                "mandate_id": "mnd_456",
                "status": "completed",
                "amount_minor": "50000000",
                "token": "USDC",
                "chain": "base_sepolia",
                "tx_hash": "0xabc",
                "ledger_tx_id": "ltx_789",
                "audit_anchor": "anchor_123",
                "created_at": "2025-01-20T00:00:00Z",
            },
        )

        mandate = {"mandate_id": "mnd_456", "amount": "50"}
        result = await client.execute_payment(mandate)

        assert result["payment_id"] == "pay_123"
        assert result["status"] == "completed"

    async def test_execute_ap2_payment_legacy(self, client, httpx_mock):
        """Should execute AP2 payment using legacy method."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/ap2/payments/execute",
            method="POST",
            json={
                "mandate_id": "mnd_456",
                "status": "completed",
                "chain": "base_sepolia",
                "chain_tx_hash": "0xabc123",
                "ledger_tx_id": "ltx_789",
                "audit_anchor": "anchor_456",
            },
        )

        bundle = {
            "intent": {"id": "intent_123"},
            "cart": {"items": []},
            "payment": {"amount_minor": "100000000"},
        }
        result = await client.execute_ap2_payment(bundle)

        assert result["mandate_id"] == "mnd_456"
        assert result["status"] == "completed"
