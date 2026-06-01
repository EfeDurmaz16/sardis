# Package Maturity Matrix

This matrix is the coordination source for Sardis open-source cleanup.

Status meanings:

- `core`: public OSS primitive that should remain stable and heavily tested.
- `supported`: public package intended for external use, but narrower than core.
- `demo`: public example or demo, not a stable library surface.

The monorepo was consolidated from 47 packages into 5 in May 2026; see
PR #387 / commit `5ab3e301` for the rationale.

The backend payment engine and the reference FastAPI service moved to the
private service repository in the OSS/private split; this matrix now covers the
public SDK + adapter surface only.

## Core

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `packages/sardis/` | Unified Python SDK umbrella (v2.0.0a0): the published thin client (`_client`, `models`, `resources`, `cli`, `integrations`, `bulk`, `pagination`, `telemetry`). Integration extras: `langchain`, `crewai`, `openai-agents`, `autogpt`, `browser-use`, `composio`, `adk`, `a2a`, `anthropic`, `ai-sdk`. | Keep `packages/sardis/tests/` client suite green. |
| `packages/sardis-js/` | Unified TypeScript SDK umbrella (v2.0.0-rc.0). Replaces the prior fragmented `@sardis/sdk` + `@sardis/ai-sdk` packages. Provides the `sardis-migrate` codemod. | Keep subpath exports stable; codemod from v1 maintained. |

## Supported

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `packages/sardis-mcp-server/` | MCP server binary (`npx @sardis/mcp-server`) exposing Sardis tools to MCP-aware clients. | Keep schema tests and examples current. |
| `packages/sardis-reference/` | Reference simulator and protocol verifiers contributors can run without private credentials. | Keep verifier fixtures aligned with the published protocol payloads. |
| `packages/sardis-agent-tools/` | Framework-agnostic agent tool definitions wrapping the SDK client. | Keep tool schemas in sync with the SDK surface. |
| `packages/sardis-hermes/` | Hermes agent-framework adapter built on the Sardis client. | Keep the adapter green against the published client. |
| `packages/sardis-nemoclaw/` | NeMoClaw agent-framework adapter built on the Sardis client. | Keep the adapter green against the published client. |
| `packages/sardis-openclaw/` | OpenClaw agent-framework adapter built on the Sardis client. | Keep the adapter green against the published client. |

## Demo

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `packages/create-sardis-app/` | `create-sardis-app` scaffolder for bootstrapping a Sardis SDK project. | Keep the generated template building against the current SDK. |
