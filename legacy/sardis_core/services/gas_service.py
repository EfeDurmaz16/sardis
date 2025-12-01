"""Gas Abstraction Service.

Enables agents to pay transaction fees in stablecoins (USDC)
while Sardis handles the actual native token gas payments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio


class GasStrategy(str, Enum):
    """Gas pricing strategy."""
    SLOW = "slow"       # Lower fee, longer confirmation
    STANDARD = "standard"  # Normal speed
    FAST = "fast"       # Higher fee, faster confirmation
    INSTANT = "instant"  # Maximum priority


@dataclass
class GasEstimate:
    """Estimated gas costs for a transaction."""
    gas_limit: int
    gas_price_gwei: Decimal
    max_fee_per_gas_gwei: Optional[Decimal]  # For EIP-1559
    max_priority_fee_gwei: Optional[Decimal]  # For EIP-1559
    estimated_cost_native: Decimal
    estimated_cost_usd: Decimal
    native_symbol: str
    chain_id: int
    strategy: GasStrategy
    is_eip1559: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GasTank:
    """Gas tank for a specific chain."""
    chain_id: int
    balance_native: Decimal  # Native token balance (ETH, MATIC, etc.)
    balance_usd: Decimal  # Estimated USD value
    native_symbol: str
    address: str  # Sardis relayer address for this chain
    last_refilled: Optional[datetime] = None
    total_spent_24h: Decimal = Decimal("0")
    transactions_24h: int = 0


@dataclass
class SponsoredTransaction:
    """Record of a gas-sponsored transaction."""
    sponsor_id: str
    agent_id: str
    chain_id: int
    tx_hash: str
    gas_used: int
    gas_price_gwei: Decimal
    cost_native: Decimal
    cost_usd: Decimal
    fee_charged_usdc: Decimal  # What we charged the agent
    profit_usd: Decimal  # Our margin
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GasService:
    """
    Service for gas abstraction and sponsorship.
    
    Enables:
    - Paying gas fees in USDC
    - Gas estimation across chains
    - Gas tank management for relayers
    - Dynamic pricing with margins
    """
    
    # Default gas margin (10%)
    GAS_MARGIN: Decimal = Decimal("0.10")
    
    # Mock native token prices (USD)
    NATIVE_PRICES: Dict[str, Decimal] = {
        "ETH": Decimal("3000"),
        "MATIC": Decimal("0.80"),
        "SOL": Decimal("150"),
    }
    
    # Mock gas prices by chain (in gwei for EVM)
    GAS_PRICES: Dict[int, Dict[GasStrategy, Decimal]] = {
        # Ethereum mainnet
        1: {
            GasStrategy.SLOW: Decimal("15"),
            GasStrategy.STANDARD: Decimal("25"),
            GasStrategy.FAST: Decimal("35"),
            GasStrategy.INSTANT: Decimal("50"),
        },
        # Base
        8453: {
            GasStrategy.SLOW: Decimal("0.001"),
            GasStrategy.STANDARD: Decimal("0.002"),
            GasStrategy.FAST: Decimal("0.003"),
            GasStrategy.INSTANT: Decimal("0.005"),
        },
        # Base Sepolia
        84532: {
            GasStrategy.SLOW: Decimal("0.001"),
            GasStrategy.STANDARD: Decimal("0.002"),
            GasStrategy.FAST: Decimal("0.003"),
            GasStrategy.INSTANT: Decimal("0.005"),
        },
        # Polygon
        137: {
            GasStrategy.SLOW: Decimal("30"),
            GasStrategy.STANDARD: Decimal("50"),
            GasStrategy.FAST: Decimal("75"),
            GasStrategy.INSTANT: Decimal("100"),
        },
        # Polygon Amoy
        80002: {
            GasStrategy.SLOW: Decimal("30"),
            GasStrategy.STANDARD: Decimal("50"),
            GasStrategy.FAST: Decimal("75"),
            GasStrategy.INSTANT: Decimal("100"),
        },
    }
    
    # Chain ID to native symbol
    CHAIN_NATIVE: Dict[int, str] = {
        1: "ETH",
        8453: "ETH",
        84532: "ETH",
        137: "MATIC",
        80002: "MATIC",
    }
    
    def __init__(self, margin: Optional[Decimal] = None):
        """
        Initialize gas service.
        
        Args:
            margin: Gas margin to charge (default 10%)
        """
        self.margin = margin or self.GAS_MARGIN
        self._gas_tanks: Dict[int, GasTank] = {}
        self._sponsored_txs: List[SponsoredTransaction] = []
        
        # Initialize mock gas tanks
        self._initialize_gas_tanks()
    
    def _initialize_gas_tanks(self):
        """Initialize gas tanks for each chain."""
        chains = [
            (1, "ETH", Decimal("10"), "0x" + "1" * 40),
            (8453, "ETH", Decimal("5"), "0x" + "2" * 40),
            (84532, "ETH", Decimal("1"), "0x" + "3" * 40),
            (137, "MATIC", Decimal("1000"), "0x" + "4" * 40),
            (80002, "MATIC", Decimal("100"), "0x" + "5" * 40),
        ]
        
        for chain_id, native, balance, address in chains:
            usd_value = balance * self.NATIVE_PRICES.get(native, Decimal("0"))
            self._gas_tanks[chain_id] = GasTank(
                chain_id=chain_id,
                balance_native=balance,
                balance_usd=usd_value,
                native_symbol=native,
                address=address,
            )
    
    async def estimate_gas(
        self,
        chain_id: int,
        gas_limit: int = 65000,
        strategy: GasStrategy = GasStrategy.STANDARD
    ) -> GasEstimate:
        """
        Estimate gas cost for a transaction.
        
        Args:
            chain_id: Target chain ID
            gas_limit: Estimated gas limit
            strategy: Gas pricing strategy
            
        Returns:
            GasEstimate with costs
        """
        if chain_id not in self.GAS_PRICES:
            raise ValueError(f"Unknown chain: {chain_id}")
        
        gas_price_gwei = self.GAS_PRICES[chain_id].get(
            strategy,
            self.GAS_PRICES[chain_id][GasStrategy.STANDARD]
        )
        
        native_symbol = self.CHAIN_NATIVE.get(chain_id, "ETH")
        native_price = self.NATIVE_PRICES.get(native_symbol, Decimal("0"))
        
        # Calculate cost in native token
        gas_price_eth = gas_price_gwei / Decimal("1000000000")  # gwei to ETH
        cost_native = Decimal(gas_limit) * gas_price_eth
        
        # Calculate USD cost
        cost_usd = cost_native * native_price
        
        return GasEstimate(
            gas_limit=gas_limit,
            gas_price_gwei=gas_price_gwei,
            max_fee_per_gas_gwei=gas_price_gwei * Decimal("1.5"),
            max_priority_fee_gwei=Decimal("1"),
            estimated_cost_native=cost_native,
            estimated_cost_usd=cost_usd,
            native_symbol=native_symbol,
            chain_id=chain_id,
            strategy=strategy,
            is_eip1559=True,
        )
    
    async def get_gas_cost_in_usdc(
        self,
        chain_id: int,
        gas_limit: int = 65000,
        strategy: GasStrategy = GasStrategy.STANDARD,
        include_margin: bool = True
    ) -> Decimal:
        """
        Get the USDC cost for gas.
        
        This is what agents will pay in USDC.
        
        Args:
            chain_id: Target chain
            gas_limit: Estimated gas
            strategy: Pricing strategy
            include_margin: Whether to include Sardis margin
            
        Returns:
            Cost in USDC
        """
        estimate = await self.estimate_gas(chain_id, gas_limit, strategy)
        
        usdc_cost = estimate.estimated_cost_usd
        
        if include_margin:
            usdc_cost = usdc_cost * (1 + self.margin)
        
        # Round up to 6 decimals (USDC precision)
        return usdc_cost.quantize(Decimal("0.000001"))
    
    def get_gas_tank(self, chain_id: int) -> Optional[GasTank]:
        """Get gas tank for a chain."""
        return self._gas_tanks.get(chain_id)
    
    def get_all_tanks(self) -> List[GasTank]:
        """Get all gas tanks."""
        return list(self._gas_tanks.values())
    
    def get_total_balance_usd(self) -> Decimal:
        """Get total gas tank balance in USD."""
        return sum(tank.balance_usd for tank in self._gas_tanks.values())
    
    async def sponsor_transaction(
        self,
        agent_id: str,
        chain_id: int,
        tx_hash: str,
        gas_used: int,
        gas_price_gwei: Decimal,
        usdc_charged: Decimal
    ) -> SponsoredTransaction:
        """
        Record a sponsored transaction.
        
        Args:
            agent_id: Agent who initiated the transaction
            chain_id: Chain where transaction executed
            tx_hash: Transaction hash
            gas_used: Actual gas used
            gas_price_gwei: Actual gas price paid
            usdc_charged: Amount charged to agent in USDC
            
        Returns:
            Sponsored transaction record
        """
        native_symbol = self.CHAIN_NATIVE.get(chain_id, "ETH")
        native_price = self.NATIVE_PRICES.get(native_symbol, Decimal("0"))
        
        # Calculate actual costs
        gas_price_native = gas_price_gwei / Decimal("1000000000")
        cost_native = Decimal(gas_used) * gas_price_native
        cost_usd = cost_native * native_price
        
        # Calculate profit
        profit = usdc_charged - cost_usd
        
        # Record transaction
        sponsored = SponsoredTransaction(
            sponsor_id=f"sponsor_{tx_hash[:16]}",
            agent_id=agent_id,
            chain_id=chain_id,
            tx_hash=tx_hash,
            gas_used=gas_used,
            gas_price_gwei=gas_price_gwei,
            cost_native=cost_native,
            cost_usd=cost_usd,
            fee_charged_usdc=usdc_charged,
            profit_usd=profit,
        )
        
        self._sponsored_txs.append(sponsored)
        
        # Update gas tank
        if chain_id in self._gas_tanks:
            tank = self._gas_tanks[chain_id]
            tank.balance_native -= cost_native
            tank.balance_usd = tank.balance_native * native_price
            tank.total_spent_24h += cost_usd
            tank.transactions_24h += 1
        
        return sponsored
    
    def get_sponsored_transactions(
        self,
        agent_id: Optional[str] = None,
        chain_id: Optional[int] = None,
        limit: int = 100
    ) -> List[SponsoredTransaction]:
        """Get sponsored transaction history."""
        txs = self._sponsored_txs
        
        if agent_id:
            txs = [t for t in txs if t.agent_id == agent_id]
        if chain_id:
            txs = [t for t in txs if t.chain_id == chain_id]
        
        return txs[-limit:]
    
    def get_total_profit(self) -> Decimal:
        """Get total profit from gas sponsorship."""
        return sum(tx.profit_usd for tx in self._sponsored_txs)
    
    async def refill_tank(
        self,
        chain_id: int,
        amount_native: Decimal
    ) -> bool:
        """
        Refill a gas tank.
        
        In production, this would trigger an actual transfer.
        
        Args:
            chain_id: Chain to refill
            amount_native: Amount in native token
            
        Returns:
            Success status
        """
        if chain_id not in self._gas_tanks:
            return False
        
        tank = self._gas_tanks[chain_id]
        native_price = self.NATIVE_PRICES.get(tank.native_symbol, Decimal("0"))
        
        tank.balance_native += amount_native
        tank.balance_usd = tank.balance_native * native_price
        tank.last_refilled = datetime.now(timezone.utc)
        
        return True
    
    def needs_refill(self, chain_id: int, threshold_usd: Decimal = Decimal("100")) -> bool:
        """Check if gas tank needs refill."""
        tank = self._gas_tanks.get(chain_id)
        if not tank:
            return False
        
        return tank.balance_usd < threshold_usd


# Singleton instance
_gas_service: Optional[GasService] = None


def get_gas_service() -> GasService:
    """Get or create the gas service singleton."""
    global _gas_service
    if _gas_service is None:
        _gas_service = GasService()
    return _gas_service

