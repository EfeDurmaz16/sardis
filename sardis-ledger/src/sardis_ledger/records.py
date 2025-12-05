"""Ledger storage abstractions."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sardis_v2_core.transactions import Transaction, OnChainRecord


@dataclass
class ChainReceipt:
    tx_hash: str
    chain: str
    block_number: int
    audit_anchor: str


class LedgerStore:
    """Ledger storage supporting both SQLite (dev) and PostgreSQL (production)."""
    
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._pg_pool = None
        self._records: list[Transaction] = []
        
        if dsn.startswith("sqlite:///"):
            # SQLite for local development
            path = Path(dsn.removeprefix("sqlite:///"))
            path.parent.mkdir(parents=True, exist_ok=True)
            self._sqlite_conn = sqlite3.connect(path, check_same_thread=False)
            self._sqlite_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ledger_entries (
                    tx_id TEXT PRIMARY KEY,
                    mandate_id TEXT,
                    from_wallet TEXT,
                    to_wallet TEXT,
                    amount TEXT,
                    currency TEXT,
                    chain TEXT,
                    chain_tx_hash TEXT,
                    audit_anchor TEXT,
                    created_at TEXT
                )
                """
            )
            self._sqlite_conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_created ON ledger_entries(created_at)")
            self._sqlite_conn.commit()
        elif dsn.startswith("postgresql://") or dsn.startswith("postgres://"):
            # PostgreSQL for production - pool will be created on first use
            self._use_postgres = True
        else:
            # In-memory fallback
            self._use_postgres = False
    
    async def _get_pg_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pg_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pg_pool

    def append(self, payment_mandate, chain_receipt: ChainReceipt) -> Transaction:
        """Append a transaction to the ledger (sync version for SQLite)."""
        amount = Decimal(payment_mandate.amount_minor) / Decimal(10**2)
        tx = Transaction(
            from_wallet=payment_mandate.subject,
            to_wallet=payment_mandate.destination,
            amount=amount,
            currency=payment_mandate.token,
            audit_anchor=chain_receipt.audit_anchor,
        )
        tx.add_on_chain_record(
            OnChainRecord(
                chain=chain_receipt.chain,
                tx_hash=chain_receipt.tx_hash,
                from_address=payment_mandate.subject,
                to_address=payment_mandate.destination,
                block_number=chain_receipt.block_number,
                status="confirmed" if chain_receipt.block_number else "pending",
            )
        )
        created_at = tx.created_at.isoformat()
        if self._sqlite_conn:
            self._sqlite_conn.execute(
                """
                INSERT OR REPLACE INTO ledger_entries (
                    tx_id, mandate_id, from_wallet, to_wallet, amount, currency, chain,
                    chain_tx_hash, audit_anchor, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.tx_id,
                    payment_mandate.mandate_id,
                    payment_mandate.subject,
                    payment_mandate.destination,
                    str(amount),
                    payment_mandate.token,
                    chain_receipt.chain,
                    chain_receipt.tx_hash,
                    chain_receipt.audit_anchor,
                    created_at,
                ),
            )
            self._sqlite_conn.commit()
        else:
            self._records.append(tx)
        return tx
    
    async def append_async(self, payment_mandate, chain_receipt: ChainReceipt) -> Transaction:
        """Append a transaction to the ledger (async version for PostgreSQL)."""
        amount = Decimal(payment_mandate.amount_minor) / Decimal(10**2)
        tx = Transaction(
            from_wallet=payment_mandate.subject,
            to_wallet=payment_mandate.destination,
            amount=amount,
            currency=payment_mandate.token,
            audit_anchor=chain_receipt.audit_anchor,
        )
        tx.add_on_chain_record(
            OnChainRecord(
                chain=chain_receipt.chain,
                tx_hash=chain_receipt.tx_hash,
                from_address=payment_mandate.subject,
                to_address=payment_mandate.destination,
                block_number=chain_receipt.block_number,
                status="confirmed" if chain_receipt.block_number else "pending",
            )
        )
        
        if hasattr(self, '_use_postgres') and self._use_postgres:
            pool = await self._get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO ledger_entries (
                        tx_id, mandate_id, from_wallet, to_wallet, amount, currency, chain,
                        chain_tx_hash, audit_anchor, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    ON CONFLICT (tx_id) DO UPDATE SET
                        chain_tx_hash = EXCLUDED.chain_tx_hash,
                        audit_anchor = EXCLUDED.audit_anchor
                    """,
                    tx.tx_id,
                    payment_mandate.mandate_id,
                    payment_mandate.subject,
                    payment_mandate.destination,
                    float(amount),
                    payment_mandate.token,
                    chain_receipt.chain,
                    chain_receipt.tx_hash,
                    chain_receipt.audit_anchor,
                )
        elif self._sqlite_conn:
            # Fall back to sync SQLite
            return self.append(payment_mandate, chain_receipt)
        else:
            self._records.append(tx)
        
        return tx

    def list_recent(self, limit: int = 50) -> list[Transaction]:
        """List recent transactions (sync version for SQLite)."""
        if not self._sqlite_conn:
            return self._records[-limit:]
        rows = self._sqlite_conn.execute(
            "SELECT tx_id, from_wallet, to_wallet, amount, currency, chain, chain_tx_hash, audit_anchor, created_at"
            " FROM ledger_entries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return self._rows_to_transactions(rows)
    
    async def list_recent_async(self, limit: int = 50) -> list[Transaction]:
        """List recent transactions (async version for PostgreSQL)."""
        if hasattr(self, '_use_postgres') and self._use_postgres:
            pool = await self._get_pg_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT tx_id, from_wallet, to_wallet, amount, currency, chain, 
                           chain_tx_hash, audit_anchor, created_at
                    FROM ledger_entries 
                    ORDER BY created_at DESC 
                    LIMIT $1
                    """,
                    limit,
                )
                return self._rows_to_transactions(rows, is_asyncpg=True)
        else:
            return self.list_recent(limit)
    
    def _rows_to_transactions(self, rows, is_asyncpg: bool = False) -> list[Transaction]:
        """Convert database rows to Transaction objects."""
        entries: list[Transaction] = []
        for row in rows:
            if is_asyncpg:
                # asyncpg returns Record objects
                tx = Transaction(
                    tx_id=row['tx_id'],
                    from_wallet=row['from_wallet'],
                    to_wallet=row['to_wallet'],
                    amount=Decimal(str(row['amount'])),
                    currency=row['currency'],
                    audit_anchor=row['audit_anchor'],
                    created_at=row['created_at'],
                )
                tx.add_on_chain_record(
                    OnChainRecord(
                        chain=row['chain'],
                        tx_hash=row['chain_tx_hash'],
                        from_address=row['from_wallet'],
                        to_address=row['to_wallet'],
                        status="confirmed",
                    )
                )
            else:
                # SQLite returns tuples
                tx = Transaction(
                    tx_id=row[0],
                    from_wallet=row[1],
                    to_wallet=row[2],
                    amount=Decimal(row[3]),
                    currency=row[4],
                    audit_anchor=row[7],
                    created_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                )
                tx.add_on_chain_record(
                    OnChainRecord(
                        chain=row[5],
                        tx_hash=row[6],
                        from_address=row[1],
                        to_address=row[2],
                        status="confirmed",
                    )
                )
            entries.append(tx)
        return entries
