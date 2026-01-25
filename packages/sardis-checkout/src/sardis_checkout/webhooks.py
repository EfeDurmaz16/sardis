"""
Webhook delivery system with retry support.

This module provides comprehensive webhook management including:
- Endpoint registration and management
- Secure signature generation and verification
- Delivery with exponential backoff retry
- Delivery status tracking
- Dead letter queue for failed deliveries
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

import httpx

from sardis_checkout.models import (
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEndpoint,
    CheckoutEventType,
)

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Base exception for webhook errors."""
    pass


class WebhookEndpointNotFound(WebhookError):
    """Raised when a webhook endpoint is not found."""
    pass


class WebhookDeliveryFailed(WebhookError):
    """Raised when webhook delivery fails permanently."""
    pass


class WebhookSignatureInvalid(WebhookError):
    """Raised when webhook signature verification fails."""
    pass


# Retry configuration
@dataclass
class RetryConfig:
    """Configuration for webhook retry behavior."""
    max_attempts: int = 5
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 3600.0  # 1 hour max
    exponential_base: float = 2.0
    jitter_factor: float = 0.1  # 10% jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number."""
        delay = min(
            self.initial_delay_seconds * (self.exponential_base ** attempt),
            self.max_delay_seconds,
        )
        # Add jitter
        jitter = delay * self.jitter_factor
        return delay + (jitter * (2 * (hash(str(attempt)) % 100) / 100 - 1))


class WebhookStore(ABC):
    """Abstract interface for webhook storage."""

    @abstractmethod
    async def create_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Create a new webhook endpoint."""
        pass

    @abstractmethod
    async def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        """Get a webhook endpoint by ID."""
        pass

    @abstractmethod
    async def list_endpoints(
        self,
        enabled_only: bool = True,
    ) -> List[WebhookEndpoint]:
        """List all webhook endpoints."""
        pass

    @abstractmethod
    async def update_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Update a webhook endpoint."""
        pass

    @abstractmethod
    async def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete a webhook endpoint."""
        pass

    @abstractmethod
    async def create_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Create a new webhook delivery record."""
        pass

    @abstractmethod
    async def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """Get a webhook delivery by ID."""
        pass

    @abstractmethod
    async def update_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Update a webhook delivery."""
        pass

    @abstractmethod
    async def get_pending_deliveries(self, limit: int = 100) -> List[WebhookDelivery]:
        """Get deliveries that need to be retried."""
        pass

    @abstractmethod
    async def get_deliveries_for_endpoint(
        self,
        endpoint_id: str,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """Get delivery history for an endpoint."""
        pass


class InMemoryWebhookStore(WebhookStore):
    """
    In-memory webhook store for development and testing.

    Note: This store is not suitable for production use.
    Use a persistent store like a database.
    """

    def __init__(self):
        self._endpoints: Dict[str, WebhookEndpoint] = {}
        self._deliveries: Dict[str, WebhookDelivery] = {}

    async def create_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        self._endpoints[endpoint.endpoint_id] = endpoint
        return endpoint

    async def get_endpoint(self, endpoint_id: str) -> Optional[WebhookEndpoint]:
        return self._endpoints.get(endpoint_id)

    async def list_endpoints(
        self,
        enabled_only: bool = True,
    ) -> List[WebhookEndpoint]:
        endpoints = list(self._endpoints.values())
        if enabled_only:
            endpoints = [e for e in endpoints if e.enabled]
        return endpoints

    async def update_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        self._endpoints[endpoint.endpoint_id] = endpoint
        return endpoint

    async def delete_endpoint(self, endpoint_id: str) -> bool:
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            return True
        return False

    async def create_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        self._deliveries[delivery.delivery_id] = delivery
        return delivery

    async def get_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        return self._deliveries.get(delivery_id)

    async def update_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        self._deliveries[delivery.delivery_id] = delivery
        return delivery

    async def get_pending_deliveries(self, limit: int = 100) -> List[WebhookDelivery]:
        now = datetime.utcnow()
        pending = [
            d for d in self._deliveries.values()
            if d.status in (WebhookDeliveryStatus.PENDING, WebhookDeliveryStatus.RETRYING)
            and (d.next_retry_at is None or d.next_retry_at <= now)
        ]
        return sorted(pending, key=lambda d: d.created_at)[:limit]

    async def get_deliveries_for_endpoint(
        self,
        endpoint_id: str,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        deliveries = [
            d for d in self._deliveries.values()
            if d.webhook_id == endpoint_id
        ]
        return sorted(deliveries, key=lambda d: d.created_at, reverse=True)[:limit]


class WebhookSigner:
    """Handles webhook signature generation and verification."""

    def __init__(
        self,
        algorithm: str = "sha256",
        signature_header: str = "X-Webhook-Signature",
        timestamp_header: str = "X-Webhook-Timestamp",
        tolerance_seconds: int = 300,  # 5 minutes
    ):
        self.algorithm = algorithm
        self.signature_header = signature_header
        self.timestamp_header = timestamp_header
        self.tolerance_seconds = tolerance_seconds

    def sign(
        self,
        payload: bytes,
        secret: str,
        timestamp: Optional[int] = None,
    ) -> tuple[str, int]:
        """
        Generate a signature for a webhook payload.

        Returns (signature, timestamp).
        """
        ts = timestamp or int(time.time())
        signed_payload = f"{ts}.{payload.decode()}".encode()

        signature = hmac.new(
            secret.encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        return f"v1={signature}", ts

    def verify(
        self,
        payload: bytes,
        secret: str,
        signature: str,
        timestamp: int,
    ) -> bool:
        """
        Verify a webhook signature.

        Returns True if valid, False otherwise.
        """
        # Check timestamp tolerance
        now = int(time.time())
        if abs(now - timestamp) > self.tolerance_seconds:
            return False

        # Generate expected signature
        expected_sig, _ = self.sign(payload, secret, timestamp)

        # Constant-time comparison
        return hmac.compare_digest(expected_sig, signature)

    def get_headers(
        self,
        payload: bytes,
        secret: str,
    ) -> Dict[str, str]:
        """Generate webhook headers including signature."""
        signature, timestamp = self.sign(payload, secret)
        return {
            self.signature_header: signature,
            self.timestamp_header: str(timestamp),
            "Content-Type": "application/json",
        }


class WebhookDeliveryManager:
    """
    Manages webhook delivery with retry support.

    Features:
    - Asynchronous delivery
    - Exponential backoff retry
    - Signature generation
    - Delivery status tracking
    - Circuit breaker for failing endpoints
    """

    def __init__(
        self,
        store: WebhookStore,
        signer: Optional[WebhookSigner] = None,
        retry_config: Optional[RetryConfig] = None,
        http_timeout: float = 30.0,
        max_concurrent_deliveries: int = 10,
    ):
        self.store = store
        self.signer = signer or WebhookSigner()
        self.retry_config = retry_config or RetryConfig()
        self.http_timeout = http_timeout
        self.max_concurrent = max_concurrent_deliveries
        self._client: Optional[httpx.AsyncClient] = None
        self._delivery_task: Optional[asyncio.Task] = None
        self._running = False
        self._semaphore = asyncio.Semaphore(max_concurrent_deliveries)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.http_timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client and stop delivery task."""
        self._running = False
        if self._delivery_task:
            self._delivery_task.cancel()
            try:
                await self._delivery_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
            self._client = None

    # Endpoint Management

    async def register_endpoint(
        self,
        url: str,
        events: List[str],
        secret: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WebhookEndpoint:
        """
        Register a new webhook endpoint.

        Args:
            url: Endpoint URL
            events: List of event types to receive
            secret: Signing secret (generated if not provided)
            metadata: Additional metadata

        Returns:
            The created WebhookEndpoint
        """
        endpoint = WebhookEndpoint(
            endpoint_id=str(uuid.uuid4()),
            url=url,
            secret=secret or self._generate_secret(),
            events=events,
            enabled=True,
            metadata=metadata or {},
        )

        await self.store.create_endpoint(endpoint)
        logger.info(f"Registered webhook endpoint {endpoint.endpoint_id} for {url}")

        return endpoint

    def _generate_secret(self) -> str:
        """Generate a random webhook secret."""
        return hashlib.sha256(uuid.uuid4().bytes).hexdigest()

    async def get_endpoint(self, endpoint_id: str) -> WebhookEndpoint:
        """Get a webhook endpoint by ID."""
        endpoint = await self.store.get_endpoint(endpoint_id)
        if not endpoint:
            raise WebhookEndpointNotFound(f"Endpoint {endpoint_id} not found")
        return endpoint

    async def update_endpoint(
        self,
        endpoint_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        enabled: Optional[bool] = None,
        secret: Optional[str] = None,
    ) -> WebhookEndpoint:
        """Update a webhook endpoint."""
        endpoint = await self.get_endpoint(endpoint_id)

        if url is not None:
            endpoint.url = url
        if events is not None:
            endpoint.events = events
        if enabled is not None:
            endpoint.enabled = enabled
        if secret is not None:
            endpoint.secret = secret

        await self.store.update_endpoint(endpoint)
        return endpoint

    async def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete a webhook endpoint."""
        return await self.store.delete_endpoint(endpoint_id)

    async def list_endpoints(self) -> List[WebhookEndpoint]:
        """List all webhook endpoints."""
        return await self.store.list_endpoints(enabled_only=False)

    # Delivery

    async def queue_delivery(
        self,
        event_type: str,
        payload: Dict[str, Any],
        endpoint_ids: Optional[List[str]] = None,
    ) -> List[WebhookDelivery]:
        """
        Queue webhook delivery to matching endpoints.

        Args:
            event_type: Event type (e.g., "checkout.session.completed")
            payload: Event payload
            endpoint_ids: Specific endpoints (None = all matching)

        Returns:
            List of created WebhookDelivery records
        """
        if endpoint_ids:
            endpoints = []
            for eid in endpoint_ids:
                try:
                    endpoint = await self.get_endpoint(eid)
                    if endpoint.enabled:
                        endpoints.append(endpoint)
                except WebhookEndpointNotFound:
                    continue
        else:
            all_endpoints = await self.store.list_endpoints(enabled_only=True)
            endpoints = [
                e for e in all_endpoints
                if event_type in e.events or "*" in e.events
            ]

        deliveries = []
        for endpoint in endpoints:
            delivery = WebhookDelivery(
                delivery_id=str(uuid.uuid4()),
                webhook_id=endpoint.endpoint_id,
                endpoint_url=endpoint.url,
                event_type=event_type,
                payload=payload,
                status=WebhookDeliveryStatus.PENDING,
                max_attempts=self.retry_config.max_attempts,
            )
            await self.store.create_delivery(delivery)
            deliveries.append(delivery)

        logger.info(
            f"Queued {len(deliveries)} webhook deliveries for event {event_type}"
        )

        return deliveries

    async def deliver(self, delivery_id: str) -> WebhookDelivery:
        """
        Attempt to deliver a webhook.

        Returns the updated delivery record.
        """
        delivery = await self.store.get_delivery(delivery_id)
        if not delivery:
            raise WebhookError(f"Delivery {delivery_id} not found")

        endpoint = await self.store.get_endpoint(delivery.webhook_id)
        if not endpoint:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.error_message = "Endpoint not found"
            await self.store.update_delivery(delivery)
            return delivery

        return await self._attempt_delivery(delivery, endpoint)

    async def _attempt_delivery(
        self,
        delivery: WebhookDelivery,
        endpoint: WebhookEndpoint,
    ) -> WebhookDelivery:
        """Attempt a single delivery."""
        delivery.attempt_count += 1
        delivery.last_attempt_at = datetime.utcnow()
        delivery.status = WebhookDeliveryStatus.RETRYING

        try:
            async with self._semaphore:
                client = await self._get_client()

                # Prepare payload
                payload_bytes = json.dumps(delivery.payload).encode()

                # Generate signature headers
                headers = self.signer.get_headers(payload_bytes, endpoint.secret)
                headers.update(delivery.headers)

                # Send request
                response = await client.post(
                    endpoint.url,
                    content=payload_bytes,
                    headers=headers,
                )

                delivery.response_status_code = response.status_code
                delivery.response_body = response.text[:1000]  # Truncate response

                if 200 <= response.status_code < 300:
                    # Success
                    delivery.status = WebhookDeliveryStatus.DELIVERED
                    delivery.delivered_at = datetime.utcnow()
                    delivery.error_message = None

                    # Update endpoint success tracking
                    endpoint.last_success_at = datetime.utcnow()
                    endpoint.failure_count = 0
                    await self.store.update_endpoint(endpoint)

                    logger.info(
                        f"Webhook delivered: {delivery.delivery_id} to {endpoint.url}"
                    )
                else:
                    # Non-success response
                    self._handle_failure(delivery, endpoint, f"HTTP {response.status_code}")

        except httpx.TimeoutException:
            self._handle_failure(delivery, endpoint, "Request timed out")
        except httpx.RequestError as e:
            self._handle_failure(delivery, endpoint, f"Request error: {e}")
        except Exception as e:
            self._handle_failure(delivery, endpoint, f"Unexpected error: {e}")

        await self.store.update_delivery(delivery)
        await self.store.update_endpoint(endpoint)

        return delivery

    def _handle_failure(
        self,
        delivery: WebhookDelivery,
        endpoint: WebhookEndpoint,
        error_message: str,
    ) -> None:
        """Handle delivery failure."""
        delivery.error_message = error_message

        # Update endpoint failure tracking
        endpoint.failure_count += 1
        endpoint.last_failure_at = datetime.utcnow()

        if delivery.attempt_count >= delivery.max_attempts:
            # Max attempts reached
            delivery.status = WebhookDeliveryStatus.FAILED
            logger.warning(
                f"Webhook delivery failed permanently: {delivery.delivery_id} "
                f"to {endpoint.url} after {delivery.attempt_count} attempts"
            )
        else:
            # Schedule retry
            delivery.status = WebhookDeliveryStatus.RETRYING
            delay = self.retry_config.get_delay(delivery.attempt_count)
            delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)

            logger.info(
                f"Webhook delivery failed, scheduling retry: {delivery.delivery_id} "
                f"attempt {delivery.attempt_count}/{delivery.max_attempts} "
                f"next retry in {delay:.1f}s"
            )

    # Background Processing

    async def start_delivery_worker(self) -> None:
        """Start the background delivery worker."""
        self._running = True
        self._delivery_task = asyncio.create_task(self._delivery_loop())
        logger.info("Webhook delivery worker started")

    async def stop_delivery_worker(self) -> None:
        """Stop the background delivery worker."""
        self._running = False
        if self._delivery_task:
            self._delivery_task.cancel()
            try:
                await self._delivery_task
            except asyncio.CancelledError:
                pass
        logger.info("Webhook delivery worker stopped")

    async def _delivery_loop(self) -> None:
        """Background loop that processes pending deliveries."""
        while self._running:
            try:
                pending = await self.store.get_pending_deliveries(
                    limit=self.max_concurrent
                )

                if pending:
                    # Process deliveries concurrently
                    tasks = [
                        self.deliver(d.delivery_id) for d in pending
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # No pending deliveries, sleep
                    await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in delivery loop: {e}")
                await asyncio.sleep(5.0)

    # Delivery Status

    async def get_delivery_status(self, delivery_id: str) -> Dict[str, Any]:
        """Get detailed status of a delivery."""
        delivery = await self.store.get_delivery(delivery_id)
        if not delivery:
            raise WebhookError(f"Delivery {delivery_id} not found")

        return {
            "delivery_id": delivery.delivery_id,
            "webhook_id": delivery.webhook_id,
            "endpoint_url": delivery.endpoint_url,
            "event_type": delivery.event_type,
            "status": delivery.status.value,
            "attempt_count": delivery.attempt_count,
            "max_attempts": delivery.max_attempts,
            "created_at": delivery.created_at.isoformat(),
            "last_attempt_at": delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
            "next_retry_at": delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
            "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            "response_status_code": delivery.response_status_code,
            "error_message": delivery.error_message,
        }

    async def get_endpoint_deliveries(
        self,
        endpoint_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get delivery history for an endpoint."""
        deliveries = await self.store.get_deliveries_for_endpoint(endpoint_id, limit)
        return [
            {
                "delivery_id": d.delivery_id,
                "event_type": d.event_type,
                "status": d.status.value,
                "attempt_count": d.attempt_count,
                "created_at": d.created_at.isoformat(),
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "error_message": d.error_message,
            }
            for d in deliveries
        ]

    async def retry_delivery(self, delivery_id: str) -> WebhookDelivery:
        """Manually retry a failed delivery."""
        delivery = await self.store.get_delivery(delivery_id)
        if not delivery:
            raise WebhookError(f"Delivery {delivery_id} not found")

        if delivery.status != WebhookDeliveryStatus.FAILED:
            raise WebhookError(
                f"Can only retry failed deliveries, current status: {delivery.status}"
            )

        # Reset for retry
        delivery.status = WebhookDeliveryStatus.PENDING
        delivery.attempt_count = 0
        delivery.next_retry_at = None
        delivery.error_message = None

        await self.store.update_delivery(delivery)
        logger.info(f"Manually retrying delivery {delivery_id}")

        return await self.deliver(delivery_id)
