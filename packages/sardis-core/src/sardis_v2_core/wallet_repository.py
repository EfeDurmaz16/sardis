"""Wallet repository for CRUD operations."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Literal

from .wallets import Wallet
from .tokens import TokenType
from .utils import TTLDict


class WalletRepository:
    """In-memory wallet repository (swap for PostgreSQL in production).
    
    Uses TTLDict to prevent memory leaks in long-running processes.
    Default TTL is 7 days, max 10,000 wallets in memory.
    """

    # 7 days TTL for wallet cache
    DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60
    DEFAULT_MAX_ITEMS = 10000

    def __init__(
        self,
        dsn: str = "memory://",
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_items: int = DEFAULT_MAX_ITEMS,
    ):
        self._dsn = dsn
        self._wallets: TTLDict[str, Wallet] = TTLDict(
            ttl_seconds=ttl_seconds,
            max_items=max_items,
        )

    async def create(
        self,
        agent_id: str,
        wallet_id: str | None = None,
        mpc_provider: str = "turnkey",
        account_type: Literal["mpc_v1", "erc4337_v2"] = "mpc_v1",
        currency: str = "USDC",
        limit_per_tx: Decimal = Decimal("100.00"),
        limit_total: Decimal = Decimal("1000.00"),
        addresses: Optional[dict[str, str]] = None,
        smart_account_address: Optional[str] = None,
        entrypoint_address: Optional[str] = None,
        paymaster_enabled: bool = False,
        bundler_profile: Optional[str] = None,
    ) -> Wallet:
        """Create a new non-custodial wallet."""
        wallet = Wallet.new(
            agent_id,
            mpc_provider=mpc_provider,
            account_type=account_type,
            currency=currency,
            wallet_id=wallet_id,
        )
        wallet.limit_per_tx = limit_per_tx
        wallet.limit_total = limit_total
        wallet.smart_account_address = smart_account_address
        wallet.entrypoint_address = entrypoint_address
        wallet.paymaster_enabled = paymaster_enabled
        wallet.bundler_profile = bundler_profile
        if addresses:
            wallet.addresses.update(addresses)
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
        account_type: Optional[Literal["mpc_v1", "erc4337_v2"]] = None,
        smart_account_address: Optional[str] = None,
        entrypoint_address: Optional[str] = None,
        paymaster_enabled: Optional[bool] = None,
        bundler_profile: Optional[str] = None,
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
        if account_type is not None:
            wallet.account_type = account_type
        if smart_account_address is not None:
            wallet.smart_account_address = smart_account_address
        if entrypoint_address is not None:
            wallet.entrypoint_address = entrypoint_address
        if paymaster_enabled is not None:
            wallet.paymaster_enabled = paymaster_enabled
        if bundler_profile is not None:
            wallet.bundler_profile = bundler_profile
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

    async def freeze(
        self,
        wallet_id: str,
        frozen_by: str,
        reason: str,
    ) -> Optional[Wallet]:
        """
        Freeze a wallet (blocks all transactions).

        Args:
            wallet_id: Wallet identifier
            frozen_by: Admin/system identifier who froze the wallet
            reason: Reason for freezing (compliance, suspicious activity, etc.)

        Returns:
            Updated wallet or None if not found
        """
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        wallet.freeze(by=frozen_by, reason=reason)
        return wallet

    async def unfreeze(self, wallet_id: str) -> Optional[Wallet]:
        """
        Unfreeze a wallet (restore transaction capability).

        Args:
            wallet_id: Wallet identifier

        Returns:
            Updated wallet or None if not found
        """
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        wallet.unfreeze()
        return wallet

    async def get_frozen_wallets(self) -> List[Wallet]:
        """
        Get all frozen wallets.

        Returns:
            List of frozen wallets
        """
        return [w for w in self._wallets.values() if w.is_frozen]
