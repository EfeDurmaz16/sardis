# Public / Private Repository Boundary

Sardis is open-core. This repository is the **public** half: the authority core,
the provider-port contracts, the three published SDKs/MCP server, protocol
adapters, examples, and public docs. The hosted Sardis Cloud (dashboard, managed
provider operations, billing, customer workflows) lives in a separate private
repository and is **not** part of this tree.

This doc is the canonical line. It is kept accurate to the **current** 3-package
tree (the May 2026 consolidation merged the old 30+ `sardis-*` packages into
`sardis`, `sardis` (npm), and `@sardis/mcp-server`). For the structural map, see
[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Public (this repo)

| Area | Paths | Why it's public |
| --- | --- | --- |
| Authority core | `packages/sardis/src/sardis/core/`, `.../ledger/`, `.../wallet/`, `.../guardrails/` | Mandates, policy, spend tracking, audit — the inspectable moat. |
| Protocol adapters | `packages/sardis/src/sardis/protocol/`, `apps/api/server/routes/protocol/` | Interoperable agent-payment semantics (AP2, TAP, x402, MPP, …). |
| Provider-port contracts + sandbox/BYO adapters | `apps/api/server/providers/` | The typed capability ports and credential-free sandbox impls. |
| Reference API | `apps/api/` | The runnable FastAPI service that wires the core to the ports. |
| Python SDK + CLI | `packages/sardis/` | The published `sardis` package and its submodules. |
| TypeScript SDK | `packages/sardis-js/` | The published `sardis` npm package. |
| MCP server | `packages/sardis-mcp-server/` | The published `@sardis/mcp-server`. |
| Framework integrations | `packages/sardis/src/sardis/integrations/`, `packages/sardis-js` subpaths | LangChain, CrewAI, OpenAI Agents, ADK, A2A, Vercel AI SDK, … |
| Examples + demos | `examples/`, `demos/` | Adoption material that runs without private credentials. |
| Smart contracts | `contracts/` | Wallet / escrow / ledger-anchor Solidity + Foundry tests. |
| Public docs | `README.md`, `ARCHITECTURE.md`, `docs/` (incl. `docs/oss/`), `llms.txt` | Explanation and contributor onboarding. |
| Public landing | `apps/landing/` | Explains Sardis and links to docs/GitHub; hosted-product CTAs follow [`landing-surface.md`](landing-surface.md). |

## Private (not in this repo)

These live in the private product/company repos and must never be added here:

| Area | Why it's private |
| --- | --- |
| Hosted dashboard + product UI | Managed-product surface, not part of the open core. |
| Managed credential vault + provider operations | Holds live provider credentials and routing for the hosted product. |
| Billing / customer workflows | Commercial operations. |
| GTM, sales, outreach material | Go-to-market; not a contribution surface. |
| Investor, YC, diligence, hiring, partnership drafts | Company-confidential. |
| Production compliance operations (SOC2 evidence, runbooks) | Sensitive operational material (sanitized templates may be public). |

## Policy

1. Do not add tracked sales, investor, customer, hiring, GTM, or private
   partnership material to this repository.
2. Public examples and demos must run without production provider credentials;
   if a key is required, fail fast with a clear message — never a fake fallback.
3. Public CI must not depend on dashboard secrets, hosted billing, customer
   data, or live provider accounts.
4. Provider-specific code stays public only as a generic capability-port adapter
   or a sandbox integration (see [`../../apps/api/server/providers/README.md`](../../apps/api/server/providers/README.md)).
5. Genuinely unfinished protocol code is quarantined under
   `packages/sardis/src/sardis/protocol/experimental/` — see
   [`../../.github/CONTRIBUTING.md`](../../.github/CONTRIBUTING.md).
6. Public indexing surfaces (sitemap, `llms.txt`, SDK examples, CLI demos, docs,
   `.env.example`) must not route contributors into the private hosted product.
   See [`landing-surface.md`](landing-surface.md).

The boundary is enforced in CI by the credential-free contributor gate
(`pnpm run check:contributor`), which includes `oss_surface_check` (blocks
tracked private paths) and the other surface checkers.
