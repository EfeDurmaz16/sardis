"""Payments resource for Sardis SDK."""
from __future__ import annotations

from typing import Any

from ..models.payment import (
    ExecuteAP2Request,
    ExecuteAP2Response,
    ExecuteMandateRequest,
    ExecutePaymentResponse,
)
from .base import BaseResource


class PaymentsResource(BaseResource):
    """Resource for payment operations."""
    
    async def execute_mandate(self, mandate: dict[str, Any]) -> ExecutePaymentResponse:
        """
        Execute a single payment mandate.
        
        Args:
            mandate: The mandate to execute
            
        Returns:
            ExecutePaymentResponse with transaction details
        """
        response = await self._post("mandates/execute", {"mandate": mandate})
        return ExecutePaymentResponse.model_validate(response)
    
    async def execute_ap2(
        self,
        intent: dict[str, Any],
        cart: dict[str, Any],
        payment: dict[str, Any],
    ) -> ExecuteAP2Response:
        """
        Execute a full AP2 payment bundle (Intent → Cart → Payment).
        
        Args:
            intent: The intent mandate
            cart: The cart mandate
            payment: The payment mandate
            
        Returns:
            ExecuteAP2Response with transaction details
        """
        response = await self._post(
            "/api/v2/ap2/payments/execute",
            {"intent": intent, "cart": cart, "payment": payment},
        )
        return ExecuteAP2Response.model_validate(response)
    
    async def execute_ap2_bundle(self, bundle: dict[str, Any]) -> ExecuteAP2Response:
        """
        Execute a pre-built AP2 payment bundle.
        
        Args:
            bundle: Dict containing intent, cart, and payment mandates
            
        Returns:
            ExecuteAP2Response with transaction details
        """
        return await self.execute_ap2(
            intent=bundle["intent"],
            cart=bundle["cart"],
            payment=bundle["payment"],
        )
