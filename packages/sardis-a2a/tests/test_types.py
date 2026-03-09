"""Tests for Google A2A spec-compliant types."""

import pytest

from sardis_a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentProvider,
    AgentSkill,
    Artifact,
    DataPart,
    FilePart,
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcError,
    Message,
    PushNotificationConfig,
    Task,
    TaskCancelParams,
    TaskGetParams,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
    create_sardis_agent_card,
    part_from_dict,
)


class TestParts:
    def test_text_part_roundtrip(self):
        p = TextPart(text="hello")
        d = p.to_dict()
        assert d == {"type": "text", "text": "hello"}
        p2 = part_from_dict(d)
        assert isinstance(p2, TextPart)
        assert p2.text == "hello"

    def test_file_part_roundtrip(self):
        p = FilePart(name="doc.pdf", mime_type="application/pdf", uri="https://x.com/doc.pdf")
        d = p.to_dict()
        assert d["type"] == "file"
        assert d["file"]["name"] == "doc.pdf"
        assert d["file"]["mimeType"] == "application/pdf"
        assert d["file"]["uri"] == "https://x.com/doc.pdf"
        p2 = part_from_dict(d)
        assert isinstance(p2, FilePart)
        assert p2.name == "doc.pdf"

    def test_data_part_roundtrip(self):
        p = DataPart(data={"amount": "10", "token": "USDC"})
        d = p.to_dict()
        assert d["type"] == "data"
        assert d["data"]["amount"] == "10"
        p2 = part_from_dict(d)
        assert isinstance(p2, DataPart)
        assert p2.data["token"] == "USDC"

    def test_part_with_metadata(self):
        p = TextPart(text="hi", metadata={"source": "test"})
        d = p.to_dict()
        assert d["metadata"] == {"source": "test"}


class TestMessage:
    def test_roundtrip(self):
        msg = Message(
            role="user",
            parts=[TextPart(text="Pay 10 USDC")],
            metadata={"intent": "payment"},
        )
        d = msg.to_dict()
        assert d["role"] == "user"
        assert len(d["parts"]) == 1
        assert d["parts"][0]["text"] == "Pay 10 USDC"

        msg2 = Message.from_dict(d)
        assert msg2.role == "user"
        assert isinstance(msg2.parts[0], TextPart)

    def test_agent_message(self):
        msg = Message(role="agent", parts=[TextPart(text="Payment completed")])
        assert msg.role == "agent"


class TestArtifact:
    def test_roundtrip(self):
        a = Artifact(
            parts=[DataPart(data={"tx_hash": "0x123"})],
            name="payment_receipt",
        )
        d = a.to_dict()
        assert d["name"] == "payment_receipt"
        a2 = Artifact.from_dict(d)
        assert a2.name == "payment_receipt"
        assert isinstance(a2.parts[0], DataPart)


class TestTaskStatus:
    def test_roundtrip(self):
        ts = TaskStatus(
            state=TaskState.WORKING,
            message=Message(role="agent", parts=[TextPart(text="Processing...")]),
            timestamp="2026-03-09T12:00:00Z",
        )
        d = ts.to_dict()
        assert d["state"] == "working"
        ts2 = TaskStatus.from_dict(d)
        assert ts2.state == TaskState.WORKING
        assert ts2.message.parts[0].text == "Processing..."

    def test_all_states(self):
        for state in TaskState:
            ts = TaskStatus(state=state)
            d = ts.to_dict()
            ts2 = TaskStatus.from_dict(d)
            assert ts2.state == state


class TestTask:
    def test_roundtrip(self):
        task = Task(
            id="task-123",
            session_id="sess-456",
            status=TaskStatus(state=TaskState.COMPLETED),
            artifacts=[Artifact(parts=[TextPart(text="Done")])],
            history=[Message(role="user", parts=[TextPart(text="Do it")])],
        )
        d = task.to_dict()
        assert d["id"] == "task-123"
        assert d["sessionId"] == "sess-456"
        assert d["status"]["state"] == "completed"
        assert len(d["artifacts"]) == 1
        assert len(d["history"]) == 1

        task2 = Task.from_dict(d)
        assert task2.id == "task-123"
        assert task2.status.state == TaskState.COMPLETED


class TestTaskParams:
    def test_send_params_roundtrip(self):
        params = TaskSendParams(
            id="t-1",
            message=Message(role="user", parts=[TextPart(text="hello")]),
            session_id="s-1",
            history_length=10,
        )
        d = params.to_dict()
        assert d["id"] == "t-1"
        assert d["sessionId"] == "s-1"
        assert d["historyLength"] == 10
        p2 = TaskSendParams.from_dict(d)
        assert p2.id == "t-1"
        assert p2.session_id == "s-1"

    def test_get_params(self):
        params = TaskGetParams(id="t-1", history_length=5)
        d = params.to_dict()
        assert d["id"] == "t-1"
        p2 = TaskGetParams.from_dict(d)
        assert p2.history_length == 5

    def test_cancel_params(self):
        params = TaskCancelParams(id="t-1")
        d = params.to_dict()
        p2 = TaskCancelParams.from_dict(d)
        assert p2.id == "t-1"


class TestPushNotificationConfig:
    def test_roundtrip(self):
        cfg = PushNotificationConfig(
            url="https://callback.example.com",
            authentication={"schemes": ["jwt"]},
        )
        d = cfg.to_dict()
        assert d["url"] == "https://callback.example.com"
        cfg2 = PushNotificationConfig.from_dict(d)
        assert cfg2.url == "https://callback.example.com"


class TestAgentCard:
    def test_sardis_card_factory(self):
        card = create_sardis_agent_card("https://api.sardis.sh")
        assert card.name == "Sardis Payment Agent"
        assert card.url == "https://api.sardis.sh"
        assert card.provider.organization == "Sardis"
        assert card.capabilities.streaming is True
        assert len(card.skills) == 5
        assert card.skills[0].id == "payment-execute"

    def test_roundtrip(self):
        card = create_sardis_agent_card("https://api.sardis.sh")
        d = card.to_dict()
        assert d["name"] == "Sardis Payment Agent"
        assert d["defaultInputModes"] == ["text/plain", "application/json"]
        assert d["capabilities"]["streaming"] is True
        assert len(d["skills"]) == 5

        card2 = AgentCard.from_dict(d)
        assert card2.name == card.name
        assert card2.url == card.url
        assert len(card2.skills) == 5

    def test_google_maps_example(self):
        """Test parsing the Google Maps example from the spec."""
        data = {
            "name": "Google Maps Agent",
            "description": "Plan routes",
            "url": "https://maps-agent.google.com",
            "provider": {"organization": "Google", "url": "https://google.com"},
            "version": "1",
            "authentication": {"schemes": ["OAuth2"]},
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain", "application/html"],
            "capabilities": {"streaming": True, "pushNotifications": False},
            "skills": [
                {
                    "id": "route-planner",
                    "name": "Route planning",
                    "description": "Plan routes between locations",
                    "tags": ["maps", "routing"],
                    "examples": ["plan my route from A to B"],
                }
            ],
        }
        card = AgentCard.from_dict(data)
        assert card.name == "Google Maps Agent"
        assert card.provider.organization == "Google"
        assert card.capabilities.streaming is True
        assert card.skills[0].id == "route-planner"


class TestJsonRpc:
    def test_request_roundtrip(self):
        req = JsonRpcRequest(method="tasks/send", params={"id": "t-1"}, id=1)
        d = req.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["method"] == "tasks/send"
        assert d["id"] == 1

        req2 = JsonRpcRequest.from_dict(d)
        assert req2.method == "tasks/send"
        assert req2.id == 1

    def test_response_success(self):
        resp = JsonRpcResponse(id=1, result={"id": "t-1", "status": {"state": "completed"}})
        d = resp.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["result"]["id"] == "t-1"
        assert "error" not in d

    def test_response_error(self):
        resp = JsonRpcResponse(
            id=1,
            error=JsonRpcError(code=-32601, message="Method not found"),
        )
        d = resp.to_dict()
        assert d["error"]["code"] == -32601
        assert d["error"]["message"] == "Method not found"
        assert "result" not in d  # error responses omit result


class TestSSEEvents:
    def test_status_update_event(self):
        evt = TaskStatusUpdateEvent(
            id="t-1",
            status=TaskStatus(state=TaskState.WORKING),
            final=False,
        )
        d = evt.to_dict()
        assert d["id"] == "t-1"
        assert d["status"]["state"] == "working"
        assert d["final"] is False

    def test_final_event(self):
        evt = TaskStatusUpdateEvent(
            id="t-1",
            status=TaskStatus(state=TaskState.COMPLETED),
            final=True,
        )
        d = evt.to_dict()
        assert d["final"] is True
