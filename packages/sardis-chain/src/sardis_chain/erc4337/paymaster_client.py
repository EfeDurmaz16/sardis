"""Minimal ERC-4337 paymaster client (Pimlico-compatible)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .user_operation import UserOperation


@dataclass
class PaymasterConfig:
    url: str
    timeout_seconds: float = 30.0


@dataclass
class SponsoredUserOperation:
    paymaster_and_data: str


class PaymasterClient:
    def __init__(self, config: PaymasterConfig):
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = await self._client.post(self._config.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"Paymaster RPC error ({method}): {data['error']}")
        return data.get("result")

    async def sponsor_user_operation(self, user_op: UserOperation, entrypoint: str, chain: str) -> SponsoredUserOperation:
        result = await self._rpc(
            "pm_sponsorUserOperation",
            [
                user_op.to_rpc(),
                entrypoint,
                {
                    "sponsorshipPolicyId": f"sardis-{chain}",
                },
            ],
        )
        if not isinstance(result, dict) or not isinstance(result.get("paymasterAndData"), str):
            raise RuntimeError("Paymaster returned invalid sponsorship payload")
        return SponsoredUserOperation(paymaster_and_data=result["paymasterAndData"])

    async def close(self) -> None:
        await self._client.aclose()
