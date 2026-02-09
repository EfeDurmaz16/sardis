"""
Pytest configuration and fixtures for Sardis SDK tests.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import pytest

from sardis_sdk import AsyncSardisClient
from sardis_sdk.client import RetryConfig


@dataclass
class _MockEntry:
    method: str
    url: str
    response: Optional[httpx.Response] = None
    exception: Optional[Exception] = None


class _LocalHTTPXMock:
    """Minimal pytest-httpx-compatible mock used when plugin is unavailable."""

    def __init__(self) -> None:
        self._entries: list[_MockEntry] = []

    def add_response(
        self,
        *,
        url: str,
        method: str = "GET",
        status_code: int = 200,
        json: Any = None,
        content: bytes | None = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        if content is None and json is not None:
            content = json_dumps_bytes(json)
            response_headers = {"content-type": "application/json"}
            if headers:
                response_headers.update(headers)
        else:
            response_headers = headers or {}

        request = httpx.Request(method.upper(), url)
        response = httpx.Response(
            status_code=status_code,
            headers=response_headers,
            content=content or b"",
            request=request,
        )
        self._entries.append(
            _MockEntry(method=method.upper(), url=url, response=response)
        )

    def add_exception(
        self,
        exception: Exception,
        *,
        url: str,
        method: str = "GET",
    ) -> None:
        self._entries.append(
            _MockEntry(method=method.upper(), url=url, exception=exception)
        )

    def _pop_match(self, method: str, url: str) -> _MockEntry:
        normalized_method = method.upper()
        normalized_url = _normalize_url(url)
        for idx, entry in enumerate(self._entries):
            if entry.method == normalized_method and _normalize_url(entry.url) == normalized_url:
                return self._entries.pop(idx)
        raise AssertionError(
            f"No mocked response for {normalized_method} {url}. "
            f"Available: {[f'{e.method} {e.url}' for e in self._entries]}"
        )


def json_dumps_bytes(payload: Any) -> bytes:
    return json.dumps(payload, default=str).encode("utf-8")


def _append_query_params(url: str, params: Optional[dict[str, Any]]) -> str:
    if not params:
        return url
    query = urlencode(params, doseq=True)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


def _normalize_url(url: str) -> str:
    parts = urlsplit(url)
    normalized_query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)), doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))


@pytest.fixture
def httpx_mock(monkeypatch):
    """Fallback `httpx_mock` fixture compatible with this test suite."""
    mock = _LocalHTTPXMock()

    async def _async_request(self, method, url, params=None, **kwargs):
        full_url = _append_query_params(str(url), params)
        match = mock._pop_match(method, full_url)
        if match.exception is not None:
            raise match.exception
        assert match.response is not None
        return match.response

    def _sync_request(self, method, url, params=None, **kwargs):
        full_url = _append_query_params(str(url), params)
        match = mock._pop_match(method, full_url)
        if match.exception is not None:
            raise match.exception
        assert match.response is not None
        return match.response

    monkeypatch.setattr(httpx.AsyncClient, "request", _async_request)
    monkeypatch.setattr(httpx.Client, "request", _sync_request)
    return mock


# Mock response data
MOCK_RESPONSES = {
    "health": {
        "status": "healthy",
        "version": "0.3.0",
    },
    "wallet": {
        "wallet_id": "wallet_test123",
        "agent_id": "agent_001",
        "mpc_provider": "turnkey",
        "addresses": {"base_sepolia": "0x1234567890abcdef1234567890abcdef12345678"},
        "currency": "USDC",
        "limit_per_tx": "1000.00",
        "limit_total": "10000.00",
        "is_active": True,
        "created_at": "2025-01-20T00:00:00Z",
        "updated_at": "2025-01-20T00:00:00Z",
    },
    "balance": {
        "wallet_id": "wallet_test123",
        "chain": "base",
        "token": "USDC",
        "balance": "1000.00",
        "balance_minor": 1000000000,
        "address": "0x1234567890abcdef1234567890abcdef12345678",
    },
    "mandate": {
        "mandate_id": "mandate_abc123",
        "status": "completed",
        "chain_tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "chain": "base_sepolia",
        "ledger_tx_id": "ltx_456",
        "audit_anchor": "anchor_789",
    },
    "hold": {
        "hold_id": "hold_xyz789",
        "wallet_id": "wallet_test123",
        "amount": "100.00",
        "token": "USDC",
        "status": "active",
        "expires_at": "2025-01-21T00:00:00Z",
        "created_at": "2025-01-20T00:00:00Z",
    },
    "webhook": {
        "id": "webhook_def456",
        "url": "https://example.com/webhook",
        "events": ["payment.completed", "payment.failed"],
        "active": True,
        "secret": "whsec_abc123",
        "created_at": "2025-01-20T00:00:00Z",
    },
    "policy": {
        "allowed": True,
        "policy_id": "policy_test",
        "reason": None,
    },
    "policy_violation": {
        "allowed": False,
        "policy_id": "policy_test",
        "reason": "Amount exceeds daily limit",
    },
}


@pytest.fixture
def api_key() -> str:
    """Test API key."""
    return "test-api-key"


@pytest.fixture
def base_url() -> str:
    """Test base URL."""
    return "https://api.sardis.sh"


@pytest.fixture
async def client(api_key: str, base_url: str) -> AsyncSardisClient:
    """Create a test client."""
    # Keep non-retry tests deterministic; retry behavior is tested explicitly.
    client = AsyncSardisClient(api_key=api_key, base_url=base_url, retry=RetryConfig(max_retries=0))
    yield client
    await client.close()


@pytest.fixture
def mock_responses() -> dict:
    """Return mock response data."""
    return MOCK_RESPONSES


@pytest.fixture
def mock_health_response(httpx_mock):
    """Mock health endpoint."""
    httpx_mock.add_response(
        url="https://api.sardis.sh/health",
        method="GET",
        json=MOCK_RESPONSES["health"],
    )
    return httpx_mock


@pytest.fixture
def mock_wallet_endpoints(httpx_mock):
    """Mock wallet endpoints."""
    # Create wallet
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/wallets",
        method="POST",
        json=MOCK_RESPONSES["wallet"],
    )
    # Get wallet
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/wallets/wallet_test123",
        method="GET",
        json=MOCK_RESPONSES["wallet"],
    )
    # Get balance
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/wallets/wallet_test123/balance",
        method="GET",
        json=MOCK_RESPONSES["balance"],
    )
    return httpx_mock


@pytest.fixture
def mock_payment_endpoints(httpx_mock):
    """Mock payment endpoints."""
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/mandates/execute",
        method="POST",
        json=MOCK_RESPONSES["mandate"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/ap2/payments/execute",
        method="POST",
        json=MOCK_RESPONSES["mandate"],
    )
    return httpx_mock


@pytest.fixture
def mock_hold_endpoints(httpx_mock):
    """Mock hold endpoints."""
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/holds",
        method="POST",
        json=MOCK_RESPONSES["hold"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/holds/hold_xyz789",
        method="GET",
        json=MOCK_RESPONSES["hold"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/holds/hold_xyz789/capture",
        method="POST",
        json={**MOCK_RESPONSES["hold"], "status": "captured"},
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/holds/hold_xyz789/void",
        method="POST",
        json={**MOCK_RESPONSES["hold"], "status": "voided"},
    )
    return httpx_mock


@pytest.fixture
def mock_webhook_endpoints(httpx_mock):
    """Mock webhook endpoints."""
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/webhooks",
        method="POST",
        json=MOCK_RESPONSES["webhook"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/webhooks",
        method="GET",
        json={"webhooks": [MOCK_RESPONSES["webhook"]]},
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/webhooks/webhook_def456",
        method="GET",
        json=MOCK_RESPONSES["webhook"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.sh/api/v2/webhooks/webhook_def456",
        method="DELETE",
        status_code=204,
    )
    return httpx_mock
