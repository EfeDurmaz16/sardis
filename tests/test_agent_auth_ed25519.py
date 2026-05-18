"""Tests for delegated Agent Auth JWT verification.

Sardis no longer owns an in-memory Ed25519 agent registry in the API process.
Cryptographic verification is delegated to the better-auth agent-auth service;
the API route keeps fail-closed behavior around that verification boundary.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import sardis_server.routes.identity.agent_auth as agent_auth
from sardis_server.routes.identity.agent_auth import _verify_agent_jwt


def _make_request_with_jwt(token: str | None) -> MagicMock:
    request = MagicMock()
    request.headers = {"x-agent-jwt": token} if token is not None else {}
    return request


class _MockVerifyClient:
    def __init__(self, response: httpx.Response | Exception):
        self.response = response
        self.post = AsyncMock(side_effect=response if isinstance(response, Exception) else None)
        if not isinstance(response, Exception):
            self.post.return_value = response


@pytest.fixture(autouse=True)
def _reset_http_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SARDIS_AGENT_AUTH_MODE", "proxy")
    monkeypatch.setattr(agent_auth, "_http_client", None)


@pytest.mark.asyncio
async def test_missing_jwt_header_returns_none() -> None:
    result = await _verify_agent_jwt(_make_request_with_jwt(None))

    assert result is None


@pytest.mark.asyncio
async def test_empty_jwt_header_returns_none() -> None:
    result = await _verify_agent_jwt(_make_request_with_jwt(""))

    assert result is None


@pytest.mark.asyncio
async def test_valid_better_auth_payload_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _MockVerifyClient(httpx.Response(200, json={"payload": {"sub": "agent_auth_test", "capability": "payment"}}))
    monkeypatch.setattr(agent_auth, "_get_http_client", lambda: client)

    result = await _verify_agent_jwt(_make_request_with_jwt("signed.jwt.token"))

    assert result == {"sub": "agent_auth_test", "capability": "payment"}
    client.post.assert_awaited_once_with(
        "/api/auth/agent/verify-token",
        headers={"X-Agent-JWT": "signed.jwt.token", "Accept": "application/json"},
    )


@pytest.mark.asyncio
async def test_valid_better_auth_top_level_response_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _MockVerifyClient(httpx.Response(200, json={"sub": "agent_auth_test"}))
    monkeypatch.setattr(agent_auth, "_get_http_client", lambda: client)

    result = await _verify_agent_jwt(_make_request_with_jwt("signed.jwt.token"))

    assert result == {"sub": "agent_auth_test"}


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 500])
async def test_better_auth_rejection_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    client = _MockVerifyClient(httpx.Response(status_code, json={"error": "invalid token"}))
    monkeypatch.setattr(agent_auth, "_get_http_client", lambda: client)

    result = await _verify_agent_jwt(_make_request_with_jwt("bad.jwt.token"))

    assert result is None


@pytest.mark.asyncio
async def test_better_auth_network_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "https://app.sardis.sh/api/auth/agent/verify-token")
    client = _MockVerifyClient(httpx.ConnectError("unavailable", request=request))
    monkeypatch.setattr(agent_auth, "_get_http_client", lambda: client)

    result = await _verify_agent_jwt(_make_request_with_jwt("signed.jwt.token"))

    assert result is None
