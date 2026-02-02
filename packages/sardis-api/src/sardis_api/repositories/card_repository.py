"""Card repository for PostgreSQL persistence."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import uuid


class CardRepository:
    """PostgreSQL repository for virtual card data."""

    def __init__(self, pool):
        self._pool = pool

    async def create(
        self,
        card_id: str,
        wallet_id: str,
        provider: str,
        provider_card_id: str | None = None,
        card_type: str = "multi_use",
        limit_per_tx: float = 0,
        limit_daily: float = 0,
        limit_monthly: float = 0,
    ) -> Dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO virtual_cards (
                    id, card_id, wallet_id, provider, provider_card_id,
                    card_type, status, limit_per_tx, limit_daily, limit_monthly,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7, $8, $9, NOW())
                RETURNING *
                """,
                str(uuid.uuid4()), card_id, wallet_id, provider,
                provider_card_id, card_type,
                limit_per_tx, limit_daily, limit_monthly,
            )
            return dict(row)

    async def get_by_card_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM virtual_cards WHERE card_id = $1", card_id
            )
            return dict(row) if row else None

    async def get_by_wallet_id(self, wallet_id: str) -> List[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM virtual_cards WHERE wallet_id = $1 ORDER BY created_at DESC",
                wallet_id,
            )
            return [dict(r) for r in rows]

    async def update_status(
        self, card_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        ts_field = {
            "active": "activated_at",
            "frozen": "frozen_at",
            "cancelled": "cancelled_at",
        }.get(status)
        extra = f", {ts_field} = NOW()" if ts_field else ""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE virtual_cards SET status = $1{extra} WHERE card_id = $2 RETURNING *",
                status, card_id,
            )
            return dict(row) if row else None

    async def update_limits(
        self, card_id: str, limit_per_tx: float | None = None,
        limit_daily: float | None = None, limit_monthly: float | None = None,
    ) -> Optional[Dict[str, Any]]:
        sets = []
        params = []
        idx = 1
        for field, val in [
            ("limit_per_tx", limit_per_tx),
            ("limit_daily", limit_daily),
            ("limit_monthly", limit_monthly),
        ]:
            if val is not None:
                sets.append(f"{field} = ${idx}")
                params.append(val)
                idx += 1
        if not sets:
            return await self.get_by_card_id(card_id)
        params.append(card_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE virtual_cards SET {', '.join(sets)} WHERE card_id = ${idx} RETURNING *",
                *params,
            )
            return dict(row) if row else None

    async def update_funded_amount(
        self, card_id: str, amount: float
    ) -> Optional[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE virtual_cards SET funded_amount = $1 WHERE card_id = $2 RETURNING *",
                amount, card_id,
            )
            return dict(row) if row else None

    async def record_transaction(
        self,
        transaction_id: str,
        card_id: str,
        provider_tx_id: str | None = None,
        amount: float = 0,
        currency: str = "USD",
        merchant_name: str | None = None,
        merchant_category: str | None = None,
        status: str = "pending",
    ) -> Dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO card_transactions (
                    id, transaction_id, card_id, provider_tx_id,
                    amount, currency, merchant_name, merchant_category,
                    status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                RETURNING *
                """,
                str(uuid.uuid4()), transaction_id, card_id,
                provider_tx_id, amount, currency,
                merchant_name, merchant_category, status,
            )
            return dict(row)

    async def list_transactions(
        self, card_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM card_transactions
                WHERE card_id = $1
                ORDER BY created_at DESC LIMIT $2
                """,
                card_id, limit,
            )
            return [dict(r) for r in rows]
