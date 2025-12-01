"""Persistence helpers for mandate archives and replay cache."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
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
        self._conn: Optional[sqlite3.Connection] = None
        if dsn and dsn.startswith("sqlite:///"):
            path = _path_from_dsn(dsn)
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mandate_chains (
                    mandate_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            self._conn.commit()
        else:
            self._buffer: list[MandateChain] = []

    def store(self, chain: MandateChain) -> None:
        if not self._conn:
            self._buffer.append(chain)
            return
        payload = json.dumps(asdict(chain))
        self._conn.execute(
            "INSERT OR REPLACE INTO mandate_chains (mandate_id, payload, created_at) VALUES (?, ?, ?)",
            (chain.payment.mandate_id, payload, int(time.time())),
        )
        self._conn.commit()


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
