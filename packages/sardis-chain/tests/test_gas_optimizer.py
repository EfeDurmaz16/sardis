"""
Tests for multi-chain gas optimizer.
"""
import asyncio
import sys
import time
from decimal import Decimal
from pathlib import Path

import pytest

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core", "sardis-ledger"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_chain.gas_optimizer import (
    GasOptimizer,
    GasEstimate,
    ChainRoute,
    get_gas_optimizer,
)


class TestGasEstimate:
    """Test GasEstimate dataclass."""

    def test_gas_estimate_creation(self):
        """Test creating a GasEstimate."""
        estimate = GasEstimate(
            chain="base",
            gas_price_gwei=Decimal("0.003"),
            estimated_gas_units=65000,
            estimated_cost_usd=Decimal("0.0005"),
            estimated_time_seconds=6,
            congestion_level="low",
        )

        assert estimate.chain == "base"
        assert estimate.gas_price_gwei == Decimal("0.003")
        assert estimate.estimated_gas_units == 65000
        assert estimate.estimated_cost_usd == Decimal("0.0005")
        assert estimate.estimated_time_seconds == 6
        assert estimate.congestion_level == "low"


class TestChainRoute:
    """Test ChainRoute dataclass."""

    def test_same_chain_route(self):
        """Test creating a same-chain route."""
        route = ChainRoute(
            source_chain="base",
            destination_chain=None,
            token="USDC",
            estimated_gas_cost_usd=Decimal("0.0005"),
            estimated_total_cost_usd=Decimal("0.0005"),
            estimated_time_seconds=6,
            recommended=True,
        )

        assert route.source_chain == "base"
        assert route.destination_chain is None
        assert route.token == "USDC"
        assert route.recommended is True

    def test_cross_chain_route(self):
        """Test creating a cross-chain route."""
        route = ChainRoute(
            source_chain="ethereum",
            destination_chain="base",
            token="USDC",
            estimated_gas_cost_usd=Decimal("5.00"),
            estimated_total_cost_usd=Decimal("5.50"),  # includes bridge fee
            estimated_time_seconds=306,
            recommended=False,
        )

        assert route.source_chain == "ethereum"
        assert route.destination_chain == "base"
        assert route.estimated_total_cost_usd > route.estimated_gas_cost_usd


class TestGasOptimizer:
    """Test GasOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create a fresh optimizer instance."""
        return GasOptimizer(cache_ttl_seconds=30)

    @pytest.mark.asyncio
    async def test_estimate_gas_ethereum(self, optimizer):
        """Test gas estimation for Ethereum mainnet."""
        estimate = await optimizer.estimate_gas(
            chain="ethereum",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )

        assert estimate.chain == "ethereum"
        assert estimate.gas_price_gwei > 0
        assert estimate.estimated_gas_units == 65000
        assert estimate.estimated_cost_usd > 0
        assert estimate.estimated_time_seconds > 0
        assert estimate.congestion_level in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_estimate_gas_base(self, optimizer):
        """Test gas estimation for Base L2."""
        estimate = await optimizer.estimate_gas(
            chain="base",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )

        assert estimate.chain == "base"
        assert estimate.gas_price_gwei < Decimal("1")  # L2s are cheap
        assert estimate.estimated_gas_units == 65000
        assert estimate.estimated_cost_usd < Decimal("1")  # Should be very cheap
        assert estimate.congestion_level in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_estimate_gas_polygon(self, optimizer):
        """Test gas estimation for Polygon."""
        estimate = await optimizer.estimate_gas(
            chain="polygon",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )

        assert estimate.chain == "polygon"
        assert estimate.gas_price_gwei > Decimal("10")  # Polygon typically higher
        assert estimate.estimated_gas_units == 65000
        assert estimate.estimated_cost_usd >= 0
        assert estimate.congestion_level in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_estimate_gas_arbitrum(self, optimizer):
        """Test gas estimation for Arbitrum."""
        estimate = await optimizer.estimate_gas(
            chain="arbitrum",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )

        assert estimate.chain == "arbitrum"
        assert estimate.gas_price_gwei < Decimal("1")  # L2 cheap
        assert estimate.estimated_gas_units == 65000
        assert estimate.estimated_time_seconds > 0

    @pytest.mark.asyncio
    async def test_estimate_gas_optimism(self, optimizer):
        """Test gas estimation for Optimism."""
        estimate = await optimizer.estimate_gas(
            chain="optimism",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )

        assert estimate.chain == "optimism"
        assert estimate.gas_price_gwei < Decimal("1")  # L2 cheap
        assert estimate.estimated_gas_units == 65000

    @pytest.mark.asyncio
    async def test_find_cheapest_route(self, optimizer):
        """Test finding cheapest route across multiple chains."""
        routes = await optimizer.find_cheapest_route(
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
            source_chains=["ethereum", "base", "polygon", "arbitrum", "optimism"],
        )

        # Should return all chains
        assert len(routes) == 5

        # Should be sorted by cost (cheapest first)
        for i in range(len(routes) - 1):
            assert routes[i].estimated_total_cost_usd <= routes[i + 1].estimated_total_cost_usd

        # First route should be marked as recommended
        assert routes[0].recommended is True

        # Others should not be recommended
        for route in routes[1:]:
            assert route.recommended is False

        # L2s should generally be cheaper than Ethereum
        eth_route = next((r for r in routes if r.source_chain == "ethereum"), None)
        l2_routes = [r for r in routes if r.source_chain in ["base", "arbitrum", "optimism"]]

        if eth_route and l2_routes:
            # At least one L2 should be cheaper
            assert any(l2.estimated_total_cost_usd < eth_route.estimated_total_cost_usd for l2 in l2_routes)

    @pytest.mark.asyncio
    async def test_find_cheapest_route_single_chain(self, optimizer):
        """Test route finding with single chain."""
        routes = await optimizer.find_cheapest_route(
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
            source_chains=["base"],
        )

        assert len(routes) == 1
        assert routes[0].source_chain == "base"
        assert routes[0].recommended is True

    @pytest.mark.asyncio
    async def test_get_gas_prices(self, optimizer):
        """Test getting gas prices for all chains."""
        prices = await optimizer.get_gas_prices()

        # Should have estimates for multiple chains
        assert len(prices) > 0

        # Check that all are valid GasEstimate objects
        for chain, estimate in prices.items():
            assert isinstance(estimate, GasEstimate)
            assert estimate.chain == chain
            assert estimate.gas_price_gwei > 0
            assert estimate.estimated_gas_units == 65000
            assert estimate.congestion_level in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_gas_price_caching(self, optimizer):
        """Test that gas prices are cached correctly."""
        chain = "base"

        # First call - should fetch
        price1 = await optimizer._get_gas_price(chain)
        assert price1 > 0

        # Second call - should use cache
        price2 = await optimizer._get_gas_price(chain)
        assert price2 == price1  # Should be identical (cached)

        # Check cache directly
        cached = optimizer._get_cached_gas_price(chain)
        assert cached == price1

    @pytest.mark.asyncio
    async def test_gas_price_cache_expiry(self, optimizer):
        """Test that cache expires after TTL."""
        # Use very short TTL
        optimizer.cache_ttl = 0.1  # 100ms
        chain = "base"

        # First call
        price1 = await optimizer._get_gas_price(chain)

        # Wait for cache to expire
        await asyncio.sleep(0.15)

        # Should be expired
        cached = optimizer._get_cached_gas_price(chain)
        assert cached is None

        # Next call should fetch fresh
        price2 = await optimizer._get_gas_price(chain)
        assert price2 > 0
        # Might be different due to randomization

    @pytest.mark.asyncio
    async def test_calculate_bridge_fee(self, optimizer):
        """Test bridge fee calculation."""
        # Small transfer
        fee_small = optimizer._calculate_bridge_fee(
            source="ethereum",
            dest="base",
            amount=Decimal("100"),
        )
        assert fee_small > optimizer.BRIDGE_FLAT_FEE_USD
        assert fee_small == optimizer.BRIDGE_FLAT_FEE_USD + (Decimal("100") * optimizer.BRIDGE_FEE_PERCENTAGE)

        # Large transfer
        fee_large = optimizer._calculate_bridge_fee(
            source="ethereum",
            dest="base",
            amount=Decimal("10000"),
        )
        assert fee_large > fee_small
        assert fee_large == optimizer.BRIDGE_FLAT_FEE_USD + (Decimal("10000") * optimizer.BRIDGE_FEE_PERCENTAGE)

    @pytest.mark.asyncio
    async def test_congestion_level_detection(self, optimizer):
        """Test that congestion levels are set correctly."""
        # Force different gas prices and check congestion
        chain = "ethereum"

        # Get estimate
        estimate = await optimizer.estimate_gas(
            chain=chain,
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )

        # Should have a valid congestion level
        assert estimate.congestion_level in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_parallel_route_estimation(self, optimizer):
        """Test that routes are estimated in parallel."""
        import time as time_module

        chains = ["ethereum", "base", "polygon", "arbitrum", "optimism"]

        start = time_module.time()
        routes = await optimizer.find_cheapest_route(
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
            source_chains=chains,
        )
        elapsed = time_module.time() - start

        # Should have all routes
        assert len(routes) == len(chains)

        # Should be fast due to parallelization (less than serial time)
        # Serial would take 5 * (fetch time), parallel should be ~1 * fetch time
        assert elapsed < 2.0  # Should complete in under 2 seconds

    @pytest.mark.asyncio
    async def test_optimizer_singleton(self):
        """Test that get_gas_optimizer returns singleton."""
        opt1 = get_gas_optimizer()
        opt2 = get_gas_optimizer()

        assert opt1 is opt2

    @pytest.mark.asyncio
    async def test_gas_estimates_within_range(self, optimizer):
        """Test that gas estimates are within expected ranges."""
        chains_to_test = {
            "ethereum": (Decimal("15"), Decimal("50")),
            "base": (Decimal("0.001"), Decimal("0.01")),
            "polygon": (Decimal("30"), Decimal("100")),
            "arbitrum": (Decimal("0.1"), Decimal("0.5")),
            "optimism": (Decimal("0.001"), Decimal("0.01")),
        }

        for chain, (min_gwei, max_gwei) in chains_to_test.items():
            estimate = await optimizer.estimate_gas(
                chain=chain,
                token="USDC",
                amount=Decimal("100"),
                destination="0x1234567890123456789012345678901234567890",
            )

            # Gas price should be in expected range
            assert estimate.gas_price_gwei >= min_gwei
            assert estimate.gas_price_gwei <= max_gwei

    @pytest.mark.asyncio
    async def test_route_contains_all_required_fields(self, optimizer):
        """Test that routes contain all required fields."""
        routes = await optimizer.find_cheapest_route(
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
            source_chains=["base"],
        )

        route = routes[0]

        # Check all fields are present and valid
        assert isinstance(route.source_chain, str)
        assert route.source_chain == "base"
        assert route.destination_chain is None or isinstance(route.destination_chain, str)
        assert isinstance(route.token, str)
        assert isinstance(route.estimated_gas_cost_usd, Decimal)
        assert isinstance(route.estimated_total_cost_usd, Decimal)
        assert isinstance(route.estimated_time_seconds, int)
        assert isinstance(route.recommended, bool)
        assert route.estimated_total_cost_usd >= route.estimated_gas_cost_usd

    @pytest.mark.asyncio
    async def test_block_time_estimates(self, optimizer):
        """Test that block time estimates are correct."""
        # Ethereum should have ~12s blocks
        eth_estimate = await optimizer.estimate_gas(
            chain="ethereum",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )
        assert eth_estimate.estimated_time_seconds >= 24  # 2+ blocks

        # Base should have ~2s blocks
        base_estimate = await optimizer.estimate_gas(
            chain="base",
            token="USDC",
            amount=Decimal("100"),
            destination="0x1234567890123456789012345678901234567890",
        )
        assert base_estimate.estimated_time_seconds >= 4  # 2+ blocks
        assert base_estimate.estimated_time_seconds < eth_estimate.estimated_time_seconds

    @pytest.mark.asyncio
    async def test_custom_rpc_urls(self):
        """Test optimizer with custom RPC URLs."""
        custom_rpcs = {
            "base": "https://custom-base-rpc.example.com",
            "ethereum": "https://custom-eth-rpc.example.com",
        }

        optimizer = GasOptimizer(rpc_urls=custom_rpcs)
        assert optimizer.rpc_urls == custom_rpcs

    @pytest.mark.asyncio
    async def test_custom_cache_ttl(self):
        """Test optimizer with custom cache TTL."""
        optimizer = GasOptimizer(cache_ttl_seconds=60)
        assert optimizer.cache_ttl == 60

        # Fetch a price
        await optimizer._get_gas_price("base")

        # Should still be cached after 1 second
        await asyncio.sleep(1)
        cached = optimizer._get_cached_gas_price("base")
        assert cached is not None
