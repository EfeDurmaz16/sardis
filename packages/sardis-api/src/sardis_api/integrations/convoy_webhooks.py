"""Convoy webhook delivery adapter for Sardis.

Replaces hand-rolled webhook delivery with Convoy's enterprise-grade
gateway: circuit breaking, endpoint health, retries, delivery dashboard.

Setup:
    Deploy Convoy: docker run -p 5005:5005 frain-dev/convoy:latest
    Set env vars: CONVOY_API_URL, CONVOY_API_KEY, CONVOY_PROJECT_ID

Usage:
    from sardis_api.integrations.convoy_webhooks import ConvoyWebhookAdapter

    adapter = ConvoyWebhookAdapter()
    await adapter.send_event(
        endpoint_id="ep_123",
        event_type="payment.completed",
        data={"tx_id": "tx_abc", "amount": "50.00"},
    )
"""
from __future__ import annotations

import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)


class ConvoyWebhookAdapter:
    """Adapter for Convoy webhook gateway.

    Falls back to direct HTTP delivery if Convoy is not configured.
    """

    def __init__(self) -> None:
        self._api_url = os.getenv("CONVOY_API_URL", "").rstrip("/")
        self._api_key = os.getenv("CONVOY_API_KEY", "")
        self._project_id = os.getenv("CONVOY_PROJECT_ID", "")
        self._enabled = bool(self._api_url and self._api_key and self._project_id)
        self._client = None

        if self._enabled:
            _logger.info("Convoy webhook adapter enabled: %s", self._api_url)
        else:
            _logger.info("Convoy not configured, using direct webhook delivery")

    async def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=f"{self._api_url}/api/v1/projects/{self._project_id}",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
        return self._client

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def create_endpoint(
        self,
        url: str,
        name: str,
        secret: str | None = None,
        description: str = "",
    ) -> str | None:
        """Register a webhook endpoint in Convoy. Returns endpoint ID."""
        if not self._enabled:
            return None

        client = await self._get_client()
        body: dict[str, Any] = {
            "url": url,
            "name": name,
            "description": description,
        }
        if secret:
            body["secret"] = secret

        try:
            resp = await client.post("/endpoints", json=body)
            resp.raise_for_status()
            data = resp.json()
            endpoint_id = data.get("data", {}).get("uid", "")
            _logger.info("Convoy endpoint created: %s → %s", name, endpoint_id)
            return endpoint_id
        except Exception as e:
            _logger.error("Convoy create_endpoint failed: %s", e)
            return None

    async def send_event(
        self,
        event_type: str,
        data: dict[str, Any],
        endpoint_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> str | None:
        """Send a webhook event via Convoy. Returns event ID."""
        if not self._enabled:
            return None

        client = await self._get_client()
        body: dict[str, Any] = {
            "event_type": event_type,
            "data": data,
        }
        if endpoint_id:
            body["endpoint_id"] = endpoint_id
        if idempotency_key:
            body["idempotency_key"] = idempotency_key

        try:
            resp = await client.post("/events", json=body)
            resp.raise_for_status()
            event_data = resp.json()
            event_id = event_data.get("data", {}).get("uid", "")
            _logger.debug("Convoy event sent: %s %s → %s", event_type, endpoint_id or "broadcast", event_id)
            return event_id
        except Exception as e:
            _logger.error("Convoy send_event failed: %s %s", event_type, e)
            return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
