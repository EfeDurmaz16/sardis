"""Wallet + token balance primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from .tokens import TokenType
from .virtual_card import VirtualCard


class TokenBalance(BaseModel):
    token: TokenType
    balance: Decimal = Field(default=Decimal("0.00"))
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None
    spent_total: Decimal = Field(default=Decimal("0.00"))

    def remaining_limit(self, wallet_limit_total: Decimal) -> Decimal:
        limit = self.limit_total or wallet_limit_total
        return max(Decimal("0.00"), limit - self.spent_total)


class Wallet(BaseModel):
    wallet_id: str
    agent_id: str
    balance: Decimal = Field(default=Decimal("0.00"))
    currency: str = Field(default="USDC")
    token_balances: dict[str, TokenBalance] = Field(default_factory=dict)
    limit_per_tx: Decimal = Field(default=Decimal("100.00"))
    limit_total: Decimal = Field(default=Decimal("1000.00"))
    spent_total: Decimal = Field(default=Decimal("0.00"))
    virtual_card: Optional[VirtualCard] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }

    @staticmethod
    def new(agent_id: str, *, currency: str = "USDC") -> "Wallet":
        from uuid import uuid4

        return Wallet(wallet_id=f"wallet_{uuid4().hex[:16]}", agent_id=agent_id, currency=currency)

    def get_token_balance(self, token: TokenType) -> Decimal:
        if token.value == self.currency:
            return self.balance
        token_data = self.token_balances.get(token.value)
        return token_data.balance if token_data else Decimal("0.00")

    def set_token_balance(self, token: TokenType, amount: Decimal) -> None:
        if token.value == self.currency:
            self.balance = amount
        else:
            if token.value not in self.token_balances:
                self.token_balances[token.value] = TokenBalance(token=token)
            self.token_balances[token.value].balance = amount
        self.updated_at = datetime.now(timezone.utc)

    def add_token_balance(self, token: TokenType, amount: Decimal) -> None:
        current = self.get_token_balance(token)
        self.set_token_balance(token, current + amount)

    def subtract_token_balance(self, token: TokenType, amount: Decimal) -> bool:
        current = self.get_token_balance(token)
        if current < amount:
            return False
        self.set_token_balance(token, current - amount)
        return True

    def remaining_limit(self, token: Optional[TokenType] = None) -> Decimal:
        if token and token.value in self.token_balances:
            return self.token_balances[token.value].remaining_limit(self.limit_total)
        return max(Decimal("0.00"), self.limit_total - self.spent_total)

    def get_limit_per_tx(self, token: Optional[TokenType] = None) -> Decimal:
        if token and token.value in self.token_balances:
            token_data = self.token_balances[token.value]
            if token_data.limit_per_tx is not None:
                return token_data.limit_per_tx
        return self.limit_per_tx

    def can_spend(self, amount: Decimal, fee: Decimal = Decimal("0.00"), token: Optional[TokenType] = None) -> tuple[bool, str]:
        if token is None:
            token = TokenType(self.currency)
        total_cost = amount + fee
        balance = self.get_token_balance(token)
        limit_per_tx = self.get_limit_per_tx(token)
        remaining = self.remaining_limit(token)
        if not self.is_active:
            return False, "wallet_inactive"
        if total_cost > balance:
            return False, "insufficient_balance"
        if amount > limit_per_tx:
            return False, "per_transaction_limit"
        if amount > remaining:
            return False, "total_limit_exceeded"
        return True, "OK"

    def record_spend(self, amount: Decimal, token: Optional[TokenType] = None) -> None:
        token = token or TokenType(self.currency)
        if token.value == self.currency:
            self.spent_total += amount
        else:
            entry = self.token_balances.setdefault(token.value, TokenBalance(token=token))
            entry.spent_total += amount
        self.updated_at = datetime.now(timezone.utc)

    def total_balance_usd(self) -> Decimal:
        total = self.balance
        for token_data in self.token_balances.values():
            total += token_data.balance
        return total


@dataclass(slots=True)
class WalletSnapshot:
    wallet_id: str
    balances: dict[str, Decimal]
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
