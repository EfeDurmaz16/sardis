"""
Webhooks resource for Sardis SDK.

This module provides both async and sync interfaces for webhook management.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..models.webhook import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    Webhook,
    WebhookDelivery,
    WebhookEventType,
)
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncWebhooksResource(AsyncBaseResource):
    """Async resource for webhook management.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create a webhook
            webhook = await client.webhooks.create(
                url="https://example.com/webhooks",
                events=["payment.completed", "hold.captured"],
            )

            # List webhooks
            webhooks = await client.webhooks.list()

            # Delete a webhook
            await client.webhooks.delete(webhook.webhook_id)
        ```
    """

    async def list_event_types(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[str]:
        """List all available webhook event types.

        Args:
            timeout: Optional request timeout

        Returns:
            List of event type strings
        """
        response = await self._get("/api/v2/webhooks/event-types", timeout=timeout)
        return response.get("event_types", [])

    async def create(
        self,
        url: str,
        events: List[str],
        organization_id: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Webhook:
        """Create a webhook subscription.

        Args:
            url: The URL to send webhook events to
            events: List of event types to subscribe to
            organization_id: Optional organization ID
            description: Optional description
            is_active: Whether the webhook is active
            timeout: Optional request timeout

        Returns:
            Created webhook subscription
        """
        request = CreateWebhookRequest(
            url=url,
            events=events,
            organization_id=organization_id,
        )
        response = await self._post("/api/v2/webhooks", request.to_dict(), timeout=timeout)
        return Webhook.model_validate(response)

    async def list(
        self,
        limit: int = 100,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Webhook]:
        """List all webhook subscriptions.

        Args:
            limit: Maximum number of webhooks to return
            timeout: Optional request timeout

        Returns:
            List of webhook subscriptions
        """
        response = await self._get("/api/v2/webhooks", params={"limit": limit}, timeout=timeout)
        return [Webhook.model_validate(w) for w in response.get("webhooks", [])]

    async def get(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Webhook:
        """Get a webhook subscription by ID.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout

        Returns:
            Webhook subscription details
        """
        response = await self._get(f"/api/v2/webhooks/{webhook_id}", timeout=timeout)
        return Webhook.model_validate(response)

    async def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Webhook:
        """Update a webhook subscription.

        Args:
            webhook_id: The webhook ID
            url: New URL (optional)
            events: New event list (optional)
            is_active: New active status (optional)
            timeout: Optional request timeout

        Returns:
            Updated webhook subscription
        """
        request = UpdateWebhookRequest(
            url=url,
            events=events,
            is_active=is_active,
        )
        data = {k: v for k, v in request.to_dict().items() if v is not None}
        response = await self._patch(f"/api/v2/webhooks/{webhook_id}", data, timeout=timeout)
        return Webhook.model_validate(response)

    async def delete(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> None:
        """Delete a webhook subscription.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout
        """
        await self._delete(f"/api/v2/webhooks/{webhook_id}", timeout=timeout)

    async def test(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> WebhookDelivery:
        """Send a test event to a webhook.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout

        Returns:
            Delivery attempt details
        """
        response = await self._post(f"/api/v2/webhooks/{webhook_id}/test", {}, timeout=timeout)
        return WebhookDelivery.model_validate(response)

    async def list_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[WebhookDelivery]:
        """List delivery attempts for a webhook.

        Args:
            webhook_id: The webhook ID
            limit: Maximum number of deliveries to return
            timeout: Optional request timeout

        Returns:
            List of delivery attempts
        """
        response = await self._get(
            f"/api/v2/webhooks/{webhook_id}/deliveries",
            params={"limit": limit},
            timeout=timeout,
        )
        return [WebhookDelivery.model_validate(d) for d in response.get("deliveries", [])]

    async def rotate_secret(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, str]:
        """Rotate the webhook signing secret.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout

        Returns:
            Dict with new secret
        """
        return await self._post(f"/api/v2/webhooks/{webhook_id}/rotate-secret", {}, timeout=timeout)


class WebhooksResource(SyncBaseResource):
    """Sync resource for webhook management.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create a webhook
            webhook = client.webhooks.create(
                url="https://example.com/webhooks",
                events=["payment.completed", "hold.captured"],
            )

            # List webhooks
            webhooks = client.webhooks.list()

            # Delete a webhook
            client.webhooks.delete(webhook.webhook_id)
        ```
    """

    def list_event_types(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[str]:
        """List all available webhook event types.

        Args:
            timeout: Optional request timeout

        Returns:
            List of event type strings
        """
        response = self._get("/api/v2/webhooks/event-types", timeout=timeout)
        return response.get("event_types", [])

    def create(
        self,
        url: str,
        events: List[str],
        organization_id: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Webhook:
        """Create a webhook subscription.

        Args:
            url: The URL to send webhook events to
            events: List of event types to subscribe to
            organization_id: Optional organization ID
            description: Optional description
            is_active: Whether the webhook is active
            timeout: Optional request timeout

        Returns:
            Created webhook subscription
        """
        request = CreateWebhookRequest(
            url=url,
            events=events,
            organization_id=organization_id,
        )
        response = self._post("/api/v2/webhooks", request.to_dict(), timeout=timeout)
        return Webhook.model_validate(response)

    def list(
        self,
        limit: int = 100,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Webhook]:
        """List all webhook subscriptions.

        Args:
            limit: Maximum number of webhooks to return
            timeout: Optional request timeout

        Returns:
            List of webhook subscriptions
        """
        response = self._get("/api/v2/webhooks", params={"limit": limit}, timeout=timeout)
        return [Webhook.model_validate(w) for w in response.get("webhooks", [])]

    def get(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Webhook:
        """Get a webhook subscription by ID.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout

        Returns:
            Webhook subscription details
        """
        response = self._get(f"/api/v2/webhooks/{webhook_id}", timeout=timeout)
        return Webhook.model_validate(response)

    def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Webhook:
        """Update a webhook subscription.

        Args:
            webhook_id: The webhook ID
            url: New URL (optional)
            events: New event list (optional)
            is_active: New active status (optional)
            timeout: Optional request timeout

        Returns:
            Updated webhook subscription
        """
        request = UpdateWebhookRequest(
            url=url,
            events=events,
            is_active=is_active,
        )
        data = {k: v for k, v in request.to_dict().items() if v is not None}
        response = self._patch(f"/api/v2/webhooks/{webhook_id}", data, timeout=timeout)
        return Webhook.model_validate(response)

    def delete(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> None:
        """Delete a webhook subscription.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout
        """
        self._delete(f"/api/v2/webhooks/{webhook_id}", timeout=timeout)

    def test(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> WebhookDelivery:
        """Send a test event to a webhook.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout

        Returns:
            Delivery attempt details
        """
        response = self._post(f"/api/v2/webhooks/{webhook_id}/test", {}, timeout=timeout)
        return WebhookDelivery.model_validate(response)

    def list_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[WebhookDelivery]:
        """List delivery attempts for a webhook.

        Args:
            webhook_id: The webhook ID
            limit: Maximum number of deliveries to return
            timeout: Optional request timeout

        Returns:
            List of delivery attempts
        """
        response = self._get(
            f"/api/v2/webhooks/{webhook_id}/deliveries",
            params={"limit": limit},
            timeout=timeout,
        )
        return [WebhookDelivery.model_validate(d) for d in response.get("deliveries", [])]

    def rotate_secret(
        self,
        webhook_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, str]:
        """Rotate the webhook signing secret.

        Args:
            webhook_id: The webhook ID
            timeout: Optional request timeout

        Returns:
            Dict with new secret
        """
        return self._post(f"/api/v2/webhooks/{webhook_id}/rotate-secret", {}, timeout=timeout)


__all__ = [
    "AsyncWebhooksResource",
    "WebhooksResource",
]
