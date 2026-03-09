"""Tests for Google A2A spec-compliant JSON-RPC 2.0 client."""

import pytest
from sardis_a2a.client import A2AClient, A2AClientConfig, A2AClientError
from sardis_a2a.types import (
    Message,
    TaskState,
    TextPart,
)


class MockHttpClient:
    def __init__(self, responses=None):
        self.responses = responses or []
        self._call_idx = 0
        self.post_calls = []
        self.get_calls = []

    async def post(self, url, json=None, headers=None):
        self.post_calls.append({"url": url, "json": json, "headers": headers})
        if self._call_idx < len(self.responses):
            resp = self.responses[self._call_idx]
            self._call_idx += 1
            return resp
        return (200, {"jsonrpc": "2.0", "id": 1, "result": {}})

    async def get(self, url, headers=None):
        self.get_calls.append({"url": url, "headers": headers})
        if self._call_idx < len(self.responses):
            resp = self.responses[self._call_idx]
            self._call_idx += 1
            return resp
        return (200, {})


def _task_resp(task_id="t-1", state="working"):
    return (200, {
        "jsonrpc": "2.0", "id": 1,
        "result": {"id": task_id, "sessionId": "s-1", "status": {"state": state}},
    })


def _card_resp():
    return (200, {
        "name": "Test Agent", "description": "Test", "url": "https://test.com/a2a",
        "version": "1", "capabilities": {}, "authentication": {"schemes": ["Bearer"]},
        "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "echo", "name": "Echo", "description": "Echo", "tags": []}],
    })


class TestA2AClient:
    def _make(self, responses=None):
        http = MockHttpClient(responses or [])
        cfg = A2AClientConfig(agent_id="sardis-1", agent_name="Sardis")
        return A2AClient(cfg, http), http

    @pytest.mark.asyncio
    async def test_discover(self):
        c, h = self._make([_card_resp()])
        card = await c.discover("https://test.com")
        assert card.name == "Test Agent"
        assert h.get_calls[0]["url"] == "https://test.com/.well-known/agent.json"

    @pytest.mark.asyncio
    async def test_discover_caches(self):
        c, h = self._make([_card_resp()])
        await c.discover("https://test.com")
        await c.discover("https://test.com")
        assert len(h.get_calls) == 1

    @pytest.mark.asyncio
    async def test_discover_failure(self):
        c, _ = self._make([(404, {})])
        with pytest.raises(A2AClientError):
            await c.discover("https://bad.com")

    @pytest.mark.asyncio
    async def test_send_task_text(self):
        c, h = self._make([_task_resp()])
        task = await c.send_task("https://test.com/a2a", task_id="t-1", text="Pay 10 USDC")
        assert task.id == "t-1"
        assert task.status.state == TaskState.WORKING
        req = h.post_calls[0]["json"]
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "tasks/send"

    @pytest.mark.asyncio
    async def test_send_task_data(self):
        c, h = self._make([_task_resp()])
        await c.send_task("https://test.com/a2a", data={"amount": "10"})
        parts = h.post_calls[0]["json"]["params"]["message"]["parts"]
        assert any(p["type"] == "data" for p in parts)

    @pytest.mark.asyncio
    async def test_send_task_message(self):
        c, _ = self._make([_task_resp()])
        msg = Message(role="user", parts=[TextPart(text="hi")])
        task = await c.send_task("https://test.com/a2a", message=msg)
        assert task.id == "t-1"

    @pytest.mark.asyncio
    async def test_send_task_no_content(self):
        c, _ = self._make()
        with pytest.raises(A2AClientError):
            await c.send_task("https://test.com/a2a")

    @pytest.mark.asyncio
    async def test_get_task(self):
        c, h = self._make([_task_resp("t-1", "completed")])
        task = await c.get_task("https://test.com/a2a", "t-1")
        assert task.status.state == TaskState.COMPLETED
        assert h.post_calls[0]["json"]["method"] == "tasks/get"

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        c, h = self._make([_task_resp("t-1", "canceled")])
        task = await c.cancel_task("https://test.com/a2a", "t-1")
        assert task.status.state == TaskState.CANCELED
        assert h.post_calls[0]["json"]["method"] == "tasks/cancel"

    @pytest.mark.asyncio
    async def test_send_payment(self):
        c, h = self._make([_task_resp()])
        await c.send_payment("https://test.com/a2a", amount="10", token="USDC", chain="base")
        data_parts = [p for p in h.post_calls[0]["json"]["params"]["message"]["parts"]
                      if p.get("type") == "data"]
        assert data_parts[0]["data"]["type"] == "sardis/payment-request"
        assert data_parts[0]["data"]["amount"] == "10"

    @pytest.mark.asyncio
    async def test_jsonrpc_error(self):
        c, _ = self._make([(200, {
            "jsonrpc": "2.0", "id": 1,
            "error": {"code": -32001, "message": "Task not found"},
        })])
        with pytest.raises(A2AClientError, match="Task not found"):
            await c.get_task("https://test.com/a2a", "missing")

    @pytest.mark.asyncio
    async def test_http_error(self):
        c, _ = self._make([(500, {"error": "Internal"})])
        with pytest.raises(A2AClientError, match="HTTP 500"):
            await c.send_task("https://test.com/a2a", text="hi")

    @pytest.mark.asyncio
    async def test_empty_result(self):
        c, _ = self._make([(200, {"jsonrpc": "2.0", "id": 1})])
        with pytest.raises(A2AClientError, match="Empty result"):
            await c.send_task("https://test.com/a2a", text="hi")
