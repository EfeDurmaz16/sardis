"""Integration tests for on-ramp flow."""
from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sardis_ramp.ramp import SardisFiatRamp, KYCRequired


class MockHTTPResponse:
    """Mock HTTP response."""

    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self):
        self.requests = []

    async def request(self, method, url, **kwargs):
        self.requests.append({
            "method": method,
            "url": url,
            "kwargs": kwargs,
        })

        # Mock wallet response
        if "/wallets/" in url and method == "GET":
            wallet_id = url.split("/wallets/")[1]
            return MockHTTPResponse({
                "wallet_id": wallet_id,
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                "chain": "base",
                "agent_id": "agent_123",
            })

        # Mock KYC status response
        if "/agents/" in url and "/kyc" in url and method == "GET":
            return MockHTTPResponse({
                "status": "approved",
                "inquiry_id": "inq_123",
                "inquiry_url": "https://withpersona.com/verify/inq_123",
            })

        # Mock Bridge transfer response
        if "/transfers" in url and method == "POST":
            return MockHTTPResponse({
                "id": "transfer_123",
                "amount": "100.00",
                "source_deposit_instructions": {
                    "payment_rail": "ach",
                    "account_number": "1234567890",
                    "routing_number": "021000021",
                    "bank_name": "Test Bank",
                    "account_holder": "Sardis Funding",
                    "reference": "REF123456",
                },
                "hosted_url": "https://bridge.xyz/pay/transfer_123",
                "estimated_completion_at": "2026-02-05T12:00:00Z",
                "fee": {
                    "amount": "2.50",
                    "percent": "2.5",
                },
            })

        return MockHTTPResponse({})

    async def aclose(self):
        pass


@pytest.mark.asyncio
class TestOnRampFlow:
    """Test on-ramp integration flow."""

    async def test_fund_wallet_bank_below_kyc_threshold(self):
        """Test funding wallet via bank ACH below KYC threshold."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
            kyc_threshold_usd=1000.00,
        )
        ramp._http = MockHTTPClient()

        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=500.00,  # Below threshold
            method="bank",
        )

        assert result.type == "fiat"
        assert result.ach_instructions is not None
        assert result.ach_instructions.account_number == "1234567890"
        assert result.ach_instructions.routing_number == "021000021"
        assert result.ach_instructions.bank_name == "Test Bank"
        assert result.transfer_id == "transfer_123"
        assert result.payment_link == "https://bridge.xyz/pay/transfer_123"

    async def test_fund_wallet_bank_above_kyc_threshold_verified(self):
        """Test funding wallet above KYC threshold with verified KYC."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
            kyc_threshold_usd=1000.00,
        )
        ramp._http = MockHTTPClient()

        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=5000.00,  # Above threshold
            method="bank",
        )

        # Should succeed with verified KYC
        assert result.type == "fiat"
        assert result.ach_instructions is not None
        assert result.transfer_id == "transfer_123"

        # Verify KYC check was called
        kyc_request = [r for r in ramp._http.requests if "/kyc" in r["url"]]
        assert len(kyc_request) == 1

    async def test_fund_wallet_above_kyc_threshold_not_verified(self):
        """Test funding wallet above KYC threshold without verification."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="production",  # Production mode
            kyc_threshold_usd=1000.00,
        )

        # Mock HTTP client with KYC not verified
        client = MockHTTPClient()
        original_request = client.request

        async def mock_request_kyc_not_verified(method, url, **kwargs):
            if "/kyc" in url:
                return MockHTTPResponse({
                    "status": "not_started",
                    "inquiry_url": "https://withpersona.com/verify/new",
                })
            return await original_request(method, url, **kwargs)

        client.request = mock_request_kyc_not_verified
        ramp._http = client

        with pytest.raises(KYCRequired) as exc_info:
            await ramp.fund_wallet(
                wallet_id="wallet_123",
                amount_usd=5000.00,  # Above threshold
                method="bank",
            )

        assert "KYC verification required" in str(exc_info.value)
        assert "$1000" in str(exc_info.value)

    async def test_fund_wallet_crypto_direct(self):
        """Test funding wallet via direct crypto deposit."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
        )
        ramp._http = MockHTTPClient()

        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=100.00,
            method="crypto",
        )

        # Should return deposit address directly
        assert result.type == "crypto"
        assert result.deposit_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        assert result.chain == "base"
        assert result.token == "USDC"

        # Should not call Bridge API for crypto deposits
        bridge_requests = [r for r in ramp._http.requests if "bridge" in r["url"]]
        assert len(bridge_requests) == 0

    async def test_fund_wallet_card(self):
        """Test funding wallet via credit/debit card."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
        )
        ramp._http = MockHTTPClient()

        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=250.00,
            method="card",
        )

        assert result.type == "fiat"
        assert result.payment_link is not None
        assert result.transfer_id == "transfer_123"

        # Verify Bridge transfer was called with card payment rail
        transfer_requests = [r for r in ramp._http.requests if "/transfers" in r["url"]]
        assert len(transfer_requests) == 1
        transfer_payload = transfer_requests[0]["kwargs"]["json"]
        assert transfer_payload["source"]["payment_rail"] == "card"

    async def test_kyc_check_no_agent(self):
        """Test KYC check when wallet has no associated agent."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="production",
            kyc_threshold_usd=1000.00,
        )

        client = MockHTTPClient()
        original_request = client.request

        async def mock_request_no_agent(method, url, **kwargs):
            if "/wallets/" in url and method == "GET":
                return MockHTTPResponse({
                    "wallet_id": "wallet_123",
                    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                    "chain": "base",
                    "agent_id": None,  # No agent
                })
            return await original_request(method, url, **kwargs)

        client.request = mock_request_no_agent
        ramp._http = client

        with pytest.raises(KYCRequired):
            await ramp.fund_wallet(
                wallet_id="wallet_123",
                amount_usd=5000.00,
                method="bank",
            )

    async def test_kyc_check_sandbox_bypass(self):
        """Test KYC check bypasses in sandbox mode on error."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
            kyc_threshold_usd=1000.00,
        )

        client = MockHTTPClient()
        original_request = client.request

        async def mock_request_kyc_error(method, url, **kwargs):
            if "/kyc" in url:
                raise Exception("KYC service unavailable")
            return await original_request(method, url, **kwargs)

        client.request = mock_request_kyc_error
        ramp._http = client

        # Should succeed in sandbox mode even if KYC check fails
        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=5000.00,
            method="bank",
        )

        assert result.transfer_id == "transfer_123"

    async def test_kyc_check_production_fail_closed(self):
        """Test KYC check fails closed in production on error."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="production",
            kyc_threshold_usd=1000.00,
        )

        client = MockHTTPClient()
        original_request = client.request

        async def mock_request_kyc_error(method, url, **kwargs):
            if "/kyc" in url:
                raise Exception("KYC service unavailable")
            return await original_request(method, url, **kwargs)

        client.request = mock_request_kyc_error
        ramp._http = client

        # Should fail in production mode if KYC check fails
        with pytest.raises(KYCRequired):
            await ramp.fund_wallet(
                wallet_id="wallet_123",
                amount_usd=5000.00,
                method="bank",
            )

    async def test_custom_kyc_threshold(self):
        """Test custom KYC threshold configuration."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
            kyc_threshold_usd=5000.00,  # Custom threshold
        )
        ramp._http = MockHTTPClient()

        # Below custom threshold - no KYC check
        result = await ramp.fund_wallet(
            wallet_id="wallet_123",
            amount_usd=4999.00,
            method="bank",
        )

        assert result.transfer_id == "transfer_123"

        # Verify no KYC check was made
        kyc_requests = [r for r in ramp._http.requests if "/kyc" in r["url"]]
        assert len(kyc_requests) == 0

    async def test_get_funding_status(self):
        """Test getting status of funding transfer."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
        )

        client = MockHTTPClient()
        original_request = client.request

        async def mock_request_transfer_status(method, url, **kwargs):
            if "/transfers/transfer_123" in url:
                return MockHTTPResponse({
                    "id": "transfer_123",
                    "status": "completed",
                    "amount": "100.00",
                })
            return await original_request(method, url, **kwargs)

        client.request = mock_request_transfer_status
        ramp._http = client

        status = await ramp.get_funding_status("transfer_123")

        assert status["id"] == "transfer_123"
        assert status["status"] == "completed"
        assert status["amount"] == "100.00"

    async def test_chain_conversion(self):
        """Test chain name conversion for Bridge API."""
        ramp = SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
        )

        assert ramp._chain_to_bridge("base") == "base"
        assert ramp._chain_to_bridge("polygon") == "polygon"
        assert ramp._chain_to_bridge("ethereum") == "ethereum"
        assert ramp._chain_to_bridge("arbitrum") == "arbitrum"
        assert ramp._chain_to_bridge("optimism") == "optimism"
        assert ramp._chain_to_bridge("BASE") == "base"

    async def test_context_manager(self):
        """Test using ramp as context manager."""
        async with SardisFiatRamp(
            sardis_api_key="sk_test_123",
            bridge_api_key="bridge_test_123",
            environment="sandbox",
        ) as ramp:
            ramp._http = MockHTTPClient()

            result = await ramp.fund_wallet(
                wallet_id="wallet_123",
                amount_usd=100.00,
                method="crypto",
            )

            assert result.type == "crypto"

        # HTTP client should be closed after context exit
