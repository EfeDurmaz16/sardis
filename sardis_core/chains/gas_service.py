"""
Gas abstraction service.

Provides:
- Gas funding pool management per chain
- Agents pay in stablecoins, Sardis pays gas
- Automatic pool refill from treasury
- Fallback logic for gas price spikes
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import threading

from .base import ChainType


class GasPriceLevel(str, Enum):
    """Gas price levels for estimation."""
    LOW = "low"         # Slower, cheaper
    MEDIUM = "medium"   # Standard
    HIGH = "high"       # Faster, more expensive
    URGENT = "urgent"   # As fast as possible


@dataclass
class GasEstimate:
    """Gas cost estimate for a transaction."""
    
    chain: ChainType
    gas_units: int
    
    # Gas prices by priority level
    low_gwei: Decimal
    medium_gwei: Decimal
    high_gwei: Decimal
    
    # Cost in native token
    low_cost_native: Decimal
    medium_cost_native: Decimal
    high_cost_native: Decimal
    
    # Cost in USD (for stablecoin deduction)
    low_cost_usd: Decimal
    medium_cost_usd: Decimal
    high_cost_usd: Decimal
    
    # Recommended level
    recommended: GasPriceLevel = GasPriceLevel.MEDIUM
    
    estimated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_cost_usd(self, level: GasPriceLevel = GasPriceLevel.MEDIUM) -> Decimal:
        """Get USD cost for a price level."""
        costs = {
            GasPriceLevel.LOW: self.low_cost_usd,
            GasPriceLevel.MEDIUM: self.medium_cost_usd,
            GasPriceLevel.HIGH: self.high_cost_usd,
            GasPriceLevel.URGENT: self.high_cost_usd * Decimal("1.5"),
        }
        return costs.get(level, self.medium_cost_usd)


@dataclass
class FundingPool:
    """Native token funding pool for a chain."""
    
    chain: ChainType
    
    # Pool balance in native token
    balance: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Thresholds
    min_balance: Decimal = field(default_factory=lambda: Decimal("0.1"))
    target_balance: Decimal = field(default_factory=lambda: Decimal("1.0"))
    
    # Statistics
    total_funded: Decimal = field(default_factory=lambda: Decimal("0"))
    total_used: Decimal = field(default_factory=lambda: Decimal("0"))
    transactions_covered: int = 0
    
    # Last refill
    last_refill_at: Optional[datetime] = None
    refill_count: int = 0
    
    def needs_refill(self) -> bool:
        """Check if pool needs refilling."""
        return self.balance < self.min_balance
    
    def use(self, amount: Decimal) -> bool:
        """
        Use funds from the pool.
        
        Returns True if successful, False if insufficient funds.
        """
        if amount > self.balance:
            return False
        
        self.balance -= amount
        self.total_used += amount
        self.transactions_covered += 1
        return True
    
    def refill(self, amount: Decimal):
        """Add funds to the pool."""
        self.balance += amount
        self.total_funded += amount
        self.last_refill_at = datetime.now(timezone.utc)
        self.refill_count += 1


@dataclass
class GasServiceConfig:
    """Configuration for gas service."""
    
    # Default gas limits by transaction type
    default_gas_limits: dict = field(default_factory=lambda: {
        "transfer": 65000,
        "token_transfer": 100000,
        "multi_transfer": 200000,
        "contract_call": 150000,
    })
    
    # Price markup for safety margin
    price_buffer_percent: float = 20.0
    
    # Maximum gas price we're willing to pay (in USD)
    max_gas_price_usd: Decimal = field(default_factory=lambda: Decimal("10.00"))
    
    # Pool refill thresholds
    pool_min_balance_eth: Decimal = field(default_factory=lambda: Decimal("0.05"))
    pool_target_balance_eth: Decimal = field(default_factory=lambda: Decimal("0.5"))
    
    # Native token prices (would come from oracle in production)
    native_token_prices_usd: dict = field(default_factory=lambda: {
        "ETH": Decimal("2000.00"),
        "SOL": Decimal("100.00"),
        "MATIC": Decimal("0.80"),
    })


class GasService:
    """
    Service for gas abstraction.
    
    Hides blockchain gas complexity from agents:
    - Estimates gas costs in USD
    - Manages native token funding pools
    - Handles gas price spikes with fallback logic
    - Agents pay in stablecoins, Sardis covers gas
    """
    
    def __init__(self, config: Optional[GasServiceConfig] = None):
        """Initialize the gas service."""
        self.config = config or GasServiceConfig()
        self._lock = threading.RLock()
        
        # Funding pools per chain
        self._pools: dict[ChainType, FundingPool] = {}
        
        # Initialize pools for supported chains
        for chain in [ChainType.BASE, ChainType.ETHEREUM, ChainType.POLYGON]:
            self._pools[chain] = FundingPool(
                chain=chain,
                min_balance=self.config.pool_min_balance_eth,
                target_balance=self.config.pool_target_balance_eth,
            )
        
        # Separate config for Solana
        self._pools[ChainType.SOLANA] = FundingPool(
            chain=ChainType.SOLANA,
            min_balance=Decimal("0.5"),  # SOL
            target_balance=Decimal("5.0"),
        )
    
    # ==================== Gas Estimation ====================
    
    def estimate_gas(
        self,
        chain: ChainType,
        tx_type: str = "token_transfer"
    ) -> GasEstimate:
        """
        Estimate gas costs for a transaction.
        
        Args:
            chain: Target blockchain
            tx_type: Type of transaction
            
        Returns:
            GasEstimate with costs in USD
        """
        gas_units = self.config.default_gas_limits.get(tx_type, 100000)
        
        # Get base gas prices per chain (would be from RPC in production)
        base_prices = self._get_chain_gas_prices(chain)
        
        # Get native token price
        native_token = self._get_native_token(chain)
        native_price_usd = self.config.native_token_prices_usd.get(
            native_token, Decimal("1.0")
        )
        
        # Calculate costs
        def calc_cost(gwei: Decimal) -> tuple[Decimal, Decimal]:
            cost_native = (gwei * Decimal(gas_units)) / Decimal("1e9")
            cost_usd = cost_native * native_price_usd
            return cost_native, cost_usd
        
        low_native, low_usd = calc_cost(base_prices["low"])
        med_native, med_usd = calc_cost(base_prices["medium"])
        high_native, high_usd = calc_cost(base_prices["high"])
        
        # Determine recommended level
        recommended = GasPriceLevel.MEDIUM
        if high_usd > self.config.max_gas_price_usd:
            recommended = GasPriceLevel.LOW
        
        return GasEstimate(
            chain=chain,
            gas_units=gas_units,
            low_gwei=base_prices["low"],
            medium_gwei=base_prices["medium"],
            high_gwei=base_prices["high"],
            low_cost_native=low_native,
            medium_cost_native=med_native,
            high_cost_native=high_native,
            low_cost_usd=low_usd,
            medium_cost_usd=med_usd,
            high_cost_usd=high_usd,
            recommended=recommended,
        )
    
    def _get_chain_gas_prices(self, chain: ChainType) -> dict:
        """Get gas prices for a chain (simulated)."""
        # In production, this would query the chain's RPC
        prices = {
            ChainType.BASE: {"low": Decimal("0.001"), "medium": Decimal("0.005"), "high": Decimal("0.01")},
            ChainType.ETHEREUM: {"low": Decimal("10"), "medium": Decimal("20"), "high": Decimal("50")},
            ChainType.POLYGON: {"low": Decimal("30"), "medium": Decimal("50"), "high": Decimal("100")},
            ChainType.SOLANA: {"low": Decimal("0.000005"), "medium": Decimal("0.00001"), "high": Decimal("0.00005")},
        }
        return prices.get(chain, {"low": Decimal("10"), "medium": Decimal("20"), "high": Decimal("50")})
    
    def _get_native_token(self, chain: ChainType) -> str:
        """Get native token symbol for a chain."""
        tokens = {
            ChainType.BASE: "ETH",
            ChainType.ETHEREUM: "ETH",
            ChainType.POLYGON: "MATIC",
            ChainType.SOLANA: "SOL",
        }
        return tokens.get(chain, "ETH")
    
    # ==================== Pool Management ====================
    
    def get_pool(self, chain: ChainType) -> Optional[FundingPool]:
        """Get the funding pool for a chain."""
        return self._pools.get(chain)
    
    def fund_pool(self, chain: ChainType, amount: Decimal):
        """Add funds to a chain's pool."""
        with self._lock:
            pool = self._pools.get(chain)
            if pool:
                pool.refill(amount)
    
    def use_from_pool(
        self,
        chain: ChainType,
        amount: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        Use funds from pool to cover gas.
        
        Returns (success, error_message).
        """
        with self._lock:
            pool = self._pools.get(chain)
            if not pool:
                return False, f"No funding pool for {chain.value}"
            
            if pool.use(amount):
                return True, None
            else:
                return False, f"Insufficient funds in {chain.value} pool"
    
    def check_pools(self) -> dict[ChainType, dict]:
        """Check status of all funding pools."""
        status = {}
        for chain, pool in self._pools.items():
            status[chain] = {
                "balance": str(pool.balance),
                "min_balance": str(pool.min_balance),
                "needs_refill": pool.needs_refill(),
                "transactions_covered": pool.transactions_covered,
                "total_used": str(pool.total_used),
            }
        return status
    
    def get_pools_needing_refill(self) -> list[ChainType]:
        """Get list of pools that need refilling."""
        return [chain for chain, pool in self._pools.items() if pool.needs_refill()]
    
    # ==================== Gas Payment Abstraction ====================
    
    def calculate_gas_fee_usd(
        self,
        chain: ChainType,
        tx_type: str = "token_transfer",
        priority: GasPriceLevel = GasPriceLevel.MEDIUM
    ) -> Decimal:
        """
        Calculate gas fee to charge agent in USD.
        
        This is what the agent pays in stablecoins.
        Sardis covers the actual native token gas.
        """
        estimate = self.estimate_gas(chain, tx_type)
        base_cost = estimate.get_cost_usd(priority)
        
        # Add buffer for price fluctuations
        buffer = Decimal(str(1 + self.config.price_buffer_percent / 100))
        return (base_cost * buffer).quantize(Decimal("0.01"))
    
    def should_use_fallback(self, chain: ChainType) -> tuple[bool, str]:
        """
        Check if we should use fallback logic for this chain.
        
        Returns (should_fallback, reason).
        """
        estimate = self.estimate_gas(chain)
        
        # Check if gas prices are too high
        if estimate.medium_cost_usd > self.config.max_gas_price_usd:
            return True, f"Gas price ${estimate.medium_cost_usd} exceeds max ${self.config.max_gas_price_usd}"
        
        # Check if pool is low
        pool = self._pools.get(chain)
        if pool and pool.needs_refill():
            return True, f"Funding pool needs refill"
        
        return False, ""
    
    def get_fallback_chain(self, preferred: ChainType) -> Optional[ChainType]:
        """
        Get a fallback chain if the preferred chain is unavailable.
        
        Priority: Base > Polygon > Solana
        """
        fallback_order = [ChainType.BASE, ChainType.POLYGON, ChainType.SOLANA]
        
        for chain in fallback_order:
            if chain == preferred:
                continue
            
            should_skip, _ = self.should_use_fallback(chain)
            if not should_skip:
                return chain
        
        return None


# Global gas service instance
_gas_service: Optional[GasService] = None


def get_gas_service() -> GasService:
    """Get the global gas service instance."""
    global _gas_service
    if _gas_service is None:
        _gas_service = GasService()
    return _gas_service

