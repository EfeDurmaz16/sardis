"""
Payment Objects resource for Sardis SDK.

Sardis Protocol v1.0 -- Payment Objects are tokenized payment instruments
minted from spending mandates. They encapsulate pre-authorized value that
merchants can verify and present for settlement without touching the
underlying wallet.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    import builtins
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncPaymentObjectsResource(AsyncBaseResource):
    """Async resource for payment object operations.

    Payment objects represent tokenized, pre-authorized payment instruments
    minted from spending mandates. They allow merchants to verify and
    present payments independently of the payer's wallet.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Mint a payment object from a mandate
            obj = await client.payment_objects.mint(
                mandate_id="mnd_abc",
                merchant_id="merch_xyz",
                amount=Decimal("25.00"),
                currency="USDC",
            )

            # Present the object to a merchant
            result = await client.payment_objects.present(
                object_id=obj["id"],
                merchant_id="merch_xyz",
            )
        ```
    """

    async def mint(
        self,
        mandate_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        chain: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Mint a new payment object from a spending mandate.

        Args:
            mandate_id: The spending mandate to draw from
            merchant_id: The merchant who will receive the payment
            amount: Payment amount
            currency: Currency code (default: USDC)
            chain: Optional chain identifier
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The minted payment object
        """
        payload: dict[str, Any] = {
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
        }

        if chain is not None:
            payload["chain"] = chain
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post("payment-objects/mint", payload, timeout=timeout)

    async def present(
        self,
        object_id: str,
        merchant_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Present a payment object to a merchant for settlement.

        Args:
            object_id: The payment object ID
            merchant_id: The receiving merchant ID
            timeout: Optional request timeout

        Returns:
            Presentation result with settlement details
        """
        payload: dict[str, Any] = {
            "merchant_id": merchant_id,
        }

        return await self._post(
            f"payment-objects/{object_id}/present", payload, timeout=timeout
        )

    async def verify(
        self,
        object_id: str,
        merchant_id: str,
        signature: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Verify a payment object's authenticity and validity.

        Args:
            object_id: The payment object ID
            merchant_id: The merchant verifying the object
            signature: Cryptographic signature for verification
            timeout: Optional request timeout

        Returns:
            Verification result with validity status
        """
        payload: dict[str, Any] = {
            "merchant_id": merchant_id,
            "signature": signature,
        }

        return await self._post(
            f"payment-objects/{object_id}/verify", payload, timeout=timeout
        )

    async def get(
        self,
        object_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a payment object by ID.

        Args:
            object_id: The payment object ID
            timeout: Optional request timeout

        Returns:
            The payment object
        """
        return await self._get(f"payment-objects/{object_id}", timeout=timeout)

    async def list(
        self,
        mandate_id: str | None = None,
        merchant_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List payment objects with optional filters.

        Args:
            mandate_id: Filter by source mandate ID
            merchant_id: Filter by merchant ID
            status: Filter by status (e.g., "active", "presented", "settled")
            limit: Maximum number of objects to return
            timeout: Optional request timeout

        Returns:
            List of payment objects
        """
        params: dict[str, Any] = {"limit": limit}
        if mandate_id is not None:
            params["mandate_id"] = mandate_id
        if merchant_id is not None:
            params["merchant_id"] = merchant_id
        if status is not None:
            params["status"] = status

        data = await self._get("payment-objects", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("payment_objects", data.get("items", []))


class PaymentObjectsResource(SyncBaseResource):
    """Sync resource for payment object operations.

    Payment objects represent tokenized, pre-authorized payment instruments
    minted from spending mandates. They allow merchants to verify and
    present payments independently of the payer's wallet.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Mint a payment object from a mandate
            obj = client.payment_objects.mint(
                mandate_id="mnd_abc",
                merchant_id="merch_xyz",
                amount=Decimal("25.00"),
                currency="USDC",
            )

            # Present the object to a merchant
            result = client.payment_objects.present(
                object_id=obj["id"],
                merchant_id="merch_xyz",
            )
        ```
    """

    def mint(
        self,
        mandate_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        chain: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Mint a new payment object from a spending mandate.

        Args:
            mandate_id: The spending mandate to draw from
            merchant_id: The merchant who will receive the payment
            amount: Payment amount
            currency: Currency code (default: USDC)
            chain: Optional chain identifier
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The minted payment object
        """
        payload: dict[str, Any] = {
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
        }

        if chain is not None:
            payload["chain"] = chain
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post("payment-objects/mint", payload, timeout=timeout)

    def present(
        self,
        object_id: str,
        merchant_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Present a payment object to a merchant for settlement.

        Args:
            object_id: The payment object ID
            merchant_id: The receiving merchant ID
            timeout: Optional request timeout

        Returns:
            Presentation result with settlement details
        """
        payload: dict[str, Any] = {
            "merchant_id": merchant_id,
        }

        return self._post(
            f"payment-objects/{object_id}/present", payload, timeout=timeout
        )

    def verify(
        self,
        object_id: str,
        merchant_id: str,
        signature: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Verify a payment object's authenticity and validity.

        Args:
            object_id: The payment object ID
            merchant_id: The merchant verifying the object
            signature: Cryptographic signature for verification
            timeout: Optional request timeout

        Returns:
            Verification result with validity status
        """
        payload: dict[str, Any] = {
            "merchant_id": merchant_id,
            "signature": signature,
        }

        return self._post(
            f"payment-objects/{object_id}/verify", payload, timeout=timeout
        )

    def get(
        self,
        object_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a payment object by ID.

        Args:
            object_id: The payment object ID
            timeout: Optional request timeout

        Returns:
            The payment object
        """
        return self._get(f"payment-objects/{object_id}", timeout=timeout)

    def list(
        self,
        mandate_id: str | None = None,
        merchant_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List payment objects with optional filters.

        Args:
            mandate_id: Filter by source mandate ID
            merchant_id: Filter by merchant ID
            status: Filter by status (e.g., "active", "presented", "settled")
            limit: Maximum number of objects to return
            timeout: Optional request timeout

        Returns:
            List of payment objects
        """
        params: dict[str, Any] = {"limit": limit}
        if mandate_id is not None:
            params["mandate_id"] = mandate_id
        if merchant_id is not None:
            params["merchant_id"] = merchant_id
        if status is not None:
            params["status"] = status

        data = self._get("payment-objects", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("payment_objects", data.get("items", []))


__all__ = [
    "AsyncPaymentObjectsResource",
    "PaymentObjectsResource",
]
