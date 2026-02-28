"""Stablecoin token metadata reused across Sardis services."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class TokenType(str, Enum):
    """Supported stablecoin tickers."""

    USDC = "USDC"
    USDT = "USDT"
    PYUSD = "PYUSD"
    EURC = "EURC"


@dataclass(slots=True)
class TokenMetadata:
    """Chain-aware token metadata."""

    symbol: str
    name: str
    decimals: int
    issuer: str
    peg_currency: str = "USD"
    peg_ratio: Decimal = field(default_factory=lambda: Decimal("1.0"))
    contract_addresses: dict[str, str] = field(default_factory=dict)
    min_transfer_amount: Decimal = field(default_factory=lambda: Decimal("0.01"))
    is_active: bool = True

    def normalize_amount(self, raw_amount: int) -> Decimal:
        divisor = Decimal(10**self.decimals)
        return Decimal(raw_amount) / divisor

    def to_raw_amount(self, amount: Decimal) -> int:
        multiplier = Decimal(10**self.decimals)
        return int(amount * multiplier)

    def to_usd(self, amount: Decimal) -> Decimal:
        if self.peg_currency == "USD":
            return amount
        return amount * self.peg_ratio


TOKEN_REGISTRY: dict[TokenType, TokenMetadata] = {
    TokenType.USDC: TokenMetadata(
        symbol="USDC",
        name="USD Coin",
        decimals=6,
        issuer="Circle",
        contract_addresses={
            "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
            "solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        },
    ),
    TokenType.USDT: TokenMetadata(
        symbol="USDT",
        name="Tether USD",
        decimals=6,
        issuer="Tether",
        contract_addresses={
            "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
            "arbitrum": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "optimism": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
            "solana": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        },
    ),
    TokenType.PYUSD: TokenMetadata(
        symbol="PYUSD",
        name="PayPal USD",
        decimals=6,
        issuer="PayPal",
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
        peg_ratio=Decimal("1.08"),
        contract_addresses={
            "base": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
            "ethereum": "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",
            "polygon": "0x9912af6da4F87Fc2b0Ae0B77A124e9B1B7Ba2F70",
        },
    ),
}


def get_token_metadata(token: TokenType) -> TokenMetadata:
    try:
        return TOKEN_REGISTRY[token]
    except KeyError as exc:
        raise ValueError(f"unknown token: {token}") from exc


def get_supported_tokens() -> list[TokenType]:
    return list(TOKEN_REGISTRY.keys())


def get_active_tokens() -> list[TokenType]:
    return [token for token, meta in TOKEN_REGISTRY.items() if meta.is_active]


def get_tokens_for_chain(chain: str) -> list[TokenType]:
    return [token for token, meta in TOKEN_REGISTRY.items() if chain in meta.contract_addresses and meta.is_active]


def normalize_token_amount(token: TokenType, raw_amount: int) -> Decimal:
    return get_token_metadata(token).normalize_amount(raw_amount)


def to_raw_token_amount(token: TokenType, amount: Decimal) -> int:
    return get_token_metadata(token).to_raw_amount(amount)
