"""Integration tests for Circle Programmable Wallets.

Tests the full wallet lifecycle: create → fund → sign → pay,
Circle signer, Turnkey fallback, and multi-chain support.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_chain.circle_signer import CircleWalletSigner
from sardis_chain.executor import MPCSignerPort
from sardis_wallet.circle_client import (
    CIRCLE_BLOCKCHAIN_IDS,
    CircleAPIError,
    CircleTransaction,
    CircleWalletClient,
)

# ── CircleWalletClient ───────────────────────────────────────────────────


class TestCircleWalletClient:
    @pytest.fixture
    def mock_client(self):
        return CircleWalletClient(
            api_key="test-api-key",
            entity_secret="test-entity-secret",
        )

    def test_blockchain_id_mapping(self):
        assert CIRCLE_BLOCKCHAIN_IDS["base"] == "BASE"
        assert CIRCLE_BLOCKCHAIN_IDS["base_sepolia"] == "BASE-SEPOLIA"
        assert CIRCLE_BLOCKCHAIN_IDS["ethereum"] == "ETH"
        assert CIRCLE_BLOCKCHAIN_IDS["polygon"] == "MATIC"
        assert CIRCLE_BLOCKCHAIN_IDS["arbitrum"] == "ARB"

    @pytest.mark.asyncio
    async def test_create_wallet_set(self, mock_client):
        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"walletSet": {"id": "ws_123"}}
            ws_id = await mock_client.create_wallet_set("test-set")
            assert ws_id == "ws_123"
            mock_req.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_wallet(self, mock_client):
        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "wallets": [{
                    "id": "cw_456",
                    "address": "0x1234567890abcdef1234567890abcdef12345678",
                    "blockchain": "BASE",
                    "accountType": "SCA",
                    "state": "LIVE",
                    "createDate": "2026-03-01T00:00:00Z",
                }]
            }
            wallets = await mock_client.create_wallet(
                wallet_set_id="ws_123",
                blockchains=["base"],
            )
            assert len(wallets) == 1
            assert wallets[0].wallet_id == "cw_456"
            assert wallets[0].address.startswith("0x")
            assert wallets[0].account_type == "SCA"

    @pytest.mark.asyncio
    async def test_create_wallet_invalid_chain(self, mock_client):
        with pytest.raises(ValueError, match="not supported by Circle"):
            await mock_client.create_wallet(
                wallet_set_id="ws_123",
                blockchains=["invalid_chain"],
            )

    @pytest.mark.asyncio
    async def test_sign_transaction(self, mock_client):
        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "id": "tx_789",
                "state": "INITIATED",
            }
            tx = await mock_client.sign_transaction(
                wallet_id="cw_456",
                raw_transaction="0xabcdef",
            )
            assert tx.tx_id == "tx_789"
            assert tx.state == "INITIATED"

    @pytest.mark.asyncio
    async def test_get_balance(self, mock_client):
        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "tokenBalances": [
                    {"token": {"symbol": "USDC"}, "amount": "100.50"},
                    {"token": {"symbol": "ETH"}, "amount": "0.01"},
                ]
            }
            balances = await mock_client.get_balance("cw_456")
            assert len(balances) == 2

    @pytest.mark.asyncio
    async def test_get_transaction(self, mock_client):
        with patch.object(mock_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "transaction": {
                    "id": "tx_789",
                    "state": "CONFIRMED",
                    "txHash": "0xabc123",
                }
            }
            tx = await mock_client.get_transaction("tx_789")
            assert tx.state == "CONFIRMED"
            assert tx.tx_hash == "0xabc123"

    @pytest.mark.asyncio
    async def test_poll_transaction_success(self, mock_client):
        call_count = 0

        async def mock_get_tx(tx_id):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return CircleTransaction(tx_id=tx_id, state="PENDING")
            return CircleTransaction(tx_id=tx_id, state="CONFIRMED", tx_hash="0xfinal")

        with patch.object(mock_client, "get_transaction", side_effect=mock_get_tx):
            tx = await mock_client.poll_transaction("tx_789", interval=0.01, timeout=5)
            assert tx.state == "CONFIRMED"
            assert tx.tx_hash == "0xfinal"

    @pytest.mark.asyncio
    async def test_poll_transaction_failure(self, mock_client):
        async def mock_get_tx(tx_id):
            return CircleTransaction(
                tx_id=tx_id, state="FAILED", error_reason="Insufficient funds"
            )

        with patch.object(mock_client, "get_transaction", side_effect=mock_get_tx):
            with pytest.raises(CircleAPIError, match="FAILED"):
                await mock_client.poll_transaction("tx_789", interval=0.01)

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        import httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"message": "Unauthorized", "code": "UNAUTHORIZED"}

        with patch.object(
            mock_client._client, "request",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_resp),
        ):
            with pytest.raises(CircleAPIError, match="401"):
                await mock_client.create_wallet_set("test")


# ── CircleWalletSigner ───────────────────────────────────────────────────


class TestCircleWalletSigner:
    @pytest.fixture
    def mock_circle_client(self):
        client = AsyncMock(spec=CircleWalletClient)
        client.sign_transaction = AsyncMock(
            return_value=CircleTransaction(tx_id="tx_001", state="INITIATED")
        )
        client.poll_transaction = AsyncMock(
            return_value=CircleTransaction(
                tx_id="tx_001", state="CONFIRMED", tx_hash="0xhash123"
            )
        )
        return client

    @pytest.fixture
    def signer(self, mock_circle_client):
        return CircleWalletSigner(
            circle_client=mock_circle_client,
            wallet_id="cw_456",
            address="0x1234567890abcdef1234567890abcdef12345678",
        )

    def test_is_mpc_signer_port(self, signer):
        assert isinstance(signer, MPCSignerPort)

    @pytest.mark.asyncio
    async def test_sign_transaction(self, signer, mock_circle_client):
        tx = MagicMock()
        tx.data = b"\xab\xcd"
        tx.to_address = "0xrecipient"

        result = await signer.sign_transaction("sardis_w_123", tx)
        assert result == "0xhash123"
        mock_circle_client.sign_transaction.assert_called_once()
        mock_circle_client.poll_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_address(self, signer):
        addr = await signer.get_address("sardis_w_123", "base")
        assert addr == "0x1234567890abcdef1234567890abcdef12345678"

        # Same address on different chains (SCA)
        addr2 = await signer.get_address("sardis_w_123", "ethereum")
        assert addr == addr2

    @pytest.mark.asyncio
    async def test_sign_user_operation_hash(self, signer, mock_circle_client):
        result = await signer.sign_user_operation_hash(
            "sardis_w_123", "0xooo111"
        )
        assert result == "0xhash123"


# ── Wallet Manager Integration ───────────────────────────────────────────


class TestWalletManagerCircle:
    @pytest.mark.asyncio
    async def test_create_wallet_defaults_to_circle(self):
        """The default MPC provider in CreateWalletRequest should be circle."""
        from sardis_api.routers.wallets import CreateWalletRequest

        req = CreateWalletRequest(agent_id="agent_1")
        assert req.mpc_provider == "circle"

    def test_wallet_model_circle_fields(self):
        from sardis_v2_core.wallets import Wallet

        wallet = Wallet.new("agent_1", mpc_provider="circle")
        assert wallet.mpc_provider == "circle"
        assert wallet.circle_wallet_id is None

        wallet.circle_wallet_id = "cw_123"
        assert wallet.circle_wallet_id == "cw_123"

    def test_config_supports_circle_mpc(self):
        from sardis_v2_core.config import MPCProvider

        p = MPCProvider(name="circle")
        assert p.name == "circle"


# ── Turnkey Fallback ─────────────────────────────────────────────────────


class TestTurnkeyFallback:
    @pytest.mark.asyncio
    async def test_fallback_to_turnkey_on_circle_failure(self):
        """When Circle fails and Turnkey is available, wallet creation falls back."""
        from sardis_v2_core.config import SardisSettings
        from sardis_wallet.manager import EnhancedWalletManager

        settings = MagicMock(spec=SardisSettings)
        settings.circle_wallet_api_key = "test-key"
        settings.circle_entity_secret = "test-secret"
        settings.circle_wallet_set_id = "ws_test"
        settings.circle_account_type = "SCA"

        manager = MagicMock(spec=EnhancedWalletManager)
        manager._settings = settings
        manager._turnkey_client = MagicMock()

        # Simulate Circle failure then Turnkey success
        manager.create_circle_wallet = AsyncMock(
            side_effect=CircleAPIError("API down", status_code=500)
        )
        manager.create_turnkey_wallet = AsyncMock(
            return_value={"wallet_id": "tk_123", "addresses": [], "provider": "turnkey"}
        )

        # Call the unbound create_wallet method logic
        result = await EnhancedWalletManager.create_wallet(
            manager, "test-wallet", "agent_1", provider="circle"
        )
        assert result["provider"] == "turnkey"
        manager.create_turnkey_wallet.assert_called_once()
