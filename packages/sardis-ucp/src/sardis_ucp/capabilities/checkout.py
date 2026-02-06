"""UCP Checkout Capability.

Provides checkout session management for UCP commerce flows:
- create_checkout: Initialize a new checkout session
- update_checkout: Modify cart contents, apply discounts
- complete_checkout: Finalize and generate payment mandate
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from ..models.mandates import (
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPPaymentMandate,
    UCPLineItem,
    UCPDiscount,
    UCPCurrency,
)
from ..models.orders import UCPOrder, UCPOrderStatus

logger = logging.getLogger(__name__)


class CheckoutSessionStatus(str, Enum):
    """Status of a checkout session."""

    OPEN = "open"  # Session active, can be modified
    PENDING_PAYMENT = "pending_payment"  # Awaiting payment
    COMPLETED = "completed"  # Payment successful
    EXPIRED = "expired"  # Session timed out
    CANCELLED = "cancelled"  # Explicitly cancelled
    REQUIRES_ESCALATION = "requires_escalation"  # Needs human review


class CheckoutError(Exception):
    """Base exception for checkout errors."""

    def __init__(self, message: str, code: str, details: Dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class CheckoutSessionExpiredError(CheckoutError):
    """Raised when checkout session has expired."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Checkout session {session_id} has expired",
            code="session_expired",
            details={"session_id": session_id},
        )


class CheckoutSessionNotFoundError(CheckoutError):
    """Raised when checkout session is not found."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Checkout session {session_id} not found",
            code="session_not_found",
            details={"session_id": session_id},
        )


class InvalidCheckoutOperationError(CheckoutError):
    """Raised when an operation is not valid for the session state."""

    def __init__(self, session_id: str, operation: str, status: CheckoutSessionStatus):
        super().__init__(
            f"Cannot {operation} on session {session_id} with status {status.value}",
            code="invalid_operation",
            details={"session_id": session_id, "operation": operation, "status": status.value},
        )


@dataclass(slots=True)
class CheckoutSession:
    """A checkout session tracking the cart and checkout state."""

    session_id: str
    merchant_id: str
    merchant_name: str
    merchant_domain: str
    customer_id: str  # Agent or user identifier

    # Session state
    status: CheckoutSessionStatus = CheckoutSessionStatus.OPEN
    currency: UCPCurrency = UCPCurrency.USD

    # Cart contents
    line_items: List[UCPLineItem] = field(default_factory=list)
    discounts: List[UCPDiscount] = field(default_factory=list)

    # Pricing
    subtotal_minor: int = 0
    taxes_minor: int = 0
    shipping_minor: int = 0
    total_minor: int = 0
    tax_rate: Decimal = Decimal("0.00")  # Applied tax rate

    # Mandates
    cart_mandate: Optional[UCPCartMandate] = None
    checkout_mandate: Optional[UCPCheckoutMandate] = None
    payment_mandate: Optional[UCPPaymentMandate] = None

    # Result
    order_id: Optional[str] = None
    chain_tx_hash: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: int = field(default_factory=lambda: int(time.time()) + 3600)  # 1 hour

    # Escalation
    escalation_reason: Optional[str] = None
    escalation_resolved_at: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return self.expires_at <= int(time.time())

    def recalculate_totals(self) -> None:
        """Recalculate pricing based on line items and discounts."""
        # Calculate subtotal
        self.subtotal_minor = sum(item.total_minor for item in self.line_items)

        # Calculate taxes
        self.taxes_minor = int(self.subtotal_minor * self.tax_rate)

        # Calculate discount
        discount_minor = sum(d.calculate_discount_minor(self.subtotal_minor) for d in self.discounts)

        # Calculate total
        self.total_minor = self.subtotal_minor + self.taxes_minor + self.shipping_minor - discount_minor
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "merchant_domain": self.merchant_domain,
            "customer_id": self.customer_id,
            "status": self.status.value,
            "currency": self.currency.value,
            "line_items": [item.to_dict() for item in self.line_items],
            "discounts": [d.to_dict() for d in self.discounts],
            "subtotal_minor": self.subtotal_minor,
            "taxes_minor": self.taxes_minor,
            "shipping_minor": self.shipping_minor,
            "total_minor": self.total_minor,
            "cart_mandate": self.cart_mandate.to_dict() if self.cart_mandate else None,
            "checkout_mandate": self.checkout_mandate.to_dict() if self.checkout_mandate else None,
            "payment_mandate": self.payment_mandate.to_dict() if self.payment_mandate else None,
            "order_id": self.order_id,
            "chain_tx_hash": self.chain_tx_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at,
            "escalation_reason": self.escalation_reason,
            "escalation_resolved_at": self.escalation_resolved_at.isoformat() if self.escalation_resolved_at else None,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class CheckoutResult:
    """Result of completing a checkout."""

    success: bool
    session_id: str
    order_id: Optional[str] = None
    payment_mandate: Optional[UCPPaymentMandate] = None
    chain_tx_hash: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "session_id": self.session_id,
            "order_id": self.order_id,
            "payment_mandate": self.payment_mandate.to_dict() if self.payment_mandate else None,
            "chain_tx_hash": self.chain_tx_hash,
            "error": self.error,
            "error_code": self.error_code,
        }


class CheckoutSessionStore(Protocol):
    """Protocol for checkout session storage."""

    def save(self, session: CheckoutSession) -> None:
        """Save or update a checkout session."""
        ...

    def get(self, session_id: str) -> Optional[CheckoutSession]:
        """Retrieve a checkout session by ID."""
        ...

    def delete(self, session_id: str) -> bool:
        """Delete a checkout session."""
        ...


class PaymentExecutor(Protocol):
    """Protocol for executing payments."""

    async def execute_payment(
        self,
        payment_mandate: UCPPaymentMandate,
    ) -> tuple[bool, str | None, str | None]:
        """
        Execute a payment mandate.

        Returns:
            Tuple of (success, chain_tx_hash, error_message)
        """
        ...


class InMemoryCheckoutSessionStore:
    """In-memory implementation of CheckoutSessionStore.

    For production, replace with a persistent store (Redis, PostgreSQL, etc.).
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, CheckoutSession] = {}

    def save(self, session: CheckoutSession) -> None:
        """Save or update a checkout session."""
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> Optional[CheckoutSession]:
        """Retrieve a checkout session by ID."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """Delete a checkout session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


class UCPCheckoutCapability:
    """
    UCP Checkout capability for managing checkout flows.

    Provides methods to:
    - Create checkout sessions with cart items
    - Update sessions (add/remove items, discounts)
    - Complete checkout and generate payment mandates
    """

    def __init__(
        self,
        store: CheckoutSessionStore | None = None,
        payment_executor: PaymentExecutor | None = None,
        default_tax_rate: Decimal = Decimal("0.00"),
        session_ttl_seconds: int = 3600,
    ) -> None:
        """
        Initialize the checkout capability.

        Args:
            store: Session storage implementation
            payment_executor: Payment execution implementation
            default_tax_rate: Default tax rate for calculations
            session_ttl_seconds: Session time-to-live in seconds
        """
        self._store = store or InMemoryCheckoutSessionStore()
        self._payment_executor = payment_executor
        self._default_tax_rate = default_tax_rate
        self._session_ttl = session_ttl_seconds

    def create_checkout(
        self,
        merchant_id: str,
        merchant_name: str,
        merchant_domain: str,
        customer_id: str,
        line_items: List[UCPLineItem],
        currency: UCPCurrency = UCPCurrency.USD,
        tax_rate: Decimal | None = None,
        shipping_minor: int = 0,
        metadata: Dict[str, Any] | None = None,
    ) -> CheckoutSession:
        """
        Create a new checkout session.

        Args:
            merchant_id: Merchant identifier
            merchant_name: Merchant display name
            merchant_domain: Merchant domain
            customer_id: Customer/agent identifier
            line_items: Items in the cart
            currency: Currency for the checkout
            tax_rate: Tax rate to apply (uses default if not specified)
            shipping_minor: Shipping cost in minor units
            metadata: Additional metadata

        Returns:
            The created CheckoutSession
        """
        session_id = f"cs_{uuid.uuid4().hex}"
        now = int(time.time())

        session = CheckoutSession(
            session_id=session_id,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            merchant_domain=merchant_domain,
            customer_id=customer_id,
            currency=currency,
            line_items=list(line_items),
            tax_rate=tax_rate if tax_rate is not None else self._default_tax_rate,
            shipping_minor=shipping_minor,
            expires_at=now + self._session_ttl,
            metadata=metadata or {},
        )

        # Calculate initial totals
        session.recalculate_totals()

        # Generate cart mandate
        session.cart_mandate = self._create_cart_mandate(session)

        # Save session
        self._store.save(session)

        logger.info(
            f"Created checkout session: session_id={session_id}, "
            f"merchant={merchant_name}, customer={customer_id}, "
            f"items={len(line_items)}, total={session.total_minor}"
        )

        return session

    def update_checkout(
        self,
        session_id: str,
        add_items: List[UCPLineItem] | None = None,
        remove_item_ids: List[str] | None = None,
        add_discounts: List[UCPDiscount] | None = None,
        remove_discount_ids: List[str] | None = None,
        shipping_minor: int | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> CheckoutSession:
        """
        Update a checkout session.

        Args:
            session_id: Session to update
            add_items: Items to add to cart
            remove_item_ids: Item IDs to remove
            add_discounts: Discounts to apply
            remove_discount_ids: Discount IDs to remove
            shipping_minor: Updated shipping cost
            metadata: Metadata to merge

        Returns:
            The updated CheckoutSession

        Raises:
            CheckoutSessionNotFoundError: If session not found
            CheckoutSessionExpiredError: If session has expired
            InvalidCheckoutOperationError: If session cannot be modified
        """
        session = self._store.get(session_id)
        if session is None:
            raise CheckoutSessionNotFoundError(session_id)

        if session.is_expired():
            session.status = CheckoutSessionStatus.EXPIRED
            self._store.save(session)
            raise CheckoutSessionExpiredError(session_id)

        if session.status != CheckoutSessionStatus.OPEN:
            raise InvalidCheckoutOperationError(session_id, "update", session.status)

        # Remove items
        if remove_item_ids:
            session.line_items = [
                item for item in session.line_items
                if item.item_id not in remove_item_ids
            ]

        # Add items
        if add_items:
            session.line_items.extend(add_items)

        # Remove discounts
        if remove_discount_ids:
            session.discounts = [
                d for d in session.discounts
                if d.discount_id not in remove_discount_ids
            ]

        # Add discounts
        if add_discounts:
            session.discounts.extend(add_discounts)

        # Update shipping
        if shipping_minor is not None:
            session.shipping_minor = shipping_minor

        # Merge metadata
        if metadata:
            session.metadata.update(metadata)

        # Recalculate totals
        session.recalculate_totals()

        # Regenerate cart mandate
        session.cart_mandate = self._create_cart_mandate(session)

        # Save session
        self._store.save(session)

        logger.info(
            f"Updated checkout session: session_id={session_id}, "
            f"items={len(session.line_items)}, total={session.total_minor}"
        )

        return session

    def get_checkout(self, session_id: str) -> CheckoutSession:
        """
        Get a checkout session.

        Args:
            session_id: Session to retrieve

        Returns:
            The CheckoutSession

        Raises:
            CheckoutSessionNotFoundError: If session not found
        """
        session = self._store.get(session_id)
        if session is None:
            raise CheckoutSessionNotFoundError(session_id)

        # Check expiration and update status if needed
        if session.is_expired() and session.status == CheckoutSessionStatus.OPEN:
            session.status = CheckoutSessionStatus.EXPIRED
            self._store.save(session)

        return session

    async def complete_checkout(
        self,
        session_id: str,
        chain: str,
        token: str,
        destination: str,
        subject: str,
        issuer: str,
        execute_payment: bool = True,
    ) -> CheckoutResult:
        """
        Complete a checkout session and generate payment mandate.

        Args:
            session_id: Session to complete
            chain: Blockchain network for payment
            token: Token for payment (e.g., "USDC")
            destination: Recipient address
            subject: Payer identifier
            issuer: Platform identifier
            execute_payment: Whether to execute payment immediately

        Returns:
            CheckoutResult with payment mandate and execution status

        Raises:
            CheckoutSessionNotFoundError: If session not found
            CheckoutSessionExpiredError: If session has expired
            InvalidCheckoutOperationError: If session cannot be completed
        """
        session = self._store.get(session_id)
        if session is None:
            raise CheckoutSessionNotFoundError(session_id)

        if session.is_expired():
            session.status = CheckoutSessionStatus.EXPIRED
            self._store.save(session)
            raise CheckoutSessionExpiredError(session_id)

        if session.status == CheckoutSessionStatus.REQUIRES_ESCALATION:
            raise InvalidCheckoutOperationError(session_id, "complete", session.status)

        if session.status != CheckoutSessionStatus.OPEN:
            raise InvalidCheckoutOperationError(session_id, "complete", session.status)

        # Validate cart has items
        if not session.line_items:
            return CheckoutResult(
                success=False,
                session_id=session_id,
                error="Cart is empty",
                error_code="empty_cart",
            )

        # Generate checkout mandate
        checkout_mandate = self._create_checkout_mandate(
            session=session,
            subject=subject,
            issuer=issuer,
        )
        session.checkout_mandate = checkout_mandate

        # Generate payment mandate
        payment_mandate = self._create_payment_mandate(
            session=session,
            checkout_mandate=checkout_mandate,
            chain=chain,
            token=token,
            destination=destination,
            subject=subject,
            issuer=issuer,
        )
        session.payment_mandate = payment_mandate

        # Update session status
        session.status = CheckoutSessionStatus.PENDING_PAYMENT
        self._store.save(session)

        # Execute payment if requested
        if execute_payment and self._payment_executor:
            success, tx_hash, error = await self._payment_executor.execute_payment(payment_mandate)

            if success:
                session.status = CheckoutSessionStatus.COMPLETED
                session.chain_tx_hash = tx_hash
                session.order_id = f"ord_{uuid.uuid4().hex}"
                self._store.save(session)

                logger.info(
                    f"Checkout completed: session_id={session_id}, "
                    f"order_id={session.order_id}, tx_hash={tx_hash}"
                )

                return CheckoutResult(
                    success=True,
                    session_id=session_id,
                    order_id=session.order_id,
                    payment_mandate=payment_mandate,
                    chain_tx_hash=tx_hash,
                )
            else:
                logger.warning(
                    f"Payment execution failed: session_id={session_id}, error={error}"
                )
                return CheckoutResult(
                    success=False,
                    session_id=session_id,
                    payment_mandate=payment_mandate,
                    error=error,
                    error_code="payment_failed",
                )

        # Return mandate without executing
        logger.info(
            f"Checkout mandate created: session_id={session_id}, "
            f"amount={payment_mandate.amount_minor}, chain={chain}"
        )

        return CheckoutResult(
            success=True,
            session_id=session_id,
            payment_mandate=payment_mandate,
        )

    def cancel_checkout(self, session_id: str) -> CheckoutSession:
        """
        Cancel a checkout session.

        Args:
            session_id: Session to cancel

        Returns:
            The cancelled CheckoutSession

        Raises:
            CheckoutSessionNotFoundError: If session not found
            InvalidCheckoutOperationError: If session cannot be cancelled
        """
        session = self._store.get(session_id)
        if session is None:
            raise CheckoutSessionNotFoundError(session_id)

        if session.status in (CheckoutSessionStatus.COMPLETED, CheckoutSessionStatus.CANCELLED):
            raise InvalidCheckoutOperationError(session_id, "cancel", session.status)

        session.status = CheckoutSessionStatus.CANCELLED
        session.updated_at = datetime.now(timezone.utc)
        self._store.save(session)

        logger.info(f"Checkout cancelled: session_id={session_id}")

        return session

    def escalate_checkout(self, session_id: str, reason: str) -> CheckoutSession:
        """Escalate a checkout session for human review.

        Transitions: OPEN -> REQUIRES_ESCALATION
        """
        session = self._store.get(session_id)
        if session is None:
            raise CheckoutSessionNotFoundError(session_id)
        if session.is_expired():
            session.status = CheckoutSessionStatus.EXPIRED
            self._store.save(session)
            raise CheckoutSessionExpiredError(session_id)
        if session.status != CheckoutSessionStatus.OPEN:
            raise InvalidCheckoutOperationError(session_id, "escalate", session.status)

        session.status = CheckoutSessionStatus.REQUIRES_ESCALATION
        session.escalation_reason = reason
        session.updated_at = datetime.now(timezone.utc)
        self._store.save(session)

        logger.info(f"Checkout escalated: session_id={session_id}, reason={reason}")
        return session

    def resolve_escalation(self, session_id: str) -> CheckoutSession:
        """Resolve an escalated checkout session back to OPEN.

        Transitions: REQUIRES_ESCALATION -> OPEN
        """
        session = self._store.get(session_id)
        if session is None:
            raise CheckoutSessionNotFoundError(session_id)
        if session.status != CheckoutSessionStatus.REQUIRES_ESCALATION:
            raise InvalidCheckoutOperationError(session_id, "resolve_escalation", session.status)

        session.status = CheckoutSessionStatus.OPEN
        session.escalation_resolved_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)
        self._store.save(session)

        logger.info(f"Escalation resolved: session_id={session_id}")
        return session

    def _create_cart_mandate(self, session: CheckoutSession) -> UCPCartMandate:
        """Create a cart mandate from a checkout session."""
        return UCPCartMandate(
            mandate_id=f"cart_{uuid.uuid4().hex}",
            merchant_id=session.merchant_id,
            merchant_name=session.merchant_name,
            merchant_domain=session.merchant_domain,
            line_items=list(session.line_items),
            currency=session.currency,
            subtotal_minor=session.subtotal_minor,
            taxes_minor=session.taxes_minor,
            shipping_minor=session.shipping_minor,
            discounts=list(session.discounts),
            expires_at=session.expires_at,
            metadata={"session_id": session.session_id},
        )

    def _create_checkout_mandate(
        self,
        session: CheckoutSession,
        subject: str,
        issuer: str,
    ) -> UCPCheckoutMandate:
        """Create a checkout mandate from a session."""
        assert session.cart_mandate is not None

        return UCPCheckoutMandate(
            mandate_id=f"checkout_{uuid.uuid4().hex}",
            cart_mandate_id=session.cart_mandate.mandate_id,
            subject=subject,
            issuer=issuer,
            authorized_amount_minor=session.total_minor,
            currency=session.currency,
            expires_at=int(time.time()) + 900,  # 15 minutes
            metadata={"session_id": session.session_id},
        )

    def _create_payment_mandate(
        self,
        session: CheckoutSession,
        checkout_mandate: UCPCheckoutMandate,
        chain: str,
        token: str,
        destination: str,
        subject: str,
        issuer: str,
    ) -> UCPPaymentMandate:
        """Create a payment mandate from checkout."""
        # Create audit hash linking cart -> checkout -> payment
        audit_data = (
            f"{session.cart_mandate.mandate_id if session.cart_mandate else ''}:"
            f"{checkout_mandate.mandate_id}:"
            f"{session.total_minor}:{chain}:{token}:{destination}"
        )
        audit_hash = hashlib.sha256(audit_data.encode()).hexdigest()

        return UCPPaymentMandate(
            mandate_id=f"payment_{uuid.uuid4().hex}",
            checkout_mandate_id=checkout_mandate.mandate_id,
            subject=subject,
            issuer=issuer,
            chain=chain,
            token=token,
            amount_minor=session.total_minor,
            destination=destination,
            audit_hash=audit_hash,
            expires_at=int(time.time()) + 300,  # 5 minutes
            metadata={"session_id": session.session_id},
        )


__all__ = [
    "CheckoutSessionStatus",
    "CheckoutError",
    "CheckoutSessionExpiredError",
    "CheckoutSessionNotFoundError",
    "InvalidCheckoutOperationError",
    "CheckoutSession",
    "CheckoutResult",
    "CheckoutSessionStore",
    "PaymentExecutor",
    "InMemoryCheckoutSessionStore",
    "UCPCheckoutCapability",
]
