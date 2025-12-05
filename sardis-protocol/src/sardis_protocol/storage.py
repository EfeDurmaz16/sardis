"""Persistence helpers for mandate archives and replay cache."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sardis_v2_core.mandates import MandateChain


def _path_from_dsn(dsn: str) -> Path:
    if not dsn.startswith("sqlite:///"):
        raise ValueError(f"unsupported DSN: {dsn}")
    path = Path(dsn.removeprefix("sqlite:///"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class MandateArchive:
    """Stores verified mandate chains for audit trail."""

    def __init__(self, dsn: str | None = None):
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._pg_pool = None
        self._use_postgres = False
        self._dsn = dsn
        self._buffer: list[MandateChain] = []
        
        if dsn and dsn.startswith("sqlite:///"):
            path = _path_from_dsn(dsn)
            self._sqlite_conn = sqlite3.connect(path, check_same_thread=False)
            self._sqlite_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mandate_chains (
                    mandate_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            self._sqlite_conn.commit()
        elif dsn and (dsn.startswith("postgresql://") or dsn.startswith("postgres://")):
            self._use_postgres = True
    
    async def _get_pg_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pg_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pg_pool

    def store(self, chain: MandateChain) -> None:
        """Store mandate chain (sync version for SQLite)."""
        if not self._sqlite_conn:
            self._buffer.append(chain)
            return
        payload = json.dumps(asdict(chain))
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO mandate_chains (mandate_id, payload, created_at) VALUES (?, ?, ?)",
            (chain.payment.mandate_id, payload, int(time.time())),
        )
        self._sqlite_conn.commit()
    
    async def store_async(self, chain: MandateChain) -> None:
        """Store mandate chain (async version for PostgreSQL)."""
        if self._use_postgres:
            pool = await self._get_pg_pool()
            payload = json.dumps(asdict(chain))
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO mandate_chains (payment_id, verified_at)
                    VALUES ($1, NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    chain.payment.mandate_id,
                )
                # Also store in mandates table for full audit
                await conn.execute(
                    """
                    INSERT INTO mandates (mandate_id, mandate_type, issuer, subject, payload, created_at)
                    VALUES ($1, 'payment', $2, $3, $4, NOW())
                    ON CONFLICT (mandate_id) DO UPDATE SET verified_at = NOW()
                    """,
                    chain.payment.mandate_id,
                    chain.payment.issuer,
                    chain.payment.subject,
                    payload,
                )
        elif self._sqlite_conn:
            self.store(chain)
        else:
            self._buffer.append(chain)


class ReplayCache:
    """In-memory replay cache fallback."""

    def __init__(self):
        self._seen: dict[str, int] = {}

    def check_and_store(self, mandate_id: str, expires_at: int) -> bool:
        deadline = self._seen.get(mandate_id)
        now = int(time.time())
        if deadline and deadline > now:
            return False
        self._seen[mandate_id] = expires_at
        return True


class SqliteReplayCache(ReplayCache):
    """Durable replay cache backed by sqlite."""

    def __init__(self, dsn: str):
        super().__init__()
        if not dsn.startswith("sqlite:///"):
            raise ValueError("SqliteReplayCache requires sqlite DSN")
        path = _path_from_dsn(dsn)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS replay_cache (
                mandate_id TEXT PRIMARY KEY,
                expires_at INTEGER NOT NULL
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_replay_exp ON replay_cache(expires_at)")
        self._conn.commit()

    def check_and_store(self, mandate_id: str, expires_at: int) -> bool:  # type: ignore[override]
        now = int(time.time())
        self._conn.execute("DELETE FROM replay_cache WHERE expires_at <= ?", (now,))
        row = self._conn.execute(
            "SELECT expires_at FROM replay_cache WHERE mandate_id = ?",
            (mandate_id,),
        ).fetchone()
        if row and row[0] > now:
            return False
        self._conn.execute(
            "INSERT OR REPLACE INTO replay_cache (mandate_id, expires_at) VALUES (?, ?)",
            (mandate_id, expires_at),
        )
        self._conn.commit()
        return True


class PostgresReplayCache(ReplayCache):
    """Durable replay cache backed by PostgreSQL."""

    def __init__(self, dsn: str):
        super().__init__()
        self._dsn = dsn
        self._pool = None
    
    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pool

    async def check_and_store_async(self, mandate_id: str, expires_at: int) -> bool:
        """Check and store mandate ID (async version for PostgreSQL)."""
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        
        async with pool.acquire() as conn:
            # Clean up expired entries
            await conn.execute(
                "DELETE FROM replay_cache WHERE expires_at <= $1",
                now,
            )
            
            # Check if mandate exists and is not expired
            row = await conn.fetchrow(
                "SELECT expires_at FROM replay_cache WHERE mandate_id = $1",
                mandate_id,
            )
            if row and row['expires_at'] > now:
                return False
            
            # Store the mandate
            await conn.execute(
                """
                INSERT INTO replay_cache (mandate_id, expires_at) 
                VALUES ($1, $2)
                ON CONFLICT (mandate_id) DO UPDATE SET expires_at = EXCLUDED.expires_at
                """,
                mandate_id,
                expires_dt,
            )
            return True
