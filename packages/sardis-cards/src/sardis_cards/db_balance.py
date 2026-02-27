"""PostgreSQL-backed unified balance service.

Replaces the in-memory ``_usd_balances`` dict in
``UnifiedBalanceService`` with persistent storage using the
``token_balances`` table (currency='USD').

Pattern follows ``policy_store_postgres.py``.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from .auto_conversion import UnifiedBalance, WalletProvider

logger = logging.getLogger(__name__)


class PostgresUnifiedBalanceService:
    """
    DB-backed unified balance service.

    USD balances are stored in ``token_balances`` with ``token = 'USD'``.
    USDC balances are fetched on-chain via the wallet provider.
    """

    def __init__(self, wallet_provider: WalletProvider, dsn: str) -> None:
        self._wallet_provider = wallet_provider
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def get_unified_balance(
        self,
        wallet_id: str,
        chain: str = "base",
    ) -> UnifiedBalance:
        """Get unified balance combining on-chain USDC and DB-persisted USD."""
        usdc_balance = await self._wallet_provider.get_usdc_balance(wallet_id, chain)

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(
                    (SELECT (balance * 100)::bigint FROM token_balances
                     WHERE wallet_id = (
                         SELECT id FROM wallets WHERE external_id = $1 LIMIT 1
                     ) AND token = 'USD'),
                    0
                ) AS usd_cents
                """,
                wallet_id,
            )
            usd_cents = int(row["usd_cents"]) if row else 0

        return UnifiedBalance(
            wallet_id=wallet_id,
            usdc_balance_minor=usdc_balance,
            usd_balance_cents=usd_cents,
            chain=chain,
        )

    async def check_sufficient_balance(
        self,
        wallet_id: str,
        amount_cents: int,
        chain: str = "base",
    ) -> bool:
        """Check if wallet has sufficient unified balance."""
        balance = await self.get_unified_balance(wallet_id, chain)
        return balance.total_balance_cents >= amount_cents

    async def add_usd_balance(self, wallet_id: str, amount_cents: int) -> None:
        """Add USD balance (persistent)."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Upsert into token_balances with token='USD'
            await conn.execute(
                """
                INSERT INTO token_balances (wallet_id, token, balance)
                SELECT w.id, 'USD', $2::numeric / 100
                FROM wallets w WHERE w.external_id = $1
                ON CONFLICT (wallet_id, token)
                DO UPDATE SET balance = token_balances.balance + ($2::numeric / 100),
                             updated_at = NOW()
                """,
                wallet_id,
                amount_cents,
            )
            logger.info(
                "Added $%.2f USD to wallet %s (persisted)",
                amount_cents / 100,
                wallet_id,
            )

    async def deduct_usd_balance(self, wallet_id: str, amount_cents: int) -> bool:
        """
        Deduct USD balance atomically.

        Returns True if deduction succeeded, False if insufficient.
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT tb.balance
                    FROM token_balances tb
                    JOIN wallets w ON w.id = tb.wallet_id
                    WHERE w.external_id = $1 AND tb.token = 'USD'
                    FOR UPDATE
                    """,
                    wallet_id,
                )
                if not row:
                    return False

                from decimal import Decimal

                current_cents = int(row["balance"] * 100)
                if current_cents < amount_cents:
                    return False

                await conn.execute(
                    """
                    UPDATE token_balances
                    SET balance = balance - ($2::numeric / 100),
                        updated_at = NOW()
                    WHERE wallet_id = (
                        SELECT id FROM wallets WHERE external_id = $1 LIMIT 1
                    ) AND token = 'USD'
                    """,
                    wallet_id,
                    amount_cents,
                )

        logger.info(
            "Deducted $%.2f USD from wallet %s (persisted)",
            amount_cents / 100,
            wallet_id,
        )
        return True

    async def close(self) -> None:
        # Pool lifecycle managed by Database.close() at app shutdown
        pass
