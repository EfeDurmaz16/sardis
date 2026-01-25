"""
Holds resource for Sardis SDK.

This module provides both async and sync interfaces for hold (pre-authorization) operations.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..models.hold import (
    CaptureHoldRequest,
    CreateHoldRequest,
    CreateHoldResponse,
    Hold,
)
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncHoldsResource(AsyncBaseResource):
    """Async resource for hold (pre-authorization) operations.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create a hold
            hold = await client.holds.create(
                wallet_id="wallet_123",
                amount=Decimal("100.00"),
            )

            # Capture the hold
            hold = await client.holds.capture(hold.hold_id)

            # Or void it
            hold = await client.holds.void(hold.hold_id)
        ```
    """

    async def create(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
        merchant_id: Optional[str] = None,
        purpose: Optional[str] = None,
        duration_hours: int = 24,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> CreateHoldResponse:
        """Create a hold (pre-authorization) on funds.

        Args:
            wallet_id: The wallet to hold funds from
            amount: Amount to hold
            token: Token type (default: USDC)
            merchant_id: Optional merchant identifier
            purpose: Optional purpose description
            duration_hours: How long the hold is valid (default: 24 hours)
            timeout: Optional request timeout

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
        response = await self._post("/api/v2/holds", request.to_dict(), timeout=timeout)
        return CreateHoldResponse.model_validate(response)

    async def get(
        self,
        hold_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Hold:
        """Get a hold by ID.

        Args:
            hold_id: The hold ID
            timeout: Optional request timeout

        Returns:
            Hold details
        """
        response = await self._get(f"/api/v2/holds/{hold_id}", timeout=timeout)
        return Hold.model_validate(response)

    async def capture(
        self,
        hold_id: str,
        amount: Optional[Decimal] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Hold:
        """Capture a hold (complete the payment).

        Args:
            hold_id: The hold ID to capture
            amount: Amount to capture (if None, captures full hold amount)
            timeout: Optional request timeout

        Returns:
            Updated hold details
        """
        data: Dict[str, Any] = {}
        if amount is not None:
            data["amount"] = str(amount)
        response = await self._post(f"/api/v2/holds/{hold_id}/capture", data, timeout=timeout)
        return Hold.model_validate(response)

    async def void(
        self,
        hold_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Hold:
        """Void a hold (cancel without payment).

        Args:
            hold_id: The hold ID to void
            timeout: Optional request timeout

        Returns:
            Updated hold details
        """
        response = await self._post(f"/api/v2/holds/{hold_id}/void", {}, timeout=timeout)
        return Hold.model_validate(response)

    async def list_by_wallet(
        self,
        wallet_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Hold]:
        """List all holds for a wallet.

        Args:
            wallet_id: The wallet ID
            timeout: Optional request timeout

        Returns:
            List of holds
        """
        response = await self._get(f"/api/v2/holds/wallet/{wallet_id}", timeout=timeout)
        return [Hold.model_validate(h) for h in response.get("holds", [])]

    async def list_active(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Hold]:
        """List all active holds.

        Args:
            timeout: Optional request timeout

        Returns:
            List of active holds
        """
        response = await self._get("/api/v2/holds", timeout=timeout)
        return [Hold.model_validate(h) for h in response.get("holds", [])]


class HoldsResource(SyncBaseResource):
    """Sync resource for hold (pre-authorization) operations.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create a hold
            hold = client.holds.create(
                wallet_id="wallet_123",
                amount=Decimal("100.00"),
            )

            # Capture the hold
            hold = client.holds.capture(hold.hold_id)

            # Or void it
            hold = client.holds.void(hold.hold_id)
        ```
    """

    def create(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
        merchant_id: Optional[str] = None,
        purpose: Optional[str] = None,
        duration_hours: int = 24,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> CreateHoldResponse:
        """Create a hold (pre-authorization) on funds.

        Args:
            wallet_id: The wallet to hold funds from
            amount: Amount to hold
            token: Token type (default: USDC)
            merchant_id: Optional merchant identifier
            purpose: Optional purpose description
            duration_hours: How long the hold is valid (default: 24 hours)
            timeout: Optional request timeout

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
        response = self._post("/api/v2/holds", request.to_dict(), timeout=timeout)
        return CreateHoldResponse.model_validate(response)

    def get(
        self,
        hold_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Hold:
        """Get a hold by ID.

        Args:
            hold_id: The hold ID
            timeout: Optional request timeout

        Returns:
            Hold details
        """
        response = self._get(f"/api/v2/holds/{hold_id}", timeout=timeout)
        return Hold.model_validate(response)

    def capture(
        self,
        hold_id: str,
        amount: Optional[Decimal] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Hold:
        """Capture a hold (complete the payment).

        Args:
            hold_id: The hold ID to capture
            amount: Amount to capture (if None, captures full hold amount)
            timeout: Optional request timeout

        Returns:
            Updated hold details
        """
        data: Dict[str, Any] = {}
        if amount is not None:
            data["amount"] = str(amount)
        response = self._post(f"/api/v2/holds/{hold_id}/capture", data, timeout=timeout)
        return Hold.model_validate(response)

    def void(
        self,
        hold_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Hold:
        """Void a hold (cancel without payment).

        Args:
            hold_id: The hold ID to void
            timeout: Optional request timeout

        Returns:
            Updated hold details
        """
        response = self._post(f"/api/v2/holds/{hold_id}/void", {}, timeout=timeout)
        return Hold.model_validate(response)

    def list_by_wallet(
        self,
        wallet_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Hold]:
        """List all holds for a wallet.

        Args:
            wallet_id: The wallet ID
            timeout: Optional request timeout

        Returns:
            List of holds
        """
        response = self._get(f"/api/v2/holds/wallet/{wallet_id}", timeout=timeout)
        return [Hold.model_validate(h) for h in response.get("holds", [])]

    def list_active(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Hold]:
        """List all active holds.

        Args:
            timeout: Optional request timeout

        Returns:
            List of active holds
        """
        response = self._get("/api/v2/holds", timeout=timeout)
        return [Hold.model_validate(h) for h in response.get("holds", [])]


__all__ = [
    "AsyncHoldsResource",
    "HoldsResource",
]
