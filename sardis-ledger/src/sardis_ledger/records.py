"""Ledger storage abstractions."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sardis_v2_core.transactions import Transaction, OnChainRecord


@dataclass
class ChainReceipt:
    tx_hash: str
    chain: str
    block_number: int
    audit_anchor: str


class LedgerStore:
    def __init__(self, dsn: str):
        self._dsn = dsn
        if dsn.startswith("sqlite:///"):
            path = Path(dsn.removeprefix("sqlite:///"))
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.execute(
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
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_created ON ledger_entries(created_at)")
            self._conn.commit()
        else:
            self._conn = None
            self._records: list[Transaction] = []

    def append(self, payment_mandate, chain_receipt: ChainReceipt) -> Transaction:
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
        if self._conn:
            self._conn.execute(
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
            self._conn.commit()
        else:
            self._records.append(tx)
        return tx

    def list_recent(self, limit: int = 50) -> list[Transaction]:
        if not self._conn:
            return self._records[-limit:]
        rows = self._conn.execute(
            "SELECT tx_id, from_wallet, to_wallet, amount, currency, chain, chain_tx_hash, audit_anchor, created_at"
            " FROM ledger_entries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        entries: list[Transaction] = []
        for row in rows:
            tx = Transaction(
                tx_id=row[0],
                from_wallet=row[1],
                to_wallet=row[2],
                amount=Decimal(row[3]),
                currency=row[4],
                audit_anchor=row[7],
                created_at=datetime.fromisoformat(row[8]),
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
