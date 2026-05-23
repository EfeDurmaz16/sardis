"""Minimal ERC-4337 bundler client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from .user_operation import UserOperation


@dataclass
class BundlerConfig:
    url: str
    timeout_seconds: float = 30.0


class BundlerClient:
    def __init__(self, config: BundlerConfig):
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = await self._client.post(self._config.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"Bundler RPC error ({method}): {data['error']}")
        return data.get("result")

    async def get_user_operation_nonce(self, sender: str, entrypoint: str) -> int:
        nonce_hex = await self._rpc("eth_getUserOperationCount", [sender, entrypoint])
        if not nonce_hex:
            return 0
        return int(nonce_hex, 16)

    async def estimate_user_operation_gas(self, user_op: UserOperation, entrypoint: str) -> dict[str, str]:
        result = await self._rpc("eth_estimateUserOperationGas", [user_op.to_rpc(), entrypoint])
        if not isinstance(result, dict):
            raise RuntimeError("Bundler returned invalid gas estimate payload")
        return result

    async def get_user_operation_hash(self, user_op: UserOperation, entrypoint: str) -> str:
        result = await self._rpc("eth_getUserOperationHash", [user_op.to_rpc(), entrypoint])
        if not isinstance(result, str):
            raise RuntimeError("Bundler returned invalid user op hash")
        return result

    async def send_user_operation(self, user_op: UserOperation, entrypoint: str) -> str:
        result = await self._rpc("eth_sendUserOperation", [user_op.to_rpc(), entrypoint])
        if not isinstance(result, str):
            raise RuntimeError("Bundler returned invalid user op hash")
        return result

    async def get_user_operation_receipt(self, user_op_hash: str) -> dict[str, Any] | None:
        result = await self._rpc("eth_getUserOperationReceipt", [user_op_hash])
        if result is None:
            return None
        if not isinstance(result, dict):
            raise RuntimeError("Bundler returned invalid receipt payload")
        return result

    async def wait_for_receipt(self, user_op_hash: str, timeout_seconds: int = 180, poll_seconds: float = 2.0) -> dict[str, Any]:
        waited = 0.0
        while waited < timeout_seconds:
            receipt = await self.get_user_operation_receipt(user_op_hash)
            if receipt:
                return receipt
            await asyncio.sleep(poll_seconds)
            waited += poll_seconds
        raise TimeoutError(f"UserOperation not included within {timeout_seconds}s: {user_op_hash}")

    async def close(self) -> None:
        await self._client.aclose()
