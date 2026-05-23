# Sardis SDK Package Boundary

Sardis has multiple SDK-shaped packages because they serve different developer
entry points. They should not be merged or renamed casually.

## Package Roles

| Package | Distribution/import | Role | Primary contributor |
| --- | --- | --- | --- |
| `packages/sardis-sdk-python/` | `sardis-sdk` / `sardis_sdk` | Official Python API SDK for Sardis resources, models, errors, pagination, webhooks, and async client behavior. | Backend and app developers calling the Sardis API. |
| `packages/sardis-sdk-js/` | `@sardis/sdk` | Official TypeScript API SDK for Sardis resources and typed client behavior. | TypeScript app, server, and integration developers. |
| `packages/sardis-agent-sdk/` | `sardis-agent-sdk` / `sardis_agent_sdk` | Anthropic Claude Agent SDK integration: tool definitions, toolkit helpers, and agent-loop glue around the public Sardis client. | Developers embedding Sardis tools inside Claude/Anthropic agent runtimes. |
| `packages/sardis-ai-sdk/` | `@sardis/ai-sdk` | Vercel AI SDK integration. | Developers adding Sardis tool surfaces to Vercel AI SDK apps. |

## Decision

Keep the official API SDKs and framework-specific agent integrations separate.
The official SDKs own canonical client behavior. Agent integration packages own
runtime glue for specific agent frameworks.

Do not move resource models, pagination behavior, API errors, idempotency
helpers, webhook verification, or canonical API request/response semantics into
`packages/sardis-agent-sdk/`. That package may wrap the official Python SDK but
must not become a second Python API SDK.

Do not move Anthropic-specific tool schemas, Claude message loop behavior, or
agent-tool orchestration into `packages/sardis-sdk-python/`. Those belong in
`packages/sardis-agent-sdk/`.

## Contribution Rules

- API client/resource/model changes go to `packages/sardis-sdk-python/` or
  `packages/sardis-sdk-js/`.
- Anthropic/Claude Agent SDK tool-loop changes go to
  `packages/sardis-agent-sdk/`.
- Vercel AI SDK tool integration changes go to `packages/sardis-ai-sdk/`.
- Generic payment, mandate, policy, x402, MPP, or evidence semantics belong in
  protocol/core packages first, then SDK packages can expose them.
- Rename only after preserving install commands, import paths, examples,
  package-owned tests, and downstream compatibility.

## Validation

Run the package-local command for the package you changed:

```bash
uv run pytest packages/sardis-sdk-python/tests -q
pnpm --filter @sardis/sdk test
pnpm --filter @sardis/sdk typecheck
PYTHONPATH=packages/sardis-agent-sdk/src uv run pytest packages/sardis-agent-sdk/tests -q
pnpm --filter @sardis/ai-sdk test
```

Then run the contributor package inventory gate:

```bash
python3 scripts/package_validation_inventory.py --check-no-fallback
pnpm run check:contributor
```
