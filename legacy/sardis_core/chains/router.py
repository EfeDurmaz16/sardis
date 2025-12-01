"""Chain routing logic for optimal transaction execution."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import asyncio

from .base import BaseChain, ChainType, TokenType, OnChainTransaction, DEFAULT_CONFIGS
from .evm import EVMChain
from .solana import SolanaChain


@dataclass
class RouteOption:
    """A possible route for a transaction."""
    chain: ChainType
    token: TokenType
    estimated_fee: Decimal
    estimated_time_seconds: int
    is_available: bool
    reason: Optional[str] = None


@dataclass
class OptimalRoute:
    """The selected optimal route for a transaction."""
    chain: ChainType
    token: TokenType
    estimated_fee: Decimal
    estimated_time_seconds: int
    all_options: list[RouteOption]


class ChainRouter:
    """
    Intelligent routing engine for multi-chain transactions.
    
    Selects the optimal chain and token combination based on:
    - Transaction fees
    - Speed requirements
    - Liquidity availability
    - User preferences
    """
    
    # Estimated confirmation times in seconds
    CONFIRMATION_TIMES = {
        ChainType.SOLANA: 1,      # ~400ms finality
        ChainType.BASE: 2,        # L2 fast confirmations
        ChainType.POLYGON: 5,     # ~2 second blocks
        ChainType.ETHEREUM: 180,  # ~12 second blocks, wait for finality
    }
    
    # Priority order for chains (lower = preferred)
    CHAIN_PRIORITY = {
        ChainType.BASE: 1,      # Primary chain
        ChainType.SOLANA: 2,    # Fast and cheap
        ChainType.POLYGON: 3,   # EVM compatible
        ChainType.ETHEREUM: 4,  # Expensive, last resort
    }
    
    def __init__(self):
        """Initialize the chain router."""
        self._chains: dict[ChainType, BaseChain] = {}
        self._initialize_chains()
    
    def _initialize_chains(self):
        """Initialize all supported chains."""
        # Initialize EVM chains
        for chain_type in [ChainType.BASE, ChainType.ETHEREUM, ChainType.POLYGON]:
            config = DEFAULT_CONFIGS[chain_type]
            self._chains[chain_type] = EVMChain(config)
        
        # Initialize Solana
        self._chains[ChainType.SOLANA] = SolanaChain(DEFAULT_CONFIGS[ChainType.SOLANA])
    
    def get_chain(self, chain_type: ChainType) -> BaseChain:
        """Get a specific chain instance."""
        if chain_type not in self._chains:
            raise ValueError(f"Chain {chain_type} not initialized")
        return self._chains[chain_type]
    
    @property
    def supported_chains(self) -> list[ChainType]:
        """Get list of all supported chains."""
        return list(self._chains.keys())
    
    async def find_optimal_route(
        self,
        amount: Decimal,
        token: TokenType = TokenType.USDC,
        preferred_chain: Optional[ChainType] = None,
        max_fee: Optional[Decimal] = None,
        max_time_seconds: Optional[int] = None
    ) -> OptimalRoute:
        """
        Find the optimal route for a transaction.
        
        Args:
            amount: Transaction amount
            token: Preferred token type
            preferred_chain: User's preferred chain (if any)
            max_fee: Maximum acceptable fee
            max_time_seconds: Maximum acceptable confirmation time
            
        Returns:
            OptimalRoute with the best option and alternatives
        """
        options = await self._evaluate_all_routes(amount, token)
        
        # Filter by constraints
        valid_options = []
        for opt in options:
            if not opt.is_available:
                continue
            if max_fee and opt.estimated_fee > max_fee:
                continue
            if max_time_seconds and opt.estimated_time_seconds > max_time_seconds:
                continue
            valid_options.append(opt)
        
        if not valid_options:
            # Return best available even if it doesn't meet constraints
            valid_options = [o for o in options if o.is_available]
        
        if not valid_options:
            raise ValueError("No valid route found for this transaction")
        
        # Sort by priority
        def route_score(opt: RouteOption) -> tuple:
            # If user has preference, prioritize it
            preferred_bonus = 0 if opt.chain == preferred_chain else 1
            chain_priority = self.CHAIN_PRIORITY.get(opt.chain, 99)
            return (preferred_bonus, chain_priority, opt.estimated_fee)
        
        valid_options.sort(key=route_score)
        best = valid_options[0]
        
        return OptimalRoute(
            chain=best.chain,
            token=best.token,
            estimated_fee=best.estimated_fee,
            estimated_time_seconds=best.estimated_time_seconds,
            all_options=options
        )
    
    async def _evaluate_all_routes(
        self,
        amount: Decimal,
        token: TokenType
    ) -> list[RouteOption]:
        """Evaluate all possible routes for a transaction."""
        options = []
        
        for chain_type, chain in self._chains.items():
            # Check if chain supports the token
            if not chain.supports_token(token):
                options.append(RouteOption(
                    chain=chain_type,
                    token=token,
                    estimated_fee=Decimal("0"),
                    estimated_time_seconds=0,
                    is_available=False,
                    reason=f"Token {token} not supported on {chain_type}"
                ))
                continue
            
            try:
                # Estimate fee (use dummy addresses for estimation)
                dummy_from = "0x" + "0" * 40 if chain_type != ChainType.SOLANA else "1" * 44
                dummy_to = "0x" + "1" * 40 if chain_type != ChainType.SOLANA else "2" * 44
                
                fee = await chain.estimate_gas(dummy_from, dummy_to, amount, token)
                
                options.append(RouteOption(
                    chain=chain_type,
                    token=token,
                    estimated_fee=fee,
                    estimated_time_seconds=self.CONFIRMATION_TIMES.get(chain_type, 60),
                    is_available=True
                ))
            except Exception as e:
                options.append(RouteOption(
                    chain=chain_type,
                    token=token,
                    estimated_fee=Decimal("0"),
                    estimated_time_seconds=0,
                    is_available=False,
                    reason=str(e)
                ))
        
        return options
    
    async def execute_transfer(
        self,
        chain_type: ChainType,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token: TokenType = TokenType.USDC,
        private_key: Optional[str] = None
    ) -> OnChainTransaction:
        """
        Execute a transfer on a specific chain.
        
        Args:
            chain_type: Target blockchain
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to transfer
            token: Token type
            private_key: Private key for signing
            
        Returns:
            Transaction details
        """
        chain = self.get_chain(chain_type)
        return await chain.transfer(
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            token=token,
            private_key=private_key
        )
    
    async def get_balance(
        self,
        address: str,
        chain_type: ChainType,
        token: TokenType = TokenType.USDC
    ) -> Decimal:
        """Get token balance on a specific chain."""
        chain = self.get_chain(chain_type)
        return await chain.get_balance(address, token)
    
    async def get_all_balances(
        self,
        addresses: dict[ChainType, str]
    ) -> dict[ChainType, dict[TokenType, Decimal]]:
        """
        Get all token balances across multiple chains.
        
        Args:
            addresses: Dict mapping chain types to addresses
            
        Returns:
            Dict mapping chains to token balances
        """
        results = {}
        
        for chain_type, address in addresses.items():
            chain = self.get_chain(chain_type)
            chain_balances = {}
            
            for token in chain.supported_tokens:
                try:
                    balance = await chain.get_balance(address, token)
                    chain_balances[token] = balance
                except Exception:
                    chain_balances[token] = Decimal("0")
            
            results[chain_type] = chain_balances
        
        return results
    
    def get_token_availability(self, token: TokenType) -> dict[ChainType, bool]:
        """Check which chains support a specific token."""
        return {
            chain_type: chain.supports_token(token)
            for chain_type, chain in self._chains.items()
        }


# Global router instance
_router: Optional[ChainRouter] = None


def get_chain_router() -> ChainRouter:
    """Get the global chain router instance."""
    global _router
    if _router is None:
        _router = ChainRouter()
    return _router

