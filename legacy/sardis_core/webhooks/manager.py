"""Webhook manager for registration and delivery."""

import asyncio
import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
import uuid
import httpx

from .events import WebhookEvent, EventType


logger = logging.getLogger(__name__)


@dataclass
class WebhookSubscription:
    """A webhook subscription configuration."""
    
    subscription_id: str = field(default_factory=lambda: f"whsub_{uuid.uuid4().hex[:16]}")
    
    # Owner
    owner_id: str = ""  # Developer or agent ID
    
    # Target URL
    url: str = ""
    
    # Events to receive
    events: list[EventType] = field(default_factory=list)
    
    # Security
    secret: str = field(default_factory=lambda: f"whsec_{uuid.uuid4().hex}")
    
    # Status
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Delivery stats
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_at: Optional[datetime] = None
    
    def subscribes_to(self, event_type: EventType) -> bool:
        """Check if this subscription wants this event type."""
        if not self.events:  # Empty means all events
            return True
        return event_type in self.events


@dataclass
class DeliveryResult:
    """Result of a webhook delivery attempt."""
    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0


class WebhookManager:
    """
    Manages webhook subscriptions and event delivery.
    
    Features:
    - Register/unregister webhook endpoints
    - Filter events by type
    - HMAC signature for security
    - Retry logic with exponential backoff
    - Delivery tracking
    """
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 5, 30]  # seconds
    DELIVERY_TIMEOUT = 10  # seconds
    
    def __init__(self):
        """Initialize the webhook manager."""
        self._subscriptions: dict[str, WebhookSubscription] = {}
        self._event_queue: asyncio.Queue[tuple[WebhookEvent, str]] = asyncio.Queue()
        self._delivery_callbacks: list[Callable] = []
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.DELIVERY_TIMEOUT)
        return self._http_client
    
    def register(
        self,
        url: str,
        owner_id: str,
        events: Optional[list[EventType]] = None
    ) -> WebhookSubscription:
        """
        Register a new webhook subscription.
        
        Args:
            url: The endpoint URL to receive events
            owner_id: Developer or agent ID
            events: List of event types to subscribe to (None = all)
            
        Returns:
            The created subscription with secret
        """
        subscription = WebhookSubscription(
            url=url,
            owner_id=owner_id,
            events=events or []
        )
        
        self._subscriptions[subscription.subscription_id] = subscription
        logger.info(f"Registered webhook {subscription.subscription_id} for {owner_id}")
        
        return subscription
    
    def unregister(self, subscription_id: str) -> bool:
        """
        Unregister a webhook subscription.
        
        Args:
            subscription_id: The subscription to remove
            
        Returns:
            True if removed, False if not found
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info(f"Unregistered webhook {subscription_id}")
            return True
        return False
    
    def get_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get a subscription by ID."""
        return self._subscriptions.get(subscription_id)
    
    def list_subscriptions(self, owner_id: Optional[str] = None) -> list[WebhookSubscription]:
        """List all subscriptions, optionally filtered by owner."""
        subs = list(self._subscriptions.values())
        if owner_id:
            subs = [s for s in subs if s.owner_id == owner_id]
        return subs
    
    def update_subscription(
        self,
        subscription_id: str,
        url: Optional[str] = None,
        events: Optional[list[EventType]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[WebhookSubscription]:
        """Update a subscription's configuration."""
        sub = self._subscriptions.get(subscription_id)
        if not sub:
            return None
        
        if url is not None:
            sub.url = url
        if events is not None:
            sub.events = events
        if is_active is not None:
            sub.is_active = is_active
        
        return sub
    
    async def emit(self, event: WebhookEvent):
        """
        Emit an event to all matching subscriptions.
        
        This queues the event for delivery and returns immediately.
        """
        matching_subs = [
            sub for sub in self._subscriptions.values()
            if sub.is_active and sub.subscribes_to(event.event_type)
        ]
        
        for sub in matching_subs:
            await self._event_queue.put((event, sub.subscription_id))
        
        logger.debug(f"Emitted {event.event_type} to {len(matching_subs)} subscriptions")
    
    async def emit_and_wait(self, event: WebhookEvent) -> dict[str, DeliveryResult]:
        """
        Emit an event and wait for all deliveries to complete.
        
        Returns:
            Dict mapping subscription_id to DeliveryResult
        """
        results = {}
        
        matching_subs = [
            sub for sub in self._subscriptions.values()
            if sub.is_active and sub.subscribes_to(event.event_type)
        ]
        
        for sub in matching_subs:
            result = await self._deliver(event, sub)
            results[sub.subscription_id] = result
        
        return results
    
    async def _deliver(
        self,
        event: WebhookEvent,
        subscription: WebhookSubscription
    ) -> DeliveryResult:
        """Deliver an event to a subscription with retries."""
        import time
        
        payload = event.to_json()
        signature = self._sign_payload(payload, subscription.secret)
        
        headers = {
            "Content-Type": "application/json",
            "X-Sardis-Signature": signature,
            "X-Sardis-Event-Type": event.event_type.value,
            "X-Sardis-Event-ID": event.event_id,
            "X-Sardis-Timestamp": str(int(event.created_at.timestamp())),
        }
        
        client = await self._get_client()
        
        for attempt in range(self.MAX_RETRIES):
            start_time = time.time()
            
            try:
                response = await client.post(
                    subscription.url,
                    content=payload,
                    headers=headers
                )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code < 300:
                    subscription.total_deliveries += 1
                    subscription.successful_deliveries += 1
                    subscription.last_delivery_at = datetime.now(timezone.utc)
                    
                    return DeliveryResult(
                        success=True,
                        status_code=response.status_code,
                        response_body=response.text[:500],
                        duration_ms=duration_ms
                    )
                else:
                    logger.warning(
                        f"Webhook {subscription.subscription_id} returned {response.status_code}"
                    )
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Webhook delivery failed: {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])
                    continue
                
                subscription.total_deliveries += 1
                subscription.failed_deliveries += 1
                
                return DeliveryResult(
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms
                )
        
        subscription.total_deliveries += 1
        subscription.failed_deliveries += 1
        
        return DeliveryResult(
            success=False,
            error="Max retries exceeded"
        )
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC signature for payload."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str
    ) -> bool:
        """Verify a webhook signature."""
        expected = self._sign_payload(payload, secret)
        return hmac.compare_digest(expected, signature)
    
    async def start_worker(self):
        """Start background worker for async delivery."""
        logger.info("Starting webhook delivery worker")
        
        while True:
            try:
                event, sub_id = await self._event_queue.get()
                
                subscription = self._subscriptions.get(sub_id)
                if subscription and subscription.is_active:
                    await self._deliver(event, subscription)
                
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Webhook worker error: {e}")
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Global webhook manager instance
_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance."""
    global _manager
    if _manager is None:
        _manager = WebhookManager()
    return _manager

