"""Card repository for virtual card persistence.

This repository supports:
- PostgreSQL (when a DSN is provided, uses a lazy pool)
- In-memory fallback (when pool is None), useful for demos/tests

NOTE: The in-memory mode is intentionally simple and not multi-instance safe.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os
import uuid


class CardRepository:
    """Repository for virtual card data (PostgreSQL if pool is provided)."""

    def __init__(self, pool=None, dsn: str | None = None):
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._cards: dict[str, dict[str, Any]] = {}
        self._transactions: dict[str, list[dict[str, Any]]] = {}

    def _use_postgres(self) -> bool:
        if self._pool is not None:
            return True
        return self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            if not self._use_postgres():
                return None
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)
        return self._pool

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
        if not self._use_postgres():
            now = datetime.now(timezone.utc).isoformat()
            row: dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "card_id": card_id,
                "wallet_id": wallet_id,
                "provider": provider,
                "provider_card_id": provider_card_id,
                "card_type": card_type,
                "status": "pending",
                "limit_per_tx": limit_per_tx,
                "limit_daily": limit_daily,
                "limit_monthly": limit_monthly,
                "funded_amount": 0,
                "created_at": now,
            }
            self._cards[card_id] = row
            self._transactions.setdefault(card_id, [])
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            wallet_row = await conn.fetchrow(
                "SELECT id FROM wallets WHERE external_id = $1",
                wallet_id,
            )
            if not wallet_row:
                raise ValueError("Wallet not found")
            wallet_uuid = str(wallet_row["id"])

            await conn.execute(
                """
                INSERT INTO virtual_cards (
                    id, card_id, wallet_id, provider, provider_card_id,
                    card_type, status, limit_per_tx, limit_daily, limit_monthly,
                    created_at
                ) VALUES ($1, $2, $3::uuid, $4, $5, $6, 'pending', $7, $8, $9, NOW())
                """,
                str(uuid.uuid4()),
                card_id,
                wallet_uuid,
                provider,
                provider_card_id,
                card_type,
                limit_per_tx,
                limit_daily,
                limit_monthly,
            )
            row = await conn.fetchrow(
                """
                SELECT vc.*, w.external_id AS wallet_external_id
                FROM virtual_cards vc
                JOIN wallets w ON w.id = vc.wallet_id
                WHERE vc.card_id = $1
                """,
                card_id,
            )
            d = dict(row)
            d["wallet_uuid"] = str(d.get("wallet_id"))
            d["wallet_id"] = str(d.get("wallet_external_id") or wallet_id)
            d.pop("wallet_external_id", None)
            return d

    async def get_by_card_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        if not self._use_postgres():
            return self._cards.get(card_id)
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT vc.*, w.external_id AS wallet_external_id
                FROM virtual_cards vc
                JOIN wallets w ON w.id = vc.wallet_id
                WHERE vc.card_id = $1
                """,
                card_id,
            )
            if not row:
                return None
            d = dict(row)
            d["wallet_uuid"] = str(d.get("wallet_id"))
            d["wallet_id"] = str(d.get("wallet_external_id"))
            d.pop("wallet_external_id", None)
            return d

    async def get_by_provider_card_id(self, provider_card_id: str) -> Optional[Dict[str, Any]]:
        if not self._use_postgres():
            for card in self._cards.values():
                if card.get("provider_card_id") == provider_card_id:
                    return card
            return None
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT vc.*, w.external_id AS wallet_external_id
                FROM virtual_cards vc
                JOIN wallets w ON w.id = vc.wallet_id
                WHERE vc.provider_card_id = $1
                """,
                provider_card_id,
            )
            if not row:
                return None
            d = dict(row)
            d["wallet_uuid"] = str(d.get("wallet_id"))
            d["wallet_id"] = str(d.get("wallet_external_id"))
            d.pop("wallet_external_id", None)
            return d

    async def get_by_wallet_id(self, wallet_id: str) -> List[Dict[str, Any]]:
        if not self._use_postgres():
            return [
                card for card in self._cards.values()
                if card.get("wallet_id") == wallet_id
            ]
        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT vc.*, w.external_id AS wallet_external_id
                FROM virtual_cards vc
                JOIN wallets w ON w.id = vc.wallet_id
                WHERE w.external_id = $1
                ORDER BY vc.created_at DESC
                """,
                wallet_id,
            )
            result: list[dict[str, Any]] = []
            for r in rows:
                d = dict(r)
                d["wallet_uuid"] = str(d.get("wallet_id"))
                d["wallet_id"] = str(d.get("wallet_external_id"))
                d.pop("wallet_external_id", None)
                result.append(d)
            return result

    async def update_status(
        self, card_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        if not self._use_postgres():
            card = self._cards.get(card_id)
            if not card:
                return None
            card["status"] = status
            return card
        ts_field = {
            "active": "activated_at",
            "frozen": "frozen_at",
            "cancelled": "cancelled_at",
        }.get(status)
        extra = f", {ts_field} = NOW()" if ts_field else ""
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE virtual_cards
                SET status = $1{extra}
                WHERE card_id = $2
                RETURNING card_id
                """,
                status,
                card_id,
            )
            if not row:
                return None
            return await self.get_by_card_id(card_id)

    async def update_limits(
        self, card_id: str, limit_per_tx: float | None = None,
        limit_daily: float | None = None, limit_monthly: float | None = None,
    ) -> Optional[Dict[str, Any]]:
        if not self._use_postgres():
            card = self._cards.get(card_id)
            if not card:
                return None
            if limit_per_tx is not None:
                card["limit_per_tx"] = limit_per_tx
            if limit_daily is not None:
                card["limit_daily"] = limit_daily
            if limit_monthly is not None:
                card["limit_monthly"] = limit_monthly
            return card
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
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE virtual_cards SET {', '.join(sets)} WHERE card_id = ${idx} RETURNING card_id",
                *params,
            )
            if not row:
                return None
            return await self.get_by_card_id(card_id)

    async def update_funded_amount(
        self, card_id: str, amount: float
    ) -> Optional[Dict[str, Any]]:
        if not self._use_postgres():
            card = self._cards.get(card_id)
            if not card:
                return None
            card["funded_amount"] = amount
            return card
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE virtual_cards SET funded_amount = $1 WHERE card_id = $2 RETURNING card_id",
                amount, card_id,
            )
            if not row:
                return None
            return await self.get_by_card_id(card_id)

    async def record_transaction(
        self,
        transaction_id: str,
        card_id: str,
        provider_tx_id: str | None = None,
        amount: float = 0,
        currency: str = "USD",
        merchant_name: str | None = None,
        merchant_category: str | None = None,
        merchant_id: str | None = None,
        status: str = "pending",
        decline_reason: str | None = None,
        settled_at: datetime | None = None,
    ) -> Dict[str, Any]:
        if not self._use_postgres():
            row: dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "transaction_id": transaction_id,
                "card_id": card_id,
                "provider_tx_id": provider_tx_id,
                "amount": amount,
                "currency": currency,
                "merchant_name": merchant_name,
                "merchant_category": merchant_category,
                "merchant_id": merchant_id,
                "status": status,
                "decline_reason": decline_reason,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "settled_at": settled_at.isoformat() if settled_at else None,
            }
            self._transactions.setdefault(card_id, []).insert(0, row)
            return row
        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            vc = await conn.fetchrow(
                "SELECT id FROM virtual_cards WHERE card_id = $1",
                card_id,
            )
            if not vc:
                raise ValueError("Card not found")
            card_uuid = str(vc["id"])

            row = await conn.fetchrow(
                """
                INSERT INTO card_transactions (
                    id, transaction_id, card_id, provider_tx_id,
                    amount, currency, merchant_name, merchant_category,
                    merchant_id, status, decline_reason, created_at, settled_at
                ) VALUES ($1, $2, $3::uuid, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), $12)
                ON CONFLICT (transaction_id) DO UPDATE
                SET status = EXCLUDED.status,
                    provider_tx_id = COALESCE(EXCLUDED.provider_tx_id, card_transactions.provider_tx_id),
                    amount = EXCLUDED.amount,
                    currency = EXCLUDED.currency,
                    merchant_name = COALESCE(EXCLUDED.merchant_name, card_transactions.merchant_name),
                    merchant_category = COALESCE(EXCLUDED.merchant_category, card_transactions.merchant_category),
                    merchant_id = COALESCE(EXCLUDED.merchant_id, card_transactions.merchant_id),
                    decline_reason = COALESCE(EXCLUDED.decline_reason, card_transactions.decline_reason),
                    settled_at = COALESCE(EXCLUDED.settled_at, card_transactions.settled_at)
                RETURNING id, transaction_id, provider_tx_id, amount, currency, merchant_name, merchant_category, merchant_id, status, decline_reason, created_at, settled_at
                """,
                str(uuid.uuid4()),
                transaction_id,
                card_uuid,
                provider_tx_id,
                amount,
                currency,
                merchant_name,
                merchant_category,
                merchant_id,
                status,
                decline_reason,
                settled_at,
            )
            d = dict(row)
            d["card_id"] = card_id
            return d

    async def list_transactions(
        self, card_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        if not self._use_postgres():
            return list(self._transactions.get(card_id, []))[:limit]
        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ct.transaction_id, vc.card_id AS card_id, ct.provider_tx_id,
                       ct.amount, ct.currency, ct.merchant_name, ct.merchant_category,
                       ct.merchant_id, ct.status, ct.decline_reason, ct.created_at, ct.settled_at
                FROM card_transactions ct
                JOIN virtual_cards vc ON vc.id = ct.card_id
                WHERE vc.card_id = $1
                ORDER BY ct.created_at DESC
                LIMIT $2
                """,
                card_id, limit,
            )
            return [dict(r) for r in rows]

    async def close(self) -> None:
        if self._pool is not None and self._use_postgres():
            try:
                await self._pool.close()
            finally:
                self._pool = None
