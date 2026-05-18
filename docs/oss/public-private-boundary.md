# Public / Private Repository Boundary

Sardis should use a clean open-core split:

- `sardis` remains the public OSS repository for protocol, SDK, policy, evidence, adapter contracts, examples, and conformance.
- `sardis-cloud` or `sardis-product` should hold hosted dashboard, managed provider operations, billing, customer workflows, and private commercial material.

## Keep Public

| Area | Paths | Reason |
| --- | --- | --- |
| Protocol and API contracts | `docs/api/`, `docs/docs/api/`, `packages/sardis-protocol/`, `packages/sardis-a2a/`, `packages/sardis-ucp/` | These define interoperable agent-payment semantics. |
| SDKs and CLI | `sardis/`, `packages/sardis-sdk-python/`, `packages/sardis-sdk-js/`, `packages/sardis-cli/` | Contributors need typed client surfaces and local tooling. |
| Core authority primitives | `packages/sardis-core/`, `packages/sardis-ledger/`, `packages/sardis-wallet/`, `packages/sardis-chain/` | These express business logic that should be inspectable. |
| API implementation | `packages/api/` | Keep as the reference implementation, but separate hosted-only routes over time. |
| MCP and framework integrations | `packages/sardis-mcp-server/`, `packages/sardis-ai-sdk/`, `packages/sardis-langchain/`, `packages/sardis-crewai/`, `examples/` | These are the main contribution surface for agent ecosystems. |
| Simulators and demos | `demos/`, `examples/`, sandbox-only provider adapters | Useful for adoption when they run without private credentials. |
| Public docs | `README.md`, `SECURITY.md`, `docs/docs/`, `docs/quickstart/`, `docs/architecture/`, `docs/oss/` | Public explanation and contributor onboarding. |

## Move Private

| Area | Current paths | Destination |
| --- | --- | --- |
| Hosted dashboard | `apps/dashboard/` | Removed from public tracking; recover into private product repo from history if needed. |
| Checkout UI if used as product surface | `packages/sardis-checkout-ui/` | Removed from public tracking unless it becomes a public embeddable widget. |
| Hosted product design system | `packages/ui-web/` | Removed from public tracking unless Sardis intentionally publishes a public UI package. |
| Managed dashboard deployment workflows | Product-only dashboard deploy jobs | Private product repo or manually triggered internal workflow; public OSS CI/CD should not deploy the hosted dashboard. |
| GTM and sales material | `docs/sales/`, `scripts/gtm/`, `scripts/outreach/` | Private product/commercial repo. |
| Investor, YC, diligence, hiring, partnership drafts | `docs/cdp/`, `docs/hiring/`, `docs/partnerships/`, `docs/yc/` | Private company repo. |
| Production compliance operations | SOC2 evidence, go/no-go evidence, internal runbooks | Private compliance repo unless sanitized into public templates. |

## Near-Term Policy

1. Do not add new tracked sales, investor, customer, hiring, or private partnership material to this repository.
2. Public examples must run without production provider credentials.
3. Public CI must not depend on dashboard secrets, hosted billing, customer data, or provider accounts.
4. Provider-specific code may stay public only when it is a generic adapter or sandbox integration.
5. Product-only paths should be marked `private-candidate` until moved.

## Extraction Plan

1. Freeze public API and SDK contracts.
2. Remove tracked private docs from the public repo and leave a manifest.
3. Make public CI OSS-only.
4. Move dashboard/product packages to a private repo using a history-preserving export if needed.
5. Consume public Sardis packages from the private product repo via published packages or a pinned git tag.
