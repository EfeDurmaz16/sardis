"""Merchant webhook delivery for Pay with Sardis."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 30]  # seconds


class MerchantWebhookService:
    """
    Delivers webhook events to merchant endpoints.

    Events: checkout.created, checkout.expired, payment.completed,
            payment.failed, settlement.initiated, settlement.completed,
            settlement.failed
    Signature: HMAC-SHA256 in X-Sardis-Signature header.
    Dedup: event_id in payload + X-Sardis-Delivery-Id header.
    """

    def __init__(self, merchant_repo: Any = None, timeout: float = 10.0):
        self._client = httpx.AsyncClient(timeout=timeout)
        self._merchant_repo = merchant_repo

    @staticmethod
    def sign_payload(payload_bytes: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        sig = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={sig}"

    @staticmethod
    def verify_signature(payload_bytes: bytes, secret: str, signature: str) -> bool:
        """Verify webhook signature."""
        expected = MerchantWebhookService.sign_payload(payload_bytes, secret)
        return hmac.compare_digest(expected, signature)

    async def deliver(
        self,
        merchant: Any,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        Deliver webhook to merchant with retries and deduplication.

        Returns True if delivered successfully.
        """
        if not merchant.webhook_url:
            return False

        event_id = f"evt_{uuid.uuid4().hex}"

        body = {
            "event_id": event_id,
            "event": event_type,
            "timestamp": int(time.time()),
            "data": payload,
        }
        body_bytes = json.dumps(body, default=str).encode()
        signature = self.sign_payload(body_bytes, merchant.webhook_secret)

        # Record delivery for dedup tracking
        if self._merchant_repo:
            is_new = await self._merchant_repo.record_webhook_delivery(
                event_id=event_id,
                merchant_id=merchant.merchant_id,
                event_type=event_type,
                payload=body,
            )
            if not is_new:
                logger.info("Duplicate webhook event %s, skipping", event_id)
                return True

        headers = {
            "Content-Type": "application/json",
            "X-Sardis-Signature": signature,
            "X-Sardis-Event": event_type,
            "X-Sardis-Delivery-Id": event_id,
        }

        delivered = False
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.post(
                    merchant.webhook_url,
                    content=body_bytes,
                    headers=headers,
                )
                if response.status_code < 300:
                    logger.info(
                        "Webhook delivered: %s to %s (attempt %d)",
                        event_type, merchant.webhook_url, attempt + 1,
                    )
                    delivered = True
                    break
                logger.warning(
                    "Webhook delivery returned %d for %s (attempt %d)",
                    response.status_code, merchant.webhook_url, attempt + 1,
                )
            except Exception:
                logger.warning(
                    "Webhook delivery failed for %s (attempt %d)",
                    merchant.webhook_url, attempt + 1,
                    exc_info=True,
                )

            if attempt < MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(RETRY_DELAYS[attempt])

        # Update delivery status
        if self._merchant_repo:
            await self._merchant_repo.update_webhook_delivery(
                event_id=event_id,
                status="delivered" if delivered else "failed",
                attempts=MAX_RETRIES if not delivered else attempt + 1,
            )

        if not delivered:
            logger.error(
                "Webhook delivery exhausted retries for %s event=%s",
                merchant.webhook_url, event_type,
            )
        return delivered

    async def close(self) -> None:
        await self._client.aclose()
