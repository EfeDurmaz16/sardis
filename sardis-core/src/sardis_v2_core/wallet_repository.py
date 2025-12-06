"""Wallet repository for CRUD operations."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from .wallets import Wallet
from .tokens import TokenType


class WalletRepository:
    """In-memory wallet repository (swap for PostgreSQL in production)."""

    def __init__(self, dsn: str = "memory://"):
        self._dsn = dsn
        self._wallets: dict[str, Wallet] = {}

    async def create(
        self,
        agent_id: str,
        currency: str = "USDC",
        balance: Decimal = Decimal("0.00"),
        limit_per_tx: Decimal = Decimal("100.00"),
        limit_total: Decimal = Decimal("1000.00"),
    ) -> Wallet:
        wallet = Wallet.new(agent_id, currency=currency)
        wallet.balance = balance
        wallet.limit_per_tx = limit_per_tx
        wallet.limit_total = limit_total
        self._wallets[wallet.wallet_id] = wallet
        return wallet

    async def get(self, wallet_id: str) -> Optional[Wallet]:
        return self._wallets.get(wallet_id)

    async def get_by_agent(self, agent_id: str) -> Optional[Wallet]:
        for wallet in self._wallets.values():
            if wallet.agent_id == agent_id:
                return wallet
        return None

    async def list(
        self,
        agent_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Wallet]:
        wallets = list(self._wallets.values())
        if agent_id:
            wallets = [w for w in wallets if w.agent_id == agent_id]
        if is_active is not None:
            wallets = [w for w in wallets if w.is_active == is_active]
        return wallets[offset : offset + limit]

    async def update(
        self,
        wallet_id: str,
        balance: Optional[Decimal] = None,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Wallet]:
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        if balance is not None:
            wallet.balance = balance
        if limit_per_tx is not None:
            wallet.limit_per_tx = limit_per_tx
        if limit_total is not None:
            wallet.limit_total = limit_total
        if is_active is not None:
            wallet.is_active = is_active
        wallet.updated_at = datetime.now(timezone.utc)
        return wallet

    async def delete(self, wallet_id: str) -> bool:
        if wallet_id in self._wallets:
            del self._wallets[wallet_id]
            return True
        return False

    async def deposit(self, wallet_id: str, amount: Decimal, token: Optional[str] = None) -> Optional[Wallet]:
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        if token and token != wallet.currency:
            wallet.add_token_balance(TokenType(token), amount)
        else:
            wallet.balance += amount
        wallet.updated_at = datetime.now(timezone.utc)
        return wallet

    async def withdraw(self, wallet_id: str, amount: Decimal, token: Optional[str] = None) -> Optional[Wallet]:
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        if token and token != wallet.currency:
            if not wallet.subtract_token_balance(TokenType(token), amount):
                return None
        else:
            if wallet.balance < amount:
                return None
            wallet.balance -= amount
        wallet.updated_at = datetime.now(timezone.utc)
        return wallet

    async def set_limits(
        self,
        wallet_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
    ) -> Optional[Wallet]:
        return await self.update(
            wallet_id,
            limit_per_tx=limit_per_tx,
            limit_total=limit_total,
        )
