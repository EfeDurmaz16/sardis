"""Google A2A spec-compliant JSON-RPC 2.0 client.

Provides methods for interacting with remote A2A agents:
  - tasks/send — Create or continue tasks
  - tasks/get — Poll task status
  - tasks/cancel — Cancel running tasks
  - tasks/sendSubscribe — Stream task updates via SSE
  - Agent card discovery via /.well-known/agent.json

Spec: https://google.github.io/A2A/
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Protocol

from .types import (
    AgentCard,
    DataPart,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Task,
    TaskCancelParams,
    TaskGetParams,
    TaskSendParams,
    TaskState,
    TextPart,
)

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Error during A2A client operations."""

    def __init__(
        self,
        message: str,
        code: int | str = -1,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class HttpClient(Protocol):
    """Protocol for HTTP client operations."""

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """POST JSON and return (status_code, json_response)."""
        ...

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """GET and return (status_code, json_response)."""
        ...


@dataclass
class A2AClientConfig:
    """Configuration for A2A client."""
    agent_id: str
    agent_name: str
    request_timeout: int = 30
    max_retries: int = 3


class A2AClient:
    """Google A2A spec-compliant JSON-RPC 2.0 client.

    Usage:
        client = A2AClient(config, http_client)

        # Discover agent
        card = await client.discover("https://agent.example.com")

        # Send a task
        task = await client.send_task(
            agent_url="https://agent.example.com/a2a",
            task_id="task-123",
            message=Message(role="user", parts=[TextPart(text="Pay 10 USDC")])
        )

        # Poll for completion
        task = await client.get_task(agent_url, "task-123")
    """

    def __init__(
        self,
        config: A2AClientConfig,
        http_client: HttpClient,
    ) -> None:
        self._config = config
        self._http = http_client
        self._request_counter = 0
        self._card_cache: dict[str, AgentCard] = {}

    @property
    def agent_id(self) -> str:
        return self._config.agent_id

    # ============ Agent Discovery ============

    async def discover(self, base_url: str, force_refresh: bool = False) -> AgentCard:
        """Fetch the agent card from /.well-known/agent.json"""
        if not force_refresh and base_url in self._card_cache:
            return self._card_cache[base_url]

        url = f"{base_url.rstrip('/')}/.well-known/agent.json"
        status, data = await self._http.get(url)

        if status != 200:
            raise A2AClientError(
                f"Failed to discover agent at {url}: HTTP {status}",
                code="discovery_failed",
            )

        card = AgentCard.from_dict(data)
        self._card_cache[base_url] = card
        return card

    # ============ Task Operations ============

    async def send_task(
        self,
        agent_url: str,
        task_id: str | None = None,
        session_id: str | None = None,
        message: Message | None = None,
        text: str | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Send a task (tasks/send).

        Convenience: pass either `message`, `text`, or `data` to construct the message.
        """
        if message is None:
            parts = []
            if text:
                parts.append(TextPart(text=text))
            if data:
                parts.append(DataPart(data=data))
            if not parts:
                raise A2AClientError("Must provide message, text, or data", code="invalid_params")
            message = Message(role="user", parts=parts)

        params = TaskSendParams(
            id=task_id or str(uuid.uuid4()),
            session_id=session_id,
            message=message,
            metadata=metadata or {},
        )

        response = await self._rpc(agent_url, "tasks/send", params.to_dict())
        return Task.from_dict(response)

    async def get_task(
        self,
        agent_url: str,
        task_id: str,
        history_length: int | None = None,
    ) -> Task:
        """Get task status (tasks/get)."""
        params = TaskGetParams(
            id=task_id,
            history_length=history_length,
        )
        response = await self._rpc(agent_url, "tasks/get", params.to_dict())
        return Task.from_dict(response)

    async def cancel_task(
        self,
        agent_url: str,
        task_id: str,
    ) -> Task:
        """Cancel a task (tasks/cancel)."""
        params = TaskCancelParams(id=task_id)
        response = await self._rpc(agent_url, "tasks/cancel", params.to_dict())
        return Task.from_dict(response)

    # ============ Payment Convenience Methods ============

    async def send_payment(
        self,
        agent_url: str,
        amount: str,
        token: str = "USDC",
        chain: str = "base",
        destination: str = "",
        memo: str = "",
        reference: str | None = None,
    ) -> Task:
        """Send a payment task to a remote agent.

        This wraps tasks/send with a DataPart containing payment details.
        The remote agent's payment skill handles the actual execution.
        """
        return await self.send_task(
            agent_url=agent_url,
            text=f"Pay {amount} {token} on {chain}" + (f": {memo}" if memo else ""),
            data={
                "type": "sardis/payment-request",
                "amount": amount,
                "token": token,
                "chain": chain,
                "destination": destination,
                "memo": memo,
                "reference": reference or str(uuid.uuid4()),
            },
        )

    async def check_balance(
        self,
        agent_url: str,
        token: str = "USDC",
        chain: str = "base",
    ) -> Task:
        """Query an agent's balance via the balance-check skill."""
        return await self.send_task(
            agent_url=agent_url,
            text=f"Check {token} balance on {chain}",
            data={
                "type": "sardis/balance-query",
                "token": token,
                "chain": chain,
            },
        )

    # ============ Internal ============

    async def _rpc(
        self,
        agent_url: str,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request and return the result."""
        self._request_counter += 1
        request = JsonRpcRequest(
            method=method,
            params=params,
            id=self._request_counter,
        )

        logger.info(f"A2A RPC: {method} → {agent_url}")

        status, data = await self._http.post(
            agent_url,
            json=request.to_dict(),
            headers={"Content-Type": "application/json"},
        )

        if status >= 400:
            raise A2AClientError(
                f"HTTP {status} from {agent_url}",
                code=f"http_{status}",
                details={"response": data},
            )

        # Parse JSON-RPC response
        if "error" in data and data["error"]:
            err = data["error"]
            raise A2AClientError(
                message=err.get("message", "Unknown error"),
                code=err.get("code", -1),
                details=err.get("data"),
            )

        result = data.get("result")
        if result is None:
            raise A2AClientError("Empty result in JSON-RPC response", code="empty_result")

        return result


__all__ = [
    "A2AClientError",
    "HttpClient",
    "A2AClientConfig",
    "A2AClient",
]
