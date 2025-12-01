"""
Stripe Issuing Integration

Implements the CardIssuer interface using Stripe Issuing API
for real virtual card creation and management.

Requirements:
- Stripe Issuing account
- stripe Python package
- Webhook endpoint for real-time authorizations
"""

import os
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

from .card_issuer import (
    CardIssuer,
    VirtualCardResult,
    CardTransaction,
    SpendingControls,
    CardStatus,
    TransactionStatus,
)


class StripeCardProvider(CardIssuer):
    """
    Stripe Issuing implementation.
    
    Provides real virtual card issuance using Stripe's Issuing API.
    
    Setup:
    1. Enable Stripe Issuing on your account
    2. Set STRIPE_SECRET_KEY environment variable
    3. Configure webhook endpoint for issuing_authorization.request
    """
    
    def __init__(self, api_key: Optional[str] = None):
        if not STRIPE_AVAILABLE:
            raise RuntimeError("stripe package not installed. Run: pip install stripe")
        
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        if not self.api_key:
            raise ValueError("Stripe API key required")
        
        stripe.api_key = self.api_key
    
    async def create_cardholder(
        self,
        agent_id: str,
        name: str,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a Stripe cardholder."""
        try:
            cardholder = stripe.issuing.Cardholder.create(
                type="individual",
                name=name,
                email=email or f"{agent_id}@sardis.network",
                status="active",
                billing={
                    "address": {
                        "line1": "Sardis Network",
                        "city": "San Francisco",
                        "state": "CA",
                        "postal_code": "94102",
                        "country": "US",
                    }
                },
                metadata={
                    "sardis_agent_id": agent_id,
                    **(metadata or {}),
                },
            )
            return cardholder.id
        except stripe.error.StripeError as e:
            raise RuntimeError(f"Failed to create cardholder: {e}")
    
    async def create_virtual_card(
        self,
        cardholder_id: str,
        spending_controls: SpendingControls,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VirtualCardResult:
        """Create a Stripe Issuing virtual card."""
        try:
            # Build spending controls
            stripe_controls = {
                "spending_limits": [{
                    "amount": int(spending_controls.spending_limit * 100),  # cents
                    "interval": self._map_interval(spending_controls.spending_limit_interval),
                }]
            }
            
            if spending_controls.allowed_categories:
                stripe_controls["allowed_categories"] = spending_controls.allowed_categories
            if spending_controls.blocked_categories:
                stripe_controls["blocked_categories"] = spending_controls.blocked_categories
            
            # Create the card
            card = stripe.issuing.Card.create(
                cardholder=cardholder_id,
                currency="usd",
                type="virtual",
                status="active",
                spending_controls=stripe_controls,
                metadata=metadata or {},
            )
            
            # Retrieve card details (including sensitive data)
            card_details = stripe.issuing.Card.retrieve(
                card.id,
                expand=["number", "cvc"],
            )
            
            return VirtualCardResult(
                success=True,
                card_id=card.id,
                last_four=card.last4,
                card_number=getattr(card_details, "number", None),
                exp_month=card.exp_month,
                exp_year=card.exp_year,
                cvc=getattr(card_details, "cvc", None),
                status=CardStatus.ACTIVE,
                spending_limit=spending_controls.spending_limit,
            )
            
        except stripe.error.StripeError as e:
            return VirtualCardResult(
                success=False,
                error=str(e),
            )
    
    async def get_card(self, card_id: str) -> VirtualCardResult:
        """Get card details from Stripe."""
        try:
            card = stripe.issuing.Card.retrieve(card_id)
            
            return VirtualCardResult(
                success=True,
                card_id=card.id,
                last_four=card.last4,
                exp_month=card.exp_month,
                exp_year=card.exp_year,
                status=self._map_status(card.status),
            )
        except stripe.error.StripeError as e:
            return VirtualCardResult(success=False, error=str(e))
    
    async def update_card_status(
        self,
        card_id: str,
        status: CardStatus
    ) -> VirtualCardResult:
        """Update Stripe card status."""
        try:
            stripe_status = {
                CardStatus.ACTIVE: "active",
                CardStatus.INACTIVE: "inactive",
                CardStatus.CANCELED: "canceled",
                CardStatus.FROZEN: "inactive",  # Stripe doesn't have frozen
            }[status]
            
            card = stripe.issuing.Card.modify(
                card_id,
                status=stripe_status,
            )
            
            return VirtualCardResult(
                success=True,
                card_id=card.id,
                status=self._map_status(card.status),
            )
        except stripe.error.StripeError as e:
            return VirtualCardResult(success=False, error=str(e))
    
    async def update_spending_controls(
        self,
        card_id: str,
        spending_controls: SpendingControls
    ) -> VirtualCardResult:
        """Update Stripe card spending controls."""
        try:
            stripe_controls = {
                "spending_limits": [{
                    "amount": int(spending_controls.spending_limit * 100),
                    "interval": self._map_interval(spending_controls.spending_limit_interval),
                }]
            }
            
            card = stripe.issuing.Card.modify(
                card_id,
                spending_controls=stripe_controls,
            )
            
            return VirtualCardResult(
                success=True,
                card_id=card.id,
                spending_limit=spending_controls.spending_limit,
            )
        except stripe.error.StripeError as e:
            return VirtualCardResult(success=False, error=str(e))
    
    async def list_transactions(
        self,
        card_id: str,
        limit: int = 100,
        starting_after: Optional[str] = None
    ) -> List[CardTransaction]:
        """List Stripe transactions for a card."""
        try:
            params = {
                "card": card_id,
                "limit": limit,
            }
            if starting_after:
                params["starting_after"] = starting_after
            
            transactions = stripe.issuing.Transaction.list(**params)
            
            return [
                CardTransaction(
                    transaction_id=tx.id,
                    card_id=tx.card,
                    amount=Decimal(str(tx.amount)) / 100,  # from cents
                    currency=tx.currency.upper(),
                    merchant_name=tx.merchant_data.get("name", "Unknown"),
                    merchant_category=tx.merchant_data.get("category", ""),
                    status=self._map_tx_status(tx.type),
                    created_at=datetime.fromtimestamp(tx.created),
                    authorization_code=getattr(tx, "authorization", None),
                )
                for tx in transactions.data
            ]
        except stripe.error.StripeError:
            return []
    
    async def handle_authorization(
        self,
        authorization_id: str,
        approve: bool,
        amount: Optional[Decimal] = None
    ) -> bool:
        """Handle Stripe authorization request."""
        try:
            if approve:
                if amount is not None:
                    # Partial approval
                    stripe.issuing.Authorization.approve(
                        authorization_id,
                        amount=int(amount * 100),
                    )
                else:
                    stripe.issuing.Authorization.approve(authorization_id)
            else:
                stripe.issuing.Authorization.decline(authorization_id)
            
            return True
        except stripe.error.StripeError:
            return False
    
    def _map_interval(self, interval: str) -> str:
        """Map our interval to Stripe's."""
        mapping = {
            "per_authorization": "per_authorization",
            "daily": "daily",
            "weekly": "weekly",
            "monthly": "monthly",
            "all_time": "all_time",
        }
        return mapping.get(interval, "per_authorization")
    
    def _map_status(self, stripe_status: str) -> CardStatus:
        """Map Stripe status to our status."""
        mapping = {
            "active": CardStatus.ACTIVE,
            "inactive": CardStatus.INACTIVE,
            "canceled": CardStatus.CANCELED,
        }
        return mapping.get(stripe_status, CardStatus.INACTIVE)
    
    def _map_tx_status(self, tx_type: str) -> TransactionStatus:
        """Map Stripe transaction type to status."""
        if tx_type == "capture":
            return TransactionStatus.COMPLETED
        elif tx_type == "refund":
            return TransactionStatus.REVERSED
        else:
            return TransactionStatus.PENDING


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    endpoint_secret: str
) -> Dict[str, Any]:
    """
    Verify Stripe webhook signature.
    
    Args:
        payload: Raw request body
        signature: Stripe-Signature header
        endpoint_secret: Webhook endpoint secret
        
    Returns:
        Parsed webhook event
        
    Raises:
        ValueError if signature is invalid
    """
    if not STRIPE_AVAILABLE:
        raise RuntimeError("stripe package not installed")
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            endpoint_secret,
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid signature: {e}")

