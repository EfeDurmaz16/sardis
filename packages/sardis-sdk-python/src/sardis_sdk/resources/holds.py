"""Holds resource for Sardis SDK."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from ..models.hold import (
    CaptureHoldRequest,
    CreateHoldRequest,
    CreateHoldResponse,
    Hold,
)
from .base import BaseResource


class HoldsResource(BaseResource):
    """Resource for hold (pre-authorization) operations."""
    
    async def create(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
        merchant_id: Optional[str] = None,
        purpose: Optional[str] = None,
        duration_hours: int = 24,
    ) -> CreateHoldResponse:
        """
        Create a hold (pre-authorization) on funds.
        
        Args:
            wallet_id: The wallet to hold funds from
            amount: Amount to hold
            token: Token type (default: USDC)
            merchant_id: Optional merchant identifier
            purpose: Optional purpose description
            duration_hours: How long the hold is valid (default: 24 hours)
            
        Returns:
            CreateHoldResponse with hold details
        """
        request = CreateHoldRequest(
            wallet_id=wallet_id,
            amount=amount,
            token=token,
            merchant_id=merchant_id,
            purpose=purpose,
            duration_hours=duration_hours,
        )
        response = await self._post("/api/v2/holds", request.to_dict())
        return CreateHoldResponse.model_validate(response)
    
    async def get(self, hold_id: str) -> Hold:
        """
        Get a hold by ID.
        
        Args:
            hold_id: The hold ID
            
        Returns:
            Hold details
        """
        response = await self._get(f"/api/v2/holds/{hold_id}")
        return Hold.model_validate(response)
    
    async def capture(
        self,
        hold_id: str,
        amount: Optional[Decimal] = None,
    ) -> Hold:
        """
        Capture a hold (complete the payment).
        
        Args:
            hold_id: The hold ID to capture
            amount: Amount to capture (if None, captures full hold amount)
            
        Returns:
            Updated hold details
        """
        data = {}
        if amount is not None:
            data["amount"] = str(amount)
        response = await self._post(f"/api/v2/holds/{hold_id}/capture", data)
        return Hold.model_validate(response)
    
    async def void(self, hold_id: str) -> Hold:
        """
        Void a hold (cancel without payment).
        
        Args:
            hold_id: The hold ID to void
            
        Returns:
            Updated hold details
        """
        response = await self._post(f"/api/v2/holds/{hold_id}/void", {})
        return Hold.model_validate(response)
    
    async def list_by_wallet(self, wallet_id: str) -> list[Hold]:
        """
        List all holds for a wallet.
        
        Args:
            wallet_id: The wallet ID
            
        Returns:
            List of holds
        """
        response = await self._get(f"/api/v2/holds/wallet/{wallet_id}")
        return [Hold.model_validate(h) for h in response.get("holds", [])]
    
    async def list_active(self) -> list[Hold]:
        """
        List all active holds.
        
        Returns:
            List of active holds
        """
        response = await self._get("/api/v2/holds")
        return [Hold.model_validate(h) for h in response.get("holds", [])]
