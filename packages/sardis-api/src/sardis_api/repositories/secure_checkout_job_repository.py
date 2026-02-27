"""Persistent secure checkout job repository (metadata only, no PAN/CVV)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
import os


class SecureCheckoutJobRepository:
    """Persists secure checkout job metadata to PostgreSQL when configured."""

    def __init__(self, pool=None, dsn: str | None = None):
        self._pool = pool
        self._dsn = dsn or os.getenv("DATABASE_URL", "")
        self._jobs: dict[str, dict[str, Any]] = {}
        self._jobs_by_intent_id: dict[str, str] = {}

    def _use_postgres(self) -> bool:
        if self._pool is not None:
            return True
        return self._dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def _ensure_schema(self) -> None:
        pool = self._pool
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS secure_checkout_jobs (
                    id BIGSERIAL PRIMARY KEY,
                    job_id VARCHAR(80) UNIQUE NOT NULL,
                    intent_id VARCHAR(120) UNIQUE NOT NULL,
                    wallet_id VARCHAR(120) NOT NULL,
                    card_id VARCHAR(120) NOT NULL,
                    merchant_origin TEXT NOT NULL,
                    merchant_mode VARCHAR(40) NOT NULL,
                    status VARCHAR(40) NOT NULL,
                    amount NUMERIC(20, 6) NOT NULL,
                    currency VARCHAR(16) NOT NULL,
                    purpose VARCHAR(120) NOT NULL,
                    approval_required BOOLEAN NOT NULL DEFAULT FALSE,
                    approval_id VARCHAR(120),
                    policy_reason TEXT,
                    executor_ref TEXT,
                    secret_ref VARCHAR(120),
                    secret_expires_at TIMESTAMPTZ,
                    redacted_card JSONB NOT NULL DEFAULT '{}'::jsonb,
                    options JSONB NOT NULL DEFAULT '{}'::jsonb,
                    error_code TEXT,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_secure_checkout_jobs_wallet
                  ON secure_checkout_jobs(wallet_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_secure_checkout_jobs_status
                  ON secure_checkout_jobs(status, updated_at DESC);
                """
            )

    @staticmethod
    def _normalize_job(row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        if not isinstance(result.get("amount"), Decimal):
            result["amount"] = Decimal(str(result.get("amount") or "0"))
        created_at = result.get("created_at")
        updated_at = result.get("updated_at")
        if isinstance(created_at, str):
            result["created_at"] = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            result["updated_at"] = datetime.fromisoformat(updated_at)
        return result

    async def upsert_job(self, job: dict[str, Any]) -> dict[str, Any]:
        if not self._use_postgres():
            existing_id = self._jobs_by_intent_id.get(job["intent_id"])
            if existing_id:
                return dict(self._jobs[existing_id])
            now = datetime.now(timezone.utc)
            item = dict(job)
            item.setdefault("created_at", now)
            item.setdefault("updated_at", now)
            self._jobs[item["job_id"]] = item
            self._jobs_by_intent_id[item["intent_id"]] = item["job_id"]
            return dict(item)

        pool = await self._get_pool()
        if pool is None:
            raise RuntimeError("PostgreSQL pool unavailable")
        async with pool.acquire() as conn:
            inserted = await conn.fetchrow(
                """
                INSERT INTO secure_checkout_jobs (
                    job_id, intent_id, wallet_id, card_id, merchant_origin, merchant_mode, status,
                    amount, currency, purpose, approval_required, approval_id, policy_reason,
                    executor_ref, secret_ref, secret_expires_at, redacted_card, options,
                    error_code, error, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8::numeric, $9, $10, $11, $12, $13,
                    $14, $15, $16::timestamptz, $17::jsonb, $18::jsonb, $19, $20, $21::timestamptz, $22::timestamptz
                )
                ON CONFLICT (intent_id) DO NOTHING
                RETURNING *
                """,
                job["job_id"],
                job["intent_id"],
                job["wallet_id"],
                job["card_id"],
                job["merchant_origin"],
                job["merchant_mode"],
                job["status"],
                str(job["amount"]),
                job["currency"],
                job["purpose"],
                bool(job["approval_required"]),
                job.get("approval_id"),
                job.get("policy_reason"),
                job.get("executor_ref"),
                job.get("secret_ref"),
                job.get("secret_expires_at"),
                job.get("redacted_card") or {},
                job.get("options") or {},
                job.get("error_code"),
                job.get("error"),
                job["created_at"],
                job["updated_at"],
            )
            if inserted:
                return self._normalize_job(dict(inserted))
            existing = await conn.fetchrow(
                "SELECT * FROM secure_checkout_jobs WHERE intent_id = $1",
                job["intent_id"],
            )
            if not existing:
                raise RuntimeError("secure_checkout_job_upsert_failed")
            return self._normalize_job(dict(existing))

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        if not self._use_postgres():
            item = self._jobs.get(job_id)
            return dict(item) if item else None
        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM secure_checkout_jobs WHERE job_id = $1",
                job_id,
            )
            return self._normalize_job(dict(row)) if row else None

    async def update_job(self, job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        if not fields:
            return await self.get_job(job_id)
        if not self._use_postgres():
            existing = self._jobs.get(job_id)
            if not existing:
                return None
            updated = dict(existing)
            updated.update(fields)
            updated["updated_at"] = datetime.now(timezone.utc)
            self._jobs[job_id] = updated
            return dict(updated)

        allowed = {
            "status",
            "approval_id",
            "executor_ref",
            "secret_ref",
            "secret_expires_at",
            "error_code",
            "error",
            "policy_reason",
        }
        set_fragments: list[str] = []
        values: list[Any] = []
        idx = 1
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "secret_expires_at":
                set_fragments.append(f"{key} = ${idx}::timestamptz")
            else:
                set_fragments.append(f"{key} = ${idx}")
            values.append(value)
            idx += 1
        if not set_fragments:
            return await self.get_job(job_id)

        values.append(job_id)
        sql = (
            "UPDATE secure_checkout_jobs "
            f"SET {', '.join(set_fragments)}, updated_at = NOW() "
            f"WHERE job_id = ${idx} RETURNING *"
        )

        pool = await self._get_pool()
        if pool is None:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, *values)
            return self._normalize_job(dict(row)) if row else None
