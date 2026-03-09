"""Machine-verifiable execution receipts for compliance and audit.

Every payment produces an ExecutionReceipt containing hashes of the
intent, policy snapshot, compliance result, and ledger IDs — signed
with HMAC for tamper detection.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def _receipt_id() -> str:
    return f"rcpt_{uuid.uuid4().hex[:16]}"


def _now() -> float:
    return time.time()


@dataclass
class ExecutionReceipt:
    """Signed proof that a payment was executed through the full pipeline."""

    receipt_id: str = field(default_factory=_receipt_id)
    timestamp: float = field(default_factory=_now)

    # Hashes of pipeline artifacts
    intent_hash: str = ""           # SHA-256 of the original payment intent/mandate
    policy_snapshot_hash: str = ""  # SHA-256 of the policy config at evaluation time
    compliance_result_hash: str = ""  # SHA-256 of the compliance check result

    # Execution outputs
    tx_hash: str = ""               # On-chain transaction hash
    chain: str = ""
    ledger_entry_id: str = ""       # Sardis ledger entry ID
    ledger_tx_id: str = ""          # Sardis ledger transaction ID

    # Context
    org_id: str = ""
    agent_id: str = ""
    amount: str = ""
    currency: str = ""

    # HMAC signature for tamper detection
    signature: str = ""

    def compute_signature(self, secret: str | None = None) -> str:
        """Compute HMAC-SHA256 signature over receipt fields."""
        resolved = secret or os.getenv("SARDIS_RECEIPT_HMAC_KEY", "")
        if not resolved:
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env in ("prod", "production", "staging"):
                raise RuntimeError(
                    "SARDIS_RECEIPT_HMAC_KEY must be set in production/staging. "
                    "Refusing to sign with a default key."
                )
            resolved = "dev-receipt-key"
        key = resolved.encode()
        payload = "|".join([
            self.receipt_id,
            str(self.timestamp),
            self.intent_hash,
            self.policy_snapshot_hash,
            self.compliance_result_hash,
            self.tx_hash,
            self.chain,
            self.ledger_entry_id,
            self.org_id,
            self.agent_id,
            self.amount,
            self.currency,
        ])
        return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()

    def sign(self, secret: str | None = None) -> ExecutionReceipt:
        """Sign the receipt in place and return self for chaining."""
        self.signature = self.compute_signature(secret)
        return self

    def verify(self, secret: str | None = None) -> bool:
        """Verify the HMAC signature."""
        expected = self.compute_signature(secret)
        return hmac.compare_digest(self.signature, expected)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionReceipt:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def hash_artifact(data: Any) -> str:
    """SHA-256 hash any JSON-serializable artifact."""
    if isinstance(data, str):
        raw = data
    elif isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    else:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def build_receipt(
    *,
    intent: Any = None,
    policy_snapshot: Any = None,
    compliance_result: Any = None,
    tx_hash: str = "",
    chain: str = "",
    ledger_entry_id: str = "",
    ledger_tx_id: str = "",
    org_id: str = "",
    agent_id: str = "",
    amount: str = "",
    currency: str = "",
) -> ExecutionReceipt:
    """Build and sign an execution receipt from pipeline artifacts."""
    receipt = ExecutionReceipt(
        intent_hash=hash_artifact(intent) if intent else "",
        policy_snapshot_hash=hash_artifact(policy_snapshot) if policy_snapshot else "",
        compliance_result_hash=hash_artifact(compliance_result) if compliance_result else "",
        tx_hash=tx_hash,
        chain=chain,
        ledger_entry_id=ledger_entry_id,
        ledger_tx_id=ledger_tx_id,
        org_id=org_id,
        agent_id=agent_id,
        amount=amount,
        currency=currency,
    )
    return receipt.sign()
