"""Webhook API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from sardis_core.webhooks import WebhookManager, EventType, get_webhook_manager

from sardis_core.api.auth import get_api_key

router = APIRouter(
    prefix="/webhooks", 
    tags=["Webhooks"],
    dependencies=[Depends(get_api_key)]
)


# ========== Schemas ==========

class CreateWebhookRequest(BaseModel):
    """Request to create a webhook subscription."""
    url: str = Field(..., description="The endpoint URL to receive webhook events")
    events: Optional[list[str]] = Field(
        None,
        description="List of event types to subscribe to. Empty/null means all events."
    )


class WebhookResponse(BaseModel):
    """Webhook subscription response."""
    subscription_id: str
    url: str
    events: list[str]
    secret: str
    is_active: bool
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int


class UpdateWebhookRequest(BaseModel):
    """Request to update a webhook subscription."""
    url: Optional[str] = None
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook."""
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    duration_ms: int = 0


# ========== Dependency ==========

def get_manager() -> WebhookManager:
    """Get the webhook manager."""
    return get_webhook_manager()


# ========== Routes ==========

@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook subscription",
    description="Register a new webhook endpoint to receive events."
)
async def create_webhook(
    request: CreateWebhookRequest,
    owner_id: str = "default",  # In production, get from auth
    manager: WebhookManager = Depends(get_manager)
) -> WebhookResponse:
    """Create a new webhook subscription."""
    
    # Parse event types
    events = None
    if request.events:
        try:
            events = [EventType(e) for e in request.events]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {e}"
            )
    
    subscription = manager.register(
        url=request.url,
        owner_id=owner_id,
        events=events
    )
    
    return WebhookResponse(
        subscription_id=subscription.subscription_id,
        url=subscription.url,
        events=[e.value for e in subscription.events] if subscription.events else [],
        secret=subscription.secret,
        is_active=subscription.is_active,
        total_deliveries=subscription.total_deliveries,
        successful_deliveries=subscription.successful_deliveries,
        failed_deliveries=subscription.failed_deliveries
    )


@router.get(
    "",
    response_model=list[WebhookResponse],
    summary="List webhook subscriptions",
    description="List all webhook subscriptions for the current owner."
)
async def list_webhooks(
    owner_id: str = "default",
    manager: WebhookManager = Depends(get_manager)
) -> list[WebhookResponse]:
    """List all webhooks for an owner."""
    subscriptions = manager.list_subscriptions(owner_id=owner_id)
    
    return [
        WebhookResponse(
            subscription_id=sub.subscription_id,
            url=sub.url,
            events=[e.value for e in sub.events] if sub.events else [],
            secret="***",  # Don't expose secret in list
            is_active=sub.is_active,
            total_deliveries=sub.total_deliveries,
            successful_deliveries=sub.successful_deliveries,
            failed_deliveries=sub.failed_deliveries
        )
        for sub in subscriptions
    ]


@router.get(
    "/{subscription_id}",
    response_model=WebhookResponse,
    summary="Get webhook subscription",
    description="Get details of a specific webhook subscription."
)
async def get_webhook(
    subscription_id: str,
    manager: WebhookManager = Depends(get_manager)
) -> WebhookResponse:
    """Get a webhook subscription by ID."""
    subscription = manager.get_subscription(subscription_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found"
        )
    
    return WebhookResponse(
        subscription_id=subscription.subscription_id,
        url=subscription.url,
        events=[e.value for e in subscription.events] if subscription.events else [],
        secret=subscription.secret,
        is_active=subscription.is_active,
        total_deliveries=subscription.total_deliveries,
        successful_deliveries=subscription.successful_deliveries,
        failed_deliveries=subscription.failed_deliveries
    )


@router.patch(
    "/{subscription_id}",
    response_model=WebhookResponse,
    summary="Update webhook subscription",
    description="Update a webhook subscription's configuration."
)
async def update_webhook(
    subscription_id: str,
    request: UpdateWebhookRequest,
    manager: WebhookManager = Depends(get_manager)
) -> WebhookResponse:
    """Update a webhook subscription."""
    
    # Parse event types if provided
    events = None
    if request.events is not None:
        try:
            events = [EventType(e) for e in request.events]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type: {e}"
            )
    
    subscription = manager.update_subscription(
        subscription_id=subscription_id,
        url=request.url,
        events=events,
        is_active=request.is_active
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found"
        )
    
    return WebhookResponse(
        subscription_id=subscription.subscription_id,
        url=subscription.url,
        events=[e.value for e in subscription.events] if subscription.events else [],
        secret=subscription.secret,
        is_active=subscription.is_active,
        total_deliveries=subscription.total_deliveries,
        successful_deliveries=subscription.successful_deliveries,
        failed_deliveries=subscription.failed_deliveries
    )


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook subscription",
    description="Remove a webhook subscription."
)
async def delete_webhook(
    subscription_id: str,
    manager: WebhookManager = Depends(get_manager)
):
    """Delete a webhook subscription."""
    if not manager.unregister(subscription_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found"
        )


@router.post(
    "/{subscription_id}/test",
    response_model=WebhookTestResponse,
    summary="Test webhook endpoint",
    description="Send a test event to verify the webhook endpoint is working."
)
async def test_webhook(
    subscription_id: str,
    manager: WebhookManager = Depends(get_manager)
) -> WebhookTestResponse:
    """Send a test event to a webhook endpoint."""
    from sardis_core.webhooks.events import WebhookEvent, EventType
    
    subscription = manager.get_subscription(subscription_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription {subscription_id} not found"
        )
    
    # Create a test event
    test_event = WebhookEvent(
        event_type=EventType.PAYMENT_COMPLETED,
        data={
            "test": True,
            "message": "This is a test webhook event from Sardis",
            "subscription_id": subscription_id,
        }
    )
    
    # Deliver and wait for result
    results = await manager.emit_and_wait(test_event)
    result = results.get(subscription_id)
    
    if not result:
        return WebhookTestResponse(
            success=False,
            error="No delivery attempted"
        )
    
    return WebhookTestResponse(
        success=result.success,
        status_code=result.status_code,
        error=result.error,
        duration_ms=result.duration_ms
    )


@router.get(
    "/events/types",
    response_model=list[str],
    summary="List available event types",
    description="Get a list of all available webhook event types."
)
async def list_event_types() -> list[str]:
    """List all available event types."""
    return [e.value for e in EventType]

