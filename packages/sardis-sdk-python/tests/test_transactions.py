"""Tests for TransactionsResource."""
import pytest
from decimal import Decimal


MOCK_CHAIN_INFO = {
    "name": "Base Sepolia",
    "chain_id": 84532,
    "native_token": "ETH",
    "block_time": 2,
    "explorer": "https://sepolia.basescan.org",
}

MOCK_GAS_ESTIMATE = {
    "gas_limit": 65000,
    "gas_price_gwei": "0.001",
    "max_fee_gwei": "0.002",
    "max_priority_fee_gwei": "0.001",
    "estimated_cost_wei": 65000000,
    "estimated_cost_usd": "0.0001",
}

MOCK_TX_STATUS = {
    "tx_hash": "0xabc123",
    "chain": "base_sepolia",
    "status": "confirmed",
    "block_number": 12345,
    "confirmations": 10,
}


class TestListChains:
    """Tests for listing supported chains."""

    async def test_list_chains(self, client, httpx_mock):
        """Should list supported chains."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/chains",
            method="GET",
            json={"chains": [MOCK_CHAIN_INFO]},
        )

        chains = await client.transactions.list_chains()
        assert len(chains) == 1
        assert chains[0].name == "Base Sepolia"
        assert chains[0].chain_id == 84532

    async def test_list_empty_chains(self, client, httpx_mock):
        """Should handle empty chain list."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/chains",
            method="GET",
            json={"chains": []},
        )

        chains = await client.transactions.list_chains()
        assert len(chains) == 0


class TestEstimateGas:
    """Tests for gas estimation."""

    async def test_estimate_gas(self, client, httpx_mock):
        """Should estimate gas for a transaction."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/estimate-gas",
            method="POST",
            json=MOCK_GAS_ESTIMATE,
        )

        estimate = await client.transactions.estimate_gas(
            chain="base_sepolia",
            to_address="0x123456789",
            amount=Decimal("100.00"),
        )

        assert estimate.gas_limit == 65000
        assert estimate.gas_price_gwei == Decimal("0.001")
        assert estimate.estimated_cost_usd == Decimal("0.0001")

    async def test_estimate_gas_with_token(self, client, httpx_mock):
        """Should estimate gas with specific token."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/estimate-gas",
            method="POST",
            json=MOCK_GAS_ESTIMATE,
        )

        estimate = await client.transactions.estimate_gas(
            chain="base",
            to_address="0x987654321",
            amount=Decimal("50.00"),
            token="USDT",
        )

        assert estimate.gas_limit == 65000


class TestGetStatus:
    """Tests for transaction status."""

    async def test_get_confirmed_status(self, client, httpx_mock):
        """Should get confirmed transaction status."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/status/0xabc123?chain=base_sepolia",
            method="GET",
            json=MOCK_TX_STATUS,
        )

        status = await client.transactions.get_status("0xabc123", "base_sepolia")
        assert status.status == "confirmed"
        assert status.confirmations == 10
        assert status.block_number == 12345

    async def test_get_pending_status(self, client, httpx_mock):
        """Should get pending transaction status."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/status/0xdef456?chain=base",
            method="GET",
            json={
                "tx_hash": "0xdef456",
                "chain": "base",
                "status": "pending",
                "block_number": None,
                "confirmations": 0,
            },
        )

        status = await client.transactions.get_status("0xdef456", "base")
        assert status.status == "pending"
        assert status.confirmations == 0
        assert status.block_number is None

    async def test_get_failed_status(self, client, httpx_mock):
        """Should get failed transaction status."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/status/0xfailed?chain=base",
            method="GET",
            json={
                "tx_hash": "0xfailed",
                "chain": "base",
                "status": "failed",
                "block_number": 12340,
                "confirmations": 5,
            },
        )

        status = await client.transactions.get_status("0xfailed", "base")
        assert status.status == "failed"


class TestListTokens:
    """Tests for listing supported tokens."""

    async def test_list_tokens(self, client, httpx_mock):
        """Should list tokens for a chain."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/tokens/base",
            method="GET",
            json={
                "tokens": [
                    {"symbol": "USDC", "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
                    {"symbol": "USDT", "address": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"},
                ],
            },
        )

        tokens = await client.transactions.list_tokens("base")
        assert len(tokens) == 2
        assert tokens[0]["symbol"] == "USDC"

    async def test_list_empty_tokens(self, client, httpx_mock):
        """Should handle chain with no tokens."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/transactions/tokens/unknown",
            method="GET",
            json={"tokens": []},
        )

        tokens = await client.transactions.list_tokens("unknown")
        assert len(tokens) == 0
