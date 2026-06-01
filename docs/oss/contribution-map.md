# Sardis Contribution Map

This map turns the package maturity matrix into practical contribution paths.
Use it to pick the right package, scope the PR, and choose the validation
command before making changes.

Start with:

```bash
pnpm run check:contributor
```

That gate is intentionally credential-free. It checks the OSS/private boundary,
stale API paths, source-layout invariants, package documentation coverage,
root-test migration inventory, and a small pytest smoke suite.

The monorepo was consolidated from 47 packages into 5 in May 2026 (PR #387 /
commit `5ab3e301`); see `docs/packages.md` for the current package list.

## Contribution Principles

- Keep one logical change per PR.
- Prefer package-owned tests over root `tests/`.
- Do not add hosted-product, customer, sales, investor, or production-provider
  material to the public repo.
- Provider integrations must be sandbox-safe by default and explicit about
  credential requirements.
- Security-sensitive work must include fail-closed tests or a clear validation
  command.
- Keep source placement aligned with `docs/oss/source-layout.md`. The backend
  payment engine and the FastAPI service live in the private service repo; do
  not reintroduce a backend API source tree or repeated API package names here.
- Keep package layout aligned with `docs/oss/package-layout.md`.

## Core Contribution Paths

These packages are the stable OSS center of gravity.

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Python SDK client | `packages/sardis/` | Client fixes (`_client`, `models`, `resources`, `cli`, `integrations`), integration extras (`langchain`, `crewai`, `openai-agents`, `anthropic`, `ai-sdk`, etc.), typed examples, error handling, idempotency helpers | `uv run pytest packages/sardis/tests -q` |
| TypeScript SDK umbrella | `packages/sardis-js/` | Subpath export stability, v1 codemod updates, type fixes, examples | `pnpm --filter sardis test`; `pnpm --filter sardis typecheck` |

## Supported Package Paths

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Agent tooling | `packages/sardis-mcp-server/` | MCP schema improvements, examples, simulated-response labeling | `pnpm --filter @sardis/mcp-server build`; `pnpm --filter @sardis/mcp-server test` |
| Reference + verifiers | `packages/sardis-reference/` | Simulator/verifier fixtures, protocol payload alignment, credential-free examples | `pnpm --filter @sardis/reference test` |
| Agent tools | `packages/sardis-agent-tools/` | Tool-definition fixes, SDK-surface alignment | `pnpm --filter @sardis/agent-tools test` |
| Framework adapters | `packages/sardis-hermes/`, `packages/sardis-nemoclaw/`, `packages/sardis-openclaw/` | Adapter fixes against the published client, examples | package build/test for the touched adapter |
| Project scaffolder | `packages/create-sardis-app/` | Template updates, generated-project build fixes | `pnpm --filter create-sardis-app build` |

## What Not To Put In Public PRs

Do not add:

- hosted dashboard or approval inbox code
- production deployment secrets or customer runbooks
- sales, GTM, investor, hiring, or partner-development material
- real provider credentials, webhook secrets, API keys, private keys, or raw
  customer payloads
- generated artifacts unless the source and regeneration command are clear

Use `docs/oss/public-private-boundary.md` when a file looks borderline.

## Choosing A Test Location

| Change | Put tests in |
| --- | --- |
| Python SDK client behavior | `packages/sardis/tests/` |
| TypeScript SDK behavior | `packages/sardis-js/__tests__/` |
| MCP server | `packages/sardis-mcp-server/` package tests |
| Reference / adapters | the touched package's own test dir |

Root tests are a migration backlog, not the default contribution path. If a
root test becomes important for a new PR, move it to the owning package first
unless it genuinely spans multiple packages.
