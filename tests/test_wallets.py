"""Unit tests for non-custodial wallet models and operations."""
from __future__ import annotations

from decimal import Decimal
import pytest

from sardis_v2_core.wallets import Wallet, TokenLimit, WalletSnapshot
from sardis_v2_core.tokens import TokenType


class TestTokenLimit:
    """Tests for TokenLimit model (non-custodial, limits only)."""

    def test_token_limit_creation(self):
        """Test creating a TokenLimit."""
        limit = TokenLimit(
            token=TokenType.USDC,
            limit_per_tx=Decimal("100.00"),
            limit_total=Decimal("1000.00"),
        )
        
        assert limit.token == TokenType.USDC
        assert limit.limit_per_tx == Decimal("100.00")
        assert limit.limit_total == Decimal("1000.00")
        # Note: No balance field - balances are read from chain


class TestWallet:
    """Tests for non-custodial Wallet model."""

    def test_wallet_creation(self):
        """Test creating a non-custodial Wallet."""
        wallet = Wallet(
            wallet_id="wallet_test001",
            agent_id="agent_001",
            mpc_provider="turnkey",
            currency="USDC",
        )
        
        assert wallet.wallet_id == "wallet_test001"
        assert wallet.agent_id == "agent_001"
        assert wallet.mpc_provider == "turnkey"
        assert wallet.is_active is True
        assert wallet.addresses == {}

    def test_wallet_new_factory(self):
        """Test Wallet.new() factory method."""
        wallet = Wallet.new("agent_123", mpc_provider="turnkey", currency="USDT")
        
        assert wallet.agent_id == "agent_123"
        assert wallet.wallet_id.startswith("wallet_")
        assert wallet.currency == "USDT"
        assert wallet.mpc_provider == "turnkey"
        assert wallet.addresses == {}

    def test_wallet_address_management(self):
        """Test wallet address management."""
        wallet = Wallet.new("agent_001")
        
        # Set address for base chain
        wallet.set_address("base", "0x1234567890123456789012345678901234567890")
        
        assert wallet.get_address("base") == "0x1234567890123456789012345678901234567890"
        assert wallet.get_address("polygon") is None

    def test_wallet_multiple_addresses(self):
        """Test wallet with multiple chain addresses."""
        wallet = Wallet.new("agent_001")
        
        wallet.set_address("base", "0x1111111111111111111111111111111111111111")
        wallet.set_address("polygon", "0x2222222222222222222222222222222222222222")
        wallet.set_address("ethereum", "0x3333333333333333333333333333333333333333")
        
        assert len(wallet.addresses) == 3
        assert wallet.addresses["base"] == "0x1111111111111111111111111111111111111111"
        assert wallet.addresses["polygon"] == "0x2222222222222222222222222222222222222222"
        assert wallet.addresses["ethereum"] == "0x3333333333333333333333333333333333333333"

    @pytest.mark.asyncio
    async def test_get_balance_requires_address(self):
        """Test get_balance requires wallet address for chain."""
        wallet = Wallet.new("agent_001")
        
        # No address set - should raise ValueError
        with pytest.raises(ValueError, match="No address found"):
            await wallet.get_balance("base", TokenType.USDC)

    @pytest.mark.asyncio
    async def test_get_balance_requires_rpc_client(self):
        """Test get_balance requires RPC client."""
        wallet = Wallet.new("agent_001")
        wallet.set_address("base", "0x1234567890123456789012345678901234567890")
        
        # No RPC client - should raise ValueError
        with pytest.raises(ValueError, match="RPC client required"):
            await wallet.get_balance("base", TokenType.USDC)

    def test_get_limit_per_tx_default(self):
        """Test get_limit_per_tx returns wallet default."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            limit_per_tx=Decimal("100.00"),
        )
        
        limit = wallet.get_limit_per_tx()
        assert limit == Decimal("100.00")

    def test_get_limit_per_tx_token_override(self):
        """Test get_limit_per_tx uses token-specific limit when set."""
        from sardis_v2_core.wallets import TokenLimit
        
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            limit_per_tx=Decimal("100.00"),
            token_limits={
                "USDT": TokenLimit(
                    token=TokenType.USDT,
                    limit_per_tx=Decimal("50.00"),
                ),
            },
        )
        
        limit = wallet.get_limit_per_tx(TokenType.USDT)
        assert limit == Decimal("50.00")

    def test_get_limit_total_default(self):
        """Test get_limit_total returns wallet default."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            limit_total=Decimal("1000.00"),
        )
        
        limit = wallet.get_limit_total()
        assert limit == Decimal("1000.00")

    def test_get_limit_total_token_override(self):
        """Test get_limit_total uses token-specific limit when set."""
        from sardis_v2_core.wallets import TokenLimit
        
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            limit_total=Decimal("1000.00"),
            token_limits={
                "USDT": TokenLimit(
                    token=TokenType.USDT,
                    limit_total=Decimal("500.00"),
                ),
            },
        )
        
        limit = wallet.get_limit_total(TokenType.USDT)
        assert limit == Decimal("500.00")


class TestWalletSnapshot:
    """Tests for WalletSnapshot model."""

    def test_wallet_snapshot_creation(self):
        """Test creating a WalletSnapshot."""
        snapshot = WalletSnapshot(
            wallet_id="wallet_001",
            balances={"USDC": Decimal("100.00"), "USDT": Decimal("50.00")},
        )
        
        assert snapshot.wallet_id == "wallet_001"
        assert snapshot.balances["USDC"] == Decimal("100.00")
        assert snapshot.balances["USDT"] == Decimal("50.00")
        assert snapshot.captured_at is not None
