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
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
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
    def test_idempotency_key_auto_generated_on_write(self) -> None:
        # Anthropic-style: writes get an auto-generated Idempotency-Key so a
        # transparent retry never double-executes the mutation.
        route = respx.post(f"{BASE_URL}/api/v2/mandates/execute").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        with _make_sync() as client:
            client.execute_payment({"id": "m1"})

        key = route.calls.last.request.headers.get("Idempotency-Key")
        assert key is not None
        assert key.startswith("sardis-retry-")

    @respx.mock
    def test_idempotency_key_not_set_on_get(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        with _make_sync() as client:
            client.health()

        assert "Idempotency-Key" not in route.calls.last.request.headers

    @respx.mock
    def test_idempotency_key_stable_across_retries(self) -> None:
        # The auto-generated key must be identical on the retried attempt.
        route = respx.post(f"{BASE_URL}/api/v2/mandates/execute").mock(
            side_effect=[
                httpx.Response(500, json={"detail": "boom"}),
                httpx.Response(200, json={"ok": True}),
            ]
        )
        with _make_sync() as client:
            client.execute_payment({"id": "m1"})

        assert route.call_count == 2
        first = route.calls[0].request.headers["Idempotency-Key"]
        second = route.calls[1].request.headers["Idempotency-Key"]
        assert first == second

    @respx.mock
    def test_caller_idempotency_key_preserved(self) -> None:
        route = respx.post(f"{BASE_URL}/api/v2/mandates/execute").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        with _make_sync() as client:
            ctx = RequestContext(idempotency_key="idem_caller_xyz")
            client._request(
                "POST",
                "/api/v2/mandates/execute",
                json={"mandate": {"id": "m1"}},
                context=ctx,
            )

        assert route.calls.last.request.headers["Idempotency-Key"] == "idem_caller_xyz"

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

    @respx.mock
    def test_400_maps_to_bad_request_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(400, json={"detail": "bad"})
        )
        with _make_sync() as client:
            with pytest.raises(BadRequestError) as exc:
                client.health()
        assert exc.value.status_code == 400

    @respx.mock
    def test_403_maps_to_permission_denied_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(403, json={"detail": "forbidden"})
        )
        with _make_sync() as client:
            # PermissionDeniedError subclasses AuthenticationError for
            # backwards compatibility with older except clauses.
            with pytest.raises(PermissionDeniedError):
                client.health()
            with pytest.raises(AuthenticationError):
                client.health()

    @respx.mock
    def test_409_maps_to_conflict_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(409, json={"detail": "exists"})
        )
        with _make_sync() as client:
            with pytest.raises(ConflictError):
                client.health()

    @respx.mock
    def test_422_maps_to_unprocessable_entity_error(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(
                422, json={"detail": [{"loc": ["body", "x"], "msg": "required"}]}
            )
        )
        with _make_sync() as client:
            # UnprocessableEntityError subclasses ValidationError.
            with pytest.raises(UnprocessableEntityError):
                client.health()
            with pytest.raises(ValidationError):
                client.health()

    @respx.mock
    def test_status_errors_are_api_status_errors(self) -> None:
        respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(404, json={"detail": "missing"})
        )
        with _make_sync() as client:
            with pytest.raises(APIStatusError):
                client.health()


class TestWithOptions:
    def test_with_options_returns_new_client(self) -> None:
        client = _make_sync()
        derived = client.with_options(max_retries=0, timeout=5.0)
        assert derived is not client
        assert isinstance(derived, Sardis)
        assert derived._retry.max_retries == 0
        # Original is unchanged.
        assert client._retry.max_retries == 3

    def test_with_options_merges_default_headers(self) -> None:
        client = Sardis(api_key=API_KEY, base_url=BASE_URL)
        derived = client.with_options(default_headers={"X-Tenant": "acme"})
        assert derived._default_headers["X-Tenant"] == "acme"
        assert "X-Tenant" not in client._default_headers

    @respx.mock
    def test_with_options_header_sent_on_request(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        base = Sardis(api_key=API_KEY, base_url=BASE_URL, retry=_no_wait_retry())
        with base.with_options(default_headers={"X-Tenant": "acme"}) as client:
            client.health()
        assert route.calls.last.request.headers["X-Tenant"] == "acme"

    def test_async_with_options_returns_async_client(self) -> None:
        client = _make_async()
        derived = client.with_options(max_retries=1)
        assert isinstance(derived, AsyncSardis)
        assert derived._retry.max_retries == 1


class TestMaxRetries:
    @respx.mock
    def test_max_retries_constructor_caps_attempts(self) -> None:
        route = respx.get(f"{BASE_URL}/health").mock(
            return_value=httpx.Response(500, json={"detail": "boom"})
        )
        # max_retries=0 -> exactly one attempt, no retry.
        client = Sardis(
            api_key=API_KEY,
            base_url=BASE_URL,
            max_retries=0,
            retry=_no_wait_retry(),
        )
        with client, pytest.raises(Exception):
            client.health()
        assert route.call_count == 1


class TestResourceCalls:
    @respx.mock
    def test_pay_execute_posts_to_pay_endpoint(self) -> None:
        route = respx.post(f"{BASE_URL}/api/v2/pay").mock(
            return_value=httpx.Response(
                200, json={"status": "executed", "tx_hash": "0xdead"}
            )
        )
        with _make_sync() as client:
            result = client.pay.execute(to="0xabc", amount="25.00", chain="base")

        assert result["tx_hash"] == "0xdead"
        sent = route.calls.last.request
        body = sent.content.decode()
        assert '"to":"0xabc"' in body.replace(" ", "")
        assert '"amount":"25.00"' in body.replace(" ", "")
        assert '"chain":"base"' in body.replace(" ", "")
        # Writes carry an auto idempotency key.
        assert sent.headers.get("Idempotency-Key", "").startswith("sardis-retry-")

    @respx.mock
    async def test_async_pay_execute(self) -> None:
        respx.post(f"{BASE_URL}/api/v2/pay").mock(
            return_value=httpx.Response(200, json={"status": "executed"})
        )
        async with _make_async() as client:
            result = await client.pay.execute(to="0xabc", amount="1.00")
        assert result["status"] == "executed"

    @respx.mock
    def test_wallets_list_parses_items(self) -> None:
        respx.get(f"{BASE_URL}/api/v2/wallets").mock(
            return_value=httpx.Response(
                200,
                json={
                    "wallets": [
                        {
                            "wallet_id": "w_1",
                            "agent_id": "a_1",
                            "created_at": "2026-01-01T00:00:00Z",
                            "updated_at": "2026-01-01T00:00:00Z",
                        },
                        {
                            "wallet_id": "w_2",
                            "agent_id": "a_1",
                            "created_at": "2026-01-01T00:00:00Z",
                            "updated_at": "2026-01-01T00:00:00Z",
                        },
                    ]
                },
            )
        )
        with _make_sync() as client:
            wallets = client.wallets.list(agent_id="a_1")
        assert [w.wallet_id for w in wallets] == ["w_1", "w_2"]
