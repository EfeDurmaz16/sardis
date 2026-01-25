"""
Payments resource for Sardis SDK.

This module provides both async and sync interfaces for payment operations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from ..models.payment import (
    ExecuteAP2Request,
    ExecuteAP2Response,
    ExecuteMandateRequest,
    ExecutePaymentResponse,
)
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncPaymentsResource(AsyncBaseResource):
    """Async resource for payment operations.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Execute a mandate
            result = await client.payments.execute_mandate(mandate)

            # Execute an AP2 payment bundle
            result = await client.payments.execute_ap2(
                intent=intent_mandate,
                cart=cart_mandate,
                payment=payment_mandate,
            )
        ```
    """

    async def execute_mandate(
        self,
        mandate: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExecutePaymentResponse:
        """Execute a single payment mandate.

        Args:
            mandate: The mandate to execute
            timeout: Optional request timeout

        Returns:
            ExecutePaymentResponse with transaction details
        """
        response = await self._post("mandates/execute", {"mandate": mandate}, timeout=timeout)
        return ExecutePaymentResponse.model_validate(response)

    async def execute_ap2(
        self,
        intent: Dict[str, Any],
        cart: Dict[str, Any],
        payment: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExecuteAP2Response:
        """Execute a full AP2 payment bundle (Intent -> Cart -> Payment).

        Args:
            intent: The intent mandate
            cart: The cart mandate
            payment: The payment mandate
            timeout: Optional request timeout

        Returns:
            ExecuteAP2Response with transaction details
        """
        response = await self._post(
            "/api/v2/ap2/payments/execute",
            {"intent": intent, "cart": cart, "payment": payment},
            timeout=timeout,
        )
        return ExecuteAP2Response.model_validate(response)

    async def execute_ap2_bundle(
        self,
        bundle: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExecuteAP2Response:
        """Execute a pre-built AP2 payment bundle.

        Args:
            bundle: Dict containing intent, cart, and payment mandates
            timeout: Optional request timeout

        Returns:
            ExecuteAP2Response with transaction details
        """
        return await self.execute_ap2(
            intent=bundle["intent"],
            cart=bundle["cart"],
            payment=bundle["payment"],
            timeout=timeout,
        )


class PaymentsResource(SyncBaseResource):
    """Sync resource for payment operations.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Execute a mandate
            result = client.payments.execute_mandate(mandate)

            # Execute an AP2 payment bundle
            result = client.payments.execute_ap2(
                intent=intent_mandate,
                cart=cart_mandate,
                payment=payment_mandate,
            )
        ```
    """

    def execute_mandate(
        self,
        mandate: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExecutePaymentResponse:
        """Execute a single payment mandate.

        Args:
            mandate: The mandate to execute
            timeout: Optional request timeout

        Returns:
            ExecutePaymentResponse with transaction details
        """
        response = self._post("mandates/execute", {"mandate": mandate}, timeout=timeout)
        return ExecutePaymentResponse.model_validate(response)

    def execute_ap2(
        self,
        intent: Dict[str, Any],
        cart: Dict[str, Any],
        payment: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExecuteAP2Response:
        """Execute a full AP2 payment bundle (Intent -> Cart -> Payment).

        Args:
            intent: The intent mandate
            cart: The cart mandate
            payment: The payment mandate
            timeout: Optional request timeout

        Returns:
            ExecuteAP2Response with transaction details
        """
        response = self._post(
            "/api/v2/ap2/payments/execute",
            {"intent": intent, "cart": cart, "payment": payment},
            timeout=timeout,
        )
        return ExecuteAP2Response.model_validate(response)

    def execute_ap2_bundle(
        self,
        bundle: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ExecuteAP2Response:
        """Execute a pre-built AP2 payment bundle.

        Args:
            bundle: Dict containing intent, cart, and payment mandates
            timeout: Optional request timeout

        Returns:
            ExecuteAP2Response with transaction details
        """
        return self.execute_ap2(
            intent=bundle["intent"],
            cart=bundle["cart"],
            payment=bundle["payment"],
            timeout=timeout,
        )


__all__ = [
    "AsyncPaymentsResource",
    "PaymentsResource",
]
