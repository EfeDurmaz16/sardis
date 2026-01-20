"""Checkout surface data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class PSPType(str, Enum):
    """Payment Service Provider types."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    COINBASE = "coinbase"
    CIRCLE = "circle"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class CheckoutRequest:
    """Request to create a checkout session."""
    agent_id: str
    wallet_id: str
    mandate_id: str
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    chain: Optional[str] = None  # For on-chain mode
    token: Optional[str] = None  # For on-chain mode
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckoutResponse:
    """Checkout response from PSP."""
    checkout_id: str
    redirect_url: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    psp_name: Optional[str] = None
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    agent_id: str = ""
    mandate_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    psp_payment_id: Optional[str] = None  # PSP's payment ID


@dataclass
class CheckoutSession:
    """Checkout session created by PSP (legacy, for backwards compatibility)."""
    session_id: str
    psp: PSPType
    checkout_url: str
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    agent_id: str = ""
    merchant_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    psp_payment_id: Optional[str] = None  # PSP's payment ID


@dataclass
class PSPConfig:
    """PSP configuration."""
    psp: PSPType
    enabled: bool = True
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MerchantConfig:
    """Merchant configuration."""
    merchant_id: str
    preferred_psps: list[PSPType] = field(default_factory=list)
    psp_configs: dict[PSPType, PSPConfig] = field(default_factory=dict)
    default_currency: str = "USD"
    metadata: dict[str, Any] = field(default_factory=dict)
