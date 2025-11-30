"""Tests for chain abstraction layer."""

import pytest
from decimal import Decimal

from sardis_core.chains import (
    ChainType,
    ChainConfig,
    EVMChain,
    SolanaChain,
    ChainRouter,
)
from sardis_core.chains.base import TokenType, DEFAULT_CONFIGS


class TestEVMChain:
    """Tests for EVM chain operations."""
    
    @pytest.fixture
    def base_chain(self):
        """Create a Base chain instance for testing."""
        config = DEFAULT_CONFIGS[ChainType.BASE]
        return EVMChain(config)
    
    @pytest.fixture
    def ethereum_chain(self):
        """Create an Ethereum chain instance for testing."""
        config = DEFAULT_CONFIGS[ChainType.ETHEREUM]
        return EVMChain(config)
    
    @pytest.mark.asyncio
    async def test_create_wallet(self, base_chain):
        """Test wallet creation returns valid address and key."""
        address, private_key = await base_chain.create_wallet()
        
        assert address.startswith("0x")
        assert len(address) == 42
        assert len(private_key) == 64  # 32 bytes hex
    
    @pytest.mark.asyncio
    async def test_valid_address_check(self, base_chain):
        """Test address validation."""
        # Valid address
        valid = await base_chain.is_valid_address("0x" + "a" * 40)
        assert valid is True
        
        # Invalid: no 0x prefix
        invalid = await base_chain.is_valid_address("a" * 40)
        assert invalid is False
        
        # Invalid: wrong length
        invalid = await base_chain.is_valid_address("0x" + "a" * 30)
        assert invalid is False
        
        # Invalid: empty
        invalid = await base_chain.is_valid_address("")
        assert invalid is False
    
    @pytest.mark.asyncio
    async def test_initial_balance_is_zero(self, base_chain):
        """Test new wallet has zero balance."""
        address, _ = await base_chain.create_wallet()
        balance = await base_chain.get_balance(address, TokenType.USDC)
        
        assert balance == Decimal("0")
    
    @pytest.mark.asyncio
    async def test_fund_wallet(self, base_chain):
        """Test funding a wallet."""
        address, _ = await base_chain.create_wallet()
        
        # Fund with USDC
        base_chain.fund_wallet(address, Decimal("100.00"), TokenType.USDC)
        balance = await base_chain.get_balance(address, TokenType.USDC)
        
        assert balance == Decimal("100.00")
    
    @pytest.mark.asyncio
    async def test_transfer_success(self, base_chain):
        """Test successful transfer between wallets."""
        # Create two wallets
        sender, _ = await base_chain.create_wallet()
        receiver, _ = await base_chain.create_wallet()
        
        # Fund sender
        base_chain.fund_wallet(sender, Decimal("100.00"), TokenType.USDC)
        
        # Transfer
        tx = await base_chain.transfer(
            from_address=sender,
            to_address=receiver,
            amount=Decimal("30.00"),
            token=TokenType.USDC
        )
        
        assert tx.status == "confirmed"
        assert tx.amount == Decimal("30.00")
        assert tx.tx_hash.startswith("0x")
        
        # Check balances
        sender_balance = await base_chain.get_balance(sender, TokenType.USDC)
        receiver_balance = await base_chain.get_balance(receiver, TokenType.USDC)
        
        assert sender_balance == Decimal("70.00")
        assert receiver_balance == Decimal("30.00")
    
    @pytest.mark.asyncio
    async def test_transfer_insufficient_balance(self, base_chain):
        """Test transfer fails with insufficient balance."""
        sender, _ = await base_chain.create_wallet()
        receiver, _ = await base_chain.create_wallet()
        
        # Fund sender with only 10
        base_chain.fund_wallet(sender, Decimal("10.00"), TokenType.USDC)
        
        # Try to transfer 50
        with pytest.raises(ValueError, match="Insufficient balance"):
            await base_chain.transfer(
                from_address=sender,
                to_address=receiver,
                amount=Decimal("50.00"),
                token=TokenType.USDC
            )
    
    @pytest.mark.asyncio
    async def test_transfer_invalid_addresses(self, base_chain):
        """Test transfer fails with invalid addresses."""
        sender, _ = await base_chain.create_wallet()
        
        with pytest.raises(ValueError, match="Invalid"):
            await base_chain.transfer(
                from_address=sender,
                to_address="invalid_address",
                amount=Decimal("10.00"),
                token=TokenType.USDC
            )
    
    @pytest.mark.asyncio
    async def test_get_transaction(self, base_chain):
        """Test retrieving transaction by hash."""
        sender, _ = await base_chain.create_wallet()
        receiver, _ = await base_chain.create_wallet()
        base_chain.fund_wallet(sender, Decimal("100.00"), TokenType.USDC)
        
        tx = await base_chain.transfer(
            from_address=sender,
            to_address=receiver,
            amount=Decimal("25.00"),
            token=TokenType.USDC
        )
        
        # Retrieve transaction
        retrieved = await base_chain.get_transaction(tx.tx_hash)
        
        assert retrieved is not None
        assert retrieved.tx_hash == tx.tx_hash
        assert retrieved.amount == Decimal("25.00")
    
    @pytest.mark.asyncio
    async def test_estimate_gas(self, base_chain):
        """Test gas estimation returns reasonable value."""
        sender, _ = await base_chain.create_wallet()
        receiver, _ = await base_chain.create_wallet()
        
        gas_cost = await base_chain.estimate_gas(
            from_address=sender,
            to_address=receiver,
            amount=Decimal("10.00"),
            token=TokenType.USDC
        )
        
        # Should be a small positive value
        assert gas_cost > Decimal("0")
        assert gas_cost < Decimal("1")  # Less than 1 ETH
    
    @pytest.mark.asyncio
    async def test_token_info(self, ethereum_chain):
        """Test getting token info."""
        info = await ethereum_chain.get_token_info(TokenType.USDC)
        
        assert info["symbol"] == "USDC"
        assert info["name"] == "USD Coin"
        assert info["decimals"] == 6
        assert "contract_address" in info
    
    def test_supports_token(self, ethereum_chain):
        """Test token support check."""
        # Ethereum supports USDC, USDT, PYUSD
        assert ethereum_chain.supports_token(TokenType.USDC) is True
        assert ethereum_chain.supports_token(TokenType.USDT) is True
        assert ethereum_chain.supports_token(TokenType.PYUSD) is True
    
    def test_supported_tokens(self, ethereum_chain):
        """Test getting list of supported tokens."""
        tokens = ethereum_chain.supported_tokens
        
        assert TokenType.USDC in tokens
        assert len(tokens) >= 1


class TestSolanaChain:
    """Tests for Solana chain operations."""
    
    @pytest.fixture
    def solana_chain(self):
        """Create a Solana chain instance for testing."""
        config = DEFAULT_CONFIGS[ChainType.SOLANA]
        return SolanaChain(config)
    
    @pytest.mark.asyncio
    async def test_create_wallet(self, solana_chain):
        """Test Solana wallet creation."""
        address, private_key = await solana_chain.create_wallet()
        
        # Solana addresses are base58 encoded
        assert len(address) >= 32
        assert len(address) <= 44
    
    @pytest.mark.asyncio
    async def test_valid_address_check(self, solana_chain):
        """Test Solana address validation."""
        # Create a valid address
        address, _ = await solana_chain.create_wallet()
        
        valid = await solana_chain.is_valid_address(address)
        assert valid is True
        
        # Invalid
        invalid = await solana_chain.is_valid_address("")
        assert invalid is False
    
    @pytest.mark.asyncio
    async def test_transfer_success(self, solana_chain):
        """Test Solana transfer."""
        sender, _ = await solana_chain.create_wallet()
        receiver, _ = await solana_chain.create_wallet()
        
        solana_chain.fund_wallet(sender, Decimal("50.00"), TokenType.USDC)
        
        tx = await solana_chain.transfer(
            from_address=sender,
            to_address=receiver,
            amount=Decimal("20.00"),
            token=TokenType.USDC
        )
        
        assert tx.status == "confirmed"
        assert tx.chain == ChainType.SOLANA
        
        # Verify balances
        sender_balance = await solana_chain.get_balance(sender, TokenType.USDC)
        receiver_balance = await solana_chain.get_balance(receiver, TokenType.USDC)
        
        assert sender_balance == Decimal("30.00")
        assert receiver_balance == Decimal("20.00")
    
    @pytest.mark.asyncio
    async def test_estimate_gas_low_fees(self, solana_chain):
        """Test Solana has very low fees."""
        sender, _ = await solana_chain.create_wallet()
        receiver, _ = await solana_chain.create_wallet()
        
        gas_cost = await solana_chain.estimate_gas(
            from_address=sender,
            to_address=receiver,
            amount=Decimal("100.00"),
            token=TokenType.USDC
        )
        
        # Solana fees should be very low
        assert gas_cost < Decimal("0.001")


class TestChainRouter:
    """Tests for chain routing logic."""
    
    @pytest.fixture
    def router(self):
        """Create a chain router instance."""
        return ChainRouter()
    
    def test_supported_chains(self, router):
        """Test router has all supported chains."""
        chains = router.supported_chains
        
        assert ChainType.BASE in chains
        assert ChainType.ETHEREUM in chains
        assert ChainType.POLYGON in chains
        assert ChainType.SOLANA in chains
    
    def test_get_chain(self, router):
        """Test getting specific chain instance."""
        base = router.get_chain(ChainType.BASE)
        assert base is not None
        assert base.chain_type == ChainType.BASE
        
        solana = router.get_chain(ChainType.SOLANA)
        assert solana is not None
        assert solana.chain_type == ChainType.SOLANA
    
    def test_get_invalid_chain_raises(self, router):
        """Test getting invalid chain raises error."""
        with pytest.raises(ValueError):
            router.get_chain("invalid_chain")
    
    @pytest.mark.asyncio
    async def test_find_optimal_route(self, router):
        """Test finding optimal route for transaction."""
        route = await router.find_optimal_route(
            amount=Decimal("50.00"),
            token=TokenType.USDC
        )
        
        assert route is not None
        assert route.chain in [ChainType.BASE, ChainType.SOLANA, ChainType.POLYGON, ChainType.ETHEREUM]
        assert route.estimated_fee >= Decimal("0")
        assert route.estimated_time_seconds > 0
        assert len(route.all_options) > 0
    
    @pytest.mark.asyncio
    async def test_find_route_with_preference(self, router):
        """Test route selection respects user preference."""
        route = await router.find_optimal_route(
            amount=Decimal("50.00"),
            token=TokenType.USDC,
            preferred_chain=ChainType.POLYGON
        )
        
        # Should prefer Polygon if available
        assert route.chain == ChainType.POLYGON
    
    @pytest.mark.asyncio
    async def test_find_route_with_max_fee(self, router):
        """Test route respects max fee constraint."""
        route = await router.find_optimal_route(
            amount=Decimal("50.00"),
            token=TokenType.USDC,
            max_fee=Decimal("0.001")
        )
        
        # Should find a cheap route
        assert route.estimated_fee <= Decimal("0.001") or route.chain in [ChainType.BASE, ChainType.SOLANA]
    
    @pytest.mark.asyncio
    async def test_execute_transfer(self, router):
        """Test executing transfer through router."""
        base = router.get_chain(ChainType.BASE)
        
        sender, _ = await base.create_wallet()
        receiver, _ = await base.create_wallet()
        base.fund_wallet(sender, Decimal("100.00"), TokenType.USDC)
        
        tx = await router.execute_transfer(
            chain_type=ChainType.BASE,
            from_address=sender,
            to_address=receiver,
            amount=Decimal("40.00"),
            token=TokenType.USDC
        )
        
        assert tx.status == "confirmed"
        assert tx.amount == Decimal("40.00")
    
    @pytest.mark.asyncio
    async def test_get_balance_via_router(self, router):
        """Test getting balance through router."""
        base = router.get_chain(ChainType.BASE)
        address, _ = await base.create_wallet()
        base.fund_wallet(address, Decimal("75.00"), TokenType.USDC)
        
        balance = await router.get_balance(address, ChainType.BASE, TokenType.USDC)
        
        assert balance == Decimal("75.00")
    
    def test_token_availability(self, router):
        """Test checking token availability across chains."""
        availability = router.get_token_availability(TokenType.USDC)
        
        # USDC should be available on all chains
        assert availability[ChainType.BASE] is True
        assert availability[ChainType.ETHEREUM] is True
        assert availability[ChainType.SOLANA] is True


class TestChainConfig:
    """Tests for chain configuration."""
    
    def test_default_configs_exist(self):
        """Test default configs are defined for all chains."""
        for chain_type in ChainType:
            assert chain_type in DEFAULT_CONFIGS
            config = DEFAULT_CONFIGS[chain_type]
            assert config.chain_type == chain_type
    
    def test_evm_chains_have_chain_id(self):
        """Test EVM chains have chain IDs."""
        for chain_type in [ChainType.BASE, ChainType.ETHEREUM, ChainType.POLYGON]:
            config = DEFAULT_CONFIGS[chain_type]
            assert config.chain_id is not None
            assert config.chain_id > 0
    
    def test_solana_no_chain_id(self):
        """Test Solana config has no chain ID."""
        config = DEFAULT_CONFIGS[ChainType.SOLANA]
        assert config.chain_id is None
    
    def test_configs_have_rpc_urls(self):
        """Test all configs have RPC URLs."""
        for chain_type in ChainType:
            config = DEFAULT_CONFIGS[chain_type]
            assert config.rpc_url is not None
            assert config.rpc_url.startswith("http")
    
    def test_configs_have_token_addresses(self):
        """Test configs have token contract addresses."""
        for chain_type in ChainType:
            config = DEFAULT_CONFIGS[chain_type]
            assert len(config.token_addresses) > 0
            assert TokenType.USDC in config.token_addresses

