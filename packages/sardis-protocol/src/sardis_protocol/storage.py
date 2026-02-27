"""Persistence helpers for mandate archives and replay cache."""
from __future__ import annotations

import json
import sqlite3
import threading
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
            from sardis_v2_core.database import Database
            self._pg_pool = await Database.get_pool()
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
    """In-memory replay cache with TTL cleanup.
    
    Prevents memory leaks by automatically cleaning up expired entries.
    
    Args:
        default_ttl_seconds: Default TTL for entries (24 hours).
        cleanup_interval_seconds: How often to run cleanup (5 minutes).
        max_entries: Maximum entries before forced cleanup (100,000).
    """
    
    DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24 hours
    CLEANUP_INTERVAL_SECONDS = 5 * 60  # 5 minutes
    MAX_ENTRIES = 100000

    def __init__(
        self,
        default_ttl_seconds: int = DEFAULT_TTL_SECONDS,
        cleanup_interval_seconds: int = CLEANUP_INTERVAL_SECONDS,
        max_entries: int = MAX_ENTRIES,
    ):
        self._seen: dict[str, int] = {}
        self._default_ttl = default_ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._max_entries = max_entries
        self._last_cleanup = time.time()
        self._lock = threading.RLock()

    def check_and_store(self, mandate_id: str, expires_at: int) -> bool:
        """Check if mandate was seen and store if not."""
        with self._lock:
            now = int(time.time())

            # Run periodic cleanup
            self._maybe_cleanup(now)

            deadline = self._seen.get(mandate_id)
            if deadline and deadline > now:
                return False

            # Use default TTL if expires_at is not set or too far in future
            if expires_at <= now:
                expires_at = now + self._default_ttl

            self._seen[mandate_id] = expires_at
            return True
    
    def _maybe_cleanup(self, now: int) -> None:
        """Run cleanup if interval has passed or at max capacity."""
        should_cleanup = (
            (now - self._last_cleanup) >= self._cleanup_interval
            or len(self._seen) >= self._max_entries
        )
        if should_cleanup:
            self.cleanup(now)
    
    def cleanup(self, now: Optional[int] = None) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            if now is None:
                now = int(time.time())

            expired = [
                mandate_id
                for mandate_id, expires_at in self._seen.items()
                if expires_at <= now
            ]
            for mandate_id in expired:
                del self._seen[mandate_id]

            self._last_cleanup = now
            return len(expired)
    
    def stats(self) -> dict:
        """Return cache statistics."""
        now = int(time.time())
        expired_count = sum(1 for exp in self._seen.values() if exp <= now)
        return {
            "total_entries": len(self._seen),
            "expired_entries": expired_count,
            "active_entries": len(self._seen) - expired_count,
            "max_entries": self._max_entries,
            "last_cleanup": self._last_cleanup,
        }
    
    def clear(self) -> None:
        """Clear all entries."""
        self._seen.clear()
        self._last_cleanup = time.time()


class SqliteReplayCache(ReplayCache):
    """Durable replay cache backed by sqlite with automatic cleanup."""

    def __init__(
        self,
        dsn: str,
        default_ttl_seconds: int = ReplayCache.DEFAULT_TTL_SECONDS,
        cleanup_interval_seconds: int = ReplayCache.CLEANUP_INTERVAL_SECONDS,
    ):
        super().__init__(
            default_ttl_seconds=default_ttl_seconds,
            cleanup_interval_seconds=cleanup_interval_seconds,
        )
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

        # Periodic cleanup (not on every call)
        if (now - self._last_cleanup) >= self._cleanup_interval:
            self.cleanup(now)

        # Use default TTL if expires_at is not set
        if expires_at <= now:
            expires_at = now + self._default_ttl

        # SECURITY: Use lock to prevent TOCTOU race between SELECT and INSERT.
        # Without this, two concurrent threads could both see "not found" and
        # both return True, allowing a mandate to be executed twice.
        with self._lock:
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
    
    def cleanup(self, now: Optional[int] = None) -> int:
        """Remove expired entries from database."""
        if now is None:
            now = int(time.time())
        
        cursor = self._conn.execute(
            "DELETE FROM replay_cache WHERE expires_at <= ?",
            (now,),
        )
        self._conn.commit()
        self._last_cleanup = now
        return cursor.rowcount
    
    def stats(self) -> dict:
        """Return cache statistics from database."""
        now = int(time.time())
        total = self._conn.execute(
            "SELECT COUNT(*) FROM replay_cache"
        ).fetchone()[0]
        expired = self._conn.execute(
            "SELECT COUNT(*) FROM replay_cache WHERE expires_at <= ?",
            (now,),
        ).fetchone()[0]
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "last_cleanup": self._last_cleanup,
        }
    
    def clear(self) -> None:
        """Clear all entries from database."""
        self._conn.execute("DELETE FROM replay_cache")
        self._conn.commit()
        self._last_cleanup = time.time()


class PostgresReplayCache(ReplayCache):
    """Durable replay cache backed by PostgreSQL with automatic cleanup."""

    def __init__(
        self,
        dsn: str,
        default_ttl_seconds: int = ReplayCache.DEFAULT_TTL_SECONDS,
        cleanup_interval_seconds: int = ReplayCache.CLEANUP_INTERVAL_SECONDS,
    ):
        super().__init__(
            default_ttl_seconds=default_ttl_seconds,
            cleanup_interval_seconds=cleanup_interval_seconds,
        )
        self._dsn = dsn
        self._pool = None
    
    async def _get_pool(self):
        if self._pool is None:
            from sardis_v2_core.database import Database
            self._pool = await Database.get_pool()
        return self._pool

    async def check_and_store_async(self, mandate_id: str, expires_at: int) -> bool:
        """Check and store mandate ID (async version for PostgreSQL).

        SECURITY: Uses a single atomic INSERT ... ON CONFLICT to prevent TOCTOU
        race conditions. The xmax trick detects whether the row was truly inserted
        (new mandate) vs. updated (already seen).
        """
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        now_ts = int(now.timestamp())

        # Use default TTL if expires_at is not set
        if expires_at <= now_ts:
            expires_at = now_ts + self._default_ttl

        expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)

        async with pool.acquire() as conn:
            # Periodic cleanup (not on every call)
            if (now_ts - self._last_cleanup) >= self._cleanup_interval:
                await self.cleanup_async()

            # Atomic check-and-store: INSERT if not exists, otherwise check expiry.
            # Returns whether the mandate is new (True) or already seen (False).
            row = await conn.fetchrow(
                """
                INSERT INTO replay_cache (mandate_id, expires_at)
                VALUES ($1, $2)
                ON CONFLICT (mandate_id) DO UPDATE
                    SET expires_at = CASE
                        WHEN replay_cache.expires_at <= $3 THEN EXCLUDED.expires_at
                        ELSE replay_cache.expires_at
                    END
                RETURNING (xmax = 0) AS was_inserted,
                          expires_at
                """,
                mandate_id,
                expires_dt,
                now,
            )
            if row is None:
                return True
            # was_inserted=True means new row; if existing but expired we updated it
            if row["was_inserted"]:
                return True
            # Existing row — if its expiry is our new value, it was expired and we renewed it
            if row["expires_at"] == expires_dt:
                return True
            # Existing row with a future expiry — mandate already seen
            return False
    
    async def cleanup_async(self) -> int:
        """Remove expired entries from database."""
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM replay_cache WHERE expires_at <= $1",
                now,
            )
            # Parse "DELETE N" to get count
            count = int(result.split()[-1]) if result else 0
        
        self._last_cleanup = int(now.timestamp())
        return count
    
    async def stats_async(self) -> dict:
        """Return cache statistics from database."""
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)
        
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM replay_cache"
            )
            expired = await conn.fetchval(
                "SELECT COUNT(*) FROM replay_cache WHERE expires_at <= $1",
                now,
            )
        
        return {
            "total_entries": total or 0,
            "expired_entries": expired or 0,
            "active_entries": (total or 0) - (expired or 0),
            "last_cleanup": self._last_cleanup,
        }
    
    async def clear_async(self) -> None:
        """Clear all entries from database."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM replay_cache")
        self._last_cleanup = int(time.time())
