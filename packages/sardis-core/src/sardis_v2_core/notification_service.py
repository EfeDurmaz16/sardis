"""Async notification service with HMAC-signed webhook delivery and retry.

Fire-and-forget: notification delivery never blocks payment execution.
After 3 consecutive failures a webhook is marked unhealthy in the DB.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class NotificationEventType(str, Enum):
    """Supported notification event types."""

    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_REFUND_FAILED = "payment.refund_failed"

    WALLET_CREATED = "wallet.created"
    WALLET_FUNDED = "wallet.funded"

    AGENT_CREATED = "agent.created"
    POLICY_VIOLATED = "policy.violated"

    MANDATE_EXECUTED = "mandate.executed"
    MANDATE_REJECTED = "mandate.rejected"


@dataclass
class NotificationPayload:
    """Webhook delivery payload in Slack Block Kit-compatible format."""

    event_id: str = field(default_factory=lambda: f"ntf_{uuid4().hex[:16]}")
    event_type: str = ""
    org_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "org_id": self.org_id,
            "data": self.data,
            "timestamp": self.timestamp,
            # Slack Block Kit top-level structure
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Sardis: {self.event_type}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": self._summary_text(),
                    },
                },
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def _summary_text(self) -> str:
        parts = [f"*Event:* `{self.event_type}`"]
        if "payment_id" in self.data:
            parts.append(f"*Payment:* `{self.data['payment_id']}`")
        if "amount" in self.data:
            parts.append(f"*Amount:* {self.data['amount']} {self.data.get('currency', 'USDC')}")
        if "reason" in self.data:
            parts.append(f"*Reason:* {self.data['reason']}")
        return "\n".join(parts)


@dataclass
class DeliveryResult:
    """Result of a single delivery attempt."""

    config_id: str
    event_type: str
    success: bool
    status_code: int | None = None
    error: str | None = None
    attempt_number: int = 1
    duration_ms: int = 0


class NotificationService:
    """Async webhook notification service with retry and unhealthy detection."""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # seconds — exponential backoff
    DELIVERY_TIMEOUT = 10  # seconds

    def __init__(self, database: Any = None, signing_secret: str | None = None):
        self._db = database
        self._signing_secret = signing_secret or os.getenv(
            "SARDIS_NOTIFICATION_SECRET", "change-me-in-production"
        )
        self._http_client: Any = None

    async def _get_client(self) -> Any:
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(timeout=self.DELIVERY_TIMEOUT)
        return self._http_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send(
        self,
        org_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Fire-and-forget: deliver notification to all matching webhooks.

        Never raises — errors are logged and recorded.
        """
        configs = await self._get_active_configs(org_id, event_type)
        if not configs:
            return

        notification = NotificationPayload(
            event_type=event_type,
            org_id=org_id,
            data=payload,
        )

        for cfg in configs:
            # Fire and forget — do not block the caller
            asyncio.create_task(self._deliver_with_retry(cfg, notification))

    async def send_test(self, org_id: str) -> DeliveryResult | None:
        """Send a sample event to the org's configured webhook (blocking)."""
        configs = await self._get_active_configs(org_id)
        if not configs:
            return None

        cfg = configs[0]
        notification = NotificationPayload(
            event_type="notification.test",
            org_id=org_id,
            data={"message": "Test notification from Sardis", "test": True},
        )
        return await self._deliver_with_retry(cfg, notification)

    # ------------------------------------------------------------------
    # Config queries
    # ------------------------------------------------------------------

    async def _get_active_configs(
        self, org_id: str, event_type: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch active notification configs for an org, optionally filtered by event type."""
        if self._db is None:
            return []

        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id::text, org_id, webhook_url, event_types, provider,
                           consecutive_failures
                    FROM notification_configs
                    WHERE org_id = $1 AND is_active = true
                    """,
                    org_id,
                )

            configs = []
            for row in rows:
                event_types = row["event_types"] or []
                # Empty event_types list means "subscribe to all"
                if event_type and event_types and event_type not in event_types:
                    continue
                configs.append(dict(row))
            return configs

        except Exception as e:
            logger.error(f"Failed to fetch notification configs: {e}")
            return []

    # ------------------------------------------------------------------
    # Delivery with retry
    # ------------------------------------------------------------------

    async def _deliver_with_retry(
        self, config: dict[str, Any], notification: NotificationPayload
    ) -> DeliveryResult:
        """Deliver with exponential backoff. Mark unhealthy after MAX_RETRIES failures."""
        payload_json = notification.to_json()
        timestamp = int(time.time())
        signature = self._sign_payload(payload_json, timestamp)
        headers = {
            "Content-Type": "application/json",
            "X-Sardis-Signature": signature,
            "X-Sardis-Event-Type": notification.event_type,
            "X-Sardis-Event-ID": notification.event_id,
            "X-Sardis-Timestamp": str(timestamp),
        }

        client = await self._get_client()
        last_result: DeliveryResult | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            start = time.time()
            try:
                response = await client.post(
                    config["webhook_url"],
                    content=payload_json,
                    headers=headers,
                )
                duration_ms = int((time.time() - start) * 1000)
                success = response.status_code < 300

                last_result = DeliveryResult(
                    config_id=config["id"],
                    event_type=notification.event_type,
                    success=success,
                    status_code=response.status_code,
                    attempt_number=attempt,
                    duration_ms=duration_ms,
                )

                if success:
                    await self._record_delivery(config, last_result)
                    await self._reset_failure_count(config["id"])
                    return last_result

                logger.warning(
                    f"Notification delivery to {config['webhook_url']} "
                    f"returned {response.status_code} (attempt {attempt})"
                )

            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                logger.error(f"Notification delivery failed: {e}")
                last_result = DeliveryResult(
                    config_id=config["id"],
                    event_type=notification.event_type,
                    success=False,
                    error=str(e),
                    attempt_number=attempt,
                    duration_ms=duration_ms,
                )

            if attempt < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAYS[attempt - 1])

        # All retries exhausted — record and maybe mark unhealthy
        if last_result:
            await self._record_delivery(config, last_result)
            await self._increment_failure_count(config["id"])

        return last_result or DeliveryResult(
            config_id=config["id"],
            event_type=notification.event_type,
            success=False,
            error="Max retries exceeded",
        )

    # ------------------------------------------------------------------
    # HMAC signing
    # ------------------------------------------------------------------

    def _sign_payload(self, payload: str, timestamp: int) -> str:
        """HMAC-SHA256 signature in Stripe-style t=...,v1=... format."""
        signed_content = f"{timestamp}.{payload}"
        sig = hmac.new(
            self._signing_secret.encode(),
            signed_content.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"t={timestamp},v1={sig}"

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _record_delivery(
        self, config: dict[str, Any], result: DeliveryResult
    ) -> None:
        if self._db is None:
            return
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO notification_delivery_log
                        (config_id, event_type, status_code, error,
                         attempt_number, success, duration_ms)
                    VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
                    """,
                    config["id"],
                    result.event_type,
                    result.status_code,
                    result.error,
                    result.attempt_number,
                    result.success,
                    result.duration_ms,
                )
        except Exception as e:
            logger.error(f"Failed to record notification delivery: {e}")

    async def _reset_failure_count(self, config_id: str) -> None:
        if self._db is None:
            return
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE notification_configs
                    SET consecutive_failures = 0, updated_at = now()
                    WHERE id = $1::uuid
                    """,
                    config_id,
                )
        except Exception as e:
            logger.error(f"Failed to reset failure count: {e}")

    async def _increment_failure_count(self, config_id: str) -> None:
        """Increment consecutive failures. Mark unhealthy (is_active=false) after 3."""
        if self._db is None:
            return
        try:
            pool = await self._db.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE notification_configs
                    SET consecutive_failures = consecutive_failures + 1,
                        last_failure_at = now(),
                        is_active = CASE
                            WHEN consecutive_failures + 1 >= 3 THEN false
                            ELSE is_active
                        END,
                        updated_at = now()
                    WHERE id = $1::uuid
                    """,
                    config_id,
                )
        except Exception as e:
            logger.error(f"Failed to increment failure count: {e}")

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
