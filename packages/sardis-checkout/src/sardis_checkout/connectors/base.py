"""Base PSP connector interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from sardis_checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus, PSPType


class PSPConnector(ABC):
    """Abstract interface for PSP connectors."""
    
    @property
    @abstractmethod
    def psp_type(self) -> PSPType:
        """Return the PSP type."""
        pass
    
    @abstractmethod
    async def create_checkout_session(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        """
        Create a checkout session in the PSP.
        
        Args:
            request: CheckoutRequest with payment details
            
        Returns:
            CheckoutResponse with checkout URL
        """
        pass
    
    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify PSP webhook signature.
        
        Args:
            payload: Webhook payload (raw bytes)
            signature: Webhook signature from headers
            
        Returns:
            True if signature is valid
        """
        pass
    
    @abstractmethod
    async def get_payment_status(
        self,
        session_id: str,
    ) -> PaymentStatus:
        """
        Get payment status from PSP.
        
        Args:
            session_id: Checkout session ID
            
        Returns:
            PaymentStatus
        """
        pass
    
    @abstractmethod
    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Handle webhook from PSP.
        
        Args:
            payload: Webhook payload (parsed JSON)
            headers: Webhook headers (for signature verification)
            
        Returns:
            Normalized event data
        """
        pass
    
    async def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Parse webhook event from PSP (legacy method, for backwards compatibility).
        
        Args:
            payload: Webhook payload (parsed JSON)
            
        Returns:
            Normalized event data
        """
        # Default implementation - override in subclasses
        return payload
