<div align="center">
  <h1>Sardis</h1>
  <p><strong>The open-source financial authority layer for AI agents.</strong></p>
  <p>
    Mandates, deterministic policy, approvals, revocation, and audit evidence —
    enforced before any wallet, card, stablecoin, payment API, or x402 endpoint moves money.
  </p>

  <p>
    <a href="https://sardis.sh">Website</a> ·
    <a href="https://docs.sardis.sh">Docs</a> ·
    <a href="https://sardis.sh/playground">Playground</a> ·
    <a href="https://discord.gg/XMA9JwDJ">Discord</a>
  </p>

  <p>
    <a href="https://pypi.org/project/sardis/"><img src="https://img.shields.io/pypi/v/sardis?label=PyPI&color=3776AB&logo=python&logoColor=white" alt="PyPI"></a>
    <a href="https://www.npmjs.com/package/sardis"><img src="https://img.shields.io/npm/v/sardis?label=npm&color=CB3837&logo=npm&logoColor=white" alt="npm"></a>
    <a href="https://www.npmjs.com/package/@sardis/mcp-server"><img src="https://img.shields.io/npm/v/@sardis/mcp-server?label=%40sardis%2Fmcp-server&color=CB3837&logo=npm&logoColor=white" alt="MCP server"></a>
    <a href="https://github.com/EfeDurmaz16/sardis/stargazers"><img src="https://img.shields.io/github/stars/EfeDurmaz16/sardis?style=flat&logo=github&color=181717" alt="Stars"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
    <a href="https://github.com/EfeDurmaz16/sardis/actions"><img src="https://img.shields.io/github/actions/workflow/status/EfeDurmaz16/sardis/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white" alt="CI"></a>
    <a href="https://securityscorecards.dev/viewer/?uri=github.com/EfeDurmaz16/sardis"><img src="https://api.securityscorecards.dev/projects/github.com/EfeDurmaz16/sardis/badge" alt="OpenSSF Scorecard"></a>
    <a href="https://discord.gg/XMA9JwDJ"><img src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

---

## What Sardis Is

Sardis is the open-source financial authority layer for AI agents. It sits between an autonomous agent and any system that moves money — so every consequential financial action is checked against a signed mandate, deterministic policy, approval path, revocation state, and audit packet **before** it reaches a wallet, card, stablecoin, payment API, or x402 endpoint.

Sardis is not a card wrapper, a custodial wallet, or a rail-specific payment app. It is rail-agnostic governance: bring your own provider (Stripe, Lithic, Privy, Turnkey, Circle, your bank, x402 servers, your own custom adapter) and Sardis enforces the authority layer above them. The deeper thesis is that agents do not have a payments problem — they have a *trust* problem, and money is the sharpest version of it.

---

## 30-second quickstart

### Python

```bash
pip install sardis
```

```python
from sardis import Sardis

client = Sardis(api_key="sk_live_...")

# Unified pay — auto-routes the cheapest chain
result = client.pay.execute(
    to="0xabc...",       # address, wallet ID, or merchant domain
    amount="25.00",
    currency="USDC",
)
print(result["tx_hash"])
```

### TypeScript

```bash
npm install sardis
```

```ts
import { Sardis } from "sardis";

const sardis = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });

const tx = await sardis.pay({
  from: "wallet_abc",
  to: "merchant_xyz",
  amount: "25.00",
});
```

### MCP (Claude Desktop, Cursor, ChatGPT, Windsurf, VS Code)

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": { "SARDIS_API_KEY": "sk_live_..." }
    }
  }
}
```

Your agent now has a bounded financial surface — 50+ tools for wallets, holds, cards, approvals, policy checks, facility gates, and spending analytics — instead of unconstrained payment access.

---

## Features

|  |  |
| --- | --- |
| **Mandates** — Cryptographically signed authority records (AP2 Intent → Cart → Payment chain) verified before execution. | **Policy firewall** — Deterministic NL-to-policy compilation; per-tx, daily, monthly, vendor, and category limits enforced fail-closed. |
| **Approvals & revocation** — Step-up flows for high-risk actions; kill switch propagates within one decision cycle. | **Provider-neutral adapters** — One contract for cards, stablecoins, fiat APIs, x402, AP2, TAP, and simulator rails. Swap providers without rewriting policy. |
| **Append-only audit ledger** — Ed25519-signed attestation envelopes; every decision is reconstructable, every state transition is durable. | **15+ framework integrations** — LangChain, CrewAI, OpenAI Agents, Claude Agent SDK, Google ADK, Mastra, Vercel AI SDK, LlamaIndex, A2A, MCP — same policy engine under all of them. |

---

## Use cases

- **Autonomous procurement agents** — Bound a CrewAI or LangChain agent to a $500/day SaaS-only budget; every purchase passes the policy firewall, settles through your existing card program, and lands in an audit packet.
- **x402 paid HTTP** — Agents pay for API calls per-request; Sardis enforces the mandate and budget envelope before the 402 challenge is honored.
- **AP2 agentic commerce** — Full Intent → Cart → Payment mandate chain with merchant-side verification; works against any AP2-compatible merchant or your own.
- **Agent-to-agent (A2A) escrow** — Cryptographic mandate handoff between agents with on-chain or simulator escrow; no agent gets paid without delivery evidence.
- **Treasury operations agent** — Programmatic transfers, holds, and FX with human-in-the-loop step-up for anything above policy thresholds.

---

## Architecture

Every financial action follows a single authority path. There is no alternative code path that bypasses policy checks.

```
   AI AGENT  (Claude / Cursor / LangChain / OpenAI / Mastra / ...)
        │
        │  MCP  |  Python SDK  |  TypeScript SDK
        ▼
┌────────────────────────────────────────────────┐
│         FinancialActionOrchestrator            │   single entry point
└────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────┐
│           PreExecutionPipeline                 │
│   • Mandate verification (AP2 / TAP)           │
│   • Policy evaluation (deterministic)          │
│   • Atomic spend tracking                      │
│   • Dedup / idempotency                        │
│   • Compliance gate (KYC / AML)                │
│   • KYA trust scoring                          │
│   Fail-closed: any hook failure blocks the tx  │
└────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────┐
│              PROVIDER ADAPTER                  │
│   Cards / wallets / fiat / x402 / simulator    │
└────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────┐
│           APPEND-ONLY AUDIT LEDGER             │
│        Ed25519-signed attestation envelopes    │
└────────────────────────────────────────────────┘
```

**Design principles:** fail-closed by default · provider-neutral (no custodial lock-in) · audit everything (signed envelopes, not log lines).

---

## Migrating from v1.x

Sardis v2 consolidates 30+ separate `sardis-*` packages into a small surface — one Python package, one TypeScript package, one MCP binary — with submodules and optional extras (the Stripe / OpenAI / Anthropic SDK pattern).

```bash
# Python — old
pip install sardis-core sardis-cli sardis-chain sardis-langchain ...

# Python — new
pip install sardis
pip install sardis[langchain,crewai,openai-agents]
```

```python
# Old (legacy v1 — kept here only as a migration reference)
#   from sardis_v2_core import Wallet
#   from sardis_langchain import SardisToolkit

# New
from sardis import Sardis, AsyncSardis
from sardis.core import Wallet
from sardis.integrations.langchain import SardisToolkit
```

```bash
# TypeScript — codemod legacy imports
npx sardis-migrate
```

Legacy `sardis-*` packages on PyPI and npm remain published; pinned production deployments keep working. See [`packages/sardis/MIGRATION_NOTES.md`](packages/sardis/MIGRATION_NOTES.md) for the full diff.

---

## Sardis vs the alternatives

| | Raw provider integration | Stripe / Coinbase / Lithic SDK | **Sardis** |
| --- | --- | --- | --- |
| Mandate verification | DIY | None | **Built-in (AP2 / TAP)** |
| Deterministic policy firewall | DIY | None | **Built-in, fail-closed** |
| Approval / revocation flows | DIY | None | **Built-in** |
| Provider neutrality | One per integration | Locked to one provider | **Rail-agnostic adapter contract** |
| Append-only signed audit | DIY | Partial | **Built-in, Ed25519** |
| Framework integrations | DIY | DIY | **15+ first-party** |
| Custody | Up to you | Provider holds funds | **Non-custodial; BYO provider** |
| License | — | Proprietary | **MIT (open core)** |

Sardis does not replace your payment provider. It is the authority layer that sits *above* whichever providers you already use.

---

## Maturity

| Feature | Status |
| --- | --- |
| Spending policy engine | **Implemented** |
| AP2 mandate verification | **Implemented** |
| Provider adapter contract | **Implemented** |
| Policy attestation API (Ed25519) | **Implemented** |
| PreExecutionPipeline | **Implemented** |
| Hosted checkout | **Pilot** |
| ERC-8183 agentic job escrow | **Pilot** (1% fee cap, USDC-only) |
| x402 paid HTTP | **Pilot** |
| Card provider adapters | **Pilot** |
| Stablecoin provider adapters | **Pilot** |
| Multi-chain (Polygon, Arbitrum) | **Experimental** |
| UCP MCP transport | **Experimental** |
| FIDES trust graph | **Experimental** |

**Implemented** = code + tests in the public repo. **Pilot** = functional under conservative limits, active hardening. **Experimental** = code exists, not production-tested. See [`docs/packages.md`](docs/packages.md) for the package-level matrix.

---

## Roadmap

Live roadmap: [github.com/EfeDurmaz16/sardis/issues](https://github.com/EfeDurmaz16/sardis/issues?q=label%3Aroadmap).

---

## Open core boundary

| Layer | Open source (this repo) | Hosted / commercial |
| --- | --- | --- |
| Authority model | Mandates, policies, approvals, revocation, audit packets | Same semantics with managed org, RBAC, SSO, retention, support |
| Provider execution | Adapter interfaces, simulator, BYO credentials | Managed credential vault, webhook handling, alerts, routing |
| Developer surface | SDKs, MCP server, examples, protocol adapters | Hosted dashboard, approval inbox, compliance workflows, audit export |

Boundary detail: [`docs/oss/public-private-boundary.md`](docs/oss/public-private-boundary.md).

---

## Documentation

- [Getting started](https://docs.sardis.sh/getting-started) — first payment in 5 minutes
- [API reference](https://docs.sardis.sh/api)
- [MCP server setup](https://docs.sardis.sh/mcp)
- [Policy language](https://docs.sardis.sh/policies) — write spending rules in plain English
- [Framework guides](https://docs.sardis.sh/frameworks) — LangChain, OpenAI, Vercel AI SDK, …
- [Security model](https://docs.sardis.sh/security) — MPC architecture and threat model
- [Examples](https://github.com/EfeDurmaz16/sardis/tree/main/examples)
- [Package maturity matrix](docs/packages.md)
- [Source-tree policy](docs/oss/source-layout.md)
- [Contribution map](docs/oss/contribution-map.md)
- [CI/CD map](docs/oss/ci-cd.md)
- [Development guide](docs/development.md)
- [Security policy](.github/SECURITY.md) · [Code of Conduct](.github/CODE_OF_CONDUCT.md) · [Support](.github/SUPPORT.md)

---

## Contributing

Pull requests welcome. See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md). Quick path:

```bash
git clone https://github.com/EfeDurmaz16/sardis.git
cd sardis
pnpm run doctor && uv sync && pnpm install --frozen-lockfile

# Contributor gate
pnpm run check:contributor

# Start the reference API
uv run uvicorn --app-dir apps/api server.main:create_app --factory --port 8000
```

## Community

- [Discord](https://discord.gg/XMA9JwDJ) — daily questions, design discussion, office hours
- [GitHub Discussions](https://github.com/EfeDurmaz16/sardis/discussions) — long-form threads
- [Manifesto](https://sardis.sh/manifesto) — why this matters

## License

[MIT](LICENSE). See [`docs/oss/public-private-boundary.md`](docs/oss/public-private-boundary.md) for the product boundary between this open-source repo and the hosted Sardis Cloud.

---

<div align="center">
  <sub><strong>Sardis</strong> — Mandates · Policy · Approvals · Revocation · Audit · &copy; 2026 Efe Baran Durmaz</sub>
</div>
