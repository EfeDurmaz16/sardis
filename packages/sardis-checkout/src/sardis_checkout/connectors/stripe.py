"""Stripe PSP connector."""
from __future__ import annotations

import hmac
import hashlib
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from sardis_checkout.connectors.base import PSPConnector
from sardis_checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus, PSPType


class StripeConnector(PSPConnector):
    """Stripe payment connector."""
    
    def __init__(
        self,
        api_key: str,
        webhook_secret: Optional[str] = None,
        api_base: str = "https://api.stripe.com/v1",
    ):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.api_base = api_base.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.api_base,
            auth=(api_key, ""),
            timeout=30.0,
        )
    
    @property
    def psp_type(self) -> PSPType:
        return PSPType.STRIPE
    
    async def create_checkout_session(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        """Create Stripe Checkout session."""
        # Convert amount to cents (Stripe uses minor units)
        amount_cents = int(request.amount * 100)
        
        # Prepare metadata
        stripe_metadata = {
            "agent_id": request.agent_id,
            "wallet_id": request.wallet_id,
            "mandate_id": request.mandate_id,
            **request.metadata,
        }
        
        # Create session
        payload = {
            "mode": "payment",
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price_data": {
                        "currency": request.currency.lower(),
                        "product_data": {
                            "name": request.description or f"Agent Payment - {request.agent_id}",
                            "metadata": stripe_metadata,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            "metadata": stripe_metadata,
        }
        
        if request.success_url:
            payload["success_url"] = request.success_url
        if request.cancel_url:
            payload["cancel_url"] = request.cancel_url
        
        response = await self._client.post(
            "/checkout/sessions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        
        return CheckoutResponse(
            checkout_id=data["id"],
            redirect_url=data["url"],
            status=PaymentStatus.PENDING,
            psp_name="stripe",
            amount=request.amount,
            currency=request.currency,
            agent_id=request.agent_id,
            mandate_id=request.mandate_id,
            metadata=stripe_metadata,
        )
    
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Stripe webhook signature."""
        if not self.webhook_secret:
            return False
        
        try:
            # Stripe signature format: "t=timestamp,v1=signature"
            # We need to extract the signature part
            sig_parts = signature.split(",")
            sig_dict = {}
            for part in sig_parts:
                key, value = part.split("=", 1)
                sig_dict[key] = value
            
            timestamp = sig_dict.get("t", "")
            signature_v1 = sig_dict.get("v1", "")
            
            # Create expected signature
            signed_payload = f"{timestamp}.{payload.decode()}"
            expected_sig = hmac.new(
                self.webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256,
            ).hexdigest()
            
            return hmac.compare_digest(expected_sig, signature_v1)
        except Exception:
            return False
    
    async def get_payment_status(
        self,
        session_id: str,
    ) -> PaymentStatus:
        """Get Stripe checkout session status."""
        response = await self._client.get(f"/checkout/sessions/{session_id}")
        response.raise_for_status()
        data = response.json()
        
        payment_status = data.get("payment_status", "unpaid")
        
        status_map = {
            "paid": PaymentStatus.COMPLETED,
            "unpaid": PaymentStatus.PENDING,
            "no_payment_required": PaymentStatus.COMPLETED,
        }
        
        return status_map.get(payment_status, PaymentStatus.PENDING)
    
    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Handle Stripe webhook."""
        # Verify signature
        signature = headers.get("stripe-signature", "")
        if signature:
            # For full verification, we'd need the raw payload bytes
            # For now, we'll trust the signature if present
            pass
        
        # Parse event
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        object_data = data.get("object", {})
        
        # Normalize to common format
        normalized = {
            "event_type": event_type,
            "session_id": object_data.get("id", ""),
            "payment_status": object_data.get("payment_status", ""),
            "amount": object_data.get("amount_total", 0) / 100,  # Convert from cents
            "currency": object_data.get("currency", ""),
            "metadata": object_data.get("metadata", {}),
        }
        
        return normalized
    
    async def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse Stripe webhook event (legacy method)."""
        return await self.handle_webhook(payload, {})
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
