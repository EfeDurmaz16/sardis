"""Python SDK for AI agents."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_v2_core.identity import AgentIdentity
from sardis_v2_core.mandates import PaymentMandate


class SardisClient:
    def __init__(self, base_url: str, api_key: str, identity: AgentIdentity):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._identity = identity
        self._client = httpx.AsyncClient(base_url=self._base_url, headers={"x-api-key": api_key})

    async def execute_payment(self, mandate: PaymentMandate) -> dict[str, Any]:
        payload = {"mandate": mandate.__dict__}
        resp = await self._client.post("/api/v2/mandates/execute", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def execute_ap2_payment(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """Execute a full AP2 mandate bundle via Sardis."""
        resp = await self._client.post("/api/v2/ap2/payments/execute", json=bundle)
        resp.raise_for_status()
        return resp.json()
