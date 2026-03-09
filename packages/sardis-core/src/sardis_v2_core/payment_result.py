"""Unified PaymentResult returned by every execution path.

Every payment flow — orchestrator, fiat rails, checkout, x402, etc. —
should converge on this single result type so callers never have to
guess the shape of the response.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PaymentResult:
    """Standard result from PaymentOrchestrator.execute()."""

    status: str  # "success", "rejected", "failed"
    mandate_id: str = ""
    tx_hash: str = ""
    chain: str = ""
    reason: str = ""
    reason_codes: list[str] = field(default_factory=list)
    policy_evidence: dict[str, Any] = field(default_factory=dict)
    compliance_evidence: dict[str, Any] = field(default_factory=dict)
    chain_receipt: Any = None
    ledger_entry_id: str = ""
    attestation_id: str = ""

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_rejected(self) -> bool:
        return self.status == "rejected"

    @classmethod
    def success(
        cls, mandate_id: str, tx_hash: str, chain: str, **kwargs: Any
    ) -> PaymentResult:
        return cls(
            status="success",
            mandate_id=mandate_id,
            tx_hash=tx_hash,
            chain=chain,
            **kwargs,
        )

    @classmethod
    def rejected(
        cls, reason: str, mandate_id: str = "", **kwargs: Any
    ) -> PaymentResult:
        return cls(
            status="rejected",
            reason=reason,
            mandate_id=mandate_id,
            **kwargs,
        )

    @classmethod
    def failed(
        cls, reason: str, mandate_id: str = "", **kwargs: Any
    ) -> PaymentResult:
        return cls(
            status="failed",
            reason=reason,
            mandate_id=mandate_id,
            **kwargs,
        )
