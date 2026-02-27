"""Repository for recurring payment subscriptions and billing events."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SubscriptionRepository:
    def __init__(self, pool=None, dsn: str | None = None):
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._billing_events: dict[str, dict[str, Any]] = {}

    def _use_postgres(self) -> bool:
        if self._pool is not None:
            return True
        return self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def create_subscription(
        self,
        *,
        wallet_id: str,
        owner_id: str,
        merchant: str,
        amount_cents: int,
        currency: str,
        billing_cycle: str,
        billing_day: int,
        next_billing: datetime,
        merchant_mcc: str | None = None,
        card_id: str | None = None,
        auto_approve: bool = True,
        auto_approve_threshold_cents: int = 10_000,
        amount_tolerance_cents: int = 500,
        notify_owner: bool = True,
        notification_channel: str | None = None,
        max_failures: int = 3,
        destination_address: str | None = None,
        token: str = "USDC",
        chain: str = "base_sepolia",
        memo: str | None = None,
        autofund_enabled: bool = False,
        autofund_amount_cents: int | None = None,
    ) -> dict[str, Any]:
        subscription_id = f"sub_{uuid.uuid4().hex[:16]}"
        now = _utc_now()
        row: dict[str, Any] = {
            "id": subscription_id,
            "wallet_id": wallet_id,
            "owner_id": owner_id,
            "merchant": merchant,
            "merchant_mcc": merchant_mcc,
            "amount_cents": int(amount_cents),
            "currency": currency,
            "billing_cycle": billing_cycle,
            "billing_day": int(billing_day),
            "next_billing": next_billing,
            "card_id": card_id,
            "auto_approve": bool(auto_approve),
            "auto_approve_threshold_cents": int(auto_approve_threshold_cents),
            "amount_tolerance_cents": int(amount_tolerance_cents),
            "notify_owner": bool(notify_owner),
            "notification_channel": notification_channel,
            "status": "active",
            "last_charged_at": None,
            "failure_count": 0,
            "max_failures": int(max_failures),
            "destination_address": destination_address,
            "token": token,
            "chain": chain,
            "memo": memo,
            "autofund_enabled": bool(autofund_enabled),
            "autofund_amount_cents": int(autofund_amount_cents) if autofund_amount_cents is not None else None,
            "last_autofund_at": None,
            "created_at": now,
            "updated_at": now,
        }

        if not self._use_postgres():
            self._subscriptions[subscription_id] = row
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO subscriptions (
                    id, wallet_id, owner_id, merchant, merchant_mcc, amount_cents, currency,
                    billing_cycle, billing_day, next_billing, card_id, auto_approve,
                    auto_approve_threshold_cents, amount_tolerance_cents, notify_owner,
                    notification_channel, status, last_charged_at, failure_count, max_failures,
                    destination_address, token, chain, memo, autofund_enabled, autofund_amount_cents,
                    last_autofund_at, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    $8, $9, $10, $11, $12,
                    $13, $14, $15,
                    $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26,
                    $27, NOW(), NOW()
                )
                """,
                row["id"],
                row["wallet_id"],
                row["owner_id"],
                row["merchant"],
                row["merchant_mcc"],
                row["amount_cents"],
                row["currency"],
                row["billing_cycle"],
                row["billing_day"],
                row["next_billing"],
                row["card_id"],
                row["auto_approve"],
                row["auto_approve_threshold_cents"],
                row["amount_tolerance_cents"],
                row["notify_owner"],
                row["notification_channel"],
                row["status"],
                row["last_charged_at"],
                row["failure_count"],
                row["max_failures"],
                row["destination_address"],
                row["token"],
                row["chain"],
                row["memo"],
                row["autofund_enabled"],
                row["autofund_amount_cents"],
                row["last_autofund_at"],
            )
            db_row = await conn.fetchrow("SELECT * FROM subscriptions WHERE id = $1", row["id"])
            return dict(db_row) if db_row else row

    async def get_subscription(self, subscription_id: str) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            return self._subscriptions.get(subscription_id)
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM subscriptions WHERE id = $1", subscription_id)
            return dict(row) if row else None

    async def list_subscriptions(
        self,
        *,
        owner_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = list(self._subscriptions.values())
            if owner_id:
                rows = [r for r in rows if r.get("owner_id") == owner_id]
            if wallet_id:
                rows = [r for r in rows if r.get("wallet_id") == wallet_id]
            if status:
                rows = [r for r in rows if str(r.get("status", "")).lower() == status.lower()]
            rows.sort(key=lambda item: item.get("created_at") or _utc_now(), reverse=True)
            return rows[offset : offset + limit]

        pool = await self._get_pool()
        if pool is None:
            return []
        query = "SELECT * FROM subscriptions WHERE 1=1"
        args: list[Any] = []
        idx = 1
        if owner_id:
            query += f" AND owner_id = ${idx}"
            args.append(owner_id)
            idx += 1
        if wallet_id:
            query += f" AND wallet_id = ${idx}"
            args.append(wallet_id)
            idx += 1
        if status:
            query += f" AND status = ${idx}"
            args.append(status)
            idx += 1
        query += f" ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"
        args.extend([int(limit), int(offset)])

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]

    async def cancel_subscription(self, subscription_id: str) -> bool:
        if not self._use_postgres():
            sub = self._subscriptions.get(subscription_id)
            if not sub:
                return False
            sub["status"] = "cancelled"
            sub["updated_at"] = _utc_now()
            return True
        pool = await self._get_pool()
        if pool is None:
            return False
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE subscriptions SET status = 'cancelled', updated_at = NOW() WHERE id = $1",
                subscription_id,
            )
            updated = int(str(result).split()[-1]) if result else 0
            return updated > 0

    async def list_due_subscriptions(self, *, now: datetime, limit: int = 100) -> list[dict[str, Any]]:
        if not self._use_postgres():
            due = [
                sub
                for sub in self._subscriptions.values()
                if str(sub.get("status", "")).lower() == "active"
                and isinstance(sub.get("next_billing"), datetime)
                and sub["next_billing"] <= now
            ]
            due.sort(key=lambda item: item["next_billing"])
            return due[:limit]

        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM subscriptions
                WHERE status = 'active' AND next_billing <= $1
                ORDER BY next_billing ASC
                LIMIT $2
                """,
                now,
                int(limit),
            )
            return [dict(row) for row in rows]

    async def create_billing_event(
        self,
        *,
        subscription_id: str,
        wallet_id: str,
        scheduled_at: datetime,
        amount_cents: int,
        status: str = "pending",
        error: str | None = None,
        fund_tx_id: str | None = None,
        charge_tx_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = f"bill_evt_{uuid.uuid4().hex[:16]}"
        row = {
            "id": event_id,
            "subscription_id": subscription_id,
            "wallet_id": wallet_id,
            "scheduled_at": scheduled_at,
            "status": status,
            "amount_cents": int(amount_cents),
            "fund_tx_id": fund_tx_id,
            "approval_id": None,
            "charge_tx_id": charge_tx_id,
            "error": error,
            "created_at": _utc_now(),
        }

        if not self._use_postgres():
            self._billing_events[event_id] = row
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO billing_events (
                    id, subscription_id, wallet_id, scheduled_at, status,
                    amount_cents, fund_tx_id, approval_id, charge_tx_id, error, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NULL, $8, $9, NOW())
                """,
                row["id"],
                row["subscription_id"],
                row["wallet_id"],
                row["scheduled_at"],
                row["status"],
                row["amount_cents"],
                row["fund_tx_id"],
                row["charge_tx_id"],
                row["error"],
            )
            db_row = await conn.fetchrow("SELECT * FROM billing_events WHERE id = $1", row["id"])
            return dict(db_row) if db_row else row

    async def update_billing_event(
        self,
        event_id: str,
        *,
        status: Optional[str] = None,
        fund_tx_id: Optional[str] = None,
        charge_tx_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            row = self._billing_events.get(event_id)
            if not row:
                return None
            if status is not None:
                row["status"] = status
            if fund_tx_id is not None:
                row["fund_tx_id"] = fund_tx_id
            if charge_tx_id is not None:
                row["charge_tx_id"] = charge_tx_id
            if error is not None:
                row["error"] = error
            return row

        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE billing_events
                SET status = COALESCE($2, status),
                    fund_tx_id = COALESCE($3, fund_tx_id),
                    charge_tx_id = COALESCE($4, charge_tx_id),
                    error = COALESCE($5, error)
                WHERE id = $1
                """,
                event_id,
                status,
                fund_tx_id,
                charge_tx_id,
                error,
            )
            row = await conn.fetchrow("SELECT * FROM billing_events WHERE id = $1", event_id)
            return dict(row) if row else None

    async def mark_subscription_charged(
        self,
        subscription_id: str,
        *,
        charged_at: datetime,
        next_billing: datetime,
        charge_tx_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            row = self._subscriptions.get(subscription_id)
            if not row:
                return None
            row["last_charged_at"] = charged_at
            row["next_billing"] = next_billing
            row["failure_count"] = 0
            row["updated_at"] = _utc_now()
            if charge_tx_id is not None:
                row["last_charge_tx_id"] = charge_tx_id
            return row

        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscriptions
                SET last_charged_at = $2,
                    next_billing = $3,
                    failure_count = 0,
                    updated_at = NOW()
                WHERE id = $1
                """,
                subscription_id,
                charged_at,
                next_billing,
            )
            row = await conn.fetchrow("SELECT * FROM subscriptions WHERE id = $1", subscription_id)
            return dict(row) if row else None

    async def mark_subscription_failed(self, subscription_id: str, *, error: str | None = None) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            row = self._subscriptions.get(subscription_id)
            if not row:
                return None
            row["failure_count"] = int(row.get("failure_count", 0) or 0) + 1
            if row["failure_count"] >= int(row.get("max_failures", 3) or 3):
                row["status"] = "paused"
            row["updated_at"] = _utc_now()
            if error is not None:
                row["last_error"] = error
            return row

        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscriptions
                SET failure_count = failure_count + 1,
                    status = CASE
                        WHEN failure_count + 1 >= max_failures THEN 'paused'
                        ELSE status
                    END,
                    updated_at = NOW()
                WHERE id = $1
                """,
                subscription_id,
            )
            row = await conn.fetchrow("SELECT * FROM subscriptions WHERE id = $1", subscription_id)
            return dict(row) if row else None

