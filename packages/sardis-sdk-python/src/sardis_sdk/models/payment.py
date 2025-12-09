"""Payment models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import Field

from .base import SardisModel


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
    purpose: Optional[str] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ExecutePaymentRequest(SardisModel):
    """Request to execute a payment."""
    
    from_wallet: str
    to_address: str
    amount: Decimal
    token: str = "USDC"
    chain: str = "base"
    purpose: Optional[str] = None
    idempotency_key: Optional[str] = None


class ExecutePaymentResponse(SardisModel):
    """Response from payment execution."""
    
    payment_id: str
    status: PaymentStatus
    tx_hash: Optional[str] = None
    chain: str
    audit_anchor: Optional[str] = None
    ledger_tx_id: Optional[str] = None


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
    compliance_provider: Optional[str] = None
    compliance_rule: Optional[str] = None
