"""PostgreSQL-backed offramp service.

Replaces the in-memory ``_transactions`` and ``_wallet_transactions``
dicts in ``OfframpService`` with the ``offramp_transactions`` table.

Pattern follows ``policy_store_postgres.py``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .offramp import (
    MockOfframpProvider,
    OfframpProviderBase,
    OfframpQuote,
    OfframpStatus,
    OfframpTransaction,
    VelocityLimitExceeded,
)

logger = logging.getLogger(__name__)


class PostgresOfframpService:
    """
    DB-backed off-ramp service.

    Transactions are persisted in ``offramp_transactions``.
    Velocity limits are computed from DB queries instead of in-memory lists.
    """

    DEFAULT_DAILY_LIMIT_CENTS = 10_000_00
    DEFAULT_WEEKLY_LIMIT_CENTS = 50_000_00
    DEFAULT_MONTHLY_LIMIT_CENTS = 200_000_00

    def __init__(
        self,
        dsn: str,
        provider: Optional[OfframpProviderBase] = None,
        daily_limit_cents: Optional[int] = None,
        weekly_limit_cents: Optional[int] = None,
        monthly_limit_cents: Optional[int] = None,
    ) -> None:
        self._dsn = dsn
        self._provider = provider or MockOfframpProvider()
        self._daily_limit_cents = daily_limit_cents or self.DEFAULT_DAILY_LIMIT_CENTS
        self._weekly_limit_cents = weekly_limit_cents or self.DEFAULT_WEEKLY_LIMIT_CENTS
        self._monthly_limit_cents = monthly_limit_cents or self.DEFAULT_MONTHLY_LIMIT_CENTS
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pool

    async def get_quote(
        self,
        input_token: str,
        input_amount_minor: int,
        input_chain: str = "base",
        output_currency: str = "USD",
    ) -> OfframpQuote:
        """Get a quote for off-ramp."""
        return await self._provider.get_quote(
            input_token=input_token,
            input_amount_minor=input_amount_minor,
            input_chain=input_chain,
            output_currency=output_currency,
        )

    async def _check_velocity_limits(
        self,
        wallet_id: str,
        amount_cents: int,
    ) -> None:
        """Check velocity limits from DB."""
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            # Daily
            daily_vol = await conn.fetchval(
                """
                SELECT COALESCE(SUM(amount_cents), 0)
                FROM offramp_transactions
                WHERE wallet_id = $1 AND status = 'completed'
                  AND created_at > $2
                """,
                wallet_id,
                now - timedelta(days=1),
            )
            if int(daily_vol) + amount_cents > self._daily_limit_cents:
                raise VelocityLimitExceeded(
                    f"Daily off-ramp limit exceeded. "
                    f"Used: ${int(daily_vol) / 100:.2f}, "
                    f"Limit: ${self._daily_limit_cents / 100:.2f}"
                )

            # Weekly
            weekly_vol = await conn.fetchval(
                """
                SELECT COALESCE(SUM(amount_cents), 0)
                FROM offramp_transactions
                WHERE wallet_id = $1 AND status = 'completed'
                  AND created_at > $2
                """,
                wallet_id,
                now - timedelta(days=7),
            )
            if int(weekly_vol) + amount_cents > self._weekly_limit_cents:
                raise VelocityLimitExceeded(
                    f"Weekly off-ramp limit exceeded. "
                    f"Used: ${int(weekly_vol) / 100:.2f}, "
                    f"Limit: ${self._weekly_limit_cents / 100:.2f}"
                )

            # Monthly
            monthly_vol = await conn.fetchval(
                """
                SELECT COALESCE(SUM(amount_cents), 0)
                FROM offramp_transactions
                WHERE wallet_id = $1 AND status = 'completed'
                  AND created_at > $2
                """,
                wallet_id,
                now - timedelta(days=30),
            )
            if int(monthly_vol) + amount_cents > self._monthly_limit_cents:
                raise VelocityLimitExceeded(
                    f"Monthly off-ramp limit exceeded. "
                    f"Used: ${int(monthly_vol) / 100:.2f}, "
                    f"Limit: ${self._monthly_limit_cents / 100:.2f}"
                )

    async def execute(
        self,
        quote: OfframpQuote,
        source_address: str,
        destination_account: str,
        wallet_id: Optional[str] = None,
    ) -> OfframpTransaction:
        """Execute off-ramp and persist transaction."""
        if wallet_id:
            await self._check_velocity_limits(wallet_id, quote.output_amount_cents)

        tx = await self._provider.execute_offramp(
            quote=quote,
            source_address=source_address,
            destination_account=destination_account,
        )

        # Persist to DB
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO offramp_transactions
                    (id, wallet_id, amount_cents, currency, status, provider, provider_tx_id, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                tx.transaction_id,
                wallet_id or "",
                quote.output_amount_cents,
                quote.output_currency,
                tx.status.value,
                tx.provider.value,
                tx.provider_reference,
                tx.created_at,
            )

        return tx

    async def get_status(self, transaction_id: str) -> OfframpTransaction:
        """Get transaction status, refreshing from provider."""
        tx = await self._provider.get_transaction_status(transaction_id)

        # Update status in DB
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE offramp_transactions SET status = $2 WHERE id = $1",
                transaction_id,
                tx.status.value,
            )

        return tx

    async def get_pending_transactions(self) -> List[OfframpTransaction]:
        """Get all pending transactions from DB."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id FROM offramp_transactions
                WHERE status IN ('pending', 'processing')
                ORDER BY created_at DESC
                """
            )
            results = []
            for row in rows:
                try:
                    tx = await self._provider.get_transaction_status(row["id"])
                    results.append(tx)
                except Exception:
                    pass
            return results

    async def get_velocity_limits(self, wallet_id: str) -> Dict[str, Any]:
        """Get velocity limit status from DB."""
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            daily_vol = int(
                await conn.fetchval(
                    """
                    SELECT COALESCE(SUM(amount_cents), 0)
                    FROM offramp_transactions
                    WHERE wallet_id = $1 AND status = 'completed'
                      AND created_at > $2
                    """,
                    wallet_id,
                    now - timedelta(days=1),
                )
            )
            weekly_vol = int(
                await conn.fetchval(
                    """
                    SELECT COALESCE(SUM(amount_cents), 0)
                    FROM offramp_transactions
                    WHERE wallet_id = $1 AND status = 'completed'
                      AND created_at > $2
                    """,
                    wallet_id,
                    now - timedelta(days=7),
                )
            )
            monthly_vol = int(
                await conn.fetchval(
                    """
                    SELECT COALESCE(SUM(amount_cents), 0)
                    FROM offramp_transactions
                    WHERE wallet_id = $1 AND status = 'completed'
                      AND created_at > $2
                    """,
                    wallet_id,
                    now - timedelta(days=30),
                )
            )

        return {
            "daily": {
                "used_cents": daily_vol,
                "limit_cents": self._daily_limit_cents,
                "remaining_cents": self._daily_limit_cents - daily_vol,
            },
            "weekly": {
                "used_cents": weekly_vol,
                "limit_cents": self._weekly_limit_cents,
                "remaining_cents": self._weekly_limit_cents - weekly_vol,
            },
            "monthly": {
                "used_cents": monthly_vol,
                "limit_cents": self._monthly_limit_cents,
                "remaining_cents": self._monthly_limit_cents - monthly_vol,
            },
        }

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
