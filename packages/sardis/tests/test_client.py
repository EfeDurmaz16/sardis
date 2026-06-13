"""Behavioral tests for the thin ``sardis`` HTTP client.

These exercise the transport contract that every resource depends on:

  * the API key is sent as the ``X-API-Key`` auth header;
  * retryable statuses (e.g. 500) are retried, then succeed;
  * an ``Idempotency-Key`` is forwarded on POST when a context supplies one;
  * HTTP error statuses map to the typed SDK exception hierarchy.

The engine lives in the private service repo; here we only test the public
client surface, mocking the network with ``respx`` so no real API is hit.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from sardis import AsyncSardis, Sardis
from sardis._client import RequestContext, RetryConfig
from sardis.models.errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

BASE_URL = "https://api.test.sardis.sh"
API_KEY = "test-thin-client-key"


def _no_wait_retry(max_retries: int = 3) -> RetryConfig:
    """Retry config with effectively zero backoff so tests stay fast."""
    return RetryConfig(
        max_retries=max_retries,
        initial_delay=0.0,
        max_delay=0.0,
        jitter=False,
    )


def _make_sync() -> Sardis:
    return Sardis(api_key=API_KEY, base_url=BASE_URL, retry=_no_wait_retry())


def _make_async() -> AsyncSardis:
    return AsyncSardis(api_key=API_KEY, base_url=BASE_URL, retry=_no_wait_retry())


class TestConstruction:
    def test_requires_api_key(self) -> None:
        with pytest.raises(ValueError, match="API key is required"):
            Sardis(api_key="")

    def test_base_url_trailing_slash_stripped(self) -> None:
        client = Sardis(api_key=API_KEY, base_url="https://api.test.sardis.sh/")
        assert client._base_url == "https://api.test.sardis.sh"


class TestAuthHeader:
    @respx.mock
    def test_sync_sends_api_key_header(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        with _make_sync() as client:
            assert client.health() == {"status": "ok"}

        assert route.called
        sent = route.calls.last.request
        assert sent.headers["X-API-Key"] == API_KEY
        assert sent.headers["Accept"] == "application/json"
        assert sent.headers["User-Agent"].startswith("sardis-sdk-python/")

    @respx.mock
    async def test_async_sends_api_key_header(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        async with _make_async() as client:
            assert await client.health() == {"status": "ok"}

        assert route.calls.last.request.headers["X-API-Key"] == API_KEY


class TestRetryBehavior:
    @respx.mock
    def test_retries_on_500_then_succeeds(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            side_effect=[
                httpx.Response(500, json={"detail": "boom"}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        with _make_sync() as client:
            assert client.health() == {"status": "ok"}

        assert route.call_count == 2

    @respx.mock
    def test_retries_on_transport_error_then_succeeds(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            side_effect=[
                httpx.ConnectError("refused"),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        with _make_sync() as client:
            assert client.health() == {"status": "ok"}

        assert route.call_count == 2

    @respx.mock
    def test_does_not_retry_on_400(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(400, json={"detail": "bad"})
        )
        with _make_sync() as client:
            with pytest.raises(Exception):
                client.health()

        # 400 is not in retry_on_status -> exactly one attempt.
        assert route.call_count == 1

    @respx.mock
    async def test_async_retries_on_503_then_succeeds(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            side_effect=[
                httpx.Response(503, json={"detail": "unavailable"}),
                httpx.Response(200, json={"status": "ok"}),
            ]
        )
        async with _make_async() as client:
            assert await client.health() == {"status": "ok"}

        assert route.call_count == 2


class TestIdempotencyKey:
    @respx.mock
    def test_idempotency_key_forwarded_on_post(self) -> None:
        route = respx.post(f"{BASE_URL}/api/v2/mandates/execute").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        with _make_sync() as client:
            ctx = RequestContext(idempotency_key="idem_abc_123")
            client._request(
                "POST",
                "/api/v2/mandates/execute",
                json={"mandate": {"id": "m1"}},
                context=ctx,
            )

        assert route.called
        assert route.calls.last.request.headers["Idempotency-Key"] == "idem_abc_123"

    @respx.mock
    def test_no_idempotency_header_without_context_key(self) -> None:
        route = respx.post(f"{BASE_URL}/api/v2/mandates/execute").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        with _make_sync() as client:
            client.execute_payment({"id": "m1"})

        assert "Idempotency-Key" not in route.calls.last.request.headers

    @respx.mock
    def test_request_id_header_always_sent(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        with _make_sync() as client:
            client.health()

        assert route.calls.last.request.headers.get("X-Request-ID")


class TestErrorMapping:
    @respx.mock
    def test_401_maps_to_authentication_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(401, json={"detail": "no auth"})
        )
        with _make_sync() as client:
            with pytest.raises(AuthenticationError):
                client.health()

    @respx.mock
    def test_403_maps_to_authentication_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(403, json={"detail": "forbidden"})
        )
        with _make_sync() as client:
            with pytest.raises(AuthenticationError):
                client.health()

    @respx.mock
    def test_404_maps_to_not_found_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(404, json={"detail": "missing"})
        )
        with _make_sync() as client:
            with pytest.raises(NotFoundError):
                client.health()

    @respx.mock
    def test_422_maps_to_validation_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(
                422, json={"detail": [{"loc": ["body", "x"], "msg": "required"}]}
            )
        )
        with _make_sync() as client:
            with pytest.raises(ValidationError):
                client.health()

    @respx.mock
    def test_429_maps_to_rate_limit_error_after_retries(self) -> None:
        # 429 is retryable; once retries are exhausted it surfaces as a typed error.
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(
                429, headers={"Retry-After": "0"}, json={"detail": "slow down"}
            )
        )
        with _make_sync() as client:
            with pytest.raises(RateLimitError) as exc_info:
                client.health()
        assert exc_info.value.retry_after == 0

    @respx.mock
    async def test_async_404_maps_to_not_found_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(404, json={"detail": "missing"})
        )
        async with _make_async() as client:
            with pytest.raises(NotFoundError):
                await client.health()
