"""Google A2A protocol types — spec-compliant data structures.

Implements the full Google A2A type system:
  - Task, TaskStatus, TaskState
  - Message, Part (TextPart, FilePart, DataPart)
  - Artifact
  - AgentCard, AgentSkill, AgentCapabilities, AgentProvider
  - PushNotificationConfig
  - JSON-RPC 2.0 request/response wrappers

Spec: https://google.github.io/A2A/
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ============ Task States ============

class TaskState(str, Enum):
    """Canonical task lifecycle states per Google A2A spec."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    UNKNOWN = "unknown"


# ============ Parts ============

@dataclass
class TextPart:
    """Text content part."""
    text: str
    type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type, "text": self.text}
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class FilePart:
    """File content part — either inline bytes (base64) or URI reference."""
    name: str | None = None
    mime_type: str | None = None
    bytes_b64: str | None = None  # base64-encoded
    uri: str | None = None
    type: str = "file"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        file_obj: dict[str, Any] = {}
        if self.name:
            file_obj["name"] = self.name
        if self.mime_type:
            file_obj["mimeType"] = self.mime_type
        if self.bytes_b64:
            file_obj["bytes"] = self.bytes_b64
        if self.uri:
            file_obj["uri"] = self.uri
        d: dict[str, Any] = {"type": self.type, "file": file_obj}
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class DataPart:
    """Structured data part — arbitrary JSON payload."""
    data: dict[str, Any] = field(default_factory=dict)
    type: str = "data"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type, "data": self.data}
        if self.metadata:
            d["metadata"] = self.metadata
        return d


Part = TextPart | FilePart | DataPart


def part_from_dict(data: dict) -> Part:
    """Deserialize a Part from its dict representation."""
    part_type = data.get("type", "text")
    metadata = data.get("metadata", {})
    if part_type == "text":
        return TextPart(text=data["text"], metadata=metadata)
    elif part_type == "file":
        f = data.get("file", {})
        return FilePart(
            name=f.get("name"),
            mime_type=f.get("mimeType"),
            bytes_b64=f.get("bytes"),
            uri=f.get("uri"),
            metadata=metadata,
        )
    elif part_type == "data":
        return DataPart(data=data.get("data", {}), metadata=metadata)
    else:
        return DataPart(data=data, metadata=metadata)


# ============ Message ============

@dataclass
class Message:
    """A2A Message — carries Parts between user and agent."""
    role: str  # "user" or "agent"
    parts: list[Part]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Message:
        return cls(
            role=data["role"],
            parts=[part_from_dict(p) for p in data.get("parts", [])],
            metadata=data.get("metadata", {}),
        )


# ============ Artifact ============

@dataclass
class Artifact:
    """Agent-produced output artifact."""
    parts: list[Part]
    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"parts": [p.to_dict() for p in self.parts]}
        if self.name:
            d["name"] = self.name
        if self.description:
            d["description"] = self.description
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Artifact:
        return cls(
            parts=[part_from_dict(p) for p in data.get("parts", [])],
            name=data.get("name"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )


# ============ Task Status ============

@dataclass
class TaskStatus:
    """Current status of a task."""
    state: TaskState
    message: Message | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"state": self.state.value}
        if self.message:
            d["message"] = self.message.to_dict()
        if self.timestamp:
            d["timestamp"] = self.timestamp
        return d

    @classmethod
    def from_dict(cls, data: dict) -> TaskStatus:
        msg = Message.from_dict(data["message"]) if data.get("message") else None
        return cls(
            state=TaskState(data["state"]),
            message=msg,
            timestamp=data.get("timestamp"),
        )


# ============ Task ============

@dataclass
class Task:
    """A2A Task — stateful entity for client-agent interaction."""
    id: str
    session_id: str
    status: TaskStatus
    history: list[Message] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "sessionId": self.session_id,
            "status": self.status.to_dict(),
        }
        if self.history:
            d["history"] = [m.to_dict() for m in self.history]
        if self.artifacts:
            d["artifacts"] = [a.to_dict() for a in self.artifacts]
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        return cls(
            id=data["id"],
            session_id=data.get("sessionId", str(uuid.uuid4())),
            status=TaskStatus.from_dict(data["status"]),
            history=[Message.from_dict(m) for m in data.get("history", [])],
            artifacts=[Artifact.from_dict(a) for a in data.get("artifacts", [])],
            metadata=data.get("metadata", {}),
        )


# ============ Push Notification ============

@dataclass
class PushNotificationConfig:
    """Callback config for task status push notifications."""
    url: str
    authentication: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"url": self.url}
        if self.authentication:
            d["authentication"] = self.authentication
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PushNotificationConfig:
        return cls(
            url=data["url"],
            authentication=data.get("authentication", {}),
        )


# ============ Task Params ============

@dataclass
class TaskSendParams:
    """Parameters for tasks/send and tasks/sendSubscribe."""
    id: str
    message: Message
    session_id: str | None = None
    history_length: int | None = None
    push_notification: PushNotificationConfig | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "message": self.message.to_dict(),
        }
        if self.session_id:
            d["sessionId"] = self.session_id
        if self.history_length is not None:
            d["historyLength"] = self.history_length
        if self.push_notification:
            d["pushNotification"] = self.push_notification.to_dict()
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> TaskSendParams:
        pn = data.get("pushNotification")
        return cls(
            id=data["id"],
            message=Message.from_dict(data["message"]),
            session_id=data.get("sessionId"),
            history_length=data.get("historyLength"),
            push_notification=PushNotificationConfig.from_dict(pn) if pn else None,
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskGetParams:
    """Parameters for tasks/get."""
    id: str
    history_length: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"id": self.id}
        if self.history_length is not None:
            d["historyLength"] = self.history_length
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> TaskGetParams:
        return cls(
            id=data["id"],
            history_length=data.get("historyLength"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskCancelParams:
    """Parameters for tasks/cancel."""
    id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"id": self.id}
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> TaskCancelParams:
        return cls(id=data["id"], metadata=data.get("metadata", {}))


@dataclass
class PushNotificationSetParams:
    """Parameters for tasks/pushNotification/set."""
    id: str
    push_notification_config: PushNotificationConfig

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pushNotificationConfig": self.push_notification_config.to_dict(),
        }


@dataclass
class PushNotificationGetParams:
    """Parameters for tasks/pushNotification/get."""
    id: str

    def to_dict(self) -> dict:
        return {"id": self.id}


# ============ SSE Events ============

@dataclass
class TaskStatusUpdateEvent:
    """Server-sent event for task status changes."""
    id: str
    status: TaskStatus
    final: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "status": self.status.to_dict(),
            "final": self.final,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass
class TaskArtifactUpdateEvent:
    """Server-sent event for new artifacts."""
    id: str
    artifact: Artifact
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "artifact": self.artifact.to_dict(),
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d


# ============ Agent Card ============

@dataclass
class AgentProvider:
    """Agent service provider metadata."""
    organization: str
    url: str

    def to_dict(self) -> dict:
        return {"organization": self.organization, "url": self.url}

    @classmethod
    def from_dict(cls, data: dict) -> AgentProvider:
        return cls(organization=data["organization"], url=data["url"])


@dataclass
class AgentCapabilities:
    """Optional capabilities supported by the agent."""
    streaming: bool = False
    push_notifications: bool = False
    state_transition_history: bool = False

    def to_dict(self) -> dict:
        return {
            "streaming": self.streaming,
            "pushNotifications": self.push_notifications,
            "stateTransitionHistory": self.state_transition_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentCapabilities:
        return cls(
            streaming=data.get("streaming", False),
            push_notifications=data.get("pushNotifications", False),
            state_transition_history=data.get("stateTransitionHistory", False),
        )


@dataclass
class AgentAuthentication:
    """Authentication requirements for the agent."""
    schemes: list[str]
    credentials: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"schemes": self.schemes}
        if self.credentials:
            d["credentials"] = self.credentials
        return d

    @classmethod
    def from_dict(cls, data: dict) -> AgentAuthentication:
        schemes = data.get("schemes", [])
        if isinstance(schemes, str):
            schemes = [schemes]
        return cls(schemes=schemes, credentials=data.get("credentials"))


@dataclass
class AgentSkill:
    """A unit of capability the agent can perform."""
    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    input_modes: list[str] | None = None
    output_modes: list[str] | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
        }
        if self.examples:
            d["examples"] = self.examples
        if self.input_modes:
            d["inputModes"] = self.input_modes
        if self.output_modes:
            d["outputModes"] = self.output_modes
        return d

    @classmethod
    def from_dict(cls, data: dict) -> AgentSkill:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            tags=data.get("tags", []),
            examples=data.get("examples", []),
            input_modes=data.get("inputModes"),
            output_modes=data.get("outputModes"),
        )


@dataclass
class AgentCard:
    """Google A2A spec-compliant Agent Card.

    Served at /.well-known/agent.json
    """
    name: str
    description: str
    url: str
    version: str
    capabilities: AgentCapabilities
    authentication: AgentAuthentication
    default_input_modes: list[str]
    default_output_modes: list[str]
    skills: list[AgentSkill]
    provider: AgentProvider | None = None
    documentation_url: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities.to_dict(),
            "authentication": self.authentication.to_dict(),
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "skills": [s.to_dict() for s in self.skills],
        }
        if self.provider:
            d["provider"] = self.provider.to_dict()
        if self.documentation_url:
            d["documentationUrl"] = self.documentation_url
        return d

    @classmethod
    def from_dict(cls, data: dict) -> AgentCard:
        provider = AgentProvider.from_dict(data["provider"]) if data.get("provider") else None
        return cls(
            name=data["name"],
            description=data["description"],
            url=data["url"],
            version=data.get("version", "1"),
            capabilities=AgentCapabilities.from_dict(data.get("capabilities", {})),
            authentication=AgentAuthentication.from_dict(data.get("authentication", {})),
            default_input_modes=data.get("defaultInputModes", ["text/plain"]),
            default_output_modes=data.get("defaultOutputModes", ["text/plain"]),
            skills=[AgentSkill.from_dict(s) for s in data.get("skills", [])],
            provider=provider,
            documentation_url=data.get("documentationUrl"),
        )


# ============ JSON-RPC 2.0 ============

JSONRPC_VERSION = "2.0"


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 request."""
    method: str
    params: dict[str, Any]
    id: int | str | None = None
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
        }
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> JsonRpcRequest:
        return cls(
            method=data["method"],
            params=data.get("params", {}),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", JSONRPC_VERSION),
        )


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 error object."""
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 response."""
    id: int | str | None
    result: dict[str, Any] | None = None
    error: JsonRpcError | None = None
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            d["error"] = self.error.to_dict()
        else:
            d["result"] = self.result
        return d


# ============ Standard JSON-RPC Error Codes ============

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603

# A2A-specific error codes (application-defined, >= -32000)
A2A_TASK_NOT_FOUND = -32001
A2A_TASK_NOT_CANCELABLE = -32002
A2A_PUSH_NOTIFICATION_NOT_SUPPORTED = -32003
A2A_UNSUPPORTED_OPERATION = -32004


# ============ Factory Helpers ============

def create_sardis_agent_card(
    base_url: str,
    version: str = "1",
) -> AgentCard:
    """Create the standard Sardis agent card with payment skills."""
    return AgentCard(
        name="Sardis Payment Agent",
        description=(
            "Payment OS for the Agent Economy — escrow, settlement, "
            "policy-gated payments, and trust infrastructure for AI agents."
        ),
        url=base_url,
        version=version,
        provider=AgentProvider(
            organization="Sardis",
            url="https://sardis.sh",
        ),
        documentation_url="https://sardis.sh/docs",
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=True,
        ),
        authentication=AgentAuthentication(schemes=["Bearer"]),
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id="payment-execute",
                name="Execute Payment",
                description="Execute a payment from one agent to another via escrow",
                tags=["payment", "escrow", "settlement", "usdc"],
                examples=[
                    "Pay 10 USDC to agent_abc for completing the task",
                    "Send payment of 50 USDC on Base to merchant",
                ],
                input_modes=["application/json"],
                output_modes=["application/json"],
            ),
            AgentSkill(
                id="payment-verify",
                name="Verify Payment",
                description="Verify a payment was completed on-chain",
                tags=["payment", "verification", "on-chain"],
                examples=[
                    "Verify that payment tx 0x123... was settled",
                    "Check if escrow for task_xyz has been released",
                ],
            ),
            AgentSkill(
                id="balance-check",
                name="Check Balance",
                description="Check an agent wallet balance across supported chains",
                tags=["balance", "wallet", "usdc"],
                examples=[
                    "What is my USDC balance on Base?",
                    "Check available funds for agent_abc",
                ],
            ),
            AgentSkill(
                id="escrow-manage",
                name="Manage Escrow",
                description="Create, fund, deliver, release, or refund escrow payments",
                tags=["escrow", "lifecycle", "dispute"],
                examples=[
                    "Create an escrow of 100 USDC between agent_a and agent_b",
                    "Release escrow funds for completed delivery",
                ],
                input_modes=["application/json"],
                output_modes=["application/json"],
            ),
            AgentSkill(
                id="trust-check",
                name="Check Trust",
                description="Query agent trust scores, reputation, and identity verification",
                tags=["trust", "reputation", "identity", "erc-8004"],
                examples=[
                    "What is the trust score for agent_xyz?",
                    "Is agent_abc verified on-chain?",
                ],
            ),
        ],
    )
