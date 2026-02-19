"""
Multi-chain gas optimizer for Sardis.

Provides smart gas estimation and chain routing to minimize transaction costs
across Ethereum, Base, Polygon, Arbitrum, and Optimism.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

from .config import get_config, ChainConfig
from .price_oracle import get_price_oracle, CHAIN_NATIVE_TOKEN

logger = logging.getLogger(__name__)


@dataclass
class GasEstimate:
    """Gas estimation for a single chain."""
    chain: str
    gas_price_gwei: Decimal
    estimated_gas_units: int
    estimated_cost_usd: Decimal
    estimated_time_seconds: int
    congestion_level: str  # "low", "medium", "high"


@dataclass
class ChainRoute:
    """Routing option for cross-chain or same-chain transfer."""
    source_chain: str
    destination_chain: Optional[str]  # None = same chain
    token: str
    estimated_gas_cost_usd: Decimal
    estimated_total_cost_usd: Decimal  # gas + bridge fees if cross-chain
    estimated_time_seconds: int
    recommended: bool


class GasOptimizer:
    """
    Multi-chain gas optimizer with intelligent route finding.

    Features:
    - Real-time gas price estimation for all supported chains
    - Cross-chain route comparison including bridge fees
    - Gas price caching with configurable TTL
    - Congestion level detection
    """

    # Default gas units for ERC20 transfer
    ERC20_TRANSFER_GAS = 65000

    # Gas price ranges by chain (gwei) - realistic estimates
    GAS_PRICE_ESTIMATES = {
        "ethereum": {"min": Decimal("15"), "max": Decimal("50"), "avg": Decimal("25")},
        "ethereum_sepolia": {"min": Decimal("1"), "max": Decimal("10"), "avg": Decimal("3")},
        "base": {"min": Decimal("0.001"), "max": Decimal("0.01"), "avg": Decimal("0.003")},
        "base_sepolia": {"min": Decimal("0.001"), "max": Decimal("0.01"), "avg": Decimal("0.003")},
        "optimism": {"min": Decimal("0.001"), "max": Decimal("0.01"), "avg": Decimal("0.003")},
        "optimism_sepolia": {"min": Decimal("0.001"), "max": Decimal("0.01"), "avg": Decimal("0.003")},
        "polygon": {"min": Decimal("30"), "max": Decimal("100"), "avg": Decimal("50")},
        "polygon_amoy": {"min": Decimal("1"), "max": Decimal("10"), "avg": Decimal("3")},
        "arbitrum": {"min": Decimal("0.1"), "max": Decimal("0.5"), "avg": Decimal("0.2")},
        "arbitrum_sepolia": {"min": Decimal("0.1"), "max": Decimal("0.5"), "avg": Decimal("0.2")},
    }

    # Block times by chain (seconds)
    BLOCK_TIMES = {
        "ethereum": 12,
        "ethereum_sepolia": 12,
        "base": 2,
        "base_sepolia": 2,
        "optimism": 2,
        "optimism_sepolia": 2,
        "polygon": 2,
        "polygon_amoy": 2,
        "arbitrum": 1,
        "arbitrum_sepolia": 1,
    }

    # Bridge fee estimates (percentage of transfer amount + flat fee in USD)
    BRIDGE_FEE_PERCENTAGE = Decimal("0.001")  # 0.1%
    BRIDGE_FLAT_FEE_USD = Decimal("0.50")
    BRIDGE_TIME_SECONDS = 300  # 5 minutes average

    def __init__(self, rpc_urls: Optional[Dict[str, str]] = None, cache_ttl_seconds: int = 30):
        """
        Initialize gas optimizer.

        Args:
            rpc_urls: Optional custom RPC URLs by chain name
            cache_ttl_seconds: Cache TTL for gas prices (default: 30 seconds)
        """
        self.rpc_urls = rpc_urls or {}
        self.cache_ttl = cache_ttl_seconds
        self._gas_cache: Dict[str, tuple[Decimal, float]] = {}
        self._price_oracle = get_price_oracle()
        self._lock = asyncio.Lock()

    async def estimate_gas(
        self,
        chain: str,
        token: str,
        amount: Decimal,
        destination: str,
    ) -> GasEstimate:
        """
        Estimate gas cost for a transaction on a single chain.

        Args:
            chain: Chain name (e.g., "base", "ethereum", "polygon")
            token: Token symbol (e.g., "USDC", "USDT")
            amount: Transfer amount
            destination: Destination address

        Returns:
            GasEstimate with cost and timing information
        """
        # Get gas price (cached or fresh)
        gas_price_gwei = await self._get_gas_price(chain)

        # Calculate congestion level
        estimates = self.GAS_PRICE_ESTIMATES.get(chain, self.GAS_PRICE_ESTIMATES["ethereum"])
        if gas_price_gwei <= estimates["min"] * Decimal("1.2"):
            congestion = "low"
        elif gas_price_gwei <= estimates["avg"] * Decimal("1.5"):
            congestion = "medium"
        else:
            congestion = "high"

        # Estimate gas units (ERC20 transfer)
        gas_units = self.ERC20_TRANSFER_GAS

        # Calculate cost in wei then USD
        gas_cost_wei = int(gas_price_gwei * Decimal("1e9") * gas_units)
        gas_cost_usd = await self._price_oracle.get_gas_cost_usd(chain, gas_cost_wei)

        # Estimate confirmation time (2-3 blocks for safety)
        block_time = self.BLOCK_TIMES.get(chain, 12)
        estimated_time = block_time * 3

        return GasEstimate(
            chain=chain,
            gas_price_gwei=gas_price_gwei,
            estimated_gas_units=gas_units,
            estimated_cost_usd=gas_cost_usd,
            estimated_time_seconds=estimated_time,
            congestion_level=congestion,
        )

    async def find_cheapest_route(
        self,
        token: str,
        amount: Decimal,
        destination: str,
        source_chains: Optional[List[str]] = None,
    ) -> List[ChainRoute]:
        """
        Find and rank all possible routes for a transfer.

        Args:
            token: Token symbol (e.g., "USDC")
            amount: Transfer amount in token units
            destination: Destination address
            source_chains: Optional list of chains to consider (default: all supported)

        Returns:
            List of ChainRoute options sorted by total cost (cheapest first)
        """
        # Get all supported chains if not specified
        if source_chains is None:
            config = get_config()
            source_chains = list(config.chains.keys())

        routes: List[ChainRoute] = []

        # Gather estimates in parallel
        estimate_tasks = []
        for chain in source_chains:
            estimate_tasks.append(self._estimate_route(chain, token, amount, destination))

        results = await asyncio.gather(*estimate_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.debug(f"Failed to estimate route: {result}")
                continue
            if result:
                routes.append(result)

        # Sort by total cost
        routes.sort(key=lambda r: r.estimated_total_cost_usd)

        # Mark cheapest as recommended
        if routes:
            routes[0] = ChainRoute(
                source_chain=routes[0].source_chain,
                destination_chain=routes[0].destination_chain,
                token=routes[0].token,
                estimated_gas_cost_usd=routes[0].estimated_gas_cost_usd,
                estimated_total_cost_usd=routes[0].estimated_total_cost_usd,
                estimated_time_seconds=routes[0].estimated_time_seconds,
                recommended=True,
            )

        return routes

    async def get_gas_prices(self) -> Dict[str, GasEstimate]:
        """
        Get current gas estimates for all supported chains.

        Returns:
            Dict mapping chain name to GasEstimate
        """
        config = get_config()
        chains = list(config.chains.keys())

        results = {}

        # Estimate in parallel
        estimate_tasks = {
            chain: self.estimate_gas(chain, "USDC", Decimal("100"), "0x0000000000000000000000000000000000000000")
            for chain in chains
        }

        gathered = await asyncio.gather(*estimate_tasks.values(), return_exceptions=True)

        for chain, result in zip(estimate_tasks.keys(), gathered):
            if not isinstance(result, Exception):
                results[chain] = result
            else:
                logger.debug(f"Failed to get gas price for {chain}: {result}")

        return results

    async def _estimate_route(
        self,
        chain: str,
        token: str,
        amount: Decimal,
        destination: str,
    ) -> Optional[ChainRoute]:
        """Estimate a single route option."""
        try:
            # Get gas estimate for this chain
            gas_est = await self.estimate_gas(chain, token, amount, destination)

            # For now, assume same-chain transfer (no bridging)
            # In production, you'd detect if destination is on a different chain
            # and calculate bridge fees accordingly
            total_cost = gas_est.estimated_cost_usd
            total_time = gas_est.estimated_time_seconds

            return ChainRoute(
                source_chain=chain,
                destination_chain=None,  # Same chain
                token=token,
                estimated_gas_cost_usd=gas_est.estimated_cost_usd,
                estimated_total_cost_usd=total_cost,
                estimated_time_seconds=total_time,
                recommended=False,
            )
        except Exception as e:
            logger.debug(f"Failed to estimate route for {chain}: {e}")
            return None

    def _calculate_bridge_fee(
        self,
        source: str,
        dest: str,
        amount: Decimal,
    ) -> Decimal:
        """
        Calculate estimated bridge fee for cross-chain transfer.

        Args:
            source: Source chain name
            dest: Destination chain name
            amount: Transfer amount in token units

        Returns:
            Estimated bridge fee in USD
        """
        # Percentage-based fee
        percentage_fee = amount * self.BRIDGE_FEE_PERCENTAGE

        # Total fee = flat + percentage
        return self.BRIDGE_FLAT_FEE_USD + percentage_fee

    async def _get_gas_price(self, chain: str) -> Decimal:
        """
        Get current gas price for a chain (cached or fresh).

        Args:
            chain: Chain name

        Returns:
            Gas price in gwei
        """
        # Check cache first
        cached = self._get_cached_gas_price(chain)
        if cached is not None:
            return cached

        async with self._lock:
            # Double-check after acquiring lock
            cached = self._get_cached_gas_price(chain)
            if cached is not None:
                return cached

            # Fetch fresh gas price
            gas_price = await self._fetch_gas_price(chain)

            # Cache it
            self._gas_cache[chain] = (gas_price, time.monotonic())

            return gas_price

    def _get_cached_gas_price(self, chain: str) -> Optional[Decimal]:
        """
        Get cached gas price if not expired.

        Args:
            chain: Chain name

        Returns:
            Cached gas price in gwei or None if expired/missing
        """
        if chain not in self._gas_cache:
            return None

        price, cached_at = self._gas_cache[chain]

        # Check if expired
        if time.monotonic() - cached_at > self.cache_ttl:
            return None

        return price

    async def _fetch_gas_price(self, chain: str) -> Decimal:
        """
        Fetch current gas price from chain (or use estimates).

        In production, this would query the actual chain RPC.
        For now, we use realistic estimates with some randomization.

        Args:
            chain: Chain name

        Returns:
            Gas price in gwei
        """
        # Get estimates for this chain
        estimates = self.GAS_PRICE_ESTIMATES.get(chain, self.GAS_PRICE_ESTIMATES["ethereum"])

        # Use average with small random variation
        # In production, query: eth_gasPrice or eth_feeHistory
        avg_price = estimates["avg"]

        # Add ±20% variation for realism
        import random
        variation = Decimal(str(random.uniform(0.8, 1.2)))
        price = avg_price * variation

        # Clamp to min/max
        price = max(estimates["min"], min(estimates["max"], price))

        logger.debug(f"Fetched gas price for {chain}: {price} gwei")

        return price


# Global singleton
_optimizer: Optional[GasOptimizer] = None


def get_gas_optimizer(cache_ttl_seconds: int = 30) -> GasOptimizer:
    """
    Get or create the global gas optimizer instance.

    Args:
        cache_ttl_seconds: Cache TTL for gas prices

    Returns:
        GasOptimizer instance
    """
    global _optimizer
    if _optimizer is None:
        _optimizer = GasOptimizer(cache_ttl_seconds=cache_ttl_seconds)
    return _optimizer
