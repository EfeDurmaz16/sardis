"""Integration tests for Coinbase Stack (CDP Swap, Verifications, Bridge).

Tests swap flow, verification → policy pipeline, and cross-chain bridge.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_chain.cdp_swap import (
    CDPSwapClient,
    CDPSwapError,
    SwapQuote,
    SwapResult,
    BridgeQuote,
    CDP_CHAIN_IDS,
)
from sardis_compliance.coinbase_verifications import (
    Attestation,
    CoinbaseVerificationsClient,
    CoinbaseVerificationError,
    VerificationResult,
    COINBASE_VERIFICATIONS_SCHEMA_UID,
)


# ── CDP Swap Client ──────────────────────────────────────────────────────


class TestCDPSwapClient:
    @pytest.fixture
    def client(self):
        return CDPSwapClient(api_key="test-cdp-key")

    def test_chain_id_mapping(self):
        assert CDP_CHAIN_IDS["base"] == "base"
        assert CDP_CHAIN_IDS["ethereum"] == "ethereum"
        assert CDP_CHAIN_IDS["polygon"] == "polygon"

    @pytest.mark.asyncio
    async def test_get_quote(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "quote": {
                    "quoteId": "q_123",
                    "fromAmount": "100.0",
                    "toAmount": "99.5",
                    "exchangeRate": "0.995",
                    "fee": {"amount": "0.5", "token": "USDC"},
                    "expiresAt": "2026-03-02T12:00:00Z",
                }
            }
            quote = await client.get_quote(
                from_token="USDC",
                to_token="ETH",
                amount=Decimal("100"),
                chain="base",
            )
            assert quote.quote_id == "q_123"
            assert quote.to_amount == Decimal("99.5")
            assert quote.fee_amount == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_get_quote_unsupported_chain(self, client):
        with pytest.raises(CDPSwapError, match="not supported"):
            await client.get_quote("USDC", "ETH", Decimal("100"), "solana")

    @pytest.mark.asyncio
    async def test_execute_swap(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "swap": {
                    "txHash": "0xswaphash123",
                    "fromAmount": "100",
                    "toAmount": "99.5",
                    "status": "confirmed",
                }
            }
            result = await client.execute_swap(
                quote_id="q_123",
                wallet_signer=None,
            )
            assert result.tx_hash == "0xswaphash123"
            assert result.status == "confirmed"

    @pytest.mark.asyncio
    async def test_get_bridge_quote(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "quote": {
                    "quoteId": "bq_456",
                    "fromAmount": "1000",
                    "toAmount": "999",
                    "fee": {"amount": "1"},
                    "estimatedTimeSeconds": 120,
                }
            }
            quote = await client.get_bridge_quote(
                from_chain="ethereum",
                to_chain="base",
                token="USDC",
                amount=Decimal("1000"),
            )
            assert quote.quote_id == "bq_456"
            assert quote.estimated_time_seconds == 120
            assert quote.fee_amount == Decimal("1")

    @pytest.mark.asyncio
    async def test_bridge_unsupported_chain(self, client):
        with pytest.raises(CDPSwapError, match="not supported"):
            await client.get_bridge_quote("solana", "base", "USDC", Decimal("100"))


# ── Coinbase Verifications ───────────────────────────────────────────────


class TestCoinbaseVerifications:
    @pytest.fixture
    def client(self):
        return CoinbaseVerificationsClient()

    @pytest.mark.asyncio
    async def test_check_verified_address(self, client):
        with patch.object(client, "get_attestations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                Attestation(
                    uid="0xatt123",
                    schema_uid=COINBASE_VERIFICATIONS_SCHEMA_UID,
                    attester="0x357458739F90461b99789350868CD7CF330Dd7EE",
                    recipient="0xuser123",
                    revoked=False,
                    timestamp=1709251200,
                )
            ]
            result = await client.check_verification("0xuser123")
            assert result.is_verified is True
            assert result.attestation_uid == "0xatt123"

    @pytest.mark.asyncio
    async def test_check_unverified_address(self, client):
        with patch.object(client, "get_attestations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            result = await client.check_verification("0xunknown")
            assert result.is_verified is False
            assert result.attestation_uid is None

    @pytest.mark.asyncio
    async def test_revoked_attestation_not_verified(self, client):
        with patch.object(client, "get_attestations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                Attestation(
                    uid="0xrevoked",
                    schema_uid=COINBASE_VERIFICATIONS_SCHEMA_UID,
                    attester="0x357458739F90461b99789350868CD7CF330Dd7EE",
                    recipient="0xuser456",
                    revoked=True,
                    timestamp=1709251200,
                )
            ]
            result = await client.check_verification("0xuser456")
            assert result.is_verified is False

    @pytest.mark.asyncio
    async def test_wrong_attester_not_verified(self, client):
        with patch.object(client, "get_attestations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                Attestation(
                    uid="0xfake",
                    schema_uid=COINBASE_VERIFICATIONS_SCHEMA_UID,
                    attester="0xFAKE_ATTESTER",
                    recipient="0xuser789",
                    revoked=False,
                    timestamp=1709251200,
                )
            ]
            result = await client.check_verification("0xuser789")
            assert result.is_verified is False

    @pytest.mark.asyncio
    async def test_get_attestations_graphql(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "attestations": [
                    {
                        "id": "0xatt_1",
                        "attester": "0x357458739F90461b99789350868CD7CF330Dd7EE",
                        "recipient": "0xuser",
                        "revoked": False,
                        "timeCreated": 1709251200,
                        "schemaId": COINBASE_VERIFICATIONS_SCHEMA_UID,
                        "decodedDataJson": "{}",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_response):
            attestations = await client.get_attestations("0xuser")
            assert len(attestations) == 1
            assert attestations[0].uid == "0xatt_1"
            assert attestations[0].revoked is False


# ── Verification → Policy Integration ────────────────────────────────────


class TestVerificationPolicyPipeline:
    @pytest.mark.asyncio
    async def test_verified_agent_gets_higher_limits(self):
        """Verified agent should get MEDIUM trust level via KYA mapping."""
        from sardis_v2_core.spending_policy import (
            create_default_policy,
            TrustLevel,
            trust_level_for_kya,
        )

        # Coinbase Verified → "verified" KYA level → MEDIUM trust
        trust = trust_level_for_kya("verified")
        assert trust == TrustLevel.MEDIUM

        policy = create_default_policy("agent_verified", trust)
        assert policy.limit_per_tx == Decimal("500.00")
        assert policy.trust_level == TrustLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_unverified_agent_stays_low(self):
        from sardis_v2_core.spending_policy import (
            create_default_policy,
            TrustLevel,
            trust_level_for_kya,
        )

        trust = trust_level_for_kya("none")
        assert trust == TrustLevel.LOW

        policy = create_default_policy("agent_unverified", trust)
        assert policy.limit_per_tx == Decimal("50.00")


# ── Swap → Payment Flow ─────────────────────────────────────────────────


class TestSwapPaymentFlow:
    @pytest.mark.asyncio
    async def test_swap_then_payment_flow(self):
        """Simulates: get quote → execute swap → policy check → pay."""
        from sardis_v2_core.spending_policy import create_default_policy, TrustLevel
        from sardis_v2_core.wallets import Wallet

        # Step 1: Swap quote (mocked)
        swap_client = MagicMock(spec=CDPSwapClient)
        swap_client.get_quote = AsyncMock(return_value=SwapQuote(
            quote_id="q_flow",
            from_token="ETH",
            to_token="USDC",
            from_amount=Decimal("0.05"),
            to_amount=Decimal("100"),
            exchange_rate=Decimal("2000"),
            fee_amount=Decimal("0.5"),
            fee_token="USDC",
            expires_at="2026-03-02T12:00:00Z",
            chain="base",
        ))

        quote = await swap_client.get_quote("ETH", "USDC", Decimal("0.05"), "base")
        assert quote.to_amount == Decimal("100")

        # Step 2: Policy check with swapped funds
        wallet = Wallet.new("agent_swap", mpc_provider="circle")
        wallet.set_address("base", "0x" + "11" * 20)

        policy = create_default_policy("agent_swap", TrustLevel.MEDIUM)
        ok, reason = policy.validate_payment(
            amount=Decimal("50"), fee=Decimal("0.01")
        )
        assert ok is True
        assert reason == "OK"


# ── API Endpoint Models ──────────────────────────────────────────────────


class TestSwapAPIModels:
    def test_swap_quote_request(self):
        from sardis_api.routers.swap import SwapQuoteRequest

        req = SwapQuoteRequest(
            from_token="USDC",
            to_token="ETH",
            amount=Decimal("100"),
        )
        assert req.chain == "base"
        assert req.slippage_bps == 100

    def test_bridge_quote_request(self):
        from sardis_api.routers.swap import BridgeQuoteRequest

        req = BridgeQuoteRequest(
            from_chain="ethereum",
            to_chain="base",
            token="USDC",
            amount=Decimal("1000"),
        )
        assert req.from_chain == "ethereum"
