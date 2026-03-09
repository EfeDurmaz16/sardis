"""Tests for A2A JSON-RPC 2.0 server."""

import uuid
from collections.abc import AsyncGenerator

import pytest
from sardis_a2a.server import (
    A2AServer,
    TaskNotCancelableError,
    TaskNotFoundError,
)
from sardis_a2a.types import (
    Artifact,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskCancelParams,
    TaskGetParams,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)


class MockTaskHandler:
    """Simple in-memory task handler for testing."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}

    async def on_task_send(self, params: TaskSendParams) -> Task:
        session_id = params.session_id or str(uuid.uuid4())
        task = Task(
            id=params.id,
            session_id=session_id,
            status=TaskStatus(
                state=TaskState.WORKING,
                message=Message(role="agent", parts=[TextPart(text="Processing...")]),
            ),
            history=[params.message],
        )
        self.tasks[params.id] = task
        return task

    async def on_task_get(self, params: TaskGetParams) -> Task:
        if params.id not in self.tasks:
            raise TaskNotFoundError(f"Task {params.id} not found")
        task = self.tasks[params.id]
        if params.history_length is not None:
            task.history = task.history[-params.history_length:]
        return task

    async def on_task_cancel(self, params: TaskCancelParams) -> Task:
        if params.id not in self.tasks:
            raise TaskNotFoundError(f"Task {params.id} not found")
        task = self.tasks[params.id]
        if task.status.state in (TaskState.COMPLETED, TaskState.CANCELED):
            raise TaskNotCancelableError(f"Task {params.id} is {task.status.state.value}")
        task.status = TaskStatus(state=TaskState.CANCELED)
        return task

    async def on_task_send_subscribe(
        self, params: TaskSendParams
    ) -> AsyncGenerator[TaskStatusUpdateEvent | TaskArtifactUpdateEvent, None]:
        yield TaskStatusUpdateEvent(
            id=params.id,
            status=TaskStatus(state=TaskState.WORKING),
            final=False,
        )
        yield TaskArtifactUpdateEvent(
            id=params.id,
            artifact=Artifact(parts=[TextPart(text="Result")]),
        )
        yield TaskStatusUpdateEvent(
            id=params.id,
            status=TaskStatus(state=TaskState.COMPLETED),
            final=True,
        )


@pytest.fixture
def server():
    handler = MockTaskHandler()
    return A2AServer(handler=handler)


class TestTasksSend:
    @pytest.mark.asyncio
    async def test_basic_send(self, server):
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tasks/send",
            "params": {
                "id": "task-1",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Pay 10 USDC"}],
                },
            },
        }
        resp = await server.handle(body)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["result"]["id"] == "task-1"
        assert resp["result"]["status"]["state"] == "working"

    @pytest.mark.asyncio
    async def test_send_with_session(self, server):
        body = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tasks/send",
            "params": {
                "id": "task-2",
                "sessionId": "session-abc",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "hello"}],
                },
            },
        }
        resp = await server.handle(body)
        assert resp["result"]["sessionId"] == "session-abc"

    @pytest.mark.asyncio
    async def test_send_with_data_part(self, server):
        body = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tasks/send",
            "params": {
                "id": "task-3",
                "message": {
                    "role": "user",
                    "parts": [
                        {"type": "text", "text": "Pay"},
                        {"type": "data", "data": {"amount": "10", "token": "USDC"}},
                    ],
                },
            },
        }
        resp = await server.handle(body)
        assert resp["result"]["id"] == "task-3"


class TestTasksGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, server):
        # Create task first
        await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
            "params": {"id": "t-1", "message": {"role": "user", "parts": [{"type": "text", "text": "x"}]}},
        })

        resp = await server.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tasks/get",
            "params": {"id": "t-1"},
        })
        assert resp["result"]["id"] == "t-1"

    @pytest.mark.asyncio
    async def test_get_not_found(self, server):
        resp = await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tasks/get",
            "params": {"id": "nonexistent"},
        })
        assert resp["error"]["code"] == -32001
        assert "not found" in resp["error"]["message"]


class TestTasksCancel:
    @pytest.mark.asyncio
    async def test_cancel(self, server):
        await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
            "params": {"id": "t-1", "message": {"role": "user", "parts": [{"type": "text", "text": "x"}]}},
        })

        resp = await server.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tasks/cancel",
            "params": {"id": "t-1"},
        })
        assert resp["result"]["status"]["state"] == "canceled"

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, server):
        resp = await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tasks/cancel",
            "params": {"id": "nonexistent"},
        })
        assert resp["error"]["code"] == -32001


class TestPushNotifications:
    @pytest.mark.asyncio
    async def test_set_and_get(self, server):
        set_resp = await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tasks/pushNotification/set",
            "params": {
                "id": "t-1",
                "pushNotificationConfig": {
                    "url": "https://callback.example.com",
                    "authentication": {"schemes": ["jwt"]},
                },
            },
        })
        assert set_resp["result"]["pushNotificationConfig"]["url"] == "https://callback.example.com"

        get_resp = await server.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tasks/pushNotification/get",
            "params": {"id": "t-1"},
        })
        assert get_resp["result"]["pushNotificationConfig"]["url"] == "https://callback.example.com"


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_method_not_found(self, server):
        resp = await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "invalid/method",
            "params": {},
        })
        assert resp["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_invalid_request(self, server):
        resp = await server.handle({"not_valid": True})
        assert resp["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_sse_method_returns_error(self, server):
        resp = await server.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tasks/sendSubscribe",
            "params": {"id": "t-1", "message": {"role": "user", "parts": []}},
        })
        assert resp["error"]["code"] == -32004


class TestSSE:
    @pytest.mark.asyncio
    async def test_sse_stream(self, server):
        body = {
            "jsonrpc": "2.0", "id": 1, "method": "tasks/sendSubscribe",
            "params": {
                "id": "t-1",
                "message": {"role": "user", "parts": [{"type": "text", "text": "go"}]},
            },
        }

        events = []
        async for event_str in server.handle_sse(body):
            events.append(event_str)

        assert len(events) == 3  # working, artifact, completed
        assert '"working"' in events[0]
        assert '"Result"' in events[1]
        assert '"completed"' in events[2]
