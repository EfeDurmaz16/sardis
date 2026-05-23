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
- Keep source placement aligned with `docs/oss/source-layout.md`. The reference
  API source tree is `apps/api/server`; do not reintroduce the old
  repeated API package names, extra API `src` layer, or legacy flat router
  bucket.
- Keep package layout aligned with `docs/oss/package-layout.md`.

## Core Contribution Paths

These packages are the stable OSS center of gravity.

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Python SDK umbrella | `packages/sardis/` | Submodule fixes (`core`, `cards`, `ledger`, `chain`, `protocol`, `compliance`, `guardrails`, `checkout`, `wallet`, `ramp`, `cli`), integration extras (`langchain`, `crewai`, `openai-agents`, `anthropic`, `ai-sdk`, etc.), typed examples, error handling, idempotency helpers | `uv run pytest packages/sardis/tests -q` |
| TypeScript SDK umbrella | `packages/sardis-js/` | Subpath export stability, v1 codemod updates, type fixes, examples | `pnpm --filter sardis test`; `pnpm --filter sardis typecheck` |
| Reference API | `apps/api/` | Route tests, OpenAPI alignment, middleware safety, domain routing cleanup | `uv run pytest apps/api/tests -q`; `pnpm run check:contributor` |

## Supported Package Paths

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Agent tooling | `packages/sardis-mcp-server/` | MCP schema improvements, examples, simulated-response labeling | `pnpm --filter @sardis/mcp-server build`; `pnpm --filter @sardis/mcp-server test` |

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
| API route, middleware, auth, webhooks | `apps/api/tests/` |
| Anything inside the Python umbrella | `packages/sardis/tests/<submodule>/` |
| TypeScript SDK behavior | `packages/sardis-js/__tests__/` |
| MCP server | `packages/sardis-mcp-server/` package tests |

Root tests are a migration backlog, not the default contribution path. If a
root test becomes important for a new PR, move it to the owning package first
unless it genuinely spans multiple packages.
