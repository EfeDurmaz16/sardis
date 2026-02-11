"""
Gas cost price oracle for native token → USD conversion.

Provides live pricing via CoinGecko (free tier, no API key) with
multi-layer fallback: live API → env var → hardcoded defaults.

Supports ETH, MATIC, and other native tokens used for gas across
supported chains.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# CoinGecko IDs for native gas tokens
COINGECKO_IDS: Dict[str, str] = {
    "ETH": "ethereum",
    "MATIC": "matic-network",
    "POL": "matic-network",
}

# Environment variable overrides (takes precedence over live pricing)
ENV_PRICE_KEYS: Dict[str, str] = {
    "ETH": "ETH_PRICE_USD",
    "MATIC": "MATIC_PRICE_USD",
    "POL": "MATIC_PRICE_USD",
}

# Chain → native gas token mapping
CHAIN_NATIVE_TOKEN: Dict[str, str] = {
    "ethereum": "ETH",
    "base": "ETH",
    "arbitrum": "ETH",
    "optimism": "ETH",
    "polygon": "MATIC",
    # Testnets
    "base-sepolia": "ETH",
    "sepolia": "ETH",
    "goerli": "ETH",
    "mumbai": "MATIC",
    "amoy": "MATIC",
}

# Last-resort hardcoded fallbacks (conservative estimates)
FALLBACK_PRICES: Dict[str, Decimal] = {
    "ETH": Decimal("2000"),
    "MATIC": Decimal("0.50"),
    "POL": Decimal("0.50"),
}

# Cache TTL in seconds
DEFAULT_CACHE_TTL = 300  # 5 minutes


@dataclass
class PriceEntry:
    """Cached price entry."""
    price_usd: Decimal
    fetched_at: float
    source: str  # "live", "env", "fallback"


class PriceOracle:
    """
    Multi-source gas token price oracle.

    Resolution order:
    1. Environment variable override (ETH_PRICE_USD, etc.)
    2. Live API (CoinGecko free tier)
    3. Cached previous value (if API fails)
    4. Hardcoded fallback

    Thread-safe via asyncio lock. Prices are cached with configurable TTL.
    """

    def __init__(self, cache_ttl: float = DEFAULT_CACHE_TTL):
        self._cache: Dict[str, PriceEntry] = {}
        self._cache_ttl = cache_ttl
        self._lock = asyncio.Lock()

    async def get_price_usd(self, token: str) -> Decimal:
        """
        Get current USD price for a native gas token.

        Args:
            token: Token symbol (ETH, MATIC, etc.)

        Returns:
            USD price as Decimal
        """
        token = token.upper()

        # 1. Check env var override
        env_key = ENV_PRICE_KEYS.get(token)
        if env_key:
            env_val = os.getenv(env_key)
            if env_val:
                try:
                    price = Decimal(env_val)
                    self._cache[token] = PriceEntry(
                        price_usd=price,
                        fetched_at=time.monotonic(),
                        source="env",
                    )
                    return price
                except Exception:
                    pass

        # 2. Check cache
        cached = self._cache.get(token)
        if cached and (time.monotonic() - cached.fetched_at) < self._cache_ttl:
            return cached.price_usd

        # 3. Try live API
        async with self._lock:
            # Double-check cache after acquiring lock
            cached = self._cache.get(token)
            if cached and (time.monotonic() - cached.fetched_at) < self._cache_ttl:
                return cached.price_usd

            live_price = await self._fetch_live_price(token)
            if live_price is not None:
                self._cache[token] = PriceEntry(
                    price_usd=live_price,
                    fetched_at=time.monotonic(),
                    source="live",
                )
                return live_price

        # 4. Return stale cache if available
        if cached:
            logger.warning(
                f"Using stale cached price for {token}: ${cached.price_usd} "
                f"(source={cached.source})"
            )
            return cached.price_usd

        # 5. Hardcoded fallback
        fallback = FALLBACK_PRICES.get(token, Decimal("2000"))
        logger.warning(
            f"Using hardcoded fallback price for {token}: ${fallback}. "
            f"Set {ENV_PRICE_KEYS.get(token, token + '_PRICE_USD')} for accuracy."
        )
        self._cache[token] = PriceEntry(
            price_usd=fallback,
            fetched_at=time.monotonic(),
            source="fallback",
        )
        return fallback

    async def get_gas_cost_usd(
        self,
        chain: str,
        gas_cost_wei: int,
    ) -> Decimal:
        """
        Convert gas cost in wei to USD.

        Args:
            chain: Chain name (ethereum, base, polygon, etc.)
            gas_cost_wei: Gas cost in wei (native token smallest unit)

        Returns:
            Estimated USD cost
        """
        token = CHAIN_NATIVE_TOKEN.get(chain, "ETH")
        price = await self.get_price_usd(token)
        cost_native = Decimal(gas_cost_wei) / Decimal(10**18)
        return cost_native * price

    async def _fetch_live_price(self, token: str) -> Optional[Decimal]:
        """Fetch live price from CoinGecko free API."""
        coingecko_id = COINGECKO_IDS.get(token)
        if not coingecko_id:
            return None

        try:
            import aiohttp

            url = (
                f"https://api.coingecko.com/api/v3/simple/price"
                f"?ids={coingecko_id}&vs_currencies=usd"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = data.get(coingecko_id, {}).get("usd")
                        if price is not None:
                            logger.debug(f"Live price for {token}: ${price}")
                            return Decimal(str(price))
                    else:
                        logger.debug(f"CoinGecko returned {resp.status} for {token}")
        except ImportError:
            logger.debug("aiohttp not available, skipping live price fetch")
        except Exception as e:
            logger.debug(f"Failed to fetch live price for {token}: {e}")

        return None

    def get_cached_price(self, token: str) -> Optional[PriceEntry]:
        """Get cached price info (for diagnostics)."""
        return self._cache.get(token.upper())


# Global singleton
_oracle: Optional[PriceOracle] = None


def get_price_oracle() -> PriceOracle:
    """Get or create the global price oracle."""
    global _oracle
    if _oracle is None:
        _oracle = PriceOracle()
    return _oracle
