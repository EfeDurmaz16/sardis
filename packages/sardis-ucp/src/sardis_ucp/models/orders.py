"""UCP Order and Fulfillment models.

Orders represent completed checkouts and track fulfillment status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .mandates import UCPLineItem, UCPCurrency


class UCPOrderStatus(str, Enum):
    """Status of a UCP order."""

    PENDING = "pending"  # Payment not yet confirmed
    CONFIRMED = "confirmed"  # Payment confirmed, awaiting fulfillment
    PROCESSING = "processing"  # Being prepared for shipment
    SHIPPED = "shipped"  # Shipped to customer
    DELIVERED = "delivered"  # Delivered to customer
    COMPLETED = "completed"  # Order complete
    CANCELLED = "cancelled"  # Order cancelled
    REFUNDED = "refunded"  # Order refunded
    PARTIALLY_REFUNDED = "partially_refunded"  # Partial refund issued


class UCPFulfillmentStatus(str, Enum):
    """Status of order fulfillment."""

    PENDING = "pending"  # Awaiting fulfillment
    PROCESSING = "processing"  # Being prepared
    SHIPPED = "shipped"  # In transit
    OUT_FOR_DELIVERY = "out_for_delivery"  # Out for delivery
    DELIVERED = "delivered"  # Delivered
    FAILED = "failed"  # Delivery failed
    RETURNED = "returned"  # Returned to sender


@dataclass(slots=True)
class UCPShippingAddress:
    """Shipping address for order fulfillment."""

    name: str
    line1: str
    line2: Optional[str] = None
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    phone: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
        }


@dataclass(slots=True)
class UCPFulfillmentEvent:
    """An event in the fulfillment lifecycle."""

    event_id: str
    status: UCPFulfillmentStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    location: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "description": self.description,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class UCPFulfillment:
    """Fulfillment information for an order."""

    fulfillment_id: str
    order_id: str
    status: UCPFulfillmentStatus = UCPFulfillmentStatus.PENDING

    # Shipping details
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    shipping_address: Optional[UCPShippingAddress] = None

    # Line items being fulfilled (subset of order items)
    line_item_ids: List[str] = field(default_factory=list)

    # Timeline
    events: List[UCPFulfillmentEvent] = field(default_factory=list)
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_event(
        self,
        event_id: str,
        status: UCPFulfillmentStatus,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> UCPFulfillmentEvent:
        """Add a fulfillment event and update status."""
        event = UCPFulfillmentEvent(
            event_id=event_id,
            status=status,
            location=location,
            description=description,
        )
        self.events.append(event)
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

        if status == UCPFulfillmentStatus.SHIPPED and self.shipped_at is None:
            self.shipped_at = event.timestamp
        elif status == UCPFulfillmentStatus.DELIVERED and self.delivered_at is None:
            self.delivered_at = event.timestamp

        return event

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "fulfillment_id": self.fulfillment_id,
            "order_id": self.order_id,
            "status": self.status.value,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            "shipping_address": self.shipping_address.to_dict() if self.shipping_address else None,
            "line_item_ids": self.line_item_ids,
            "events": [e.to_dict() for e in self.events],
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class UCPOrder:
    """A UCP order representing a completed checkout.

    Orders are created when a checkout is completed successfully.
    They track the lifecycle from payment confirmation through fulfillment.
    """

    order_id: str
    checkout_session_id: str
    merchant_id: str
    customer_id: str  # Agent or user identifier

    # Order status
    status: UCPOrderStatus = UCPOrderStatus.PENDING

    # Line items
    line_items: List[UCPLineItem] = field(default_factory=list)
    currency: UCPCurrency = UCPCurrency.USD

    # Pricing (as confirmed at checkout)
    subtotal_minor: int = 0
    taxes_minor: int = 0
    shipping_minor: int = 0
    discount_minor: int = 0
    total_minor: int = 0

    # Payment information
    payment_mandate_id: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    ledger_tx_id: Optional[str] = None
    payment_confirmed_at: Optional[datetime] = None

    # Fulfillment
    fulfillments: List[UCPFulfillment] = field(default_factory=list)
    requires_shipping: bool = True
    shipping_address: Optional[UCPShippingAddress] = None

    # Refund tracking
    refunded_amount_minor: int = 0
    refund_reason: Optional[str] = None

    # Timeline
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def confirm_payment(
        self,
        payment_mandate_id: str,
        chain_tx_hash: str,
        ledger_tx_id: Optional[str] = None,
    ) -> None:
        """Mark the order as payment confirmed."""
        self.payment_mandate_id = payment_mandate_id
        self.chain_tx_hash = chain_tx_hash
        self.ledger_tx_id = ledger_tx_id
        self.payment_confirmed_at = datetime.now(timezone.utc)
        self.status = UCPOrderStatus.CONFIRMED
        self.updated_at = datetime.now(timezone.utc)

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the order."""
        self.status = UCPOrderStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        if reason:
            self.metadata["cancellation_reason"] = reason

    def refund(self, amount_minor: int, reason: Optional[str] = None) -> None:
        """Process a refund for the order."""
        self.refunded_amount_minor += amount_minor
        self.refund_reason = reason
        self.updated_at = datetime.now(timezone.utc)

        if self.refunded_amount_minor >= self.total_minor:
            self.status = UCPOrderStatus.REFUNDED
        else:
            self.status = UCPOrderStatus.PARTIALLY_REFUNDED

    def complete(self) -> None:
        """Mark the order as complete."""
        self.status = UCPOrderStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def add_fulfillment(self, fulfillment: UCPFulfillment) -> None:
        """Add a fulfillment to the order."""
        self.fulfillments.append(fulfillment)
        self.updated_at = datetime.now(timezone.utc)

        # Update order status based on fulfillment status
        if fulfillment.status == UCPFulfillmentStatus.SHIPPED:
            if self.status == UCPOrderStatus.CONFIRMED:
                self.status = UCPOrderStatus.SHIPPED
        elif fulfillment.status == UCPFulfillmentStatus.DELIVERED:
            # Check if all fulfillments are delivered
            all_delivered = all(
                f.status == UCPFulfillmentStatus.DELIVERED
                for f in self.fulfillments
            )
            if all_delivered:
                self.status = UCPOrderStatus.DELIVERED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "checkout_session_id": self.checkout_session_id,
            "merchant_id": self.merchant_id,
            "customer_id": self.customer_id,
            "status": self.status.value,
            "line_items": [item.to_dict() for item in self.line_items],
            "currency": self.currency.value,
            "subtotal_minor": self.subtotal_minor,
            "taxes_minor": self.taxes_minor,
            "shipping_minor": self.shipping_minor,
            "discount_minor": self.discount_minor,
            "total_minor": self.total_minor,
            "payment_mandate_id": self.payment_mandate_id,
            "chain_tx_hash": self.chain_tx_hash,
            "ledger_tx_id": self.ledger_tx_id,
            "payment_confirmed_at": self.payment_confirmed_at.isoformat() if self.payment_confirmed_at else None,
            "fulfillments": [f.to_dict() for f in self.fulfillments],
            "requires_shipping": self.requires_shipping,
            "shipping_address": self.shipping_address.to_dict() if self.shipping_address else None,
            "refunded_amount_minor": self.refunded_amount_minor,
            "refund_reason": self.refund_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "metadata": self.metadata,
        }


__all__ = [
    "UCPOrderStatus",
    "UCPFulfillmentStatus",
    "UCPShippingAddress",
    "UCPFulfillmentEvent",
    "UCPFulfillment",
    "UCPOrder",
]
