"""Checkout surface data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, List, Dict
import json
import uuid


# Session timeout reduced from 30 minutes to 15 minutes (audit fix #1)
DEFAULT_SESSION_TIMEOUT_MINUTES = 15
DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS = 24


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
    PARTIALLY_PAID = "partially_paid"
    EXPIRED = "expired"


class CheckoutEventType(str, Enum):
    """Checkout analytics event types."""
    SESSION_CREATED = "checkout.session.created"
    SESSION_STARTED = "checkout.session.started"
    SESSION_COMPLETED = "checkout.session.completed"
    SESSION_EXPIRED = "checkout.session.expired"
    SESSION_ABANDONED = "checkout.session.abandoned"
    PAYMENT_INITIATED = "checkout.payment.initiated"
    PAYMENT_SUCCEEDED = "checkout.payment.succeeded"
    PAYMENT_FAILED = "checkout.payment.failed"
    PAYMENT_REFUNDED = "checkout.payment.refunded"
    PARTIAL_PAYMENT = "checkout.payment.partial"
    FRAUD_CHECK_PASSED = "checkout.fraud.passed"
    FRAUD_CHECK_FAILED = "checkout.fraud.failed"
    FRAUD_CHECK_REVIEW = "checkout.fraud.review"
    WEBHOOK_RECEIVED = "checkout.webhook.received"
    WEBHOOK_PROCESSED = "checkout.webhook.processed"
    CURRENCY_CONVERTED = "checkout.currency.converted"


class FraudRiskLevel(str, Enum):
    """Fraud risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudDecision(str, Enum):
    """Fraud check decision."""
    # Legacy decision label used in older integrations/tests.
    ALLOW = "allow"
    APPROVE = "approve"
    REVIEW = "review"
    DECLINE = "decline"
    CHALLENGE = "challenge"


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


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
    # Idempotency support (audit fix #2)
    idempotency_key: Optional[str] = None
    # Session timeout (audit fix #1)
    session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES
    # Partial payment support
    allow_partial_payment: bool = False
    minimum_payment_amount: Optional[Decimal] = None
    # Multi-currency support
    accepted_currencies: List[str] = field(default_factory=lambda: ["USD"])
    auto_convert_currency: bool = False
    # Customization options
    customization: Optional["CheckoutCustomization"] = None
    # Customer session
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    # Payment link
    create_payment_link: bool = False
    payment_link_expiration_hours: int = DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS


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
    # Idempotency support
    idempotency_key: Optional[str] = None
    is_duplicate: bool = False
    # Partial payment support
    amount_paid: Decimal = Decimal("0")
    amount_remaining: Decimal = Decimal("0")
    partial_payments: List["PartialPayment"] = field(default_factory=list)
    # Multi-currency
    original_currency: Optional[str] = None
    original_amount: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    # Payment link
    payment_link_url: Optional[str] = None
    payment_link_id: Optional[str] = None
    payment_link_expires_at: Optional[datetime] = None
    # Fraud check result
    fraud_check_result: Optional["FraudCheckResult"] = None
    # Customer session
    customer_session_id: Optional[str] = None


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


# Idempotency support models (audit fix #2)
@dataclass
class IdempotencyRecord:
    """Record for tracking idempotent operations."""
    idempotency_key: str
    operation: str
    request_hash: str
    response: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24)
    )
    agent_id: Optional[str] = None
    checkout_id: Optional[str] = None
    # Backward-compatible fields expected by older tests/clients.
    response_code: Optional[int] = None
    response_body: Optional[str] = None

    def __post_init__(self) -> None:
        # Legacy shape -> canonical shape.
        if self.response is None and self.response_body is not None:
            try:
                self.response = json.loads(self.response_body)
            except Exception:
                self.response = {"raw": self.response_body}

        # Canonical shape -> legacy fields.
        if self.response is not None and self.response_body is None:
            try:
                self.response_body = json.dumps(self.response, default=str)
            except Exception:
                self.response_body = str(self.response)

        if self.response_code is None and self.status == "completed" and self.response is not None:
            self.response_code = 200


# Analytics models (audit fix #3)
@dataclass
class CheckoutAnalyticsEvent:
    """Checkout analytics event for tracking."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: CheckoutEventType = CheckoutEventType.SESSION_CREATED
    checkout_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    customer_id: Optional[str] = None
    psp_name: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None


# Partial payment models
@dataclass
class PartialPayment:
    """Record of a partial payment."""
    payment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checkout_id: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    psp_payment_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.COMPLETED
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Multi-currency models
@dataclass
class CurrencyConversion:
    """Currency conversion record."""
    conversion_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_currency: str = "USD"
    to_currency: str = "USD"
    from_amount: Decimal = Decimal("0")
    to_amount: Decimal = Decimal("0")
    exchange_rate: Decimal = Decimal("1")
    rate_source: str = "internal"
    rate_timestamp: datetime = field(default_factory=datetime.utcnow)
    fee_amount: Decimal = Decimal("0")
    fee_currency: str = "USD"


@dataclass
class SupportedCurrency:
    """Supported currency configuration."""
    code: str  # ISO 4217 code
    name: str
    symbol: str
    decimal_places: int = 2
    min_amount: Decimal = Decimal("0.01")
    max_amount: Decimal = Decimal("1000000")
    enabled: bool = True


# Customer session models
@dataclass
class CustomerSession:
    """Customer checkout session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    agent_id: str = ""
    status: str = "active"  # active, completed, expired, abandoned
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=DEFAULT_SESSION_TIMEOUT_MINUTES)
    )
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    checkout_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None


# Payment link models
@dataclass
class PaymentLink:
    """Payment link for sharing."""
    link_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checkout_id: str = ""
    url: str = ""
    short_url: Optional[str] = None
    status: str = "active"  # active, used, expired, revoked
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS)
    )
    used_at: Optional[datetime] = None
    max_uses: int = 1
    use_count: int = 0
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Webhook delivery models
@dataclass
class WebhookDelivery:
    """Webhook delivery record with retry support."""
    delivery_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    webhook_id: str = ""
    endpoint_url: str = ""
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    response_status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class WebhookEndpoint:
    """Registered webhook endpoint."""
    endpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    secret: str = ""
    events: List[str] = field(default_factory=list)  # Event types to receive
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    failure_count: int = 0
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None


# Checkout customization models
@dataclass
class CheckoutCustomization:
    """Checkout UI and behavior customization."""
    # Branding
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    background_color: Optional[str] = None
    button_color: Optional[str] = None
    font_family: Optional[str] = None
    # Display
    display_name: Optional[str] = None
    display_description: Optional[str] = None
    terms_url: Optional[str] = None
    privacy_url: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    # Behavior
    collect_billing_address: bool = False
    collect_shipping_address: bool = False
    collect_phone_number: bool = False
    require_terms_acceptance: bool = False
    allow_promotion_codes: bool = False
    # Locale
    locale: str = "en"
    # Custom fields
    custom_fields: List[Dict[str, Any]] = field(default_factory=list)
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


# Fraud detection models
@dataclass
class FraudSignal:
    """Individual fraud detection signal."""
    signal_type: str = ""  # e.g., "velocity", "geolocation", "device"
    signal_value: Any = None
    risk_score: float = 0.0  # Supports both 0..1 and 0..100 conventions
    confidence: float = 1.0  # 0.0 to 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    # Backward-compatible fields
    name: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Keep old/new names interoperable.
        if self.name and not self.signal_type:
            self.signal_type = self.name
        if not self.name and self.signal_type:
            self.name = self.signal_type

        # Keep old/new metadata containers interoperable.
        if self.metadata and not self.details:
            self.details = dict(self.metadata)
        elif self.details and not self.metadata:
            self.metadata = dict(self.details)


@dataclass
class FraudCheckResult:
    """Result of fraud detection check."""
    check_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checkout_id: str = ""
    decision: FraudDecision = FraudDecision.APPROVE
    risk_level: FraudRiskLevel = FraudRiskLevel.LOW
    risk_score: float = 0.0  # Overall score 0.0 to 100.0
    signals: List[FraudSignal] = field(default_factory=list)
    rules_triggered: List[str] = field(default_factory=list)
    provider: str = "internal"  # fraud detection provider
    provider_reference: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)
    review_reason: Optional[str] = None
    manual_review_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FraudRule:
    """Fraud detection rule configuration."""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    enabled: bool = True
    rule_type: str = "threshold"  # threshold, velocity, pattern, ml
    conditions: Dict[str, Any] = field(default_factory=dict)
    action: FraudDecision = FraudDecision.REVIEW
    priority: int = 100
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
