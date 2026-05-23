# Package Maturity Matrix

This matrix is the coordination source for Sardis open-source cleanup.

Status meanings:

- `core`: public OSS primitive that should remain stable and heavily tested.
- `supported`: public package intended for external use, but narrower than core.
- `demo`: public example or demo, not a stable library surface.

The monorepo was consolidated from 47 packages into 5 in May 2026; see
PR #387 / commit `5ab3e301` for the rationale.

## Core

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `packages/sardis/` | Unified Python SDK umbrella (v2.0.0a0). Consolidates the prior 30+ `sardis-*` packages into one. Submodules: `core`, `cards`, `ledger`, `chain`, `ucp`, `protocol`, `compliance`, `guardrails`, `checkout`, `wallet`, `ramp`, `cli`. Integration extras: `langchain`, `crewai`, `openai-agents`, `autogpt`, `browser-use`, `composio`, `adk`, `a2a`, `anthropic`, `ai-sdk`. | Maintain MIGRATION_NOTES; keep `packages/sardis/tests/` suite green. |
| `packages/sardis-js/` | Unified TypeScript SDK umbrella (v2.0.0-rc.0). Replaces the prior fragmented `@sardis/sdk` + `@sardis/ai-sdk` packages. Provides the `sardis-migrate` codemod. | Keep subpath exports stable; codemod from v1 maintained. |
| `apps/api/` | Reference FastAPI implementation for public API contracts. | Keep route registry under `apps/api/server/route_registry/`. |

## Supported

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `packages/sardis-mcp-server/` | MCP server binary (`npx @sardis/mcp-server`) exposing Sardis tools to MCP-aware clients. | Keep schema tests and examples current. |
