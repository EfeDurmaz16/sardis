"""Token models and registry for stablecoin support."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class TokenType(str, Enum):
    """Supported stablecoin tokens."""
    USDC = "USDC"
    USDT = "USDT"
    PYUSD = "PYUSD"
    EURC = "EURC"


@dataclass
class TokenMetadata:
    """
    Metadata for a supported stablecoin token.
    
    Contains all the information needed to properly handle
    a token across different chains and use cases.
    """
    
    symbol: str
    name: str
    decimals: int
    issuer: str
    
    # Fiat peg (for price normalization)
    peg_currency: str = "USD"
    peg_ratio: Decimal = field(default_factory=lambda: Decimal("1.0"))
    
    # Chain-specific contract addresses
    # Maps ChainType -> contract address
    contract_addresses: dict[str, str] = field(default_factory=dict)
    
    # Minimum transfer amounts
    min_transfer_amount: Decimal = field(default_factory=lambda: Decimal("0.01"))
    
    # Whether token is active for new transactions
    is_active: bool = True
    
    def normalize_amount(self, raw_amount: int) -> Decimal:
        """
        Convert raw token amount (with decimals) to human-readable Decimal.
        
        Example: 1000000 (6 decimals) -> Decimal("1.0")
        """
        divisor = Decimal(10 ** self.decimals)
        return Decimal(raw_amount) / divisor
    
    def to_raw_amount(self, amount: Decimal) -> int:
        """
        Convert human-readable Decimal to raw token amount.
        
        Example: Decimal("1.0") (6 decimals) -> 1000000
        """
        multiplier = Decimal(10 ** self.decimals)
        return int(amount * multiplier)
    
    def to_usd(self, amount: Decimal) -> Decimal:
        """
        Convert token amount to USD equivalent.
        
        Note: For stablecoins pegged to USD, this is 1:1.
        For EUR-pegged tokens like EURC, uses peg_ratio.
        """
        if self.peg_currency == "USD":
            return amount
        return amount * self.peg_ratio


# Token Registry - Static metadata for all supported tokens
TOKEN_REGISTRY: dict[TokenType, TokenMetadata] = {
    TokenType.USDC: TokenMetadata(
        symbol="USDC",
        name="USD Coin",
        decimals=6,
        issuer="Circle",
        peg_currency="USD",
        contract_addresses={
            "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            "solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        },
    ),
    TokenType.USDT: TokenMetadata(
        symbol="USDT",
        name="Tether USD",
        decimals=6,
        issuer="Tether",
        peg_currency="USD",
        contract_addresses={
            "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
            "solana": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        },
    ),
    TokenType.PYUSD: TokenMetadata(
        symbol="PYUSD",
        name="PayPal USD",
        decimals=6,
        issuer="PayPal",
        peg_currency="USD",
        contract_addresses={
            "ethereum": "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8",
            "solana": "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",
        },
    ),
    TokenType.EURC: TokenMetadata(
        symbol="EURC",
        name="Euro Coin",
        decimals=6,
        issuer="Circle",
        peg_currency="EUR",
        peg_ratio=Decimal("1.08"),  # Approximate EUR/USD rate, updated dynamically in production
        contract_addresses={
            "polygon": "0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6",
        },
    ),
}


def get_token_metadata(token: TokenType) -> TokenMetadata:
    """Get metadata for a token type."""
    if token not in TOKEN_REGISTRY:
        raise ValueError(f"Unknown token type: {token}")
    return TOKEN_REGISTRY[token]


def get_supported_tokens() -> list[TokenType]:
    """Get list of all supported token types."""
    return list(TOKEN_REGISTRY.keys())


def get_active_tokens() -> list[TokenType]:
    """Get list of active tokens available for transactions."""
    return [t for t, meta in TOKEN_REGISTRY.items() if meta.is_active]


def get_tokens_for_chain(chain: str) -> list[TokenType]:
    """Get list of tokens available on a specific chain."""
    return [
        token_type
        for token_type, meta in TOKEN_REGISTRY.items()
        if chain in meta.contract_addresses and meta.is_active
    ]


def normalize_token_amount(token: TokenType, raw_amount: int) -> Decimal:
    """Utility to normalize a raw token amount."""
    return get_token_metadata(token).normalize_amount(raw_amount)


def to_raw_token_amount(token: TokenType, amount: Decimal) -> int:
    """Utility to convert Decimal to raw token amount."""
    return get_token_metadata(token).to_raw_amount(amount)

