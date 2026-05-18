# Package Maturity Matrix

This matrix is the coordination source for Sardis open-source cleanup.

Status meanings:

- `core`: public OSS primitive that should remain stable and heavily tested.
- `supported`: public package intended for external use, but narrower than core.
- `experimental`: public package with useful code but incomplete API stability.
- `demo`: public example or demo, not a stable library surface.
- `private-candidate`: product, commercial, or ops surface that should move private.
- `archive-candidate`: likely stale, duplicate, generated, or low-value surface pending removal.

## Core

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `sardis/` | Root Python client facade for the public SDK. | Keep examples aligned with real imports. |
| `packages/sardis-core/` | Domain models, shared primitives, and configuration. | Ensure all local packages resolve from workspace sources. |
| `packages/sardis-api/` | Reference FastAPI implementation for public API contracts. | Split hosted-only routes from protocol/reference routes. |
| `packages/sardis-protocol/` | AP2/TAP/mandate verification semantics. | Add conformance fixtures and versioned schemas. |
| `packages/sardis-ledger/` | Append-only audit/evidence ledger primitives. | Add tamper-evidence and replay fixtures. |
| `packages/sardis-sdk-python/` | Python SDK package. | Keep smoke tests and quickstarts current. |
| `packages/sardis-sdk-js/` | TypeScript SDK package. | Keep build, typecheck, and tests in required CI. |
| `packages/sardis-mcp-server/` | MCP surface for agent tools. | Keep schema tests and examples current. |

## Supported

| Path | Why it exists | Required before stable |
| --- | --- | --- |
| `packages/sardis-cli/` | Local developer and demo workflow. | Add contributor-focused smoke command. |
| `packages/sardis-chain/` | Chain execution and routing primitives. | Separate simulator paths from live provider paths. |
| `packages/sardis-wallet/` | Wallet management adapter layer. | Keep non-custodial and provider-boundary docs current. |
| `packages/sardis-compliance/` | Compliance provider abstractions. | Remove raw payload logging and document sandbox mode. |
| `packages/sardis-checkout/` | Merchant checkout reference flow. | Keep mandate validation fail-closed tests. |
| `packages/sardis-ai-sdk/` | Vercel AI SDK integration. | Keep published package CI green. |
| `packages/sardis-langchain/` | LangChain integration. | Add minimal integration test. |
| `packages/sardis-crewai/` | CrewAI integration. | Add minimal integration test. |
| `packages/sardis-openai-agents/` | OpenAI Agents integration. | Add current SDK examples and tests. |
| `packages/sardis-a2a/` | Agent-to-agent protocol integration. | Add conformance tests. |
| `packages/sardis-ucp/` | UCP transport/protocol work. | Clarify API stability. |

## Experimental

| Path | Why it exists | Required before promotion |
| --- | --- | --- |
| `packages/sardis-cards/` | Card provider adapter experiments. | Keep provider-specific production ops private. |
| `packages/sardis-ramp/` | On/off-ramp provider experiments. | Add sandbox-only examples. |
| `packages/sardis-coinbase/` | Coinbase-related adapter work. | Verify current API docs before changing dependency surface. |
| `packages/sardis-lightspark/` | Lightspark/Grid-related adapter work. | Confirm provider state and sandbox viability. |
| `packages/sardis-striga/` | Striga adapter work. | Reassess after provider status changes. |
| `packages/sardis-mpp/` | MPP protocol experiments. | Add contract tests or mark archive. |
| `packages/sardis-connect/` | Python connect package. | Clarify overlap with JS connect package. |
| `packages/sardis-connect-js/` | JS connect package. | Clarify embed versus SDK boundary. |
| `packages/sardis-zk-policy/` | ZK policy experiments. | Add reproducible proving/verifying dev setup. |
| `packages/sardis-zkp/` | Experimental ZK proof circuits for identity, mandate, and funding proofs. | Add reproducible proving/verifying dev setup and fixtures. |
| `packages/sardis-guardrails/` | Guardrails integration. | Add real examples and tests. |
| `packages/sardis-adk/` | Google ADK integration. | Refresh against current ADK docs before publication. |
| `packages/sardis-agentkit/` | AgentKit integration. | Refresh against current AgentKit docs before publication. |
| `packages/sardis-browser-use/` | Browser-use integration. | Add smoke test or archive. |
| `packages/sardis-composio/` | Composio integration. | Add smoke test or archive. |
| `packages/sardis-autogpt/` | AutoGPT integration. | Revalidate current AutoGPT plugin shape. |
| `packages/sardis-openai/` | OpenAI function/tool integration. | Clarify overlap with OpenAI Agents package. |
| `packages/sardis-openclaw/` | OpenClaw integration. | Add evidence of current ecosystem use. |
| `packages/n8n-nodes-sardis/` | n8n integration. | Add build/test gate before publication. |
| `packages/sardis-activepieces/` | Activepieces integration. | Add build/test gate before publication. |

## Demo

| Path | Notes |
| --- | --- |
| `examples/` | Public examples; each must run without private credentials or clearly use placeholders. |
| `demos/` | Demo apps; should not be part of required CI unless they are fast and deterministic. |
| `apps/landing/` | Public website source; can stay public but should not block OSS protocol CI. |
| `apps/canvas-site/` | Public content/canvas source; generated outputs should be checked for drift. |

## Private Candidates

| Path | Reason |
| --- | --- |
| `apps/dashboard/` | Hosted product surface: auth, org, billing, approval inbox, onboarding, and admin flows. |
| `packages/sardis-checkout-ui/` | Product UI unless intentionally published as a stable embeddable OSS component. |
| `packages/ui-web/` | Hosted product design system unless intentionally published as a public UI package. |
| Product-only deployment and monitoring workflows | Keep out of public OSS CI/CD; dashboard deploy workflows belong in the private product repo. |

## Archive Candidates

| Path | Reason |
| --- | --- |
| Empty shell directories such as `packages/sardis-cli-go/`, `packages/sardis-cli-js/`, `packages/sardis-mpp-proxy/`, `packages/sardis-ramp-js/`, `packages/sardis-spend-widget/`, `packages/sardis-stagehand/`, and `packages/sardis-telegram-bot/` | No tracked source surface today; add code only with a clear maintainer-approved package goal. |
| Generated uptime and response-time artifacts under `api/` | Generated monitoring output should not be source unless intentionally versioned. |
| Generated `llms-full.txt` outputs | Keep generated docs reproducible from source or stop tracking generated copies. |
| Duplicate provider planning docs | Keep public templates, move company-specific provider strategy private. |

## Package README Standard

Each package README should include:

1. What this package does.
2. Why it exists in Sardis.
3. Install command.
4. Minimal usage example.
5. Public API stability.
6. Local test/build command.
7. Contribution notes.
8. Security or provider-credential caveats.
