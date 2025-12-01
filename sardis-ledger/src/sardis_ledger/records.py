"""Ledger storage abstractions."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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
        self._records.append(tx)
        return tx

    def list_recent(self, limit: int = 50) -> list[Transaction]:
        return self._records[-limit:]
