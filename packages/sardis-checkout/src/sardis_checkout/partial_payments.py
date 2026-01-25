"""
Partial payment support for checkout sessions.

This module provides functionality to accept and track partial payments,
allowing customers to pay for a checkout in multiple installments.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
import uuid

from sardis_checkout.models import (
    PartialPayment,
    PaymentStatus,
)

logger = logging.getLogger(__name__)


class PartialPaymentError(Exception):
    """Base exception for partial payment errors."""
    pass


class PaymentAmountTooSmall(PartialPaymentError):
    """Raised when payment amount is below minimum."""
    pass


class PaymentAmountTooLarge(PartialPaymentError):
    """Raised when payment amount exceeds remaining balance."""
    pass


class CheckoutAlreadyPaid(PartialPaymentError):
    """Raised when checkout is already fully paid."""
    pass


class PartialPaymentsNotAllowed(PartialPaymentError):
    """Raised when partial payments are not enabled for checkout."""
    pass


@dataclass
class PartialPaymentState:
    """Tracks the partial payment state for a checkout."""
    checkout_id: str
    total_amount: Decimal
    amount_paid: Decimal = Decimal("0")
    amount_remaining: Decimal = Decimal("0")
    currency: str = "USD"
    payments: List[PartialPayment] = field(default_factory=list)
    allow_partial: bool = True
    minimum_payment: Optional[Decimal] = None
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.amount_remaining == Decimal("0"):
            self.amount_remaining = self.total_amount


class PartialPaymentStore(ABC):
    """Abstract interface for partial payment state storage."""

    @abstractmethod
    async def get_state(self, checkout_id: str) -> Optional[PartialPaymentState]:
        """Get the partial payment state for a checkout."""
        pass

    @abstractmethod
    async def create_state(self, state: PartialPaymentState) -> PartialPaymentState:
        """Create a new partial payment state."""
        pass

    @abstractmethod
    async def update_state(self, state: PartialPaymentState) -> PartialPaymentState:
        """Update a partial payment state."""
        pass

    @abstractmethod
    async def add_payment(
        self,
        checkout_id: str,
        payment: PartialPayment,
    ) -> PartialPaymentState:
        """Add a partial payment to a checkout."""
        pass

    @abstractmethod
    async def get_payments(self, checkout_id: str) -> List[PartialPayment]:
        """Get all partial payments for a checkout."""
        pass


class InMemoryPartialPaymentStore(PartialPaymentStore):
    """
    In-memory partial payment store for development and testing.

    Note: This store is not suitable for production use.
    Use a persistent store like a database.
    """

    def __init__(self):
        self._states: Dict[str, PartialPaymentState] = {}

    async def get_state(self, checkout_id: str) -> Optional[PartialPaymentState]:
        return self._states.get(checkout_id)

    async def create_state(self, state: PartialPaymentState) -> PartialPaymentState:
        self._states[state.checkout_id] = state
        return state

    async def update_state(self, state: PartialPaymentState) -> PartialPaymentState:
        self._states[state.checkout_id] = state
        return state

    async def add_payment(
        self,
        checkout_id: str,
        payment: PartialPayment,
    ) -> PartialPaymentState:
        state = self._states.get(checkout_id)
        if state:
            state.payments.append(payment)
            state.amount_paid += payment.amount
            state.amount_remaining = state.total_amount - state.amount_paid
            state.updated_at = datetime.utcnow()

            if state.amount_remaining <= Decimal("0"):
                state.status = PaymentStatus.COMPLETED
                state.completed_at = datetime.utcnow()
            else:
                state.status = PaymentStatus.PARTIALLY_PAID

        return state

    async def get_payments(self, checkout_id: str) -> List[PartialPayment]:
        state = self._states.get(checkout_id)
        return state.payments if state else []


class PartialPaymentManager:
    """
    Manages partial payments for checkout sessions.

    Features:
    - Accept multiple partial payments
    - Track payment progress
    - Minimum payment enforcement
    - Automatic status updates
    - Payment history
    """

    def __init__(
        self,
        store: PartialPaymentStore,
        default_minimum_payment: Optional[Decimal] = None,
        default_minimum_percentage: Decimal = Decimal("0.1"),  # 10% minimum
    ):
        self.store = store
        self.default_minimum_payment = default_minimum_payment
        self.default_minimum_percentage = default_minimum_percentage

    def _round_amount(self, amount: Decimal, decimal_places: int = 2) -> Decimal:
        """Round an amount to specified decimal places."""
        quantize_str = "0." + "0" * decimal_places
        return amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    def _calculate_minimum_payment(
        self,
        total_amount: Decimal,
        amount_remaining: Decimal,
        explicit_minimum: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate the minimum payment amount.

        Uses explicit minimum if set, otherwise calculates based on percentage.
        Always returns the smaller of the calculated minimum and remaining amount.
        """
        if explicit_minimum is not None:
            minimum = explicit_minimum
        elif self.default_minimum_payment is not None:
            minimum = self.default_minimum_payment
        else:
            minimum = self._round_amount(
                total_amount * self.default_minimum_percentage
            )

        # Can't require more than what's remaining
        return min(minimum, amount_remaining)

    async def initialize_partial_payments(
        self,
        checkout_id: str,
        total_amount: Decimal,
        currency: str,
        allow_partial: bool = True,
        minimum_payment: Optional[Decimal] = None,
    ) -> PartialPaymentState:
        """
        Initialize partial payment tracking for a checkout.

        Args:
            checkout_id: The checkout session ID
            total_amount: Total amount to be collected
            currency: Payment currency
            allow_partial: Whether to allow partial payments
            minimum_payment: Explicit minimum payment amount

        Returns:
            The initialized PartialPaymentState
        """
        state = PartialPaymentState(
            checkout_id=checkout_id,
            total_amount=total_amount,
            amount_remaining=total_amount,
            currency=currency,
            allow_partial=allow_partial,
            minimum_payment=minimum_payment,
        )

        await self.store.create_state(state)
        logger.info(
            f"Initialized partial payments for checkout {checkout_id}: "
            f"total={total_amount} {currency}, allow_partial={allow_partial}"
        )

        return state

    async def get_state(self, checkout_id: str) -> Optional[PartialPaymentState]:
        """Get the current partial payment state for a checkout."""
        return await self.store.get_state(checkout_id)

    async def validate_payment_amount(
        self,
        checkout_id: str,
        amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Validate a payment amount before processing.

        Returns a dict with validation results and any error messages.
        """
        state = await self.store.get_state(checkout_id)

        if not state:
            return {
                "valid": False,
                "error": "checkout_not_found",
                "message": f"Checkout {checkout_id} not found",
            }

        # Check if already fully paid
        if state.status == PaymentStatus.COMPLETED:
            return {
                "valid": False,
                "error": "already_paid",
                "message": "Checkout is already fully paid",
            }

        # Check if partial payments allowed
        if not state.allow_partial and amount < state.total_amount:
            return {
                "valid": False,
                "error": "partial_not_allowed",
                "message": "Partial payments are not allowed for this checkout",
            }

        # Check amount not exceeding remaining
        if amount > state.amount_remaining:
            return {
                "valid": False,
                "error": "amount_too_large",
                "message": f"Amount {amount} exceeds remaining balance {state.amount_remaining}",
                "max_amount": state.amount_remaining,
            }

        # Check minimum payment
        minimum = self._calculate_minimum_payment(
            state.total_amount,
            state.amount_remaining,
            state.minimum_payment,
        )

        # Only enforce minimum if not paying the full remaining amount
        if amount < state.amount_remaining and amount < minimum:
            return {
                "valid": False,
                "error": "amount_too_small",
                "message": f"Minimum payment is {minimum} {state.currency}",
                "minimum_amount": minimum,
            }

        return {
            "valid": True,
            "checkout_id": checkout_id,
            "amount": amount,
            "currency": state.currency,
            "amount_remaining_after": state.amount_remaining - amount,
            "will_complete": (state.amount_remaining - amount) <= Decimal("0"),
        }

    async def record_payment(
        self,
        checkout_id: str,
        amount: Decimal,
        psp_payment_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PartialPaymentState:
        """
        Record a partial payment for a checkout.

        Args:
            checkout_id: The checkout session ID
            amount: Payment amount
            psp_payment_id: PSP's payment ID (if available)
            metadata: Additional payment metadata

        Returns:
            Updated PartialPaymentState

        Raises:
            PartialPaymentError: If payment cannot be recorded
        """
        state = await self.store.get_state(checkout_id)

        if not state:
            raise PartialPaymentError(f"Checkout {checkout_id} not found")

        # Validate amount
        validation = await self.validate_payment_amount(checkout_id, amount)
        if not validation["valid"]:
            error_map = {
                "already_paid": CheckoutAlreadyPaid,
                "partial_not_allowed": PartialPaymentsNotAllowed,
                "amount_too_large": PaymentAmountTooLarge,
                "amount_too_small": PaymentAmountTooSmall,
            }
            error_class = error_map.get(validation["error"], PartialPaymentError)
            raise error_class(validation["message"])

        # Create payment record
        payment = PartialPayment(
            payment_id=str(uuid.uuid4()),
            checkout_id=checkout_id,
            amount=amount,
            currency=state.currency,
            psp_payment_id=psp_payment_id,
            status=PaymentStatus.COMPLETED,
            metadata=metadata or {},
        )

        # Update state
        state = await self.store.add_payment(checkout_id, payment)

        logger.info(
            f"Recorded partial payment for checkout {checkout_id}: "
            f"amount={amount}, total_paid={state.amount_paid}, "
            f"remaining={state.amount_remaining}"
        )

        return state

    async def get_payment_summary(self, checkout_id: str) -> Dict[str, Any]:
        """
        Get a summary of payments for a checkout.

        Returns a dict with payment summary information.
        """
        state = await self.store.get_state(checkout_id)

        if not state:
            return {"error": "checkout_not_found"}

        minimum = self._calculate_minimum_payment(
            state.total_amount,
            state.amount_remaining,
            state.minimum_payment,
        )

        return {
            "checkout_id": checkout_id,
            "total_amount": state.total_amount,
            "amount_paid": state.amount_paid,
            "amount_remaining": state.amount_remaining,
            "currency": state.currency,
            "status": state.status.value,
            "payment_count": len(state.payments),
            "payments": [
                {
                    "payment_id": p.payment_id,
                    "amount": p.amount,
                    "status": p.status.value,
                    "created_at": p.created_at.isoformat(),
                    "psp_payment_id": p.psp_payment_id,
                }
                for p in state.payments
            ],
            "allow_partial": state.allow_partial,
            "minimum_payment": minimum if state.amount_remaining > Decimal("0") else None,
            "progress_percentage": float(
                (state.amount_paid / state.total_amount * 100)
                if state.total_amount > 0 else 0
            ),
            "is_complete": state.status == PaymentStatus.COMPLETED,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "completed_at": state.completed_at.isoformat() if state.completed_at else None,
        }

    async def get_next_payment_options(
        self,
        checkout_id: str,
    ) -> Dict[str, Any]:
        """
        Get suggested payment amounts for the next partial payment.

        Returns suggested amounts like "pay minimum", "pay half", "pay full".
        """
        state = await self.store.get_state(checkout_id)

        if not state or state.status == PaymentStatus.COMPLETED:
            return {"error": "no_payment_needed"}

        minimum = self._calculate_minimum_payment(
            state.total_amount,
            state.amount_remaining,
            state.minimum_payment,
        )

        half_remaining = self._round_amount(state.amount_remaining / 2)

        options = []

        # Only add options that make sense
        if minimum < state.amount_remaining:
            options.append({
                "label": "Minimum Payment",
                "amount": minimum,
                "description": f"Pay minimum of {minimum} {state.currency}",
            })

        if half_remaining > minimum and half_remaining < state.amount_remaining:
            options.append({
                "label": "Pay Half",
                "amount": half_remaining,
                "description": f"Pay half of remaining ({half_remaining} {state.currency})",
            })

        options.append({
            "label": "Pay Full Amount",
            "amount": state.amount_remaining,
            "description": f"Pay remaining balance ({state.amount_remaining} {state.currency})",
        })

        return {
            "checkout_id": checkout_id,
            "amount_remaining": state.amount_remaining,
            "currency": state.currency,
            "options": options,
        }

    async def can_accept_payment(self, checkout_id: str) -> bool:
        """Check if the checkout can accept more payments."""
        state = await self.store.get_state(checkout_id)
        return state is not None and state.status != PaymentStatus.COMPLETED

    async def refund_partial_payment(
        self,
        checkout_id: str,
        payment_id: str,
        refund_amount: Optional[Decimal] = None,
    ) -> PartialPaymentState:
        """
        Process a refund for a partial payment.

        Args:
            checkout_id: The checkout session ID
            payment_id: The payment to refund
            refund_amount: Amount to refund (defaults to full payment amount)

        Returns:
            Updated PartialPaymentState
        """
        state = await self.store.get_state(checkout_id)

        if not state:
            raise PartialPaymentError(f"Checkout {checkout_id} not found")

        # Find the payment
        payment = next(
            (p for p in state.payments if p.payment_id == payment_id),
            None,
        )

        if not payment:
            raise PartialPaymentError(f"Payment {payment_id} not found")

        if payment.status == PaymentStatus.REFUNDED:
            raise PartialPaymentError(f"Payment {payment_id} already refunded")

        # Determine refund amount
        actual_refund = refund_amount or payment.amount

        if actual_refund > payment.amount:
            raise PartialPaymentError(
                f"Refund amount {actual_refund} exceeds payment amount {payment.amount}"
            )

        # Update payment status
        payment.status = PaymentStatus.REFUNDED
        payment.metadata["refunded_amount"] = str(actual_refund)
        payment.metadata["refunded_at"] = datetime.utcnow().isoformat()

        # Update state
        state.amount_paid -= actual_refund
        state.amount_remaining += actual_refund
        state.updated_at = datetime.utcnow()

        # Update status
        if state.amount_paid <= Decimal("0"):
            state.status = PaymentStatus.REFUNDED
        elif state.amount_remaining > Decimal("0"):
            state.status = PaymentStatus.PARTIALLY_PAID

        await self.store.update_state(state)

        logger.info(
            f"Refunded {actual_refund} from payment {payment_id} "
            f"for checkout {checkout_id}"
        )

        return state
