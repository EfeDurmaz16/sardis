"""AP2 <-> UCP Mandate Adapter.

Provides bidirectional translation between AP2 mandates (from sardis-protocol)
and UCP mandates, enabling:
1. UCP flows to use existing AP2 verification
2. Existing AP2 flows to be exposed via UCP transports
3. Backwards compatibility with current integrations

Mandate Mapping:
- UCPCartMandate <-> AP2 CartMandate
- UCPCheckoutMandate <-> AP2 IntentMandate
- UCPPaymentMandate <-> AP2 PaymentMandate
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol

from ..models.mandates import (
    UCPCartMandate,
    UCPCheckoutMandate,
    UCPPaymentMandate,
    UCPLineItem,
    UCPDiscount,
    UCPCurrency,
)

logger = logging.getLogger(__name__)


# ============ AP2 Type Definitions ============
# These mirror sardis-protocol types to avoid circular imports


@dataclass(slots=True)
class AP2VCProof:
    """Verifiable Credential proof for AP2 mandates."""

    type: str = "DataIntegrityProof"
    verification_method: str = ""
    created: str = ""
    proof_purpose: str = "assertionMethod"
    proof_value: str = ""


@dataclass(slots=True)
class AP2IntentMandate:
    """AP2 Intent Mandate - user's authorization to browse/shop."""

    mandate_id: str
    mandate_type: str = "intent"
    issuer: str = ""
    subject: str = ""
    expires_at: int = 0
    nonce: str = ""
    proof: AP2VCProof = field(default_factory=AP2VCProof)
    domain: str = ""
    purpose: str = "intent"
    scope: List[str] = field(default_factory=list)
    requested_amount: Optional[int] = None


@dataclass(slots=True)
class AP2CartMandate:
    """AP2 Cart Mandate - merchant's offer."""

    mandate_id: str
    mandate_type: str = "cart"
    issuer: str = ""
    subject: str = ""
    expires_at: int = 0
    nonce: str = ""
    proof: AP2VCProof = field(default_factory=AP2VCProof)
    domain: str = ""
    purpose: str = "cart"
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    merchant_domain: str = ""
    currency: str = "USD"
    subtotal_minor: int = 0
    taxes_minor: int = 0


@dataclass(slots=True)
class AP2PaymentMandate:
    """AP2 Payment Mandate - payment instruction."""

    mandate_id: str
    mandate_type: str = "payment"
    issuer: str = ""
    subject: str = ""
    expires_at: int = 0
    nonce: str = ""
    proof: AP2VCProof = field(default_factory=AP2VCProof)
    domain: str = ""
    purpose: str = "checkout"
    chain: str = ""
    token: str = ""
    amount_minor: int = 0
    destination: str = ""
    audit_hash: str = ""


@dataclass(slots=True)
class AP2MandateChain:
    """Complete AP2 mandate chain."""

    intent: AP2IntentMandate
    cart: AP2CartMandate
    payment: AP2PaymentMandate


# ============ Adapter Result Types ============


@dataclass(slots=True)
class AdapterResult:
    """Result of an adapter operation."""

    success: bool
    error: Optional[str] = None
    error_code: Optional[str] = None


@dataclass(slots=True)
class AP2ToUCPResult(AdapterResult):
    """Result of converting AP2 to UCP mandates."""

    cart_mandate: Optional[UCPCartMandate] = None
    checkout_mandate: Optional[UCPCheckoutMandate] = None
    payment_mandate: Optional[UCPPaymentMandate] = None


@dataclass(slots=True)
class UCPToAP2Result(AdapterResult):
    """Result of converting UCP to AP2 mandates."""

    intent_mandate: Optional[AP2IntentMandate] = None
    cart_mandate: Optional[AP2CartMandate] = None
    payment_mandate: Optional[AP2PaymentMandate] = None


# ============ Verifier Protocol ============


class MandateVerifier(Protocol):
    """Protocol for AP2 mandate verification."""

    def verify_chain(
        self,
        intent: Any,
        cart: Any,
        payment: Any,
    ) -> tuple[bool, str | None]:
        """
        Verify a complete mandate chain.

        Returns:
            Tuple of (is_valid, error_message)
        """
        ...


# ============ Main Adapter ============


class AP2MandateAdapter:
    """
    Bidirectional adapter between AP2 and UCP mandates.

    This adapter enables:
    1. Converting UCP checkout flows to AP2 mandates for verification
    2. Converting AP2 mandates to UCP format for UCP-based APIs
    3. Linking mandate chains across protocols for audit trails
    """

    def __init__(
        self,
        verifier: MandateVerifier | None = None,
        platform_domain: str = "sardis.sh",
    ) -> None:
        """
        Initialize the adapter.

        Args:
            verifier: Optional AP2 mandate verifier for validation
            platform_domain: Domain for mandate issuance
        """
        self._verifier = verifier
        self._platform_domain = platform_domain

    # ============ UCP -> AP2 Conversion ============

    def ucp_cart_to_ap2(
        self,
        ucp_cart: UCPCartMandate,
        issuer: str,
        subject: str,
    ) -> AP2CartMandate:
        """
        Convert a UCP cart mandate to AP2 format.

        Args:
            ucp_cart: UCP cart mandate to convert
            issuer: Mandate issuer (merchant)
            subject: Mandate subject (customer/agent)

        Returns:
            AP2 CartMandate
        """
        # Convert line items to AP2 format
        ap2_line_items = []
        for item in ucp_cart.line_items:
            ap2_item = {
                "item_id": item.item_id,
                "name": item.name,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price_minor": item.unit_price_minor,
                "currency": item.currency.value,
                "sku": item.sku,
            }
            ap2_line_items.append(ap2_item)

        return AP2CartMandate(
            mandate_id=ucp_cart.mandate_id,
            issuer=issuer,
            subject=subject,
            expires_at=ucp_cart.expires_at,
            nonce=ucp_cart.nonce,
            domain=ucp_cart.merchant_domain,
            purpose="cart",
            line_items=ap2_line_items,
            merchant_domain=ucp_cart.merchant_domain,
            currency=ucp_cart.currency.value,
            subtotal_minor=ucp_cart.subtotal_minor,
            taxes_minor=ucp_cart.taxes_minor,
        )

    def ucp_checkout_to_ap2_intent(
        self,
        ucp_checkout: UCPCheckoutMandate,
    ) -> AP2IntentMandate:
        """
        Convert a UCP checkout mandate to AP2 intent format.

        Args:
            ucp_checkout: UCP checkout mandate to convert

        Returns:
            AP2 IntentMandate
        """
        return AP2IntentMandate(
            mandate_id=ucp_checkout.mandate_id,
            issuer=ucp_checkout.issuer,
            subject=ucp_checkout.subject,
            expires_at=ucp_checkout.expires_at,
            nonce=ucp_checkout.nonce,
            domain=self._platform_domain,
            purpose="checkout",
            scope=list(ucp_checkout.scope),
            requested_amount=ucp_checkout.authorized_amount_minor,
            proof=AP2VCProof(
                verification_method=ucp_checkout.verification_method or "",
                proof_value=ucp_checkout.proof_value or "",
                created=ucp_checkout.created_at.isoformat(),
            ),
        )

    def ucp_payment_to_ap2(
        self,
        ucp_payment: UCPPaymentMandate,
    ) -> AP2PaymentMandate:
        """
        Convert a UCP payment mandate to AP2 format.

        Args:
            ucp_payment: UCP payment mandate to convert

        Returns:
            AP2 PaymentMandate
        """
        return AP2PaymentMandate(
            mandate_id=ucp_payment.mandate_id,
            issuer=ucp_payment.issuer,
            subject=ucp_payment.subject,
            expires_at=ucp_payment.expires_at,
            nonce=ucp_payment.nonce,
            domain=self._platform_domain,
            purpose="checkout",
            chain=ucp_payment.chain,
            token=ucp_payment.token,
            amount_minor=ucp_payment.amount_minor,
            destination=ucp_payment.destination,
            audit_hash=ucp_payment.audit_hash,
            proof=AP2VCProof(
                verification_method=ucp_payment.verification_method or "",
                proof_value=ucp_payment.proof_value or "",
                created=ucp_payment.created_at.isoformat(),
            ),
        )

    def ucp_to_ap2_chain(
        self,
        cart: UCPCartMandate,
        checkout: UCPCheckoutMandate,
        payment: UCPPaymentMandate,
    ) -> UCPToAP2Result:
        """
        Convert a complete UCP mandate chain to AP2 format.

        Args:
            cart: UCP cart mandate
            checkout: UCP checkout mandate
            payment: UCP payment mandate

        Returns:
            UCPToAP2Result with converted mandates
        """
        try:
            ap2_cart = self.ucp_cart_to_ap2(
                cart,
                issuer=cart.merchant_id,
                subject=checkout.subject,
            )
            ap2_intent = self.ucp_checkout_to_ap2_intent(checkout)
            ap2_payment = self.ucp_payment_to_ap2(payment)

            # Verify chain if verifier is available
            if self._verifier:
                is_valid, error = self._verifier.verify_chain(
                    ap2_intent, ap2_cart, ap2_payment
                )
                if not is_valid:
                    return UCPToAP2Result(
                        success=False,
                        error=error or "Mandate chain verification failed",
                        error_code="verification_failed",
                    )

            return UCPToAP2Result(
                success=True,
                intent_mandate=ap2_intent,
                cart_mandate=ap2_cart,
                payment_mandate=ap2_payment,
            )

        except Exception as e:
            logger.error(f"UCP to AP2 conversion failed: {e}")
            return UCPToAP2Result(
                success=False,
                error=str(e),
                error_code="conversion_error",
            )

    # ============ AP2 -> UCP Conversion ============

    def ap2_cart_to_ucp(
        self,
        ap2_cart: AP2CartMandate,
        merchant_id: str,
        merchant_name: str,
    ) -> UCPCartMandate:
        """
        Convert an AP2 cart mandate to UCP format.

        Args:
            ap2_cart: AP2 cart mandate to convert
            merchant_id: Merchant identifier
            merchant_name: Merchant display name

        Returns:
            UCPCartMandate
        """
        # Convert line items to UCP format
        ucp_line_items = []
        for item in ap2_cart.line_items:
            ucp_item = UCPLineItem(
                item_id=item.get("item_id", str(uuid.uuid4())),
                name=item.get("name", "Unknown Item"),
                description=item.get("description", ""),
                quantity=item.get("quantity", 1),
                unit_price_minor=item.get("unit_price_minor", 0),
                currency=UCPCurrency(item.get("currency", "USD")),
                sku=item.get("sku"),
            )
            ucp_line_items.append(ucp_item)

        return UCPCartMandate(
            mandate_id=ap2_cart.mandate_id,
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            merchant_domain=ap2_cart.merchant_domain,
            line_items=ucp_line_items,
            currency=UCPCurrency(ap2_cart.currency),
            subtotal_minor=ap2_cart.subtotal_minor,
            taxes_minor=ap2_cart.taxes_minor,
            expires_at=ap2_cart.expires_at,
            nonce=ap2_cart.nonce,
        )

    def ap2_intent_to_ucp_checkout(
        self,
        ap2_intent: AP2IntentMandate,
        cart_mandate_id: str,
        currency: UCPCurrency = UCPCurrency.USD,
    ) -> UCPCheckoutMandate:
        """
        Convert an AP2 intent mandate to UCP checkout format.

        Args:
            ap2_intent: AP2 intent mandate to convert
            cart_mandate_id: ID of the associated cart mandate
            currency: Currency for the checkout

        Returns:
            UCPCheckoutMandate
        """
        return UCPCheckoutMandate(
            mandate_id=ap2_intent.mandate_id,
            cart_mandate_id=cart_mandate_id,
            subject=ap2_intent.subject,
            issuer=ap2_intent.issuer,
            authorized_amount_minor=ap2_intent.requested_amount or 0,
            currency=currency,
            scope=list(ap2_intent.scope),
            expires_at=ap2_intent.expires_at,
            nonce=ap2_intent.nonce,
            proof_value=ap2_intent.proof.proof_value,
            verification_method=ap2_intent.proof.verification_method,
        )

    def ap2_payment_to_ucp(
        self,
        ap2_payment: AP2PaymentMandate,
        checkout_mandate_id: str,
    ) -> UCPPaymentMandate:
        """
        Convert an AP2 payment mandate to UCP format.

        Args:
            ap2_payment: AP2 payment mandate to convert
            checkout_mandate_id: ID of the associated checkout mandate

        Returns:
            UCPPaymentMandate
        """
        return UCPPaymentMandate(
            mandate_id=ap2_payment.mandate_id,
            checkout_mandate_id=checkout_mandate_id,
            subject=ap2_payment.subject,
            issuer=ap2_payment.issuer,
            chain=ap2_payment.chain,
            token=ap2_payment.token,
            amount_minor=ap2_payment.amount_minor,
            destination=ap2_payment.destination,
            audit_hash=ap2_payment.audit_hash,
            nonce=ap2_payment.nonce,
            expires_at=ap2_payment.expires_at,
            proof_value=ap2_payment.proof.proof_value,
            verification_method=ap2_payment.proof.verification_method,
        )

    def ap2_to_ucp_chain(
        self,
        intent: AP2IntentMandate,
        cart: AP2CartMandate,
        payment: AP2PaymentMandate,
        merchant_id: str,
        merchant_name: str,
    ) -> AP2ToUCPResult:
        """
        Convert a complete AP2 mandate chain to UCP format.

        Args:
            intent: AP2 intent mandate
            cart: AP2 cart mandate
            payment: AP2 payment mandate
            merchant_id: Merchant identifier for UCP
            merchant_name: Merchant display name

        Returns:
            AP2ToUCPResult with converted mandates
        """
        try:
            ucp_cart = self.ap2_cart_to_ucp(
                cart,
                merchant_id=merchant_id,
                merchant_name=merchant_name,
            )
            ucp_checkout = self.ap2_intent_to_ucp_checkout(
                intent,
                cart_mandate_id=ucp_cart.mandate_id,
                currency=ucp_cart.currency,
            )
            ucp_payment = self.ap2_payment_to_ucp(
                payment,
                checkout_mandate_id=ucp_checkout.mandate_id,
            )

            return AP2ToUCPResult(
                success=True,
                cart_mandate=ucp_cart,
                checkout_mandate=ucp_checkout,
                payment_mandate=ucp_payment,
            )

        except Exception as e:
            logger.error(f"AP2 to UCP conversion failed: {e}")
            return AP2ToUCPResult(
                success=False,
                error=str(e),
                error_code="conversion_error",
            )

    # ============ Audit Hash Utilities ============

    def compute_audit_hash(
        self,
        cart_mandate_id: str,
        checkout_mandate_id: str,
        amount_minor: int,
        chain: str,
        token: str,
        destination: str,
    ) -> str:
        """
        Compute an audit hash linking the mandate chain.

        The audit hash provides a cryptographic link between all mandates
        in the chain for verification and dispute resolution.
        """
        data = f"{cart_mandate_id}:{checkout_mandate_id}:{amount_minor}:{chain}:{token}:{destination}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_audit_hash(
        self,
        payment_mandate: UCPPaymentMandate,
        cart_mandate_id: str,
        checkout_mandate_id: str,
    ) -> bool:
        """
        Verify the audit hash of a payment mandate matches the chain.
        """
        expected_hash = self.compute_audit_hash(
            cart_mandate_id=cart_mandate_id,
            checkout_mandate_id=checkout_mandate_id,
            amount_minor=payment_mandate.amount_minor,
            chain=payment_mandate.chain,
            token=payment_mandate.token,
            destination=payment_mandate.destination,
        )
        return payment_mandate.audit_hash == expected_hash


__all__ = [
    # AP2 Types
    "AP2VCProof",
    "AP2IntentMandate",
    "AP2CartMandate",
    "AP2PaymentMandate",
    "AP2MandateChain",
    # Results
    "AdapterResult",
    "AP2ToUCPResult",
    "UCPToAP2Result",
    # Protocols
    "MandateVerifier",
    # Main Adapter
    "AP2MandateAdapter",
]
