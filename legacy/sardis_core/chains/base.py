"""Abstract base class for blockchain implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class ChainType(str, Enum):
    """Supported blockchain networks."""
    BASE = "base"
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    SOLANA = "solana"


class TokenType(str, Enum):
    """Supported stablecoin tokens."""
    USDC = "USDC"
    USDT = "USDT"
    PYUSD = "PYUSD"
    EURC = "EURC"


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""
    chain_type: ChainType
    chain_id: Optional[int] = None  # For EVM chains
    rpc_url: Optional[str] = None
    explorer_url: Optional[str] = None
    is_testnet: bool = True
    
    # Token contract addresses per chain
    token_addresses: dict[TokenType, str] = field(default_factory=dict)
    
    # Gas settings
    default_gas_limit: int = 100000
    max_gas_price_gwei: int = 100


@dataclass
class OnChainTransaction:
    """Represents a transaction on a blockchain."""
    tx_hash: str
    chain: ChainType
    from_address: str
    to_address: str
    amount: Decimal
    token: TokenType
    status: str  # pending, confirmed, failed
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None
    confirmations: int = 0
    
    @property
    def explorer_link(self) -> Optional[str]:
        """Get block explorer link for this transaction."""
        explorers = {
            ChainType.BASE: "https://basescan.org/tx/",
            ChainType.ETHEREUM: "https://etherscan.io/tx/",
            ChainType.POLYGON: "https://polygonscan.com/tx/",
            ChainType.SOLANA: "https://solscan.io/tx/",
        }
        base_url = explorers.get(self.chain)
        return f"{base_url}{self.tx_hash}" if base_url else None


class BaseChain(ABC):
    """
    Abstract base class for blockchain implementations.
    
    This provides a unified interface for interacting with different
    blockchains, allowing the Sardis system to be chain-agnostic.
    """
    
    def __init__(self, config: ChainConfig):
        """
        Initialize the chain interface.
        
        Args:
            config: Chain-specific configuration
        """
        self.config = config
        self.chain_type = config.chain_type
    
    @abstractmethod
    async def get_balance(
        self,
        address: str,
        token: TokenType = TokenType.USDC
    ) -> Decimal:
        """
        Get token balance for an address.
        
        Args:
            address: Wallet address
            token: Token type to check
            
        Returns:
            Balance as Decimal
        """
        pass
    
    @abstractmethod
    async def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token: TokenType = TokenType.USDC,
        private_key: Optional[str] = None
    ) -> OnChainTransaction:
        """
        Execute a token transfer.
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to transfer
            token: Token type
            private_key: Private key for signing (in production, use MPC)
            
        Returns:
            Transaction details
        """
        pass
    
    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Optional[OnChainTransaction]:
        """
        Get transaction details by hash.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction details if found
        """
        pass
    
    @abstractmethod
    async def estimate_gas(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token: TokenType = TokenType.USDC
    ) -> Decimal:
        """
        Estimate gas cost for a transfer.
        
        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to transfer
            token: Token type
            
        Returns:
            Estimated gas cost in native token
        """
        pass
    
    @abstractmethod
    async def create_wallet(self) -> tuple[str, str]:
        """
        Create a new wallet on this chain.
        
        Returns:
            Tuple of (address, private_key)
            In production, private keys should be managed via MPC
        """
        pass
    
    @abstractmethod
    async def is_valid_address(self, address: str) -> bool:
        """
        Check if an address is valid for this chain.
        
        Args:
            address: Address to validate
            
        Returns:
            True if valid
        """
        pass
    
    @abstractmethod
    async def get_token_info(self, token: TokenType) -> dict:
        """
        Get token contract information.
        
        Args:
            token: Token type
            
        Returns:
            Dict with name, symbol, decimals, contract_address
        """
        pass
    
    def supports_token(self, token: TokenType) -> bool:
        """Check if this chain supports a token."""
        return token in self.config.token_addresses
    
    @property
    def supported_tokens(self) -> list[TokenType]:
        """Get list of supported tokens on this chain."""
        return list(self.config.token_addresses.keys())


# Default chain configurations
DEFAULT_CONFIGS = {
    ChainType.BASE: ChainConfig(
        chain_type=ChainType.BASE,
        chain_id=8453,  # Base mainnet
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        is_testnet=False,
        token_addresses={
            TokenType.USDC: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        }
    ),
    ChainType.ETHEREUM: ChainConfig(
        chain_type=ChainType.ETHEREUM,
        chain_id=1,
        rpc_url="https://eth.llamarpc.com",
        explorer_url="https://etherscan.io",
        is_testnet=False,
        token_addresses={
            TokenType.USDC: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            TokenType.USDT: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            TokenType.PYUSD: "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8",
        }
    ),
    ChainType.POLYGON: ChainConfig(
        chain_type=ChainType.POLYGON,
        chain_id=137,
        rpc_url="https://polygon-rpc.com",
        explorer_url="https://polygonscan.com",
        is_testnet=False,
        token_addresses={
            TokenType.USDC: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            TokenType.USDT: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
            TokenType.EURC: "0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6",
        }
    ),
    ChainType.SOLANA: ChainConfig(
        chain_type=ChainType.SOLANA,
        chain_id=None,  # Solana doesn't use chain IDs
        rpc_url="https://api.mainnet-beta.solana.com",
        explorer_url="https://solscan.io",
        is_testnet=False,
        token_addresses={
            TokenType.USDC: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            TokenType.USDT: "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            TokenType.PYUSD: "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",
        }
    ),
}

