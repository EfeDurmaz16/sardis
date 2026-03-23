"""
Subscriptions v2 resource for Sardis SDK.

Sardis Protocol v1.0 -- Recurring billing managed through spending mandates.
Supports fixed-rate and usage-based billing cycles with automatic charge
scheduling, amendments, and metered usage reporting.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    import builtins
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncSubscriptionsV2Resource(AsyncBaseResource):
    """Async resource for subscription management (v2).

    Subscriptions v2 provide mandate-backed recurring billing with support
    for fixed-rate and usage-based billing cycles.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create a monthly subscription
            sub = await client.subscriptions_v2.create(
                mandate_id="mnd_abc",
                merchant_id="merch_xyz",
                billing_cycle="monthly",
                charge_amount=Decimal("29.99"),
            )

            # Report metered usage
            await client.subscriptions_v2.report_usage(
                subscription_id=sub["id"],
                meter_id="api_calls",
                usage_delta=1500,
            )

            # Amend pricing
            await client.subscriptions_v2.amend(
                subscription_id=sub["id"],
                charge_amount=Decimal("39.99"),
            )
        ```
    """

    async def create(
        self,
        mandate_id: str,
        merchant_id: str,
        billing_cycle: str,
        charge_amount: Decimal,
        currency: str = "USDC",
        trial_days: int | None = None,
        usage_metered: bool = False,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create a new subscription.

        Args:
            mandate_id: The spending mandate authorizing recurring charges
            merchant_id: The merchant receiving payments
            billing_cycle: Billing frequency ("daily", "weekly", "monthly", "yearly")
            charge_amount: Amount to charge per billing cycle
            currency: Currency code (default: USDC)
            trial_days: Optional trial period in days
            usage_metered: Whether the subscription is usage-based
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created subscription
        """
        payload: dict[str, Any] = {
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "billing_cycle": billing_cycle,
            "charge_amount": str(charge_amount),
            "currency": currency,
            "usage_metered": usage_metered,
        }

        if trial_days is not None:
            payload["trial_days"] = trial_days
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post("subscriptions", payload, timeout=timeout)

    async def get(
        self,
        subscription_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a subscription by ID.

        Args:
            subscription_id: The subscription ID
            timeout: Optional request timeout

        Returns:
            The subscription object
        """
        return await self._get(f"subscriptions/{subscription_id}", timeout=timeout)

    async def list(
        self,
        status: str | None = None,
        mandate_id: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List subscriptions with optional filters.

        Args:
            status: Filter by status (e.g., "active", "paused", "cancelled")
            mandate_id: Filter by mandate ID
            limit: Maximum number of subscriptions to return
            timeout: Optional request timeout

        Returns:
            List of subscriptions
        """
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status
        if mandate_id is not None:
            params["mandate_id"] = mandate_id

        data = await self._get("subscriptions", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("subscriptions", data.get("items", []))

    async def cancel(
        self,
        subscription_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Cancel a subscription.

        Args:
            subscription_id: The subscription ID to cancel
            timeout: Optional request timeout

        Returns:
            The cancelled subscription
        """
        return await self._post(
            f"subscriptions/{subscription_id}/cancel", timeout=timeout
        )

    async def amend(
        self,
        subscription_id: str,
        charge_amount: Decimal | None = None,
        billing_cycle: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Amend a subscription's terms.

        Args:
            subscription_id: The subscription ID to amend
            charge_amount: New charge amount per billing cycle
            billing_cycle: New billing frequency
            metadata: Updated metadata
            timeout: Optional request timeout

        Returns:
            The amended subscription
        """
        payload: dict[str, Any] = {}
        if charge_amount is not None:
            payload["charge_amount"] = str(charge_amount)
        if billing_cycle is not None:
            payload["billing_cycle"] = billing_cycle
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._patch(
            f"subscriptions/{subscription_id}", payload, timeout=timeout
        )

    async def report_usage(
        self,
        subscription_id: str,
        meter_id: str,
        usage_delta: int,
        timestamp: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Report metered usage for a usage-based subscription.

        Args:
            subscription_id: The subscription ID
            meter_id: Identifier for the usage meter (e.g., "api_calls")
            usage_delta: Incremental usage amount to report
            timestamp: Optional ISO 8601 timestamp for the usage event
            metadata: Optional metadata for this usage event
            timeout: Optional request timeout

        Returns:
            Usage record confirmation
        """
        payload: dict[str, Any] = {
            "meter_id": meter_id,
            "usage_delta": usage_delta,
        }

        if timestamp is not None:
            payload["timestamp"] = timestamp
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post(
            f"subscriptions/{subscription_id}/usage", payload, timeout=timeout
        )


class SubscriptionsV2Resource(SyncBaseResource):
    """Sync resource for subscription management (v2).

    Subscriptions v2 provide mandate-backed recurring billing with support
    for fixed-rate and usage-based billing cycles.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create a monthly subscription
            sub = client.subscriptions_v2.create(
                mandate_id="mnd_abc",
                merchant_id="merch_xyz",
                billing_cycle="monthly",
                charge_amount=Decimal("29.99"),
            )

            # Report metered usage
            client.subscriptions_v2.report_usage(
                subscription_id=sub["id"],
                meter_id="api_calls",
                usage_delta=1500,
            )

            # Amend pricing
            client.subscriptions_v2.amend(
                subscription_id=sub["id"],
                charge_amount=Decimal("39.99"),
            )
        ```
    """

    def create(
        self,
        mandate_id: str,
        merchant_id: str,
        billing_cycle: str,
        charge_amount: Decimal,
        currency: str = "USDC",
        trial_days: int | None = None,
        usage_metered: bool = False,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create a new subscription.

        Args:
            mandate_id: The spending mandate authorizing recurring charges
            merchant_id: The merchant receiving payments
            billing_cycle: Billing frequency ("daily", "weekly", "monthly", "yearly")
            charge_amount: Amount to charge per billing cycle
            currency: Currency code (default: USDC)
            trial_days: Optional trial period in days
            usage_metered: Whether the subscription is usage-based
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created subscription
        """
        payload: dict[str, Any] = {
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "billing_cycle": billing_cycle,
            "charge_amount": str(charge_amount),
            "currency": currency,
            "usage_metered": usage_metered,
        }

        if trial_days is not None:
            payload["trial_days"] = trial_days
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post("subscriptions", payload, timeout=timeout)

    def get(
        self,
        subscription_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a subscription by ID.

        Args:
            subscription_id: The subscription ID
            timeout: Optional request timeout

        Returns:
            The subscription object
        """
        return self._get(f"subscriptions/{subscription_id}", timeout=timeout)

    def list(
        self,
        status: str | None = None,
        mandate_id: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List subscriptions with optional filters.

        Args:
            status: Filter by status (e.g., "active", "paused", "cancelled")
            mandate_id: Filter by mandate ID
            limit: Maximum number of subscriptions to return
            timeout: Optional request timeout

        Returns:
            List of subscriptions
        """
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status
        if mandate_id is not None:
            params["mandate_id"] = mandate_id

        data = self._get("subscriptions", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("subscriptions", data.get("items", []))

    def cancel(
        self,
        subscription_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Cancel a subscription.

        Args:
            subscription_id: The subscription ID to cancel
            timeout: Optional request timeout

        Returns:
            The cancelled subscription
        """
        return self._post(
            f"subscriptions/{subscription_id}/cancel", timeout=timeout
        )

    def amend(
        self,
        subscription_id: str,
        charge_amount: Decimal | None = None,
        billing_cycle: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Amend a subscription's terms.

        Args:
            subscription_id: The subscription ID to amend
            charge_amount: New charge amount per billing cycle
            billing_cycle: New billing frequency
            metadata: Updated metadata
            timeout: Optional request timeout

        Returns:
            The amended subscription
        """
        payload: dict[str, Any] = {}
        if charge_amount is not None:
            payload["charge_amount"] = str(charge_amount)
        if billing_cycle is not None:
            payload["billing_cycle"] = billing_cycle
        if metadata is not None:
            payload["metadata"] = metadata

        return self._patch(
            f"subscriptions/{subscription_id}", payload, timeout=timeout
        )

    def report_usage(
        self,
        subscription_id: str,
        meter_id: str,
        usage_delta: int,
        timestamp: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Report metered usage for a usage-based subscription.

        Args:
            subscription_id: The subscription ID
            meter_id: Identifier for the usage meter (e.g., "api_calls")
            usage_delta: Incremental usage amount to report
            timestamp: Optional ISO 8601 timestamp for the usage event
            metadata: Optional metadata for this usage event
            timeout: Optional request timeout

        Returns:
            Usage record confirmation
        """
        payload: dict[str, Any] = {
            "meter_id": meter_id,
            "usage_delta": usage_delta,
        }

        if timestamp is not None:
            payload["timestamp"] = timestamp
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post(
            f"subscriptions/{subscription_id}/usage", payload, timeout=timeout
        )


__all__ = [
    "AsyncSubscriptionsV2Resource",
    "SubscriptionsV2Resource",
]
