# Architecture

This is the map a new contributor should read first. It describes the **current**
repository — not a historical layout. If anything here disagrees with the code,
the code wins; please open a PR to fix this file.

For *what* Sardis is and how to install it, see [`README.md`](README.md). This
document is about *how the repository is laid out and why*.

---

## The one idea

Every consequential financial action an agent takes — a stablecoin transfer, a
card swipe, an x402 call, an AP2 checkout — passes through **one authority path**
before any money moves:

```
mandate verification  →  policy evaluation  →  spend tracking  →  compliance
        →  execution (provider adapter)  →  append-only signed audit
```

There is intentionally **no second code path** that reaches a provider without
going through this pipeline first. The pipeline is **fail-closed**: if any step
errors or is unconfigured on a money path, the action is denied, not allowed.

Everything below is in service of that one idea.

---

## Open core boundary (what lives in this repo)

| Layer | This repo (MIT, open) | Sardis Cloud (hosted, commercial) |
| --- | --- | --- |
| **Authority core** | Mandates, deterministic policy, approvals, revocation, signed audit packets | Same semantics, managed: org/RBAC/SSO, retention, support |
| **Provider execution** | Typed capability ports, sandbox adapters, BYO-credential adapters | Managed credential vault, webhook handling, routing, alerting |
| **Developer surface** | Python SDK, TypeScript SDK, MCP server, examples, protocol adapters | Hosted dashboard, approval inbox, compliance workflows, audit export |

The authority core and the port contracts are the open moat. The hosted
operations on top of them are the commercial product. Full detail:
[`docs/oss/public-private-boundary.md`](docs/oss/public-private-boundary.md).

---

## Repository layout

```
sardis/
├── apps/api/server/        # The reference FastAPI service (the "backend").
│   ├── routes/<domain>/     # HTTP routes, grouped by domain (see below).
│   ├── providers/           # The provider layer: typed ports + adapters.
│   ├── route_registry/      # Where routes get wired into the app.
│   ├── dependencies.py      # DI: builds the orchestrator + provider registry.
│   └── lifespan.py          # App startup/shutdown wiring.
│
├── packages/               # The three publishable artifacts + their source.
│   ├── sardis/              # Python: thin API client + in-repo runtime core.
│   ├── sardis-js/           # TypeScript SDK (published to npm as `sardis`).
│   └── sardis-mcp-server/   # MCP server (published as `@sardis/mcp-server`).
│
├── examples/               # Small, single-concept, runnable scripts.
├── demos/                  # Larger end-to-end scenarios.
├── contracts/              # Solidity (Foundry) — wallet/escrow/ledger anchor.
├── docs/                   # Public docs, including docs/oss/ (the OSS policy).
└── scripts/                # Contributor gate + repo-hygiene checkers.
```

> **Only three packages are published**: `sardis` (PyPI), `sardis` (npm), and
> `@sardis/mcp-server` (npm). If you read an older doc claiming "30+ packages" or
> "56 packages", that is pre-consolidation drift — those were merged into the
> three above in May 2026.

---

## The authority path, in code

The single entry point for payment execution is `PaymentOrchestrator` in
[`packages/sardis/src/sardis/core/orchestrator.py`](packages/sardis/src/sardis/core/orchestrator.py).
Its own docstring states the contract: it is *the only authorized entry point for
payment execution*, and every payment passes policy → compliance → execution →
ledger in that order. A `False` from policy raises `PolicyViolationError` and
nothing further runs; a `requires_approval` result is treated as a denial
(fail-closed) and routed to human review.

```
   AI AGENT  (Claude / Cursor / LangChain / OpenAI / Mastra / ...)
        │  MCP  |  Python SDK (sardis)  |  TypeScript SDK (sardis)
        ▼
┌──────────────────────────────────────────────┐
│  apps/api/server/routes/<domain>/...          │  HTTP surface
└──────────────────────────────────────────────┘
        ▼
┌──────────────────────────────────────────────┐
│  PaymentOrchestrator  (core/orchestrator.py)  │  single entry point
│   • mandate verification (AP2 / TAP)          │
│   • policy evaluation (deterministic)         │
│   • atomic spend tracking                     │
│   • compliance / KYA / sanctions gates        │
│   • dedup / idempotency                       │
│   Fail-closed: any failure denies the tx      │
└──────────────────────────────────────────────┘
        ▼
┌──────────────────────────────────────────────┐
│  Provider port  (providers/ports/...)         │  execute only — never authorize
└──────────────────────────────────────────────┘
        ▼
┌──────────────────────────────────────────────┐
│  Append-only audit ledger (Ed25519 envelopes) │
└──────────────────────────────────────────────┘
```

The orchestrator depends only on **ports** (`CompliancePort`, `ChainExecutorPort`,
`LedgerPort`, …), never on a concrete vendor SDK. That is what keeps the core
provider-neutral and testable.

---

## The provider layer (the "BYO provider" port contract)

Every external money/identity service sits behind a **typed capability port**.
The orchestrator and routes talk only to these ports, so an adapter can only
*execute* what was already authorized — it cannot authorize, initiate, or settle
money on its own.

Defined in [`apps/api/server/providers/ports/capabilities.py`](apps/api/server/providers/ports/capabilities.py):

| Capability | Port | Role |
| --- | --- | --- |
| `custody` | `CustodyPort` | Derive address / sign an already-authorized payload |
| `fiat_account` | `FiatAccountPort` | Bank-rail USD account + ACH/wire/RTP payout |
| `onramp` | `OnrampPort` | Fiat → crypto session (user funds it) |
| `offramp` | `OfframpPort` | Crypto → fiat payout to a bank |
| `swap` | `SwapPort` | Same-chain / cross-token quote + executable tx |
| `bridge` | `BridgePort` | Cross-chain quote + executable messages |
| `card` | `CardPort` | Virtual card issue + state/limit controls |
| `kyc` | `KycPort` | KYC/KYB identity verification session |
| `kyt` | `KytPort` | AML / address screening — **reports** a verdict only |
| `notification` | `NotificationPort` | Human-in-the-loop approval delivery only |
| `fraud_signal` | `FraudSignalPort` | External fraud signal — contributes a score only |

Two rules that hold across every port:

- **Money is integer minor units (`MinorUnits`) or `Decimal` — never `float`.**
- **Every adapter declares an explicit `CustodyModel`** so the audit trail can
  answer "who held funds at this hop?".

`ProviderRegistry.from_settings()` is the single place that decides which impl
backs each port: a real provider activates only when its keys are set; in dev/test
an unconfigured capability falls back to a `SIMULATED` sandbox impl (always tagged
`sandbox=True`); in production a **required** capability with no provider raises
`ProviderNotConfigured` rather than handing back a simulated impl on a money path.

Full detail and the "how to add a provider" checklist:
[`apps/api/server/providers/README.md`](apps/api/server/providers/README.md).

---

## Route domains

HTTP routes live under `apps/api/server/routes/<domain>/`. The domains:

| Domain | What it covers |
| --- | --- |
| `agents` | Agent lifecycle, identity, linking |
| `wallets` | Wallet creation, balances, addresses |
| `money_movement` | `pay`, FX, funding, transfers |
| `authority` | Approvals, kill switch, policy gates |
| `policy` | Spending policy parse / preview / apply |
| `protocol` | AP2, TAP, x402, MPP, SPT, ACP adapters |
| `compliance` | KYC / AML surfaces |
| `commerce` | Checkout, marketplace |
| `evidence` | Signed attestation / audit export |
| `providers` | Provider-layer status + readiness |
| `identity` | Trust scoring, agent auth |
| `operations` | Alerts, ops surfaces |
| `accounts`, `admin`, `billing`, `developer` | Account/admin/billing/dev tooling |

---

## The protocol adapters

Sardis speaks several agent-payment protocols. They live under
`apps/api/server/routes/protocol/` and `packages/sardis/src/sardis/protocol/`.

- **TAP** (Trust Anchor Protocol) and **AP2** (Agent Payment Protocol) are the
  most mature — real signature verification, fail-closed.
- Newer / partial adapters (x402, MPP, SPT, ACP) are at varying maturity. The
  honest, per-feature status lives in the README **Maturity** table; do not
  assume a protocol route is production-grade just because it exists.
- Genuinely unfinished protocol code is **quarantined** under
  `protocol/experimental/` with per-module disclaimers and zero production
  importers. See "Experimental quarantine" below.

---

## Experimental quarantine

`packages/sardis/src/sardis/protocol/experimental/` holds protocol code that is
*not* production-ready. The rules:

- Each module's README/disclaimer says **why it is here** and what is missing.
- Nothing in `core/`, `routes/`, or `middleware/` imports from `experimental/`
  on a money path. Imports there use `contextlib.suppress(ImportError)` so a
  missing experimental dep can never break the core.
- If you finish hardening an experimental adapter (real verification +
  fail-closed + bad-case tests), it graduates *out* of `experimental/`.

This is the model the rest of the surface should follow: honesty over a green
label.

---

## Where to make your first change

| You want to… | Start here |
| --- | --- |
| Fix an SDK doc/quickstart that drifted | `packages/sardis/README.md`, `examples/` |
| Add/fix a framework integration | `packages/sardis/src/sardis/integrations/<name>/` |
| Add a provider adapter | `apps/api/server/providers/<capability>/` + its README |
| Add a policy / mandate test | `apps/api/tests/`, `packages/sardis/tests/` |
| Add an example | `examples/` (one concept each) + `examples/README.md` |
| Improve MCP tool schemas | `packages/sardis-mcp-server/` |

Run the credential-free contributor gate before opening a PR:

```bash
pnpm run check:contributor
```

See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for full setup and the
contribution map (what is OSS-contributable vs commercial).
