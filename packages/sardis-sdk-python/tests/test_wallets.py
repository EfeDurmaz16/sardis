"""
Tests for WalletsResource
"""
import pytest
from sardis_sdk import SardisClient


class TestCreateWallet:
    """Tests for wallet creation."""

    async def test_create_wallet_successfully(self, client, httpx_mock, mock_responses):
        """Should create a new wallet."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets",
            method="POST",
            json=mock_responses["wallet"],
        )

        result = await client.wallets.create(
            agent_id="agent_001",
            mpc_provider="turnkey",
        )

        assert result.wallet_id == "wallet_test123"
        assert result.agent_id == "agent_001"


class TestGetWallet:
    """Tests for getting wallet by ID."""

    async def test_get_wallet_successfully(self, client, httpx_mock, mock_responses):
        """Should get wallet by ID."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_test123",
            method="GET",
            json=mock_responses["wallet"],
        )

        result = await client.wallets.get("wallet_test123")

        assert result.wallet_id == "wallet_test123"

    async def test_handle_wallet_not_found(self, client, httpx_mock):
        """Should handle wallet not found."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/nonexistent",
            method="GET",
            status_code=404,
            json={"error": "Wallet not found"},
        )

        with pytest.raises(Exception):
            await client.wallets.get("nonexistent")


class TestListWallets:
    """Tests for listing wallets."""

    async def test_list_all_wallets(self, client, httpx_mock, mock_responses):
        """Should list all wallets."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets?limit=100",
            method="GET",
            json=[mock_responses["wallet"], {**mock_responses["wallet"], "wallet_id": "wallet_2"}],
        )

        result = await client.wallets.list()

        assert len(result) == 2

    async def test_filter_by_agent_id(self, client, httpx_mock, mock_responses):
        """Should filter wallets by agent ID."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets?agent_id=agent_001&limit=100",
            method="GET",
            json=[mock_responses["wallet"]],
        )

        result = await client.wallets.list(agent_id="agent_001")

        assert len(result) == 1


class TestGetBalance:
    """Tests for getting wallet balance."""

    async def test_get_balance_successfully(self, client, httpx_mock, mock_responses):
        """Should get wallet balance."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_test123/balance?chain=base&token=USDC",
            method="GET",
            json=mock_responses["balance"],
        )

        result = await client.wallets.get_balance("wallet_test123")

        assert str(result.balance) == "1000.00"
        assert result.chain == "base"

    async def test_specify_chain_and_token(self, client, httpx_mock):
        """Should specify chain and token."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_test123/balance?chain=polygon&token=USDT",
            method="GET",
            json={
                "wallet_id": "wallet_test123",
                "chain": "polygon",
                "token": "USDT",
                "balance": "500.00",
                "balance_minor": 500000000,
                "address": "0xabcdef1234567890abcdef1234567890abcdef12",
            },
        )

        result = await client.wallets.get_balance(
            "wallet_test123",
            chain="polygon",
            token="USDT",
        )

        assert result.chain == "polygon"
        assert result.token == "USDT"


class TestGetAddresses:
    """Tests for getting wallet addresses."""

    async def test_get_addresses_successfully(self, client, httpx_mock):
        """Should get all wallet addresses."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_test123/addresses",
            method="GET",
            json={
                "base": "0x1234567890abcdef1234567890abcdef12345678",
                "polygon": "0xabcdef1234567890abcdef1234567890abcdef12",
            },
        )

        result = await client.wallets.get_addresses("wallet_test123")

        assert "base" in result
        assert "polygon" in result


class TestSetAddress:
    """Tests for setting wallet address."""

    async def test_set_address_successfully(self, client, httpx_mock, mock_responses):
        """Should set wallet address."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/wallets/wallet_test123/addresses",
            method="POST",
            json=mock_responses["wallet"],
        )

        result = await client.wallets.set_address(
            "wallet_test123",
            chain="arbitrum",
            address="0xnewaddress1234567890abcdef1234567890abcd",
        )

        assert result.wallet_id == "wallet_test123"
