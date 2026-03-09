"""Google A2A (Agent-to-Agent) protocol implementation for Sardis.

Spec-compliant implementation of Google's A2A protocol:
  - JSON-RPC 2.0 transport (tasks/send, tasks/get, tasks/cancel, tasks/sendSubscribe)
  - Agent card discovery at /.well-known/agent.json
  - Task lifecycle: submitted → working → completed/failed/canceled
  - Message/Part/Artifact types (TextPart, FilePart, DataPart)
  - SSE streaming for real-time task updates
  - Push notification configuration

Sardis extends the protocol with payment-domain skills (escrow, settlement,
trust verification) delivered as DataPart payloads within the standard A2A framework.

Spec: https://google.github.io/A2A/
"""

from .client import (
    A2AClient,
    A2AClientConfig,
    A2AClientError,
)
from .discovery import (
    AgentDiscoveryService,
    DiscoveredAgent,
)
from .server import (
    A2AServer,
    InvalidParamsError,
    TaskHandler,
    TaskNotCancelableError,
    TaskNotFoundError,
)
from .types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentProvider,
    AgentSkill,
    Artifact,
    DataPart,
    FilePart,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    Message,
    Part,
    PushNotificationConfig,
    Task,
    TaskArtifactUpdateEvent,
    TaskCancelParams,
    TaskGetParams,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
    create_sardis_agent_card,
)

# Legacy re-exports for backward compatibility during migration
from .agent_card import (
    AgentCapability,
    PaymentCapability,
    SardisAgentCard,
)
from .messages import (
    A2ACredentialRequest,
    A2ACredentialResponse,
    A2AMessage,
    A2AMessageType,
    A2APaymentRequest,
    A2APaymentResponse,
)

__all__ = [
    # Types (Google A2A spec)
    "AgentCard",
    "AgentCapabilities",
    "AgentAuthentication",
    "AgentProvider",
    "AgentSkill",
    "Task",
    "TaskState",
    "TaskStatus",
    "Message",
    "Part",
    "TextPart",
    "FilePart",
    "DataPart",
    "Artifact",
    "TaskSendParams",
    "TaskGetParams",
    "TaskCancelParams",
    "PushNotificationConfig",
    "TaskStatusUpdateEvent",
    "TaskArtifactUpdateEvent",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    # Server
    "A2AServer",
    "TaskHandler",
    "TaskNotFoundError",
    "TaskNotCancelableError",
    "InvalidParamsError",
    # Client
    "A2AClient",
    "A2AClientConfig",
    "A2AClientError",
    # Discovery
    "AgentDiscoveryService",
    "DiscoveredAgent",
    # Factory
    "create_sardis_agent_card",
    # Legacy (backward compat)
    "SardisAgentCard",
    "AgentCapability",
    "PaymentCapability",
    "A2AMessageType",
    "A2AMessage",
    "A2APaymentRequest",
    "A2APaymentResponse",
    "A2ACredentialRequest",
    "A2ACredentialResponse",
]
