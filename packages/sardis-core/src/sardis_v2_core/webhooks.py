"""Webhook system with database persistence and delivery tracking."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of webhook events."""

    # Payment events
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"

    # Hold events
    HOLD_CREATED = "hold.created"
    HOLD_CAPTURED = "hold.captured"
    HOLD_VOIDED = "hold.voided"
    HOLD_EXPIRED = "hold.expired"

    # Wallet events
    WALLET_CREATED = "wallet.created"
    WALLET_FUNDED = "wallet.funded"
    WALLET_UPDATED = "wallet.updated"

    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"

    # Mandate events (AP2)
    MANDATE_VERIFIED = "mandate.verified"
    MANDATE_EXECUTED = "mandate.executed"
    MANDATE_REJECTED = "mandate.rejected"

    # Risk events
    RISK_ALERT = "risk.alert"
    LIMIT_EXCEEDED = "limit.exceeded"

    # Policy events
    POLICY_CREATED = "policy.created"
    POLICY_UPDATED = "policy.updated"
    POLICY_VIOLATED = "policy.violated"
    POLICY_CHECK_PASSED = "policy.check.passed"

    # Spending threshold events
    SPEND_THRESHOLD_WARNING = "spend.threshold.warning"  # 80% of limit
    SPEND_THRESHOLD_REACHED = "spend.threshold.reached"  # 100% of limit
    SPEND_DAILY_SUMMARY = "spend.daily.summary"

    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    APPROVAL_EXPIRED = "approval.expired"

    # Card events
    CARD_CREATED = "card.created"
    CARD_ACTIVATED = "card.activated"
    CARD_TRANSACTION = "card.transaction"
    CARD_DECLINED = "card.declined"
    CARD_FROZEN = "card.frozen"

    # Deposit events (inbound payments)
    DEPOSIT_DETECTED = "deposit.detected"
    DEPOSIT_CONFIRMED = "deposit.confirmed"
    PAYMENT_RECEIVED = "payment.received"

    # Compliance events
    COMPLIANCE_CHECK_PASSED = "compliance.check.passed"
    COMPLIANCE_CHECK_FAILED = "compliance.check.failed"
    COMPLIANCE_ALERT = "compliance.alert"

    # Group events
    GROUP_BUDGET_WARNING = "group.budget.warning"
    GROUP_BUDGET_EXCEEDED = "group.budget.exceeded"


@dataclass
class WebhookEvent:
    """A webhook event to be delivered."""
    event_id: str = field(default_factory=lambda: f"evt_{uuid4().hex[:16]}")
    event_type: EventType = EventType.PAYMENT_COMPLETED
    data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    api_version: str = "2024-01"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.event_id,
            "type": self.event_type.value,
            "data": self._serialize(self.data),
            "created_at": self.created_at.isoformat(),
            "api_version": self.api_version,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    def _serialize(self, data: Any) -> Any:
        """Serialize data for JSON."""
        if isinstance(data, dict):
            return {k: self._serialize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize(v) for v in data]
        elif isinstance(data, Decimal):
            return str(data)
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, "value"):  # Enum
            return data.value
        return data


@dataclass
class WebhookSubscription:
    """A webhook subscription."""
    subscription_id: str = field(default_factory=lambda: f"whsub_{uuid4().hex[:16]}")
    organization_id: str = ""
    url: str = ""
    events: List[str] = field(default_factory=list)  # Empty = all events
    secret: str = field(default_factory=lambda: f"whsec_{uuid4().hex}")
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Stats
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    last_delivery_at: Optional[datetime] = None

    def subscribes_to(self, event_type: str) -> bool:
        """Check if subscription wants this event type."""
        if not self.events:
            return True
        return event_type in self.events


@dataclass
class DeliveryAttempt:
    """Record of a webhook delivery attempt."""
    attempt_id: str = field(default_factory=lambda: f"dlv_{uuid4().hex[:16]}")
    subscription_id: str = ""
    event_id: str = ""
    event_type: str = ""
    url: str = ""
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    success: bool = False
    attempt_number: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookRepository:
    """Repository for webhook subscriptions and delivery logs."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pg_pool = None
        self._use_postgres = dsn.startswith("postgresql://") or dsn.startswith("postgres://")
        # In-memory fallback
        self._subscriptions: dict[str, WebhookSubscription] = {}
        self._deliveries: List[DeliveryAttempt] = []

    async def _get_pool(self):
        """Lazy initialization of PostgreSQL pool."""
        if self._pg_pool is None and self._use_postgres:
            from sardis_v2_core.database import Database
            self._pg_pool = await Database.get_pool()
        return self._pg_pool

    async def create_subscription(
        self,
        organization_id: str,
        url: str,
        events: Optional[List[str]] = None,
    ) -> WebhookSubscription:
        """Create a new webhook subscription."""
        sub = WebhookSubscription(
            organization_id=organization_id,
            url=url,
            events=events or [],
        )

        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO webhook_subscriptions (
                        external_id, organization_id, url, events, secret, is_active, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """,
                    sub.subscription_id,
                    organization_id,
                    url,
                    events or [],
                    sub.secret,
                    True,
                )
        else:
            self._subscriptions[sub.subscription_id] = sub

        return sub

    async def get_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get a subscription by ID."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT external_id, organization_id, url, events, secret, is_active,
                           created_at, total_deliveries, successful_deliveries, 
                           failed_deliveries, last_delivery_at
                    FROM webhook_subscriptions WHERE external_id = $1
                    """,
                    subscription_id,
                )
                if not row:
                    return None
                return self._row_to_subscription(row)
        else:
            return self._subscriptions.get(subscription_id)

    async def list_subscriptions(
        self,
        organization_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[WebhookSubscription]:
        """List subscriptions."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                if organization_id:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, organization_id, url, events, secret, is_active,
                               created_at, total_deliveries, successful_deliveries,
                               failed_deliveries, last_delivery_at
                        FROM webhook_subscriptions
                        WHERE organization_id = $1 AND ($2 = FALSE OR is_active = TRUE)
                        ORDER BY created_at DESC
                        """,
                        organization_id,
                        active_only,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, organization_id, url, events, secret, is_active,
                               created_at, total_deliveries, successful_deliveries,
                               failed_deliveries, last_delivery_at
                        FROM webhook_subscriptions
                        WHERE $1 = FALSE OR is_active = TRUE
                        ORDER BY created_at DESC
                        """,
                        active_only,
                    )
                return [self._row_to_subscription(row) for row in rows]
        else:
            subs = list(self._subscriptions.values())
            if organization_id:
                subs = [s for s in subs if s.organization_id == organization_id]
            if active_only:
                subs = [s for s in subs if s.is_active]
            return subs

    async def update_subscription(
        self,
        subscription_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        secret: Optional[str] = None,
    ) -> Optional[WebhookSubscription]:
        """Update a subscription."""
        sub = await self.get_subscription(subscription_id)
        if not sub:
            return None

        if url is not None:
            sub.url = url
        if events is not None:
            sub.events = events
        if is_active is not None:
            sub.is_active = is_active
        if secret is not None:
            sub.secret = secret

        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE webhook_subscriptions SET
                        url = $2, events = $3, is_active = $4, secret = $5
                    WHERE external_id = $1
                    """,
                    subscription_id,
                    sub.url,
                    sub.events,
                    sub.is_active,
                    sub.secret,
                )
        else:
            self._subscriptions[subscription_id] = sub

        return sub

    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM webhook_subscriptions WHERE external_id = $1",
                    subscription_id,
                )
                return "DELETE 1" in result
        else:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                return True
            return False

    async def record_delivery(self, attempt: DeliveryAttempt) -> None:
        """Record a delivery attempt."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO webhook_deliveries (
                        external_id, subscription_id, event_id, event_type, url,
                        status_code, response_body, error, duration_ms, success,
                        attempt_number, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
                    """,
                    attempt.attempt_id,
                    attempt.subscription_id,
                    attempt.event_id,
                    attempt.event_type,
                    attempt.url,
                    attempt.status_code,
                    attempt.response_body[:1000] if attempt.response_body else None,
                    attempt.error,
                    attempt.duration_ms,
                    attempt.success,
                    attempt.attempt_number,
                )
                # Update subscription stats
                if attempt.success:
                    await conn.execute(
                        """
                        UPDATE webhook_subscriptions SET
                            total_deliveries = total_deliveries + 1,
                            successful_deliveries = successful_deliveries + 1,
                            last_delivery_at = NOW()
                        WHERE external_id = $1
                        """,
                        attempt.subscription_id,
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE webhook_subscriptions SET
                            total_deliveries = total_deliveries + 1,
                            failed_deliveries = failed_deliveries + 1,
                            last_delivery_at = NOW()
                        WHERE external_id = $1
                        """,
                        attempt.subscription_id,
                    )
        else:
            self._deliveries.append(attempt)
            sub = self._subscriptions.get(attempt.subscription_id)
            if sub:
                sub.total_deliveries += 1
                if attempt.success:
                    sub.successful_deliveries += 1
                else:
                    sub.failed_deliveries += 1
                sub.last_delivery_at = datetime.now(timezone.utc)

    async def list_deliveries(
        self,
        subscription_id: Optional[str] = None,
        event_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DeliveryAttempt]:
        """List delivery attempts."""
        if self._use_postgres:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                if subscription_id:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, subscription_id, event_id, event_type, url,
                               status_code, response_body, error, duration_ms, success,
                               attempt_number, created_at
                        FROM webhook_deliveries
                        WHERE subscription_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                        """,
                        subscription_id,
                        limit,
                    )
                elif event_id:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, subscription_id, event_id, event_type, url,
                               status_code, response_body, error, duration_ms, success,
                               attempt_number, created_at
                        FROM webhook_deliveries
                        WHERE event_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                        """,
                        event_id,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT external_id, subscription_id, event_id, event_type, url,
                               status_code, response_body, error, duration_ms, success,
                               attempt_number, created_at
                        FROM webhook_deliveries
                        ORDER BY created_at DESC
                        LIMIT $1
                        """,
                        limit,
                    )
                return [self._row_to_delivery(row) for row in rows]
        else:
            deliveries = self._deliveries
            if subscription_id:
                deliveries = [d for d in deliveries if d.subscription_id == subscription_id]
            if event_id:
                deliveries = [d for d in deliveries if d.event_id == event_id]
            return sorted(deliveries, key=lambda d: d.created_at, reverse=True)[:limit]

    def _row_to_subscription(self, row) -> WebhookSubscription:
        """Convert database row to WebhookSubscription."""
        return WebhookSubscription(
            subscription_id=row["external_id"],
            organization_id=row["organization_id"],
            url=row["url"],
            events=row["events"] or [],
            secret=row["secret"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            total_deliveries=row["total_deliveries"] or 0,
            successful_deliveries=row["successful_deliveries"] or 0,
            failed_deliveries=row["failed_deliveries"] or 0,
            last_delivery_at=row["last_delivery_at"],
        )

    def _row_to_delivery(self, row) -> DeliveryAttempt:
        """Convert database row to DeliveryAttempt."""
        return DeliveryAttempt(
            attempt_id=row["external_id"],
            subscription_id=row["subscription_id"],
            event_id=row["event_id"],
            event_type=row["event_type"],
            url=row["url"],
            status_code=row["status_code"],
            response_body=row["response_body"],
            error=row["error"],
            duration_ms=row["duration_ms"] or 0,
            success=row["success"],
            attempt_number=row["attempt_number"] or 1,
            created_at=row["created_at"],
        )


class WebhookService:
    """Service for webhook delivery with retries."""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 5, 30]  # seconds
    DELIVERY_TIMEOUT = 10  # seconds

    def __init__(self, repository: WebhookRepository):
        self._repo = repository
        self._http_client = None

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=self.DELIVERY_TIMEOUT)
        return self._http_client

    async def emit(self, event: WebhookEvent) -> None:
        """Emit an event to all matching subscriptions (async, non-blocking)."""
        subscriptions = await self._repo.list_subscriptions(active_only=True)
        matching = [s for s in subscriptions if s.subscribes_to(event.event_type.value)]

        for sub in matching:
            # Fire and forget
            asyncio.create_task(self._deliver_with_retries(event, sub))

        logger.debug(f"Emitted {event.event_type.value} to {len(matching)} subscriptions")

    async def emit_and_wait(self, event: WebhookEvent) -> dict[str, DeliveryAttempt]:
        """Emit and wait for all deliveries to complete."""
        subscriptions = await self._repo.list_subscriptions(active_only=True)
        matching = [s for s in subscriptions if s.subscribes_to(event.event_type.value)]

        results = {}
        for sub in matching:
            result = await self._deliver_with_retries(event, sub)
            results[sub.subscription_id] = result

        return results

    async def _deliver_with_retries(
        self,
        event: WebhookEvent,
        subscription: WebhookSubscription,
    ) -> DeliveryAttempt:
        """Deliver with exponential backoff retries."""
        import time

        payload = event.to_json()
        timestamp = int(event.created_at.timestamp())
        signature = self._sign_payload(payload, subscription.secret, timestamp)

        headers = {
            "Content-Type": "application/json",
            "X-Sardis-Signature": signature,
            "X-Sardis-Event-Type": event.event_type.value,
            "X-Sardis-Event-ID": event.event_id,
            "X-Sardis-Timestamp": str(timestamp),
        }

        client = await self._get_client()
        last_attempt = None

        for attempt_num in range(1, self.MAX_RETRIES + 1):
            start_time = time.time()

            try:
                response = await client.post(
                    subscription.url,
                    content=payload,
                    headers=headers,
                )

                duration_ms = int((time.time() - start_time) * 1000)
                success = response.status_code < 300

                last_attempt = DeliveryAttempt(
                    subscription_id=subscription.subscription_id,
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    url=subscription.url,
                    status_code=response.status_code,
                    response_body=response.text[:500] if response.text else None,
                    duration_ms=duration_ms,
                    success=success,
                    attempt_number=attempt_num,
                )

                if success:
                    await self._repo.record_delivery(last_attempt)
                    return last_attempt

                logger.warning(
                    f"Webhook {subscription.subscription_id} returned {response.status_code}"
                )

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Webhook delivery failed: {e}")

                last_attempt = DeliveryAttempt(
                    subscription_id=subscription.subscription_id,
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    url=subscription.url,
                    error=str(e),
                    duration_ms=duration_ms,
                    success=False,
                    attempt_number=attempt_num,
                )

            # Retry with backoff
            if attempt_num < self.MAX_RETRIES:
                await asyncio.sleep(self.RETRY_DELAYS[attempt_num - 1])

        # Record final failed attempt
        if last_attempt:
            await self._repo.record_delivery(last_attempt)

        return last_attempt or DeliveryAttempt(
            subscription_id=subscription.subscription_id,
            event_id=event.event_id,
            event_type=event.event_type.value,
            url=subscription.url,
            error="Max retries exceeded",
            success=False,
        )

    def _sign_payload(self, payload: str, secret: str, timestamp: int) -> str:
        """Create HMAC-SHA256 signature for payload with timestamp.

        SECURITY: The timestamp is included in the signed content so that
        an attacker who intercepts a delivery cannot replay it at a later
        time. Follows the Stripe webhook signature pattern:
            t=<unix_timestamp>,v1=<hex_hmac>

        The receiver MUST:
        1. Split the header on ","
        2. Extract t= (timestamp) and v1= (signature)
        3. Reject if |now - t| > tolerance (e.g., 5 minutes)
        4. Compute HMAC-SHA256(secret, f"{t}.{payload}") and compare to v1
        """
        # Signed content = "<timestamp>.<payload>" (Stripe convention)
        signed_content = f"{timestamp}.{payload}"
        sig = hmac.new(
            secret.encode(),
            signed_content.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"t={timestamp},v1={sig}"

    def verify_signature(
        self,
        payload: str,
        signature: str,
        secret: str,
        tolerance_seconds: int = 300,
    ) -> bool:
        """Verify a webhook signature with replay protection.

        Args:
            payload: The raw JSON payload body
            signature: The X-Sardis-Signature header value (t=...,v1=...)
            secret: The webhook subscription secret
            tolerance_seconds: Maximum age of the signature (default 5 minutes)

        Returns:
            True if signature is valid and not expired
        """
        import time as _time

        # Parse "t=<timestamp>,v1=<signature>"
        parts = {}
        for part in signature.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                parts[k.strip()] = v.strip()

        ts_str = parts.get("t")
        sig_hex = parts.get("v1")

        if not ts_str or not sig_hex:
            # Legacy format: "sha256=<hex>" (no timestamp — reject in strict mode)
            return False

        try:
            ts = int(ts_str)
        except ValueError:
            return False

        # SECURITY: Reject stale signatures to prevent replay attacks
        now = int(_time.time())
        if abs(now - ts) > tolerance_seconds:
            return False

        # Recompute expected signature
        signed_content = f"{ts}.{payload}"
        expected_sig = hmac.new(
            secret.encode(),
            signed_content.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, sig_hex)

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Event factory functions
def create_payment_event(
    event_type: EventType,
    tx_id: str,
    from_wallet: str,
    to_wallet: str,
    amount: Decimal,
    fee: Decimal,
    currency: str,
    status: str,
    error: Optional[str] = None,
) -> WebhookEvent:
    """Create a payment event."""
    data = {
        "transaction": {
            "id": tx_id,
            "from_wallet": from_wallet,
            "to_wallet": to_wallet,
            "amount": amount,
            "fee": fee,
            "total": amount + fee,
            "currency": currency,
            "status": status,
        }
    }
    if error:
        data["transaction"]["error"] = error
    return WebhookEvent(event_type=event_type, data=data)


def create_deposit_event(
    event_type: EventType,
    deposit_id: str,
    wallet_id: str,
    agent_id: str,
    tx_hash: str,
    chain: str,
    token: str,
    amount: Decimal,
    from_address: str,
    to_address: str,
    status: str,
    confirmations: int = 0,
    payment_request_id: Optional[str] = None,
    ledger_entry_id: Optional[str] = None,
) -> WebhookEvent:
    """Create a deposit/inbound payment event."""
    data: dict = {
        "deposit": {
            "id": deposit_id,
            "wallet_id": wallet_id,
            "agent_id": agent_id,
            "tx_hash": tx_hash,
            "chain": chain,
            "token": token,
            "amount": amount,
            "from_address": from_address,
            "to_address": to_address,
            "status": status,
            "confirmations": confirmations,
        }
    }
    if payment_request_id:
        data["deposit"]["payment_request_id"] = payment_request_id
    if ledger_entry_id:
        data["deposit"]["ledger_entry_id"] = ledger_entry_id
    return WebhookEvent(event_type=event_type, data=data)


def create_hold_event(
    event_type: EventType,
    hold_id: str,
    wallet_id: str,
    amount: Decimal,
    token: str,
    status: str,
    merchant_id: Optional[str] = None,
) -> WebhookEvent:
    """Create a hold event."""
    return WebhookEvent(
        event_type=event_type,
        data={
            "hold": {
                "id": hold_id,
                "wallet_id": wallet_id,
                "merchant_id": merchant_id,
                "amount": amount,
                "token": token,
                "status": status,
            }
        },
    )
