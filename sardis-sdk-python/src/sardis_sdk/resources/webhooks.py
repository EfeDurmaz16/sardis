"""Webhooks resource for Sardis SDK."""
from __future__ import annotations

from typing import Optional

from ..models.webhook import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    Webhook,
    WebhookDelivery,
    WebhookEventType,
)
from .base import BaseResource


class WebhooksResource(BaseResource):
    """Resource for webhook operations."""
    
    async def list_event_types(self) -> list[str]:
        """
        List all available webhook event types.
        
        Returns:
            List of event type strings
        """
        response = await self._get("/api/v2/webhooks/event-types")
        return response.get("event_types", [])
    
    async def create(
        self,
        url: str,
        events: list[str],
        organization_id: Optional[str] = None,
    ) -> Webhook:
        """
        Create a webhook subscription.
        
        Args:
            url: The URL to send webhook events to
            events: List of event types to subscribe to
            organization_id: Optional organization ID
            
        Returns:
            Created webhook subscription
        """
        request = CreateWebhookRequest(
            url=url,
            events=events,
            organization_id=organization_id,
        )
        response = await self._post("/api/v2/webhooks", request.to_dict())
        return Webhook.model_validate(response)
    
    async def list(self) -> list[Webhook]:
        """
        List all webhook subscriptions.
        
        Returns:
            List of webhook subscriptions
        """
        response = await self._get("/api/v2/webhooks")
        return [Webhook.model_validate(w) for w in response.get("webhooks", [])]
    
    async def get(self, webhook_id: str) -> Webhook:
        """
        Get a webhook subscription by ID.
        
        Args:
            webhook_id: The webhook ID
            
        Returns:
            Webhook subscription details
        """
        response = await self._get(f"/api/v2/webhooks/{webhook_id}")
        return Webhook.model_validate(response)
    
    async def update(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[list[str]] = None,
        is_active: Optional[bool] = None,
    ) -> Webhook:
        """
        Update a webhook subscription.
        
        Args:
            webhook_id: The webhook ID
            url: New URL (optional)
            events: New event list (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated webhook subscription
        """
        request = UpdateWebhookRequest(
            url=url,
            events=events,
            is_active=is_active,
        )
        # Only include non-None values
        data = {k: v for k, v in request.to_dict().items() if v is not None}
        response = await self._patch(f"/api/v2/webhooks/{webhook_id}", data)
        return Webhook.model_validate(response)
    
    async def delete(self, webhook_id: str) -> None:
        """
        Delete a webhook subscription.
        
        Args:
            webhook_id: The webhook ID
        """
        await self._delete(f"/api/v2/webhooks/{webhook_id}")
    
    async def test(self, webhook_id: str) -> WebhookDelivery:
        """
        Send a test event to a webhook.
        
        Args:
            webhook_id: The webhook ID
            
        Returns:
            Delivery attempt details
        """
        response = await self._post(f"/api/v2/webhooks/{webhook_id}/test", {})
        return WebhookDelivery.model_validate(response)
    
    async def list_deliveries(
        self,
        webhook_id: str,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        """
        List delivery attempts for a webhook.
        
        Args:
            webhook_id: The webhook ID
            limit: Maximum number of deliveries to return
            
        Returns:
            List of delivery attempts
        """
        response = await self._get(
            f"/api/v2/webhooks/{webhook_id}/deliveries",
            params={"limit": limit},
        )
        return [WebhookDelivery.model_validate(d) for d in response.get("deliveries", [])]
    
    async def rotate_secret(self, webhook_id: str) -> dict[str, str]:
        """
        Rotate the webhook signing secret.
        
        Args:
            webhook_id: The webhook ID
            
        Returns:
            Dict with new secret
        """
        return await self._post(f"/api/v2/webhooks/{webhook_id}/rotate-secret", {})
