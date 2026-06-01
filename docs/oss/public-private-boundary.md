# Public / Private Repository Boundary

Sardis is open-core. This repository is the **public** half: the published
SDKs and MCP server, the reference simulator/verifiers and protocol adapters,
the framework integrations, the smart contracts, examples, and public docs. The
Sardis service — the FastAPI API, the payment engine (policy, chain execution,
cards, checkout, compliance, wallet, ledger, ramp, guardrails, UCP, protocol
verification), managed provider operations, dashboard, billing, and customer
workflows — lives in a separate **private** repository and is **not** part of
this tree.

This doc is the canonical line. For the structural map, see
[`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

## Public (this repo)

| Area | Paths | Why it's public |
| --- | --- | --- |
| Python SDK client + CLI | `packages/sardis/` | The published `sardis` thin client: `_client`, `models/`, `resources/`, `cli/`, `integrations/`, `bulk`, `pagination`, `telemetry`. |
| TypeScript SDK | `packages/sardis-js/` | The published `sardis` npm package. |
| MCP server | `packages/sardis-mcp-server/` | The published `@sardis/mcp-server`. |
| Reference + adapters | `packages/sardis-reference/`, `packages/sardis-agent-tools/`, `packages/sardis-hermes/`, `packages/sardis-nemoclaw/`, `packages/sardis-openclaw/`, `packages/create-sardis-app/` | Simulator/verifiers, agent tooling, and framework adapters that run without private credentials. |
| Framework integrations | `packages/sardis/src/sardis/integrations/`, `packages/sardis-js` subpaths | LangChain, CrewAI, OpenAI Agents, ADK, A2A, Vercel AI SDK, … |
| Examples + demos | `examples/`, `demos/` | Adoption material that runs without private credentials. |
| Smart contracts | `contracts/` | Wallet / escrow / ledger-anchor Solidity + Foundry tests. |
| Public docs | `README.md`, `ARCHITECTURE.md`, `docs/` (incl. `docs/oss/`), `llms.txt` | Explanation and contributor onboarding. |
| Public landing | `apps/landing/` | Explains Sardis and links to docs/GitHub; hosted-product CTAs follow [`landing-surface.md`](landing-surface.md). |

## Private (not in this repo)

These live in the private service/product/company repos and must never be added here:

| Area | Why it's private |
| --- | --- |
| Payment engine | The policy/orchestrator, chain executor, cards, checkout, compliance, wallet, ledger, ramp, guardrails, UCP, and protocol-verification modules — the inspectable moat that must not ship a policy-bypassing execution path to pip/npm consumers. |
| Reference / hosted API service | The runnable FastAPI service (routes, migrations, provider-port adapters) that wires the engine to live providers. |
| Hosted dashboard + product UI | Managed-product surface, not part of the open core. |
| Managed credential vault + provider operations | Holds live provider credentials and routing for the hosted product. |
| Billing / customer workflows | Commercial operations. |
| GTM, sales, outreach material | Go-to-market; not a contribution surface. |
| Investor, YC, diligence, hiring, partnership drafts | Company-confidential. |
| Production compliance operations (SOC2 evidence, runbooks) | Sensitive operational material (sanitized templates may be public). |

## Policy

1. Do not add tracked sales, investor, customer, hiring, GTM, or private
   partnership material to this repository.
2. Do not reintroduce the payment engine or a backend API source tree into the
   public repo. The published `sardis` package is client-only; its `__init__`
   exposes only the thin-client submodules.
3. Public examples and demos must run without production provider credentials;
   if a key is required, fail fast with a clear message — never a fake fallback.
4. Public CI must not depend on dashboard secrets, hosted billing, customer
   data, or live provider accounts.
5. Public indexing surfaces (sitemap, `llms.txt`, SDK examples, CLI demos, docs,
   `.env.example`) must not route contributors into the private hosted product.
   See [`landing-surface.md`](landing-surface.md).

The boundary is enforced in CI by the credential-free contributor gate
(`pnpm run check:contributor`), which includes `oss_surface_check` (blocks
tracked private paths) and the other surface checkers.
