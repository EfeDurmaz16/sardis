"""Multi-chain stablecoin executor."""
from __future__ import annotations

from dataclasses import dataclass

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate
from sardis_ledger.records import ChainReceipt


@dataclass
class SubmittedTx:
    tx_hash: str
    chain: str
    audit_anchor: str


class ChainExecutor:
    def __init__(self, settings: SardisSettings):
        self._settings = settings

    async def dispatch_payment(self, mandate: PaymentMandate) -> ChainReceipt:
        # TODO: wire in actual Turnkey/Fireblocks integration. For now we simulate.
        tx_hash = f"0x{mandate.mandate_id[:32]}"
        audit_anchor = f"merkle::{mandate.audit_hash}"
        return ChainReceipt(tx_hash=tx_hash, chain=mandate.chain, block_number=0, audit_anchor=audit_anchor)
