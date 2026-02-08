"""Webhook API routes for subscription management and delivery logs."""
from __future__ import annotations

import ipaddress
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl

from sardis_api.middleware.auth import require_api_key, APIKey

_logger = logging.getLogger("sardis.api.webhooks")


def _validate_webhook_url(url: str) -> str:
    """Validate a webhook URL to prevent SSRF attacks.

    SECURITY: Without this validation, an attacker could register webhook URLs
    pointing to internal services (e.g., http://169.254.169.254/latest/meta-data/,
    http://localhost:8080/admin) and exfiltrate data or trigger internal actions
    when webhook events fire.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook URL",
        )

    # Require HTTPS in production
    if parsed.scheme not in ("https", "http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must use HTTPS (or HTTP for local development)",
        )

    hostname = parsed.hostname or ""

    # Block obviously internal hostnames
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", "metadata.google.internal"}
    if hostname.lower() in blocked_hosts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must not point to a local/internal address",
        )

    # Block private/reserved IP ranges
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook URL must not point to a private or reserved IP address",
            )
    except ValueError:
        # hostname is not a raw IP — that's fine (e.g., "example.com")
        pass

    # Block AWS/GCP/Azure metadata endpoints
    if hostname.startswith("169.254.") or hostname == "metadata.google.internal":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL must not point to cloud metadata endpoints",
        )

    return url
from sardis_v2_core.webhooks import (
    WebhookRepository,
    WebhookService,
    WebhookSubscription,
    WebhookEvent,
    EventType,
    DeliveryAttempt,
)


router = APIRouter(tags=["webhooks"])


# Request/Response Models

class CreateWebhookRequest(BaseModel):
    """Request to create a webhook subscription."""
    url: str = Field(..., description="Endpoint URL to receive events")
    events: Optional[List[str]] = Field(
        None,
        description="Event types to subscribe to. Empty/null = all events.",
        example=["payment.completed", "hold.created"],
    )


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook subscription."""
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    """Webhook subscription response."""
    subscription_id: str
    url: str
    events: List[str]
    secret: Optional[str] = None  # Only shown on create
    is_active: bool
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime]
    created_at: datetime

    @classmethod
    def from_subscription(
        cls, sub: WebhookSubscription, show_secret: bool = False
    ) -> "WebhookResponse":
        return cls(
            subscription_id=sub.subscription_id,
            url=sub.url,
            events=sub.events,
            secret=sub.secret if show_secret else None,
            is_active=sub.is_active,
            total_deliveries=sub.total_deliveries,
            successful_deliveries=sub.successful_deliveries,
            failed_deliveries=sub.failed_deliveries,
            last_delivery_at=sub.last_delivery_at,
            created_at=sub.created_at,
        )


class DeliveryResponse(BaseModel):
    """Webhook delivery attempt response."""
    attempt_id: str
    subscription_id: str
    event_id: str
    event_type: str
    url: str
    status_code: Optional[int]
    error: Optional[str]
    duration_ms: int
    success: bool
    attempt_number: int
    created_at: datetime

    @classmethod
    def from_attempt(cls, attempt: DeliveryAttempt) -> "DeliveryResponse":
        return cls(
            attempt_id=attempt.attempt_id,
            subscription_id=attempt.subscription_id,
            event_id=attempt.event_id,
            event_type=attempt.event_type,
            url=attempt.url,
            status_code=attempt.status_code,
            error=attempt.error,
            duration_ms=attempt.duration_ms,
            success=attempt.success,
            attempt_number=attempt.attempt_number,
            created_at=attempt.created_at,
        )


class TestWebhookResponse(BaseModel):
    """Response from testing a webhook."""
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    duration_ms: int = 0


class EventTypesResponse(BaseModel):
    """List of available event types."""
    event_types: List[str]


# Dependencies

class WebhookDependencies:
    """Dependencies for webhook routes."""
    def __init__(self, repository: WebhookRepository, service: WebhookService):
        self.repository = repository
        self.service = service


def get_deps() -> WebhookDependencies:
    """Dependency injection placeholder."""
    raise NotImplementedError("Must be overridden")


# Routes

@router.get("/event-types", response_model=EventTypesResponse)
async def list_event_types():
    """List all available webhook event types."""
    return EventTypesResponse(
        event_types=[e.value for e in EventType]
    )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: CreateWebhookRequest,
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """Create a new webhook subscription."""
    organization_id = api_key.organization_id
    # SECURITY: Validate URL to prevent SSRF
    _validate_webhook_url(request.url)
    # Validate event types if provided
    if request.events:
        valid_events = {e.value for e in EventType}
        for event in request.events:
            if event not in valid_events:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event}. Valid types: {list(valid_events)}",
                )

    subscription = await deps.repository.create_subscription(
        organization_id=organization_id,
        url=request.url,
        events=request.events,
    )

    return WebhookResponse.from_subscription(subscription, show_secret=True)


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """List all webhook subscriptions."""
    organization_id = api_key.organization_id
    subscriptions = await deps.repository.list_subscriptions(
        organization_id=organization_id,
        active_only=False,
    )
    return [WebhookResponse.from_subscription(s) for s in subscriptions]


@router.get("/{subscription_id}", response_model=WebhookResponse)
async def get_webhook(
    subscription_id: str,
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """Get a webhook subscription by ID."""
    subscription = await deps.repository.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    if subscription.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")
    return WebhookResponse.from_subscription(subscription, show_secret=False)


@router.patch("/{subscription_id}", response_model=WebhookResponse)
async def update_webhook(
    subscription_id: str,
    request: UpdateWebhookRequest,
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """Update a webhook subscription."""
    existing = await deps.repository.get_subscription(subscription_id)
    if not existing or existing.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    # SECURITY: Validate URL to prevent SSRF on update
    if request.url:
        _validate_webhook_url(request.url)

    # Validate event types if provided
    if request.events:
        valid_events = {e.value for e in EventType}
        for event in request.events:
            if event not in valid_events:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event}",
                )

    subscription = await deps.repository.update_subscription(
        subscription_id=subscription_id,
        url=request.url,
        events=request.events,
        is_active=request.is_active,
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )

    return WebhookResponse.from_subscription(subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    subscription_id: str,
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """Delete a webhook subscription."""
    existing = await deps.repository.get_subscription(subscription_id)
    if not existing or existing.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    deleted = await deps.repository.delete_subscription(subscription_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )


@router.post("/{subscription_id}/test", response_model=TestWebhookResponse)
async def test_webhook(
    subscription_id: str,
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """Send a test event to verify the webhook endpoint."""
    subscription = await deps.repository.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    if subscription.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    # Create test event
    test_event = WebhookEvent(
        event_type=EventType.PAYMENT_COMPLETED,
        data={
            "test": True,
            "message": "This is a test webhook event from Sardis",
            "subscription_id": subscription_id,
        },
    )

    # Deliver and wait
    results = await deps.service.emit_and_wait(test_event)
    result = results.get(subscription_id)

    if not result:
        return TestWebhookResponse(success=False, error="No delivery attempted")

    return TestWebhookResponse(
        success=result.success,
        status_code=result.status_code,
        error=result.error,
        duration_ms=result.duration_ms,
    )


@router.get("/{subscription_id}/deliveries", response_model=List[DeliveryResponse])
async def list_deliveries(
    subscription_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """List delivery attempts for a webhook subscription."""
    # Verify subscription exists
    subscription = await deps.repository.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    if subscription.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    deliveries = await deps.repository.list_deliveries(
        subscription_id=subscription_id,
        limit=limit,
    )
    return [DeliveryResponse.from_attempt(d) for d in deliveries]


@router.post("/{subscription_id}/rotate-secret", response_model=WebhookResponse)
async def rotate_secret(
    subscription_id: str,
    deps: WebhookDependencies = Depends(get_deps),
    api_key: APIKey = Depends(require_api_key),
):
    """Rotate the webhook signing secret."""
    subscription = await deps.repository.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found",
        )
    if subscription.organization_id != api_key.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")

    # Generate new secret
    from uuid import uuid4
    new_secret = f"whsec_{uuid4().hex}"

    # Persist the new secret
    await deps.repository.update_subscription(
        subscription_id, secret=new_secret
    )
    subscription.secret = new_secret

    return WebhookResponse.from_subscription(subscription, show_secret=True)
