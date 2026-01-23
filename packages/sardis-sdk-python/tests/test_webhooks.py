"""Tests for WebhooksResource."""
import pytest


MOCK_WEBHOOK = {
    "id": "webhook_123",
    "organization_id": "org_456",
    "url": "https://example.com/webhook",
    "events": ["payment.completed", "payment.failed"],
    "is_active": True,
    "total_deliveries": 0,
    "successful_deliveries": 0,
    "failed_deliveries": 0,
    "created_at": "2025-01-20T00:00:00Z",
    "updated_at": "2025-01-20T00:00:00Z",
}

MOCK_DELIVERY = {
    "id": "delivery_456",
    "subscription_id": "webhook_123",
    "event_id": "evt_789",
    "event_type": "payment.completed",
    "url": "https://example.com/webhook",
    "status_code": 200,
    "success": True,
    "duration_ms": 150,
    "attempt_number": 1,
    "created_at": "2025-01-20T00:00:00Z",
}


class TestListEventTypes:
    """Tests for listing event types."""

    async def test_list_event_types(self, client, httpx_mock):
        """Should list all available event types."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/event-types",
            method="GET",
            json={
                "event_types": [
                    "payment.completed",
                    "payment.failed",
                    "hold.created",
                    "hold.captured",
                ],
            },
        )

        event_types = await client.webhooks.list_event_types()
        assert len(event_types) == 4
        assert "payment.completed" in event_types

    async def test_list_empty_event_types(self, client, httpx_mock):
        """Should handle empty event types."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/event-types",
            method="GET",
            json={},
        )

        event_types = await client.webhooks.list_event_types()
        assert len(event_types) == 0


class TestCreateWebhook:
    """Tests for creating webhooks."""

    async def test_create_webhook(self, client, httpx_mock):
        """Should create a webhook subscription."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks",
            method="POST",
            json=MOCK_WEBHOOK,
        )

        webhook = await client.webhooks.create(
            url="https://example.com/webhook",
            events=["payment.completed", "payment.failed"],
        )

        assert webhook.webhook_id == "webhook_123"
        assert webhook.url == "https://example.com/webhook"
        assert len(webhook.events) == 2

    async def test_create_webhook_with_org_id(self, client, httpx_mock):
        """Should create a webhook with organization ID."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks",
            method="POST",
            json=MOCK_WEBHOOK,
        )

        webhook = await client.webhooks.create(
            url="https://example.com/webhook",
            events=["payment.completed"],
            organization_id="org_456",
        )

        assert webhook.webhook_id == "webhook_123"


class TestListWebhooks:
    """Tests for listing webhooks."""

    async def test_list_webhooks(self, client, httpx_mock):
        """Should list all webhooks."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks",
            method="GET",
            json={"webhooks": [MOCK_WEBHOOK]},
        )

        webhooks = await client.webhooks.list()
        assert len(webhooks) == 1
        assert webhooks[0].webhook_id == "webhook_123"

    async def test_list_empty_webhooks(self, client, httpx_mock):
        """Should handle empty webhook list."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks",
            method="GET",
            json={"webhooks": []},
        )

        webhooks = await client.webhooks.list()
        assert len(webhooks) == 0


class TestGetWebhook:
    """Tests for getting a webhook."""

    async def test_get_webhook(self, client, httpx_mock):
        """Should get a webhook by ID."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123",
            method="GET",
            json=MOCK_WEBHOOK,
        )

        webhook = await client.webhooks.get("webhook_123")
        assert webhook.webhook_id == "webhook_123"


class TestUpdateWebhook:
    """Tests for updating webhooks."""

    async def test_update_webhook_url(self, client, httpx_mock):
        """Should update webhook URL."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123",
            method="PATCH",
            json={**MOCK_WEBHOOK, "url": "https://new-url.com/webhook"},
        )

        webhook = await client.webhooks.update(
            "webhook_123",
            url="https://new-url.com/webhook",
        )

        assert webhook.url == "https://new-url.com/webhook"

    async def test_update_webhook_events(self, client, httpx_mock):
        """Should update webhook events."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123",
            method="PATCH",
            json={**MOCK_WEBHOOK, "events": ["hold.created"]},
        )

        webhook = await client.webhooks.update(
            "webhook_123",
            events=["hold.created"],
        )

        assert "hold.created" in webhook.events

    async def test_deactivate_webhook(self, client, httpx_mock):
        """Should deactivate a webhook."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123",
            method="PATCH",
            json={**MOCK_WEBHOOK, "is_active": False},
        )

        webhook = await client.webhooks.update(
            "webhook_123",
            is_active=False,
        )

        assert webhook.is_active is False


class TestDeleteWebhook:
    """Tests for deleting webhooks."""

    async def test_delete_webhook(self, client, httpx_mock):
        """Should delete a webhook."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123",
            method="DELETE",
            status_code=200,
            json={"success": True},
        )

        # Should not raise
        await client.webhooks.delete("webhook_123")


class TestTestWebhook:
    """Tests for testing webhooks."""

    async def test_send_test_event(self, client, httpx_mock):
        """Should send a test event."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123/test",
            method="POST",
            json=MOCK_DELIVERY,
        )

        delivery = await client.webhooks.test("webhook_123")
        assert delivery.success is True
        assert delivery.status_code == 200


class TestListDeliveries:
    """Tests for listing webhook deliveries."""

    async def test_list_deliveries(self, client, httpx_mock):
        """Should list webhook deliveries."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123/deliveries?limit=50",
            method="GET",
            json={"deliveries": [MOCK_DELIVERY]},
        )

        deliveries = await client.webhooks.list_deliveries("webhook_123")
        assert len(deliveries) == 1
        assert deliveries[0].success is True

    async def test_list_deliveries_with_limit(self, client, httpx_mock):
        """Should list deliveries with custom limit."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123/deliveries?limit=10",
            method="GET",
            json={"deliveries": [MOCK_DELIVERY]},
        )

        deliveries = await client.webhooks.list_deliveries("webhook_123", limit=10)
        assert len(deliveries) == 1

    async def test_list_empty_deliveries(self, client, httpx_mock):
        """Should handle empty deliveries list."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123/deliveries?limit=50",
            method="GET",
            json={"deliveries": []},
        )

        deliveries = await client.webhooks.list_deliveries("webhook_123")
        assert len(deliveries) == 0


class TestRotateSecret:
    """Tests for rotating webhook secret."""

    async def test_rotate_secret(self, client, httpx_mock):
        """Should rotate webhook secret."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/webhooks/webhook_123/rotate-secret",
            method="POST",
            json={"secret": "whsec_new_secret"},
        )

        result = await client.webhooks.rotate_secret("webhook_123")
        assert result["secret"] == "whsec_new_secret"
