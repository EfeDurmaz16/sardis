"""Unified execution intent model for all payment flows.

All route-specific request types (A2A, AP2, checkout) map into ExecutionIntent.
The ControlPlane becomes the single path from intent to execution.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class IntentSource(str, Enum):
    """Origin of the execution intent."""
    A2A = "a2a"
    AP2 = "ap2"
    CHECKOUT = "checkout"
    MANDATE = "mandate"
    CARD = "card"
    DELEGATED_CARD = "delegated_card"
    X402 = "x402"
    ERC8183 = "erc8183"


class IntentStatus(str, Enum):
    """Lifecycle status of an intent."""
    CREATED = "created"
    POLICY_CHECKED = "policy_checked"
    COMPLIANCE_CHECKED = "compliance_checked"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    SIMULATED = "simulated"


@dataclass
class ExecutionIntent:
    """Canonical representation of a payment intent across all flows."""

    intent_id: str = field(default_factory=lambda: f"int_{uuid.uuid4().hex[:16]}")
    source: IntentSource = IntentSource.A2A
    status: IntentStatus = IntentStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Principal context
    org_id: str = ""
    agent_id: str = ""
    idempotency_key: str = ""

    # Payment details
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    chain: str = "base"

    # Parties
    sender_wallet_id: str = ""
    sender_address: str = ""
    recipient_wallet_id: str = ""
    recipient_address: str = ""

    # Execution mode routing (delegated payment support)
    execution_mode: str = ""  # native_crypto, offramp_settlement, delegated_card
    credential_id: str = ""   # dcred_... for delegated card execution

    # Metadata
    memo: str = ""
    reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # Pipeline results (filled during execution)
    policy_result: dict[str, Any] | None = None
    compliance_result: dict[str, Any] | None = None
    tx_hash: str = ""
    ledger_entry_id: str = ""
    receipt_id: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "source": self.source.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "org_id": self.org_id,
            "agent_id": self.agent_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "chain": self.chain,
            "sender_wallet_id": self.sender_wallet_id,
            "recipient_wallet_id": self.recipient_wallet_id,
            "execution_mode": self.execution_mode,
            "credential_id": self.credential_id,
            "tx_hash": self.tx_hash,
            "receipt_id": self.receipt_id,
            "error": self.error,
        }


@dataclass
class ExecutionResult:
    """Result of intent execution."""
    intent_id: str
    success: bool
    status: IntentStatus
    tx_hash: str = ""
    receipt_id: str = ""
    ledger_entry_id: str = ""
    error: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Result of a dry-run simulation."""
    intent_id: str
    would_succeed: bool
    failure_reasons: list[str] = field(default_factory=list)
    policy_result: dict[str, Any] | None = None
    compliance_result: dict[str, Any] | None = None
    cap_check: dict[str, Any] | None = None
    kill_switch_status: dict[str, Any] | None = None
    estimated_gas: str | None = None
