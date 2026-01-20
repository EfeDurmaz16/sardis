"""Unit tests for chain executor and MPC signing."""
from __future__ import annotations

import time
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sardis_chain.executor import (
    CHAIN_CONFIGS,
    STABLECOIN_ADDRESSES,
    TransactionStatus,
    SubmittedTx,
    GasEstimate,
    TransactionRequest,
    SimulatedMPCSigner,
    ChainRPCClient,
    ChainExecutor,
    encode_erc20_transfer,
)
from sardis_v2_core.mandates import PaymentMandate, VCProof


def create_test_mandate(
    chain: str = "base_sepolia",
    token: str = "USDC",
    amount: int = 10000,  # $100.00
) -> PaymentMandate:
    """Create a test PaymentMandate."""
    proof = VCProof(
        verification_method="did:key:test#key-1",
        created="2025-12-08T00:00:00Z",
        proof_value="test_signature",
    )
    
    return PaymentMandate(
        mandate_id=f"test_mandate_{int(time.time())}",
        mandate_type="payment",
        issuer="test_agent",
        subject="test_wallet",
        expires_at=int(time.time()) + 300,
        nonce="test_nonce",
        proof=proof,
        domain="sardis.network",
        purpose="checkout",
        chain=chain,
        token=token,
        amount_minor=amount,
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test_audit_hash",
    )


class TestChainConfigs:
    """Tests for chain configuration constants."""

    def test_base_sepolia_config(self):
        """Test Base Sepolia configuration."""
        config = CHAIN_CONFIGS["base_sepolia"]
        
        assert config["chain_id"] == 84532
        assert "sepolia.base.org" in config["rpc_url"]
        assert config["native_token"] == "ETH"
        assert config["block_time"] == 2

    def test_base_mainnet_config(self):
        """Test Base mainnet configuration."""
        config = CHAIN_CONFIGS["base"]
        
        assert config["chain_id"] == 8453
        assert "mainnet.base.org" in config["rpc_url"]

    def test_polygon_config(self):
        """Test Polygon configuration."""
        config = CHAIN_CONFIGS["polygon"]
        
        assert config["chain_id"] == 137
        assert config["native_token"] == "MATIC"

    def test_ethereum_sepolia_config(self):
        """Test Ethereum Sepolia configuration."""
        config = CHAIN_CONFIGS["ethereum_sepolia"]
        
        assert config["chain_id"] == 11155111
        assert config["block_time"] == 12

    def test_arbitrum_sepolia_config(self):
        """Test Arbitrum Sepolia configuration."""
        config = CHAIN_CONFIGS["arbitrum_sepolia"]
        
        assert config["chain_id"] == 421614
        assert "arbitrum" in config["rpc_url"]
        assert config["native_token"] == "ETH"
        assert config["block_time"] == 1

    def test_arbitrum_mainnet_config(self):
        """Test Arbitrum mainnet configuration."""
        config = CHAIN_CONFIGS["arbitrum"]
        
        assert config["chain_id"] == 42161
        assert config["native_token"] == "ETH"

    def test_optimism_sepolia_config(self):
        """Test Optimism Sepolia configuration."""
        config = CHAIN_CONFIGS["optimism_sepolia"]
        
        assert config["chain_id"] == 11155420
        assert "optimism" in config["rpc_url"]
        assert config["native_token"] == "ETH"

    def test_optimism_mainnet_config(self):
        """Test Optimism mainnet configuration."""
        config = CHAIN_CONFIGS["optimism"]
        
        assert config["chain_id"] == 10
        assert config["native_token"] == "ETH"

    def test_solana_devnet_config(self):
        """Test Solana devnet configuration."""
        config = CHAIN_CONFIGS["solana_devnet"]
        
        assert "solana" in config["rpc_url"]
        assert config["native_token"] == "SOL"
        assert config.get("is_solana") is True

    def test_solana_mainnet_config(self):
        """Test Solana mainnet configuration."""
        config = CHAIN_CONFIGS["solana"]
        
        assert "solana" in config["rpc_url"]
        assert config["native_token"] == "SOL"


class TestStablecoinAddresses:
    """Tests for stablecoin contract addresses."""

    def test_base_sepolia_usdc(self):
        """Test USDC address on Base Sepolia."""
        addresses = STABLECOIN_ADDRESSES["base_sepolia"]
        
        assert "USDC" in addresses
        assert addresses["USDC"].startswith("0x")
        assert len(addresses["USDC"]) == 42

    def test_arbitrum_sepolia_usdc(self):
        """Test USDC address on Arbitrum Sepolia."""
        addresses = STABLECOIN_ADDRESSES["arbitrum_sepolia"]
        
        assert "USDC" in addresses
        assert addresses["USDC"].startswith("0x")

    def test_arbitrum_has_multiple_stablecoins(self):
        """Test Arbitrum mainnet has multiple stablecoins."""
        addresses = STABLECOIN_ADDRESSES["arbitrum"]
        
        assert "USDC" in addresses
        assert "USDT" in addresses

    def test_optimism_has_stablecoins(self):
        """Test Optimism has stablecoins."""
        addresses = STABLECOIN_ADDRESSES["optimism"]
        
        assert "USDC" in addresses
        assert "USDT" in addresses

    def test_solana_usdc(self):
        """Test USDC address on Solana."""
        addresses = STABLECOIN_ADDRESSES["solana"]
        
        assert "USDC" in addresses
        # Solana addresses are base58, not hex
        assert not addresses["USDC"].startswith("0x")

    def test_ethereum_has_eurc_pyusd(self):
        """Test Ethereum has EURC and PYUSD."""
        addresses = STABLECOIN_ADDRESSES["ethereum"]
        
        assert "EURC" in addresses
        assert "PYUSD" in addresses

    def test_polygon_has_multiple_stablecoins(self):
        """Test Polygon has multiple stablecoins."""
        addresses = STABLECOIN_ADDRESSES["polygon"]
        
        assert "USDC" in addresses
        assert "USDT" in addresses


class TestEncodeERC20Transfer:
    """Tests for ERC20 transfer encoding."""

    def test_encode_transfer_basic(self):
        """Test basic ERC20 transfer encoding."""
        to_address = "0x1234567890123456789012345678901234567890"
        amount = 1000000  # 1 USDC (6 decimals)
        
        data = encode_erc20_transfer(to_address, amount)
        
        # Check function selector (transfer(address,uint256))
        assert data[:4] == bytes.fromhex("a9059cbb")
        # Total length should be 4 (selector) + 32 (address) + 32 (amount) = 68 bytes
        assert len(data) == 68

    def test_encode_transfer_zero_amount(self):
        """Test ERC20 transfer with zero amount."""
        to_address = "0x0000000000000000000000000000000000000001"
        amount = 0
        
        data = encode_erc20_transfer(to_address, amount)
        
        assert len(data) == 68
        # Last 32 bytes should be zero
        assert data[-32:] == b'\x00' * 32

    def test_encode_transfer_large_amount(self):
        """Test ERC20 transfer with large amount."""
        to_address = "0xabcdef1234567890abcdef1234567890abcdef12"
        amount = 10**18  # 1 token with 18 decimals
        
        data = encode_erc20_transfer(to_address, amount)
        
        assert len(data) == 68


class TestTransactionModels:
    """Tests for transaction-related models."""

    def test_submitted_tx_creation(self):
        """Test creating SubmittedTx."""
        tx = SubmittedTx(
            tx_hash="0xabc123...",
            chain="base_sepolia",
            audit_anchor="merkle::hash123",
        )
        
        assert tx.status == TransactionStatus.SUBMITTED
        assert tx.block_number is None
        assert tx.gas_used is None

    def test_gas_estimate_creation(self):
        """Test creating GasEstimate."""
        estimate = GasEstimate(
            gas_limit=100000,
            gas_price_gwei=Decimal("30.0"),
            max_fee_gwei=Decimal("50.0"),
            max_priority_fee_gwei=Decimal("2.0"),
            estimated_cost_wei=5000000000000000,  # 0.005 ETH
        )
        
        assert estimate.gas_limit == 100000
        assert estimate.max_fee_gwei == Decimal("50.0")

    def test_transaction_request_creation(self):
        """Test creating TransactionRequest."""
        tx_request = TransactionRequest(
            chain="base_sepolia",
            to_address="0x1234567890123456789012345678901234567890",
            value=0,
            data=b"\xa9\x05\x9c\xbb" + b"\x00" * 64,
            gas_limit=100000,
        )
        
        assert tx_request.chain == "base_sepolia"
        assert tx_request.value == 0
        assert len(tx_request.data) == 68


class TestTransactionStatus:
    """Tests for TransactionStatus enum."""

    def test_status_values(self):
        """Test TransactionStatus enum values."""
        assert TransactionStatus.PENDING.value == "pending"
        assert TransactionStatus.SUBMITTED.value == "submitted"
        assert TransactionStatus.CONFIRMING.value == "confirming"
        assert TransactionStatus.CONFIRMED.value == "confirmed"
        assert TransactionStatus.FAILED.value == "failed"


class TestSimulatedMPCSigner:
    """Tests for SimulatedMPCSigner."""

    @pytest.mark.asyncio
    async def test_sign_transaction_returns_hash(self):
        """Test sign_transaction returns a valid hash."""
        signer = SimulatedMPCSigner()
        
        tx_request = TransactionRequest(
            chain="base_sepolia",
            to_address="0x1234567890123456789012345678901234567890",
        )
        
        signed_tx = await signer.sign_transaction("wallet_001", tx_request)
        
        assert signed_tx.startswith("0x")
        assert len(signed_tx) == 66  # 0x + 64 hex chars

    @pytest.mark.asyncio
    async def test_get_address_returns_consistent_address(self):
        """Test get_address returns consistent address for same wallet."""
        signer = SimulatedMPCSigner()
        
        address1 = await signer.get_address("wallet_001", "base_sepolia")
        address2 = await signer.get_address("wallet_001", "base_sepolia")
        
        assert address1 == address2
        assert address1.startswith("0x")
        assert len(address1) == 42

    @pytest.mark.asyncio
    async def test_get_address_different_for_different_wallets(self):
        """Test get_address returns different addresses for different wallets."""
        signer = SimulatedMPCSigner()
        
        address1 = await signer.get_address("wallet_001", "base_sepolia")
        address2 = await signer.get_address("wallet_002", "base_sepolia")
        
        assert address1 != address2

    @pytest.mark.asyncio
    async def test_get_address_different_for_different_chains(self):
        """Test get_address returns different addresses for different chains."""
        signer = SimulatedMPCSigner()
        
        address1 = await signer.get_address("wallet_001", "base_sepolia")
        address2 = await signer.get_address("wallet_001", "polygon")
        
        assert address1 != address2


class TestChainExecutorSimulated:
    """Tests for ChainExecutor in simulated mode."""

    @pytest.fixture
    def simulated_settings(self):
        """Create settings for simulated mode."""
        from sardis_v2_core import SardisSettings
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            settings = SardisSettings(
                chain_mode="simulated",
                environment="dev",
            )
        return settings

    def test_executor_creation_simulated(self, simulated_settings):
        """Test creating ChainExecutor in simulated mode."""
        executor = ChainExecutor(simulated_settings)
        
        assert executor._simulated is True

    @pytest.mark.asyncio
    async def test_dispatch_payment_simulated(self, simulated_settings):
        """Test dispatch_payment in simulated mode."""
        executor = ChainExecutor(simulated_settings)
        mandate = create_test_mandate()
        
        receipt = await executor.dispatch_payment(mandate)
        
        assert receipt.tx_hash.startswith("0x")
        assert receipt.chain == "base_sepolia"
        assert receipt.block_number == 0  # Simulated
        assert "merkle::" in receipt.audit_anchor

    @pytest.mark.asyncio
    async def test_dispatch_payment_different_chains(self, simulated_settings):
        """Test dispatch_payment with different chains."""
        executor = ChainExecutor(simulated_settings)
        
        for chain in ["base_sepolia", "polygon_amoy"]:
            mandate = create_test_mandate(chain=chain)
            receipt = await executor.dispatch_payment(mandate)
            
            assert receipt.chain == chain


class TestChainRPCClient:
    """Tests for ChainRPCClient."""

    @pytest.fixture
    def rpc_client(self):
        """Create an RPC client for testing."""
        return ChainRPCClient("https://sepolia.base.org")

    @pytest.mark.asyncio
    async def test_get_gas_price_mock(self, rpc_client):
        """Test get_gas_price with mocked response."""
        with patch.object(rpc_client, "_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "0x1dcd65000"  # 8 gwei
            
            gas_price = await rpc_client.get_gas_price()
            
            assert gas_price == 8000000000
            mock_call.assert_called_once_with("eth_gasPrice")

    @pytest.mark.asyncio
    async def test_get_nonce_mock(self, rpc_client):
        """Test get_nonce with mocked response."""
        with patch.object(rpc_client, "_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "0x5"  # nonce 5
            
            nonce = await rpc_client.get_nonce("0x1234...")
            
            assert nonce == 5
            mock_call.assert_called_once_with("eth_getTransactionCount", ["0x1234...", "pending"])

    @pytest.mark.asyncio
    async def test_get_block_number_mock(self, rpc_client):
        """Test get_block_number with mocked response."""
        with patch.object(rpc_client, "_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "0xf4240"  # 1000000
            
            block_number = await rpc_client.get_block_number()
            
            assert block_number == 1000000

    @pytest.mark.asyncio
    async def test_get_transaction_receipt_mock(self, rpc_client):
        """Test get_transaction_receipt with mocked response."""
        with patch.object(rpc_client, "_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "status": "0x1",
                "blockNumber": "0x100",
                "gasUsed": "0x5208",
            }
            
            receipt = await rpc_client.get_transaction_receipt("0xabc...")
            
            assert receipt["status"] == "0x1"
            assert receipt["blockNumber"] == "0x100"

    @pytest.mark.asyncio
    async def test_send_raw_transaction_mock(self, rpc_client):
        """Test send_raw_transaction with mocked response."""
        with patch.object(rpc_client, "_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "0x1234567890abcdef..."
            
            tx_hash = await rpc_client.send_raw_transaction("0xsigned...")
            
            assert tx_hash == "0x1234567890abcdef..."


class TestChainExecutorHelpers:
    """Tests for ChainExecutor helper methods."""

    @pytest.fixture
    def simulated_settings(self):
        """Create settings for simulated mode."""
        from sardis_v2_core import SardisSettings
        
        with patch.dict('os.environ', {'SARDIS_ENVIRONMENT': 'dev', 'DATABASE_URL': ''}):
            settings = SardisSettings(
                chain_mode="simulated",
                environment="dev",
            )
        return settings

    def test_get_rpc_client_unknown_chain(self, simulated_settings):
        """Test _get_rpc_client raises error for unknown chain."""
        executor = ChainExecutor(simulated_settings)
        
        with pytest.raises(ValueError, match="Unknown chain"):
            executor._get_rpc_client("unknown_chain")

    def test_get_rpc_client_caches_clients(self, simulated_settings):
        """Test _get_rpc_client caches RPC clients."""
        executor = ChainExecutor(simulated_settings)
        
        client1 = executor._get_rpc_client("base_sepolia")
        client2 = executor._get_rpc_client("base_sepolia")
        
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_transaction_status_pending(self, simulated_settings):
        """Test get_transaction_status returns PENDING when no receipt."""
        executor = ChainExecutor(simulated_settings)
        
        with patch.object(ChainRPCClient, "get_transaction_receipt", new_callable=AsyncMock) as mock:
            mock.return_value = None
            
            status = await executor.get_transaction_status("0xabc...", "base_sepolia")
            
            assert status == TransactionStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_transaction_status_failed(self, simulated_settings):
        """Test get_transaction_status returns FAILED for failed tx."""
        executor = ChainExecutor(simulated_settings)
        
        with patch.object(ChainRPCClient, "get_transaction_receipt", new_callable=AsyncMock) as mock_receipt:
            mock_receipt.return_value = {"status": "0x0", "blockNumber": "0x100"}
            
            status = await executor.get_transaction_status("0xabc...", "base_sepolia")
            
            assert status == TransactionStatus.FAILED

    @pytest.mark.asyncio
    async def test_close_cleanup(self, simulated_settings):
        """Test close() cleans up resources."""
        executor = ChainExecutor(simulated_settings)
        
        # Create some RPC clients
        executor._get_rpc_client("base_sepolia")
        executor._get_rpc_client("polygon")
        
        await executor.close()
        
        # Clients should be closed (no exception raised)







