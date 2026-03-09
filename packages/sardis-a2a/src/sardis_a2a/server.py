"""Google A2A spec-compliant JSON-RPC 2.0 server handler.

Routes incoming JSON-RPC requests to the appropriate handler functions.
Designed to be mounted into any ASGI framework (FastAPI, Starlette, etc.).

Methods:
  - tasks/send          → Create or continue a task
  - tasks/get           → Retrieve task status, history, artifacts
  - tasks/cancel        → Cancel a running task
  - tasks/sendSubscribe → Send with SSE streaming response
  - tasks/pushNotification/set → Configure push notification callback
  - tasks/pushNotification/get → Retrieve push notification config

Spec: https://google.github.io/A2A/
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable
from typing import Any, Protocol

from .types import (
    A2A_TASK_NOT_CANCELABLE,
    A2A_TASK_NOT_FOUND,
    A2A_UNSUPPORTED_OPERATION,
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    PushNotificationConfig,
    Task,
    TaskArtifactUpdateEvent,
    TaskCancelParams,
    TaskGetParams,
    TaskSendParams,
    TaskStatusUpdateEvent,
)


class TaskHandler(Protocol):
    """Protocol for task handler implementations.

    Implement this to wire Sardis business logic into the A2A server.
    """

    async def on_task_send(self, params: TaskSendParams) -> Task:
        """Handle tasks/send — create or continue a task."""
        ...

    async def on_task_get(self, params: TaskGetParams) -> Task:
        """Handle tasks/get — retrieve task details."""
        ...

    async def on_task_cancel(self, params: TaskCancelParams) -> Task:
        """Handle tasks/cancel — cancel a task."""
        ...

    async def on_task_send_subscribe(
        self, params: TaskSendParams
    ) -> AsyncGenerator[TaskStatusUpdateEvent | TaskArtifactUpdateEvent, None]:
        """Handle tasks/sendSubscribe — streaming task updates via SSE."""
        ...  # pragma: no cover
        # Must yield TaskStatusUpdateEvent or TaskArtifactUpdateEvent
        if False:
            yield  # type: ignore[misc]


class A2AServer:
    """JSON-RPC 2.0 server for Google A2A protocol.

    Usage with FastAPI:
        server = A2AServer(handler=MyTaskHandler())

        @app.post("/a2a")
        async def a2a_endpoint(request: Request):
            body = await request.json()
            response = await server.handle(body)
            return JSONResponse(response)

        @app.get("/.well-known/agent.json")
        async def agent_card():
            return server.agent_card.to_dict()
    """

    def __init__(self, handler: TaskHandler) -> None:
        self.handler = handler
        self._push_configs: dict[str, PushNotificationConfig] = {}

    async def handle(self, body: dict[str, Any]) -> dict[str, Any]:
        """Process a JSON-RPC 2.0 request and return the response."""
        try:
            req = JsonRpcRequest.from_dict(body)
        except (KeyError, TypeError):
            return JsonRpcResponse(
                id=body.get("id"),
                error=JsonRpcError(JSONRPC_INVALID_REQUEST, "Invalid JSON-RPC request"),
            ).to_dict()

        method_map: dict[str, Callable] = {
            "tasks/send": self._handle_task_send,
            "tasks/get": self._handle_task_get,
            "tasks/cancel": self._handle_task_cancel,
            "tasks/pushNotification/set": self._handle_push_set,
            "tasks/pushNotification/get": self._handle_push_get,
        }

        handler_fn = method_map.get(req.method)
        if handler_fn is None:
            # tasks/sendSubscribe is handled separately (SSE)
            if req.method == "tasks/sendSubscribe":
                return JsonRpcResponse(
                    id=req.id,
                    error=JsonRpcError(
                        A2A_UNSUPPORTED_OPERATION,
                        "Use the SSE endpoint for tasks/sendSubscribe",
                    ),
                ).to_dict()
            return JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(JSONRPC_METHOD_NOT_FOUND, f"Method not found: {req.method}"),
            ).to_dict()

        try:
            result = await handler_fn(req.params)
            return JsonRpcResponse(id=req.id, result=result).to_dict()
        except TaskNotFoundError as e:
            return JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(A2A_TASK_NOT_FOUND, str(e)),
            ).to_dict()
        except TaskNotCancelableError as e:
            return JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(A2A_TASK_NOT_CANCELABLE, str(e)),
            ).to_dict()
        except InvalidParamsError as e:
            return JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(JSONRPC_INVALID_PARAMS, str(e)),
            ).to_dict()
        except Exception as e:
            return JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(JSONRPC_INTERNAL_ERROR, f"Internal error: {e}"),
            ).to_dict()

    async def handle_sse(
        self, body: dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Handle tasks/sendSubscribe as SSE stream.

        Yields SSE-formatted lines: "data: {...}\n\n"
        """
        try:
            req = JsonRpcRequest.from_dict(body)
            params = TaskSendParams.from_dict(req.params)
        except (KeyError, TypeError) as e:
            error_resp = JsonRpcResponse(
                id=body.get("id"),
                error=JsonRpcError(JSONRPC_INVALID_PARAMS, str(e)),
            )
            yield f"data: {json.dumps(error_resp.to_dict())}\n\n"
            return

        try:
            async for event in self.handler.on_task_send_subscribe(params):
                event_data = event.to_dict()
                yield f"data: {json.dumps(event_data)}\n\n"
        except Exception as e:
            error_resp = JsonRpcResponse(
                id=req.id,
                error=JsonRpcError(JSONRPC_INTERNAL_ERROR, str(e)),
            )
            yield f"data: {json.dumps(error_resp.to_dict())}\n\n"

    # ============ Internal Handlers ============

    async def _handle_task_send(self, params: dict) -> dict:
        send_params = TaskSendParams.from_dict(params)
        task = await self.handler.on_task_send(send_params)
        return task.to_dict()

    async def _handle_task_get(self, params: dict) -> dict:
        get_params = TaskGetParams.from_dict(params)
        task = await self.handler.on_task_get(get_params)
        return task.to_dict()

    async def _handle_task_cancel(self, params: dict) -> dict:
        cancel_params = TaskCancelParams.from_dict(params)
        task = await self.handler.on_task_cancel(cancel_params)
        return task.to_dict()

    async def _handle_push_set(self, params: dict) -> dict:
        task_id = params["id"]
        config = PushNotificationConfig.from_dict(params["pushNotificationConfig"])
        self._push_configs[task_id] = config
        return {
            "id": task_id,
            "pushNotificationConfig": config.to_dict(),
        }

    async def _handle_push_get(self, params: dict) -> dict:
        task_id = params["id"]
        config = self._push_configs.get(task_id)
        result: dict[str, Any] = {"id": task_id}
        if config:
            result["pushNotificationConfig"] = config.to_dict()
        return result


# ============ Errors ============

class TaskNotFoundError(Exception):
    """Raised when a task ID is not found."""
    pass


class TaskNotCancelableError(Exception):
    """Raised when a task cannot be canceled."""
    pass


class InvalidParamsError(Exception):
    """Raised when request params are invalid."""
    pass
