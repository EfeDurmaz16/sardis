"""Wallet model with multi-token balance and spending limits."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid

from .virtual_card import VirtualCard


class TokenType(str, Enum):
    """Supported stablecoin tokens."""
    USDC = "USDC"
    USDT = "USDT"
    PYUSD = "PYUSD"
    EURC = "EURC"


class TokenBalance(BaseModel):
    """Balance for a specific token."""
    token: TokenType
    balance: Decimal = Field(default=Decimal("0.00"))
    
    # Token-specific limits (optional, falls back to wallet defaults)
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None
    spent_total: Decimal = Field(default=Decimal("0.00"))
    
    def remaining_limit(self, wallet_limit_total: Decimal) -> Decimal:
        """Get remaining spend limit for this token."""
        limit = self.limit_total or wallet_limit_total
        return max(Decimal("0.00"), limit - self.spent_total)


class Wallet(BaseModel):
    """
    Agent wallet with multi-token balance tracking and spending limits.
    
    Each agent has exactly one wallet that can hold multiple stablecoin
    balances and enforces spending constraints per token and globally.
    """
    
    wallet_id: str = Field(default_factory=lambda: f"wallet_{uuid.uuid4().hex[:16]}")
    agent_id: str
    
    # Primary token and balance (backward compatible)
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="USDC")
    
    # Multi-token balances
    token_balances: dict[str, TokenBalance] = Field(default_factory=dict)
    
    # Global spending limits (per token can override)
    limit_per_tx: Decimal = Field(default=Decimal("100.00"))
    limit_total: Decimal = Field(default=Decimal("1000.00"))
    spent_total: Decimal = Field(default=Decimal("0.00"))
    
    # Virtual card for payment identity
    virtual_card: Optional[VirtualCard] = None
    
    # Metadata
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_token_balance(self, token: TokenType) -> Decimal:
        """Get balance for a specific token."""
        if token.value == self.currency:
            return self.balance
        
        token_data = self.token_balances.get(token.value)
        return token_data.balance if token_data else Decimal("0.00")

    def get_balance(self, currency: str) -> Decimal:
        """Get balance for a specific currency string."""
        return self.get_token_balance(TokenType(currency))
    
    def set_token_balance(self, token: TokenType, amount: Decimal):
        """Set balance for a specific token."""
        if token.value == self.currency:
            self.balance = amount
        else:
            if token.value not in self.token_balances:
                self.token_balances[token.value] = TokenBalance(token=token)
            self.token_balances[token.value].balance = amount
        self.updated_at = datetime.now(timezone.utc)
    
    def add_token_balance(self, token: TokenType, amount: Decimal):
        """Add to balance for a specific token."""
        current = self.get_token_balance(token)
        self.set_token_balance(token, current + amount)
    
    def subtract_token_balance(self, token: TokenType, amount: Decimal) -> bool:
        """Subtract from balance for a specific token. Returns False if insufficient."""
        current = self.get_token_balance(token)
        if current < amount:
            return False
        self.set_token_balance(token, current - amount)
        return True
    
    def get_all_balances(self) -> dict[TokenType, Decimal]:
        """Get all token balances."""
        balances = {TokenType(self.currency): self.balance}
        for token_str, token_data in self.token_balances.items():
            balances[TokenType(token_str)] = token_data.balance
        return balances
    
    def remaining_balance(self, token: Optional[TokenType] = None) -> Decimal:
        """Get the current available balance for a token."""
        if token is None:
            token = TokenType(self.currency)
        return self.get_token_balance(token)
    
    def remaining_limit(self, token: Optional[TokenType] = None) -> Decimal:
        """Get remaining spend limit before hitting total cap."""
        if token and token.value in self.token_balances:
            token_data = self.token_balances[token.value]
            return token_data.remaining_limit(self.limit_total)
        return max(Decimal("0.00"), self.limit_total - self.spent_total)
    
    def get_limit_per_tx(self, token: Optional[TokenType] = None) -> Decimal:
        """Get per-transaction limit for a token."""
        if token and token.value in self.token_balances:
            token_data = self.token_balances[token.value]
            if token_data.limit_per_tx is not None:
                return token_data.limit_per_tx
        return self.limit_per_tx
    
    def can_spend(
        self,
        amount: Decimal,
        fee: Decimal = Decimal("0.00"),
        token: Optional[TokenType] = None
    ) -> tuple[bool, str]:
        """
        Check if a transaction of given amount (plus fee) is allowed.
        
        Args:
            amount: Amount to spend
            fee: Transaction fee
            token: Token type (defaults to primary currency)
        
        Returns:
            Tuple of (allowed, reason)
        """
        if token is None:
            token = TokenType(self.currency)
        
        total_cost = amount + fee
        balance = self.get_token_balance(token)
        limit_per_tx = self.get_limit_per_tx(token)
        remaining = self.remaining_limit(token)
        
        if not self.is_active:
            return False, "Wallet is inactive"
        
        if total_cost > balance:
            return False, f"Insufficient balance ({token.value}): have {balance}, need {total_cost}"
        
        if amount > limit_per_tx:
            return False, f"Amount {amount} exceeds per-transaction limit of {limit_per_tx}"
        
        if amount > remaining:
            return False, f"Amount {amount} exceeds remaining spending limit of {remaining}"
        
        return True, "OK"
    
    def record_spend(self, amount: Decimal, token: Optional[TokenType] = None):
        """Record a spend against limits."""
        if token is None:
            token = TokenType(self.currency)
        
        if token.value == self.currency:
            self.spent_total += amount
        elif token.value in self.token_balances:
            self.token_balances[token.value].spent_total += amount
        else:
            self.token_balances[token.value] = TokenBalance(
                token=token,
                spent_total=amount
            )
        
        self.updated_at = datetime.now(timezone.utc)
    
    def total_balance_usd(self) -> Decimal:
        """
        Get total balance across all tokens in USD equivalent.
        
        Note: Assumes all stablecoins are 1:1 with USD for simplicity.
        In production, use real-time price feeds.
        """
        total = self.balance
        for token_data in self.token_balances.values():
            total += token_data.balance
        return total
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }


# Token metadata
TOKEN_INFO = {
    TokenType.USDC: {
        "name": "USD Coin",
        "symbol": "USDC",
        "decimals": 6,
        "issuer": "Circle",
    },
    TokenType.USDT: {
        "name": "Tether USD",
        "symbol": "USDT",
        "decimals": 6,
        "issuer": "Tether",
    },
    TokenType.PYUSD: {
        "name": "PayPal USD",
        "symbol": "PYUSD",
        "decimals": 6,
        "issuer": "PayPal",
    },
    TokenType.EURC: {
        "name": "Euro Coin",
        "symbol": "EURC",
        "decimals": 6,
        "issuer": "Circle",
    },
}
