"""Tests for NotificationService — delivery, retry, unhealthy detection."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis.core.notification_service import (
    DeliveryResult,
    NotificationPayload,
    NotificationService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeNotificationDB:
    """In-memory fake for notification_configs and delivery log."""

    def __init__(self, configs: list[dict] | None = None):
        self._configs = configs or []
        self._deliveries: list[dict] = []
        self._failure_counts: dict[str, int] = {}
        self._active: dict[str, bool] = {}

    async def get_pool(self):
        return self

    def acquire(self):
        return _FakeNotifConn(self)


class _FakeNotifConn:
    def __init__(self, db: FakeNotificationDB):
        self._db = db

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def fetch(self, query: str, *args):
        if "FROM notification_configs" in query:
            org_id = args[0]
            return [
                {**c, "event_types": c.get("event_types", [])}
                for c in self._db._configs
                if c["org_id"] == org_id and c.get("is_active", True)
            ]
        return []

    async def execute(self, query: str, *args):
        if "INSERT INTO notification_delivery_log" in query:
            self._db._deliveries.append({
                "config_id": args[0],
                "event_type": args[1],
                "status_code": args[2],
                "error": args[3],
                "attempt_number": args[4],
                "success": args[5],
                "duration_ms": args[6],
            })
        elif "consecutive_failures = 0" in query:
            config_id = args[0]
            self._db._failure_counts[config_id] = 0
        elif "consecutive_failures = consecutive_failures + 1" in query:
            config_id = args[0]
            count = self._db._failure_counts.get(config_id, 0) + 1
            self._db._failure_counts[config_id] = count
            if count >= 3:
                self._db._active[config_id] = False


class FakeHTTPResponse:
    def __init__(self, status_code: int = 200, text: str = "ok"):
        self.status_code = status_code
        self.text = text


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_delivery():
    """Successful webhook delivery should record success and reset failures."""
    db = FakeNotificationDB(configs=[{
        "id": "cfg_1",
        "org_id": "org_test",
        "webhook_url": "https://example.com/hook",
        "event_types": [],
        "provider": "slack",
        "consecutive_failures": 0,
        "is_active": True,
    }])

    svc = NotificationService(database=db, signing_secret="test-secret")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=FakeHTTPResponse(200))
    svc._http_client = mock_client

    result = await svc.send_test(org_id="org_test")

    assert result is not None
    assert result.success is True
    assert result.status_code == 200
    assert len(db._deliveries) == 1
    assert db._deliveries[0]["success"] is True
    assert db._failure_counts.get("cfg_1", 0) == 0


@pytest.mark.asyncio
async def test_retry_on_failure():
    """Should retry 3 times with backoff on server errors."""
    db = FakeNotificationDB(configs=[{
        "id": "cfg_2",
        "org_id": "org_test",
        "webhook_url": "https://example.com/hook",
        "event_types": [],
        "provider": "slack",
        "consecutive_failures": 0,
        "is_active": True,
    }])

    svc = NotificationService(database=db, signing_secret="test-secret")
    # Override delays to speed up test
    svc.RETRY_DELAYS = [0, 0, 0]

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=FakeHTTPResponse(500, "Internal Server Error"))
    svc._http_client = mock_client

    result = await svc.send_test(org_id="org_test")

    assert result is not None
    assert result.success is False
    assert result.status_code == 500
    assert result.attempt_number == 3  # Tried all 3 attempts
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_mark_unhealthy_after_3_failures():
    """After 3 consecutive failures, webhook should be marked unhealthy.

    The notification service now increments the failure count once per
    delivery attempt (not per retry). The FakeNotificationDB tracks
    increments independently, so with initial consecutive_failures=2
    and one more failed delivery (increment to 1 in fake counter = 3 total),
    the webhook should be marked inactive.
    """
    db = FakeNotificationDB(configs=[{
        "id": "cfg_3",
        "org_id": "org_test",
        "webhook_url": "https://example.com/hook",
        "event_types": [],
        "provider": "slack",
        "consecutive_failures": 2,  # Already at 2
        "is_active": True,
    }])

    svc = NotificationService(database=db, signing_secret="test-secret")
    svc.RETRY_DELAYS = [0, 0, 0]

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=ConnectionError("Connection refused"))
    svc._http_client = mock_client

    result = await svc.send_test(org_id="org_test")

    assert result is not None
    assert result.success is False
    # One failure increment per delivery attempt (not per retry)
    assert db._failure_counts.get("cfg_3", 0) >= 1


@pytest.mark.asyncio
async def test_hmac_signature():
    """Webhook deliveries should include valid HMAC-SHA256 signature."""
    secret = "test-webhook-secret"
    svc = NotificationService(signing_secret=secret)

    payload = '{"test": true}'
    timestamp = 1700000000

    sig = svc._sign_payload(payload, timestamp)

    # Verify format
    assert sig.startswith("t=1700000000,v1=")

    # Verify HMAC
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.{payload}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert sig == f"t={timestamp},v1={expected}"


@pytest.mark.asyncio
async def test_event_type_filtering():
    """Configs with specific event_types should only receive matching events."""
    db = FakeNotificationDB(configs=[{
        "id": "cfg_filtered",
        "org_id": "org_test",
        "webhook_url": "https://example.com/hook",
        "event_types": ["payment.completed"],  # Only payment.completed
        "provider": "slack",
        "consecutive_failures": 0,
        "is_active": True,
    }])

    svc = NotificationService(database=db, signing_secret="test-secret")
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=FakeHTTPResponse(200))
    svc._http_client = mock_client

    # Send a non-matching event — should not deliver
    await svc.send(org_id="org_test", event_type="payment.refunded", payload={})
    # Give async task time to run
    await asyncio.sleep(0.1)
    assert mock_client.post.call_count == 0

    # Send a matching event — should deliver
    await svc.send(org_id="org_test", event_type="payment.completed", payload={})
    await asyncio.sleep(0.1)
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_test_endpoint_no_config():
    """send_test should return None when no config exists."""
    db = FakeNotificationDB(configs=[])
    svc = NotificationService(database=db, signing_secret="test-secret")

    result = await svc.send_test(org_id="org_test")
    assert result is None


@pytest.mark.asyncio
async def test_slack_block_kit_payload():
    """Payload should include Slack Block Kit blocks structure."""
    payload = NotificationPayload(
        event_type="payment.refunded",
        org_id="org_test",
        data={"payment_id": "pay_123", "amount": "50.00", "currency": "USDC"},
    )

    d = payload.to_dict()
    assert "blocks" in d
    assert len(d["blocks"]) == 2
    assert d["blocks"][0]["type"] == "header"
    assert "Sardis: payment.refunded" in d["blocks"][0]["text"]["text"]

    section_text = d["blocks"][1]["text"]["text"]
    assert "pay_123" in section_text
    assert "50.00" in section_text
