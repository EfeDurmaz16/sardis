"""Payment models for Sardis SDK."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import Field

from .base import SardisModel

if TYPE_CHECKING:
    from datetime import datetime


class PaymentStatus(str, Enum):
    """Payment status."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(SardisModel):
    """A payment transaction."""
    
    payment_id: str = Field(alias="id")
    from_wallet: str
    to_wallet: str
    amount: Decimal
    fee: Decimal = Decimal("0")
    token: str = "USDC"
    chain: str = "base"
    status: PaymentStatus
    purpose: str | None = None
    tx_hash: str | None = None
    block_number: int | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ExecutePaymentRequest(SardisModel):
    """Request to execute a payment."""
    
    from_wallet: str
    to_address: str
    amount: Decimal
    token: str = "USDC"
    chain: str = "base"
    purpose: str | None = None
    idempotency_key: str | None = None


class ExecutePaymentResponse(SardisModel):
    """Response from payment execution."""
    
    payment_id: str
    status: PaymentStatus
    tx_hash: str | None = None
    chain: str
    audit_anchor: str | None = None
    ledger_tx_id: str | None = None


class ExecuteMandateRequest(SardisModel):
    """Request to execute a mandate."""
    
    mandate: dict[str, Any]


class ExecuteAP2Request(SardisModel):
    """Request to execute an AP2 payment bundle."""
    
    intent: dict[str, Any]
    cart: dict[str, Any]
    payment: dict[str, Any]


class ExecuteAP2Response(SardisModel):
    """Response from AP2 payment execution."""
    
    mandate_id: str
    ledger_tx_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    status: str
    compliance_provider: str | None = None
    compliance_rule: str | None = None
# Aliases / Placeholders for models used in resources but not fully defined here
PaymentMandate = dict[str, Any]  # Mandates are currently raw dicts in SDK
