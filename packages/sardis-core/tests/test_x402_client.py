"""Tests for x402 client — agent pays x402 APIs."""
from __future__ import annotations

import base64
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_v2_core.x402_client import (
    X402AcceptOption,
    X402Client,
    X402CostPreview,
    X402Negotiator,
)
from sardis_v2_core.x402_policy_guard import X402PolicyDenied, X402PolicyGuard


def _mock_policy_guard(*, allowed: bool = True, reason: str = "") -> X402PolicyGuard:
    guard = MagicMock(spec=X402PolicyGuard)
    guard.evaluate = AsyncMock(return_value=(allowed, reason))
    guard.submit = AsyncMock()
    return guard


class TestX402Negotiator:
    def test_selects_preferred_chain(self):
        negotiator = X402Negotiator()
        accepts = [
            X402AcceptOption(network="polygon", amount="1000000"),
            X402AcceptOption(network="base", amount="1000000"),
        ]
        result = negotiator.select_best(
            accepts,
            preferred_chains=["base"],
        )
        assert result is not None
        assert result.network == "base"

    def test_selects_highest_balance(self):
        negotiator = X402Negotiator()
        accepts = [
            X402AcceptOption(network="polygon", currency="USDC", amount="1000000"),
            X402AcceptOption(network="base", currency="USDC", amount="1000000"),
        ]
        balances = {
            "polygon:USDC": Decimal("1000"),
            "base:USDC": Decimal("50"),
        }
        result = negotiator.select_best(accepts, available_balances=balances)
        assert result is not None
        assert result.network == "polygon"

    def test_empty_accepts(self):
        negotiator = X402Negotiator()
        result = negotiator.select_best([])
        assert result is None


class TestX402Client:
    @pytest.mark.asyncio
    async def test_non_402_passed_through(self):
        """Non-402 responses pass through without payment."""
        guard = _mock_policy_guard()
        client = X402Client(policy_guard=guard)

        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = '{"data": "ok"}'

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_http

            result = await client.request(
                "GET", "https://api.example.com/data",
                agent_id="agent_1", org_id="org_1", wallet_id="wal_1",
            )

        assert result["status_code"] == 200
        assert result["payment"] is None
        guard.evaluate.assert_not_called()

    @pytest.mark.asyncio
    async def test_policy_rejection_prevents_payment(self):
        """Policy guard rejection raises X402PolicyDenied."""
        guard = _mock_policy_guard(allowed=False, reason="daily_limit_exceeded")
        client = X402Client(policy_guard=guard)

        from sardis_protocol.x402 import X402Challenge, serialize_challenge_header

        challenge = X402Challenge(
            payment_id="x402_test",
            resource_uri="https://api.example.com/data",
            amount="1000000",
            currency="USDC",
            payee_address="0x" + "a" * 40,
            network="base",
            token_address="0x" + "b" * 40,
            expires_at=9999999999,
            nonce="test_nonce",
        )
        challenge_header = serialize_challenge_header(challenge)

        mock_402 = MagicMock()
        mock_402.status_code = 402
        mock_402.headers = {"PaymentRequired": challenge_header}
        mock_402.text = '{"error": "payment_required"}'

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.request = AsyncMock(return_value=mock_402)
            mock_client_cls.return_value = mock_http

            with pytest.raises(X402PolicyDenied, match="daily_limit_exceeded"):
                await client.request(
                    "GET", "https://api.example.com/data",
                    agent_id="agent_1", org_id="org_1", wallet_id="wal_1",
                )

    @pytest.mark.asyncio
    async def test_max_cost_respected(self):
        """Amount exceeding max_cost raises X402PolicyDenied."""
        guard = _mock_policy_guard()
        client = X402Client(policy_guard=guard, max_cost="0.50")  # Max $0.50

        from sardis_protocol.x402 import X402Challenge, serialize_challenge_header

        challenge = X402Challenge(
            payment_id="x402_test",
            resource_uri="https://api.example.com/data",
            amount="1000000",  # $1.00 USDC
            currency="USDC",
            payee_address="0x" + "a" * 40,
            network="base",
            token_address="0x" + "b" * 40,
            expires_at=9999999999,
            nonce="test_nonce",
        )
        challenge_header = serialize_challenge_header(challenge)

        mock_402 = MagicMock()
        mock_402.status_code = 402
        mock_402.headers = {"PaymentRequired": challenge_header}
        mock_402.text = '{"error": "payment_required"}'

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.request = AsyncMock(return_value=mock_402)
            mock_client_cls.return_value = mock_http

            with pytest.raises(X402PolicyDenied, match="exceeds max cost"):
                await client.request(
                    "GET", "https://api.example.com/data",
                    agent_id="agent_1", org_id="org_1", wallet_id="wal_1",
                )

    @pytest.mark.asyncio
    async def test_dry_run_no_execution(self):
        """Dry run returns preview without executing payment."""
        guard = _mock_policy_guard()
        client = X402Client(policy_guard=guard)

        from sardis_protocol.x402 import X402Challenge, serialize_challenge_header

        challenge = X402Challenge(
            payment_id="x402_test",
            resource_uri="https://api.example.com/data",
            amount="1000000",
            currency="USDC",
            payee_address="0x" + "a" * 40,
            network="base",
            token_address="0x" + "b" * 40,
            expires_at=9999999999,
            nonce="test_nonce",
        )
        challenge_header = serialize_challenge_header(challenge)

        mock_402 = MagicMock()
        mock_402.status_code = 402
        mock_402.headers = {"PaymentRequired": challenge_header}
        mock_402.text = '{"error": "payment_required"}'

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_http.request = AsyncMock(return_value=mock_402)
            mock_client_cls.return_value = mock_http

            result = await client.request(
                "GET", "https://api.example.com/data",
                agent_id="agent_1", org_id="org_1", wallet_id="wal_1",
                dry_run=True,
            )

        assert result["payment"]["dry_run"] is True
        assert result["payment"]["policy_would_allow"] is True
        assert result["status_code"] == 402
