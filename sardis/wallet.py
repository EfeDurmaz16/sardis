"""
Programmable wallet for AI agents.

Wallets hold stablecoin balances and enforce spending limits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4


@dataclass
class Wallet:
    """
    A programmable wallet for an AI agent.
    
    Example:
        >>> wallet = Wallet(initial_balance=100)
        >>> wallet.can_spend(25)
        True
        >>> wallet.spend(25)
        True
        >>> print(wallet.balance)
        75.00
    """
    
    wallet_id: str = field(default_factory=lambda: f"wallet_{uuid4().hex[:12]}")
    agent_id: Optional[str] = None
    balance: Decimal = field(default_factory=lambda: Decimal("0.00"))
    currency: str = "USDC"
    limit_per_tx: Decimal = field(default_factory=lambda: Decimal("100.00"))
    limit_total: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    spent_total: Decimal = field(default_factory=lambda: Decimal("0.00"))
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(
        self,
        initial_balance: float | Decimal = 0,
        *,
        currency: str = "USDC",
        limit_per_tx: float | Decimal = 100,
        limit_total: float | Decimal = 1000,
        agent_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
    ):
        """
        Create a new wallet.
        
        Args:
            initial_balance: Starting balance (default: 0)
            currency: Token type (default: USDC)
            limit_per_tx: Maximum per transaction (default: 100)
            limit_total: Maximum total spending (default: 1000)
            agent_id: Optional agent identifier
            wallet_id: Optional wallet ID (auto-generated if not provided)
        """
        self.wallet_id = wallet_id or f"wallet_{uuid4().hex[:12]}"
        self.agent_id = agent_id
        self.balance = Decimal(str(initial_balance))
        self.currency = currency
        self.limit_per_tx = Decimal(str(limit_per_tx))
        self.limit_total = Decimal(str(limit_total))
        self.spent_total = Decimal("0.00")
        self.is_active = True
        self.created_at = datetime.now(timezone.utc)
    
    def can_spend(self, amount: float | Decimal) -> bool:
        """Check if wallet can spend the given amount."""
        amount = Decimal(str(amount))
        
        if not self.is_active:
            return False
        if amount > self.balance:
            return False
        if amount > self.limit_per_tx:
            return False
        if self.spent_total + amount > self.limit_total:
            return False
        
        return True
    
    def spend(self, amount: float | Decimal) -> bool:
        """
        Deduct amount from wallet.
        
        Returns True if successful, False if insufficient funds or limits exceeded.
        """
        amount = Decimal(str(amount))
        
        if not self.can_spend(amount):
            return False
        
        self.balance -= amount
        self.spent_total += amount
        return True
    
    def deposit(self, amount: float | Decimal) -> None:
        """Add funds to wallet."""
        self.balance += Decimal(str(amount))
    
    def remaining_limit(self) -> Decimal:
        """Get remaining spending limit."""
        return max(Decimal("0.00"), self.limit_total - self.spent_total)
    
    def __repr__(self) -> str:
        return f"Wallet({self.wallet_id}, balance={self.balance} {self.currency})"
