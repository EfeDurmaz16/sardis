"""Treasury repository for Lithic financial accounts and ACH records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
import os
import uuid
import hashlib


class TreasuryRepository:
    def __init__(self, pool=None, dsn: str | None = None):
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._financial_accounts: dict[tuple[str, str], dict[str, Any]] = {}
        self._external_bank_accounts: dict[tuple[str, str], dict[str, Any]] = {}
        self._payments: dict[tuple[str, str], dict[str, Any]] = {}
        self._payment_events: list[dict[str, Any]] = []
        self._balance_snapshots: list[dict[str, Any]] = []
        self._reservations: dict[str, dict[str, Any]] = {}
        self._webhook_events: dict[tuple[str, str], dict[str, Any]] = {}

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
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=8)
        return self._pool

    async def upsert_financial_account(self, organization_id: str, account: dict[str, Any]) -> dict[str, Any]:
        token = str(account.get("token", ""))
        if not token:
            raise ValueError("financial account token is required")

        row = {
            "organization_id": organization_id,
            "financial_account_token": token,
            "account_token": account.get("account_token"),
            "account_role": account.get("type", "OPERATING"),
            "currency": account.get("currency", "USD"),
            "status": account.get("status", "OPEN"),
            "is_program_level": bool(account.get("is_program_level", account.get("account_token") in (None, ""))),
            "nickname": account.get("nickname"),
            "routing_number": account.get("routing_number"),
            "account_number_last4": (account.get("account_number") or "")[-4:] if account.get("account_number") else None,
            "metadata": account,
            "updated_at": datetime.now(timezone.utc),
        }

        if not self._use_postgres():
            now = datetime.now(timezone.utc).isoformat()
            row["created_at"] = self._financial_accounts.get((organization_id, token), {}).get("created_at", now)
            self._financial_accounts[(organization_id, token)] = row
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO lithic_financial_accounts (
                    id, organization_id, account_token, financial_account_token, account_role,
                    currency, status, is_program_level, nickname, routing_number,
                    account_number_last4, metadata, created_at, updated_at
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, NOW(), NOW()
                )
                ON CONFLICT (financial_account_token) DO UPDATE SET
                    organization_id = EXCLUDED.organization_id,
                    account_token = EXCLUDED.account_token,
                    account_role = EXCLUDED.account_role,
                    currency = EXCLUDED.currency,
                    status = EXCLUDED.status,
                    is_program_level = EXCLUDED.is_program_level,
                    nickname = EXCLUDED.nickname,
                    routing_number = EXCLUDED.routing_number,
                    account_number_last4 = EXCLUDED.account_number_last4,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                str(uuid.uuid4()),
                organization_id,
                row["account_token"],
                token,
                row["account_role"],
                row["currency"],
                row["status"],
                row["is_program_level"],
                row["nickname"],
                row["routing_number"],
                row["account_number_last4"],
                row["metadata"],
            )
            db_row = await conn.fetchrow(
                """
                SELECT organization_id, account_token, financial_account_token, account_role,
                       currency, status, is_program_level, nickname, routing_number,
                       account_number_last4, metadata, created_at, updated_at
                FROM lithic_financial_accounts
                WHERE organization_id = $1 AND financial_account_token = $2
                """,
                organization_id,
                token,
            )
            return dict(db_row) if db_row else row

    async def get_financial_account(self, organization_id: str, financial_account_token: str) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            return self._financial_accounts.get((organization_id, financial_account_token))
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT organization_id, account_token, financial_account_token, account_role,
                       currency, status, is_program_level, nickname, routing_number,
                       account_number_last4, metadata, created_at, updated_at
                FROM lithic_financial_accounts
                WHERE organization_id = $1 AND financial_account_token = $2
                """,
                organization_id,
                financial_account_token,
            )
            return dict(row) if row else None

    async def list_financial_accounts(
        self,
        organization_id: str,
        account_token: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = [
                value for (org, _), value in self._financial_accounts.items() if org == organization_id
            ]
            if account_token:
                rows = [r for r in rows if r.get("account_token") == account_token]
            return rows
        pool = await self._get_pool()
        if pool is None:
            return []
        query = """
            SELECT organization_id, account_token, financial_account_token, account_role,
                   currency, status, is_program_level, nickname, routing_number,
                   account_number_last4, metadata, created_at, updated_at
            FROM lithic_financial_accounts
            WHERE organization_id = $1
        """
        args: list[Any] = [organization_id]
        if account_token:
            query += " AND account_token = $2"
            args.append(account_token)
        query += " ORDER BY account_role, created_at DESC"
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]

    async def get_funding_account_for_org(
        self,
        organization_id: str,
        preferred_role: str = "ISSUING",
    ) -> Optional[str]:
        accounts = await self.list_financial_accounts(organization_id)
        if not accounts:
            return None
        by_role = [a for a in accounts if str(a.get("account_role", "")).upper() == preferred_role.upper()]
        if by_role:
            return str(by_role[0].get("financial_account_token", ""))
        return str(accounts[0].get("financial_account_token", ""))

    async def upsert_external_bank_account(self, organization_id: str, external: dict[str, Any]) -> dict[str, Any]:
        token = str(external.get("token", ""))
        if not token:
            raise ValueError("external bank account token is required")
        row = {
            "organization_id": organization_id,
            "external_bank_account_token": token,
            "financial_account_token": external.get("financial_account_token"),
            "owner_type": external.get("owner_type", ""),
            "owner": external.get("owner", ""),
            "account_type": external.get("type", ""),
            "verification_method": external.get("verification_method", ""),
            "verification_state": external.get("verification_state", "PENDING"),
            "state": external.get("state", "ENABLED"),
            "currency": external.get("currency", "USD"),
            "country": external.get("country", "USA"),
            "name": external.get("name"),
            "routing_number": external.get("routing_number"),
            "last_four": external.get("last_four"),
            "user_defined_id": external.get("user_defined_id"),
            "company_id": external.get("company_id"),
            "is_paused": False,
            "pause_reason": None,
            "last_return_reason_code": external.get("verification_failed_reason"),
            "metadata": external,
        }
        if not self._use_postgres():
            self._external_bank_accounts[(organization_id, token)] = row
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO external_bank_accounts (
                    id, organization_id, external_bank_account_token, financial_account_token,
                    owner_type, owner, account_type, verification_method, verification_state,
                    state, currency, country, name, routing_number, last_four, user_defined_id,
                    company_id, is_paused, pause_reason, last_return_reason_code, metadata, created_at, updated_at
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17,
                    $18, $19, $20, $21::jsonb, NOW(), NOW()
                )
                ON CONFLICT (external_bank_account_token) DO UPDATE SET
                    organization_id = EXCLUDED.organization_id,
                    financial_account_token = EXCLUDED.financial_account_token,
                    owner_type = EXCLUDED.owner_type,
                    owner = EXCLUDED.owner,
                    account_type = EXCLUDED.account_type,
                    verification_method = EXCLUDED.verification_method,
                    verification_state = EXCLUDED.verification_state,
                    state = EXCLUDED.state,
                    currency = EXCLUDED.currency,
                    country = EXCLUDED.country,
                    name = EXCLUDED.name,
                    routing_number = EXCLUDED.routing_number,
                    last_four = EXCLUDED.last_four,
                    user_defined_id = EXCLUDED.user_defined_id,
                    company_id = EXCLUDED.company_id,
                    last_return_reason_code = EXCLUDED.last_return_reason_code,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                str(uuid.uuid4()),
                organization_id,
                token,
                row["financial_account_token"],
                row["owner_type"],
                row["owner"],
                row["account_type"],
                row["verification_method"],
                row["verification_state"],
                row["state"],
                row["currency"],
                row["country"],
                row["name"],
                row["routing_number"],
                row["last_four"],
                row["user_defined_id"],
                row["company_id"],
                row["is_paused"],
                row["pause_reason"],
                row["last_return_reason_code"],
                row["metadata"],
            )
            db_row = await conn.fetchrow(
                """
                SELECT * FROM external_bank_accounts
                WHERE organization_id = $1 AND external_bank_account_token = $2
                """,
                organization_id,
                token,
            )
            return dict(db_row) if db_row else row

    async def get_external_bank_account(self, organization_id: str, token: str) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            return self._external_bank_accounts.get((organization_id, token))
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM external_bank_accounts
                WHERE organization_id = $1 AND external_bank_account_token = $2
                """,
                organization_id,
                token,
            )
            return dict(row) if row else None

    async def upsert_ach_payment(
        self,
        organization_id: str,
        payment: dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        payment_token = str(payment.get("token", ""))
        if not payment_token:
            raise ValueError("payment token is required")
        row = {
            "organization_id": organization_id,
            "payment_token": payment_token,
            "financial_account_token": payment.get("financial_account_token", ""),
            "external_bank_account_token": payment.get("external_bank_account_token", ""),
            "direction": payment.get("direction", ""),
            "method": payment.get("method", ""),
            "sec_code": (payment.get("method_attributes", {}) or {}).get("sec_code", "CCD"),
            "currency": payment.get("currency", "USD"),
            "amount_minor": int(payment.get("pending_amount", 0) or 0),
            "status": payment.get("status", "PENDING"),
            "result": payment.get("result"),
            "source": payment.get("source"),
            "provider_reference": payment.get("provider_reference"),
            "user_defined_id": payment.get("user_defined_id"),
            "idempotency_key": idempotency_key,
            "retry_count": 0,
            "last_return_reason_code": None,
            "metadata": payment,
        }

        if not self._use_postgres():
            self._payments[(organization_id, payment_token)] = row
            return row

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ach_payments (
                    id, payment_token, organization_id, financial_account_token, external_bank_account_token,
                    direction, method, sec_code, currency, amount_minor, status, result, source,
                    provider_reference, user_defined_id, idempotency_key, retry_count,
                    metadata, created_at, updated_at
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18::jsonb, NOW(), NOW()
                )
                ON CONFLICT (payment_token) DO UPDATE SET
                    organization_id = EXCLUDED.organization_id,
                    financial_account_token = EXCLUDED.financial_account_token,
                    external_bank_account_token = EXCLUDED.external_bank_account_token,
                    direction = EXCLUDED.direction,
                    method = EXCLUDED.method,
                    sec_code = EXCLUDED.sec_code,
                    currency = EXCLUDED.currency,
                    amount_minor = EXCLUDED.amount_minor,
                    status = EXCLUDED.status,
                    result = EXCLUDED.result,
                    source = EXCLUDED.source,
                    provider_reference = EXCLUDED.provider_reference,
                    user_defined_id = EXCLUDED.user_defined_id,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                str(uuid.uuid4()),
                payment_token,
                organization_id,
                row["financial_account_token"],
                row["external_bank_account_token"],
                row["direction"],
                row["method"],
                row["sec_code"],
                row["currency"],
                row["amount_minor"],
                row["status"],
                row["result"],
                row["source"],
                row["provider_reference"],
                row["user_defined_id"],
                row["idempotency_key"],
                row["retry_count"],
                row["metadata"],
            )
            db_row = await conn.fetchrow(
                "SELECT * FROM ach_payments WHERE organization_id = $1 AND payment_token = $2",
                organization_id,
                payment_token,
            )
            return dict(db_row) if db_row else row

    async def get_ach_payment(self, organization_id: str, payment_token: str) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            return self._payments.get((organization_id, payment_token))
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ach_payments WHERE organization_id = $1 AND payment_token = $2",
                organization_id,
                payment_token,
            )
            return dict(row) if row else None

    async def update_ach_payment_status(
        self,
        organization_id: str,
        payment_token: str,
        status_value: str,
        *,
        result: Optional[str] = None,
        return_reason_code: Optional[str] = None,
        provider_reference: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            row = self._payments.get((organization_id, payment_token))
            if row is None:
                return None
            row["status"] = status_value
            if result is not None:
                row["result"] = result
            if return_reason_code is not None:
                row["last_return_reason_code"] = return_reason_code
            if provider_reference is not None:
                row["provider_reference"] = provider_reference
            row["updated_at"] = datetime.now(timezone.utc)
            return row
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE ach_payments
                SET status = $3,
                    result = COALESCE($4, result),
                    last_return_reason_code = COALESCE($5, last_return_reason_code),
                    provider_reference = COALESCE($6, provider_reference),
                    updated_at = NOW()
                WHERE organization_id = $1 AND payment_token = $2
                RETURNING *
                """,
                organization_id,
                payment_token,
                status_value,
                result,
                return_reason_code,
                provider_reference,
            )
            return dict(row) if row else None

    async def increment_retry_count(self, organization_id: str, payment_token: str) -> None:
        if not self._use_postgres():
            row = self._payments.get((organization_id, payment_token))
            if row:
                row["retry_count"] = int(row.get("retry_count", 0) or 0) + 1
            return
        pool = await self._get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ach_payments
                SET retry_count = retry_count + 1, updated_at = NOW()
                WHERE organization_id = $1 AND payment_token = $2
                """,
                organization_id,
                payment_token,
            )

    async def append_ach_events(self, organization_id: str, payment_token: str, events: list[dict[str, Any]]) -> None:
        if not events:
            return
        if not self._use_postgres():
            for e in events:
                self._payment_events.append(
                    {
                        "organization_id": organization_id,
                        "payment_token": payment_token,
                        "event_token": e.get("token"),
                        "event_type": e.get("type"),
                        "amount_minor": int(e.get("amount", 0) or 0),
                        "result": e.get("result"),
                        "detailed_results": e.get("detailed_results", []),
                        "return_reason_code": e.get("return_reason_code"),
                        "raw_payload": e,
                    }
                )
            return
        pool = await self._get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            for e in events:
                await conn.execute(
                    """
                    INSERT INTO ach_payment_events (
                        id, payment_token, organization_id, event_token, event_type, amount_minor, result,
                        detailed_results, return_reason_code, raw_payload, created_at
                    ) VALUES (
                        $1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10::jsonb, NOW()
                    )
                    ON CONFLICT (organization_id, event_token) WHERE event_token IS NOT NULL DO NOTHING
                    """,
                    str(uuid.uuid4()),
                    payment_token,
                    organization_id,
                    e.get("token"),
                    e.get("type"),
                    int(e.get("amount", 0) or 0),
                    e.get("result"),
                    e.get("detailed_results", []),
                    e.get("return_reason_code"),
                    e,
                )

    async def add_balance_snapshot(
        self,
        organization_id: str,
        financial_account_token: str,
        currency: str,
        available_amount_minor: int,
        pending_amount_minor: int,
        total_amount_minor: int,
        as_of_event_token: Optional[str] = None,
    ) -> dict[str, Any]:
        row = {
            "organization_id": organization_id,
            "financial_account_token": financial_account_token,
            "currency": currency,
            "available_amount_minor": int(available_amount_minor),
            "pending_amount_minor": int(pending_amount_minor),
            "total_amount_minor": int(total_amount_minor),
            "as_of_event_token": as_of_event_token,
            "created_at": datetime.now(timezone.utc),
        }
        if not self._use_postgres():
            self._balance_snapshots.append(row)
            return row
        pool = await self._get_pool()
        if pool is None:
            return row
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO treasury_balance_snapshots (
                    id, organization_id, financial_account_token, currency, available_amount_minor,
                    pending_amount_minor, total_amount_minor, as_of_event_token, created_at
                ) VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, NOW())
                """,
                str(uuid.uuid4()),
                organization_id,
                financial_account_token,
                currency,
                int(available_amount_minor),
                int(pending_amount_minor),
                int(total_amount_minor),
                as_of_event_token,
            )
        return row

    async def list_latest_balance_snapshots(self, organization_id: str) -> list[dict[str, Any]]:
        if not self._use_postgres():
            latest: dict[tuple[str, str], dict[str, Any]] = {}
            for s in self._balance_snapshots:
                if s.get("organization_id") != organization_id:
                    continue
                key = (s.get("financial_account_token", ""), s.get("currency", "USD"))
                prev = latest.get(key)
                if prev is None or s["created_at"] > prev["created_at"]:
                    latest[key] = s
            return list(latest.values())
        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (financial_account_token, currency)
                    organization_id, financial_account_token, currency,
                    available_amount_minor, pending_amount_minor, total_amount_minor,
                    as_of_event_token, provider_updated_at, created_at
                FROM treasury_balance_snapshots
                WHERE organization_id = $1
                ORDER BY financial_account_token, currency, created_at DESC
                """,
                organization_id,
            )
            return [dict(r) for r in rows]

    async def create_reservation(
        self,
        *,
        reservation_id: str,
        organization_id: str,
        wallet_id: Optional[str],
        card_id: Optional[str],
        currency: str,
        amount_minor: int,
        status: str,
        reason: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        row = {
            "reservation_id": reservation_id,
            "organization_id": organization_id,
            "wallet_id": wallet_id,
            "card_id": card_id,
            "currency": currency,
            "amount_minor": amount_minor,
            "status": status,
            "reason": reason,
            "reference_id": reference_id,
            "metadata": metadata or {},
            "updated_at": datetime.now(timezone.utc),
        }
        if not self._use_postgres():
            row["created_at"] = row["updated_at"]
            self._reservations[reservation_id] = row
            return row
        pool = await self._get_pool()
        if pool is None:
            return row
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO treasury_reservations (
                    reservation_id, organization_id, wallet_id, card_id, currency, amount_minor,
                    status, reason, reference_id, metadata, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, NOW(), NOW()
                )
                ON CONFLICT (reservation_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    reason = EXCLUDED.reason,
                    reference_id = EXCLUDED.reference_id,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                reservation_id,
                organization_id,
                wallet_id,
                card_id,
                currency,
                amount_minor,
                status,
                reason,
                reference_id,
                metadata or {},
            )
            db_row = await conn.fetchrow(
                "SELECT * FROM treasury_reservations WHERE reservation_id = $1",
                reservation_id,
            )
            return dict(db_row) if db_row else row

    async def pause_external_bank_account(
        self,
        organization_id: str,
        external_bank_account_token: str,
        reason: str,
        return_code: Optional[str] = None,
    ) -> None:
        if not self._use_postgres():
            row = self._external_bank_accounts.get((organization_id, external_bank_account_token))
            if row:
                row["is_paused"] = True
                row["state"] = "PAUSED"
                row["pause_reason"] = reason
                row["last_return_reason_code"] = return_code
            return
        pool = await self._get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE external_bank_accounts
                SET is_paused = TRUE,
                    state = 'PAUSED',
                    pause_reason = $3,
                    last_return_reason_code = $4,
                    updated_at = NOW()
                WHERE organization_id = $1 AND external_bank_account_token = $2
                """,
                organization_id,
                external_bank_account_token,
                reason,
                return_code,
            )

    async def list_payments_for_reconciliation(
        self,
        organization_id: str,
        *,
        status_filter: Optional[list[str]] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if not self._use_postgres():
            rows = [row for (org, _), row in self._payments.items() if org == organization_id]
            if status_filter:
                allowed = {s.upper() for s in status_filter}
                rows = [r for r in rows if str(r.get("status", "")).upper() in allowed]
            return rows[:limit]
        pool = await self._get_pool()
        if pool is None:
            return []
        async with pool.acquire() as conn:
            if status_filter:
                rows = await conn.fetch(
                    """
                    SELECT * FROM ach_payments
                    WHERE organization_id = $1 AND status = ANY($2::text[])
                    ORDER BY updated_at DESC
                    LIMIT $3
                    """,
                    organization_id,
                    status_filter,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM ach_payments
                    WHERE organization_id = $1
                    ORDER BY updated_at DESC
                    LIMIT $2
                    """,
                    organization_id,
                    limit,
                )
            return [dict(r) for r in rows]

    async def record_treasury_webhook_event(
        self,
        *,
        provider: str,
        event_id: str,
        body: bytes,
        status_value: str = "processed",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        body_hash = hashlib.sha256(body).hexdigest() if body else ""
        if not self._use_postgres():
            self._webhook_events[(provider, event_id)] = {
                "provider": provider,
                "event_id": event_id,
                "body_hash": body_hash,
                "status": status_value,
                "metadata": metadata or {},
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            return
        pool = await self._get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO treasury_webhook_events (provider, event_id, body_hash, status, metadata, processed_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
                ON CONFLICT (provider, event_id) DO UPDATE SET
                    body_hash = EXCLUDED.body_hash,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata,
                    processed_at = NOW()
                """,
                provider,
                event_id,
                body_hash,
                status_value,
                metadata or {},
            )
