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
        mpc_provider: str = "turnkey",
        currency: str = "USDC",
        limit_per_tx: Decimal = Decimal("100.00"),
        limit_total: Decimal = Decimal("1000.00"),
    ) -> Wallet:
        """Create a new non-custodial wallet."""
        wallet = Wallet.new(agent_id, mpc_provider=mpc_provider, currency=currency)
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
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        addresses: Optional[dict[str, str]] = None,
    ) -> Optional[Wallet]:
        """Update wallet (non-custodial - no balance updates)."""
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        if limit_per_tx is not None:
            wallet.limit_per_tx = limit_per_tx
        if limit_total is not None:
            wallet.limit_total = limit_total
        if is_active is not None:
            wallet.is_active = is_active
        if addresses is not None:
            wallet.addresses.update(addresses)
        wallet.updated_at = datetime.now(timezone.utc)
        return wallet
    
    async def set_address(
        self,
        wallet_id: str,
        chain: str,
        address: str,
    ) -> Optional[Wallet]:
        """Set wallet address for a chain."""
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        wallet.set_address(chain, address)
        return wallet

    async def delete(self, wallet_id: str) -> bool:
        if wallet_id in self._wallets:
            del self._wallets[wallet_id]
            return True
        return False

    # Note: deposit() and withdraw() removed - non-custodial wallets don't hold funds
    # Balances are managed on-chain, not in our database

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
