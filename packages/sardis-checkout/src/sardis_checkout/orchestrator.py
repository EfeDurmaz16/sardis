"""Checkout orchestration logic."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional, Dict

from sardis_checkout.connectors.base import PSPConnector
from sardis_checkout.models import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentStatus,
)


class CheckoutOrchestrator:
    """
    Orchestrates checkout flow: policy check → PSP selection → session creation.
    
    This class coordinates between:
    - Core Agent Wallet OS (policy engine, mandate verification)
    - PSP connectors (Stripe, PayPal, etc.)
    - Merchant configuration
    """
    
    def __init__(self):
        self.connectors: Dict[str, PSPConnector] = {}
    
    def register_connector(self, psp_name: str, connector: PSPConnector) -> None:
        """Register a PSP connector."""
        self.connectors[psp_name] = connector
    
    async def create_checkout(
        self,
        request: CheckoutRequest,
        psp_preference: Optional[str] = None,
    ) -> CheckoutResponse:
        """
        Create checkout session with policy check and PSP routing.
        
        Flow:
        1. Verify agent identity (TAP)
        2. Verify mandate (AP2)
        3. Check policy (spending limits)
        4. Select PSP
        5. Create checkout session
        """
        # Select PSP
        psp_name = psp_preference or "stripe"  # Default to Stripe
        
        # Get connector
        connector = self.connectors.get(psp_name)
        if not connector:
            # Fallback to first available
            if not self.connectors:
                raise ValueError("No PSP connectors configured")
            psp_name = next(iter(self.connectors.keys()))
            connector = self.connectors[psp_name]
        
        # Create checkout session
        checkout_resp = await connector.create_checkout_session(request)
        return checkout_resp
    
    async def get_payment_status(
        self,
        checkout_id: str,
        psp_name: str,
    ) -> PaymentStatus:
        """Get payment status from PSP."""
        connector = self.connectors.get(psp_name)
        if not connector:
            raise ValueError(f"PSP {psp_name} not configured")
        
        status = await connector.get_payment_status(checkout_id)
        return status
    
    async def handle_webhook(
        self,
        psp: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Handle PSP webhook."""
        connector = self.connectors.get(psp)
        if not connector:
            raise ValueError(f"PSP {psp} not configured")
        
        result = await connector.handle_webhook(payload, headers)
        return result
