"""Sardis action provider for Coinbase AgentKit.

Wraps the Sardis Python SDK as AgentKit-compatible action providers,
enabling any AgentKit-powered agent to make policy-enforced payments.

Actions:
    - sardis_create_agent: Create a new AI agent with wallet
    - sardis_set_policy: Set spending policy for an agent
    - sardis_check_payment: Run policy check before payment
    - sardis_get_balance: Check wallet balance
    - sardis_list_transactions: List recent transactions
"""
from __future__ import annotations

import os
from typing import Any


class SardisActionProvider:
    """AgentKit action provider for Sardis payments.

    Args:
        api_key: Sardis API key (sk_test_... or sk_live_...)
        api_url: Sardis API base URL
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = "https://api.sardis.sh",
    ):
        self._api_key = api_key or os.getenv("SARDIS_API_KEY", "")
        self._api_url = api_url.rstrip("/")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self._api_url,
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        return self._client

    def get_actions(self) -> list[dict[str, Any]]:
        """Return AgentKit-compatible action definitions."""
        return [
            {
                "name": "sardis_create_agent",
                "description": "Create a new AI agent with a non-custodial wallet on Sardis. Returns agent_id and wallet_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Agent name"},
                        "description": {"type": "string", "description": "What this agent does"},
                    },
                    "required": ["name"],
                },
                "handler": self.create_agent,
            },
            {
                "name": "sardis_set_policy",
                "description": "Set a spending policy for an agent in natural language. Sardis enforces it automatically.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "policy_text": {"type": "string", "description": "Natural language spending rules, e.g. 'Max $100/day, only SaaS tools'"},
                    },
                    "required": ["agent_id", "policy_text"],
                },
                "handler": self.set_policy,
            },
            {
                "name": "sardis_check_payment",
                "description": "Check if a payment would be allowed by the agent's spending policy before executing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string", "default": "USDC"},
                        "merchant": {"type": "string"},
                        "memo": {"type": "string"},
                    },
                    "required": ["agent_id", "amount", "merchant"],
                },
                "handler": self.check_payment,
            },
            {
                "name": "sardis_get_balance",
                "description": "Get the wallet balance for an agent.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wallet_id": {"type": "string"},
                    },
                    "required": ["wallet_id"],
                },
                "handler": self.get_balance,
            },
        ]

    async def create_agent(self, name: str, description: str = "") -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post("/api/v2/agents", json={"name": name, "description": description})
        resp.raise_for_status()
        return resp.json()

    async def set_policy(self, agent_id: str, policy_text: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post("/api/v2/policies", json={"agent_id": agent_id, "policy_text": policy_text})
        resp.raise_for_status()
        return resp.json()

    async def check_payment(self, agent_id: str, amount: float, merchant: str, currency: str = "USDC", memo: str = "") -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post("/api/v2/sandbox/policy-check", json={
            "agent_id": agent_id, "amount": amount, "currency": currency, "merchant": merchant, "memo": memo,
        })
        resp.raise_for_status()
        return resp.json()

    async def get_balance(self, wallet_id: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"/api/v2/wallets/{wallet_id}/balance")
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
