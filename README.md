# Sardis

### The Payment OS for the Agent Economy

[![GitHub stars](https://img.shields.io/github/stars/EfeDurmaz16/sardis?style=social)](https://github.com/EfeDurmaz16/sardis)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow)](https://sardis.sh)
[![License: Open Core](https://img.shields.io/badge/License-Open--Core-blue)](LICENSE.txt)
[![CI](https://img.shields.io/github/actions/workflow/status/EfeDurmaz16/sardis/ci.yml?label=CI)](https://github.com/EfeDurmaz16/sardis/actions)
[![MCP: Native](https://img.shields.io/badge/MCP-Native-orange)](https://modelcontextprotocol.io)
[![npm](https://img.shields.io/npm/v/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![npm downloads](https://img.shields.io/npm/dw/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![PyPI](https://img.shields.io/pypi/v/sardis)](https://pypi.org/project/sardis/)
[![PyPI Downloads](https://img.shields.io/pypi/dw/sardis)](https://pypi.org/project/sardis/)
[![Chains: 5](https://img.shields.io/badge/Chains-5-brightgreen)](https://sardis.sh/docs)
[![Tools: 57](https://img.shields.io/badge/MCP%20Tools-57-blue)](https://sardis.sh/docs)
[![Discord](https://img.shields.io/badge/Discord-sardishq-5865F2?logo=discord&logoColor=white)](https://discord.gg/XMA9JwDJ)
[![Context7](https://img.shields.io/badge/Docs-Context7-5A67D8)](https://context7.com/efedurmaz16/sardis)

> **AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.**

Sardis gives AI Agents (Claude, Cursor, Autonomous Bots) **policy-controlled wallets** with **natural language spending policies**. In live MPC mode (Turnkey/Fireblocks), wallets are non-custodial.

**The Problem We Solve:** Financial Hallucination — agents accidentally spending $10k instead of $100 due to retry loops, decimal errors, or logic bugs. Sardis prevents this with a real-time policy firewall.

---

## What's New (Snapshot: 2026-02-15)

- **Group Governance** — Shared budgets across multi-agent teams with per-agent limits
- **57 MCP Tools** — Wallet management, payments, policies, virtual cards, ledger, groups (with CI parity checks)
- **ERC-4337 Base Preview** — `account_type=erc4337_v2` + fail-closed UserOperation runtime path (feature-flagged, Base Sepolia lane)
- **5 Protocols** — AP2, TAP, UCP, A2A, x402 fully implemented and wired in package exports
- **Virtual Cards** — Agents can pay anywhere Visa is accepted (Lithic)
- **Security Hardening** — Production fail-closed checks for webhook signatures, CORS, and Redis-backed rate limiting
- **Framework Examples** — OpenAI, LangChain, Vercel AI SDK, CrewAI integrations

---

## Quick Start

### Python

```bash
pip install sardis
```

```python
from decimal import Decimal
from sardis import SardisClient

client = SardisClient(api_key="sk_...")
agent = client.agents.create(name="my-agent", description="Procurement bot")
wallet = client.wallets.create(
    agent_id=agent.agent_id,
    currency="USDC",
    limit_per_tx=Decimal("100.00"),
)
tx = client.wallets.transfer(
    wallet.wallet_id,
    destination="0x...",
    amount=Decimal("25.00"),
    token="USDC",
    chain="base_sepolia",
    domain="openai.com",
)
```

### TypeScript

```bash
npm install @sardis/sdk
```

```typescript
import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'sk_...' });
const agent = await client.agents.create({ name: 'my-agent' });
const wallet = await client.wallets.create({
  agent_id: agent.agent_id,
  currency: 'USDC',
  limit_per_tx: '100.00',
});
const tx = await client.wallets.transfer(wallet.wallet_id, {
  destination: '0x...',
  amount: '25.00',
  token: 'USDC',
  chain: 'base_sepolia',
  domain: 'openai.com',
});
```

### MCP (Claude Desktop / Cursor)

```bash
npx @sardis/mcp-server start
```

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}
```

**That's it.** Your agent now has a wallet with spending limits.

### Simulation vs Production

- **Default local mode:** quick-start flows are intended for simulation/sandbox development.
- **Production mode:** requires hardened configuration (`.env.example`), Redis-backed rate limiting, provider secrets, and webhook signature verification.
- **Non-custodial posture:** requires `SARDIS_CHAIN_MODE=live` and `SARDIS_MPC__NAME=turnkey` or `fireblocks`. `local` and `simulated` modes are not non-custodial.
- **Proof commands:** run `bash scripts/release/readiness_check.sh` and `bash scripts/release/critical_path_check.sh` before production rollouts.

### Stablecoin vs Fiat Rails

- **Stablecoin rail:** wallet signing and on-chain settlement path. In live MPC mode, this is where Sardis can be operated with a non-custodial posture.
- **Fiat/card rails:** settlement is executed by regulated partners/issuers (for example Bridge and Lithic). These flows are policy-governed by Sardis, but custody/settlement is partner-mediated.
- **Design-partner note:** ERC-4337 gas sponsorship is currently a Base Sepolia feature-flagged lane until full chain-by-chain proof artifacts are published.

---

## How It Works

```
User: "Buy OpenAI API credits for $20"

Agent: sardis.pay("OpenAI", $20, "API Credits")
       |
Sardis: Policy Check -> SaaS Category OK -> Amount < Limit OK
       |
       APPROVED
       Card: 4242 **** **** 9999

---

User: "Buy me an Amazon gift card for $500"

Agent: sardis.pay("Amazon", $500, "Gift Card")
       |
Sardis: Policy Check -> Retail Category BLOCKED
       |
       BLOCKED - Financial Hallucination PREVENTED
```

---

## Architecture

```
                         AI AGENT
              (Claude, Cursor, LangChain)
                          |
                     MCP / SDK
                          |
                  SARDIS POLICY ENGINE
         Natural Language | Merchant    | Amount
         Rules            | Allowlist   | Limits
                          |
                     MPC SIGNING (Turnkey)
                    Non-custodial keys
                          |
               +----------+----------+
               |                     |
         On-Chain Rails         Fiat Rails
         USDC on Base          Virtual Cards
         Polygon, ETH           (Lithic)
```

---

## Why Sardis?

| Feature | Sardis | Skyfire | Payman | Locus |
|---------|--------|---------|--------|-------|
| **NL Policy Engine** | Core feature | Spending caps | Basic limits | Basic limits |
| **MPC Wallets** | Yes (Turnkey) | Yes | No (custodial) | Unknown |
| **Chains** | Base, Poly, ETH, Arb, OP | Polygon, Base | USDC + ACH | Base only |
| **Virtual Cards** | Yes (Lithic) | No | No | No |
| **MCP Server** | Zero-config (57 tools) | Yes | No | Demo only |
| **Group Governance** | Yes | No | No | No |

<details>
<summary>Verifiable In-Repo Evidence</summary>

| Capability | Sardis Approach | Evidence |
|---------|--------|-------|
| **Policy-First Payments** | NL + structured spending policy enforcement before execution | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` |
| **Agent-Native Access** | MCP server + Python/TS SDKs for agent frameworks | `packages/sardis-mcp-server/src/tools/index.ts`, `packages/sardis-sdk-python`, `packages/sardis-sdk-js` |
| **Execution Rails** | On-chain settlement + fiat rails behind policy checks | `packages/sardis-chain`, `packages/sardis-cards`, `packages/sardis-ramp` |
| **Governance + Controls** | Group budgets, holds/approvals, replay protection, audit ledger | `packages/sardis-api/src/sardis_api/routers/groups.py`, `packages/sardis-ledger` |
| **Claim Verification** | Launch-facing counts validated via repeatable scripts | `scripts/release/readiness_check.sh`, `docs/audits/claims-evidence.md` |

</details>

> **Positioning TL;DR:** Sardis is designed as a policy and control plane for AI-agent payments, not only a wallet API or only a payment rail.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Non-Custodial MPC** | Available in live mode with Turnkey/Fireblocks |
| **Natural Language Policies** | "Allow $50/day for SaaS only" |
| **Financial Firewall** | Block hallucinations before they cost money |
| **Group Governance** | Shared budgets across multi-agent teams |
| **Virtual Cards** | Instant card issuance for fiat payments (Lithic) |
| **Multi-Chain** | Base, Polygon, Ethereum, Arbitrum, Optimism |
| **5 Protocols** | AP2, TAP, UCP, A2A, x402 |
| **MCP Native** | Zero-integration setup for Claude/Cursor |
| **Compliance** | KYC/AML/SAR framework with provider integrations and staged onboarding lanes |

---

## Packages

### Python (PyPI)

| Package | Description |
|---------|-------------|
| [`sardis`](https://pypi.org/project/sardis/) | Meta-package — installs SDK + Core + CLI |
| `sardis-sdk` | Production Python SDK |
| `sardis-core` | Domain models and config |
| `sardis-chain` | Multi-chain execution |
| `sardis-compliance` | KYC/AML/SAR |
| `sardis-cards` | Virtual cards (Lithic) |
| `sardis-wallet` | Wallet orchestration |
| `sardis-ledger` | Append-only audit trail |
| `sardis-api` | FastAPI gateway |
| `sardis-protocol` | AP2/TAP verification |
| `sardis-a2a` | Agent-to-Agent protocol |
| `sardis-ucp` | Universal Commerce Protocol |
| `sardis-ramp` | Fiat on/off-ramp |
| `sardis-cli` | Command-line interface |
| `sardis-checkout` | Merchant checkout flows |

```bash
pip install sardis          # SDK + Core + CLI
pip install sardis[all]     # Everything
pip install sardis[cards]   # + virtual cards
```

### TypeScript (npm)

| Package | Description |
|---------|-------------|
| [`@sardis/sdk`](https://www.npmjs.com/package/@sardis/sdk) | TypeScript SDK |
| [`@sardis/mcp-server`](https://www.npmjs.com/package/@sardis/mcp-server) | MCP server (57 tools) |
| [`@sardis/ai-sdk`](https://www.npmjs.com/package/@sardis/ai-sdk) | Vercel AI SDK integration |
| [`@sardis/ramp`](https://www.npmjs.com/package/@sardis/ramp) | Fiat on/off-ramp |

---

## Framework Integrations

| Framework | Package | Status | Example |
|-----------|---------|--------|---------|
| **Claude Desktop / Cursor** | `@sardis/mcp-server` | Stable | — |
| **OpenAI Functions / Swarm** | `sardis-sdk` | Stable | [`openai_agents_payment.py`](examples/openai_agents_payment.py) |
| **LangChain** | `sardis-sdk` | Stable | [`langchain_sardis_agent.py`](examples/langchain_sardis_agent.py) |
| **Vercel AI SDK** | `@sardis/ai-sdk` | Stable | [`vercel_ai_payment.ts`](examples/vercel_ai_payment.ts) |
| **CrewAI** | `sardis-sdk` | Beta | [`crewai_finance_team.py`](examples/crewai_finance_team.py) |
| **LlamaIndex** | `sardis-sdk` | Beta | — |
| **Mastra** | `@sardis/sdk` | Beta | — |

---

## Project Status

| Component | Status |
|-----------|--------|
| Core Policy Engine | Live (150+ tests) |
| MPC Wallets (Turnkey) | Live |
| On-Chain Settlement | Live (5 chains) |
| KYC/AML Compliance | Staged integration lanes (Persona/Elliptic onboarding in progress) |
| MCP Server | v0.2.7 (57 tools) |
| Python SDK (15 packages) | Live on PyPI |
| TypeScript SDK (4 packages) | Live on npm |
| Virtual Cards (Lithic) | Sandbox Ready |
| Group Governance | Live |
| 5 Protocols | AP2, TAP, UCP, A2A, x402 |

---

<!-- Built with / Trusted by — uncomment and populate after launch
## Trusted By

<p align="center">
  <img src="https://sardis.sh/logos/company1.svg" height="32" alt="Company 1" />&nbsp;&nbsp;&nbsp;
  <img src="https://sardis.sh/logos/company2.svg" height="32" alt="Company 2" />&nbsp;&nbsp;&nbsp;
  <img src="https://sardis.sh/logos/company3.svg" height="32" alt="Company 3" />
</p>

---
-->

## Open Core Licensing

- **MIT License** — SDKs, MCP Server, Integration Adapters
  - `sardis` (Python meta-package)
  - `@sardis/sdk`, `@sardis/mcp-server`, `@sardis/ai-sdk`

- **Proprietary** — Core Banking Infrastructure, Policy Engine internals, MPC Node management

---

## Links

- **Website**: [sardis.sh](https://sardis.sh)
- **Documentation**: [sardis.sh/docs](https://sardis.sh/docs)
- **GitHub**: [github.com/EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)
- **Discord**: [discord.gg/XMA9JwDJ](https://discord.gg/XMA9JwDJ)
- **PyPI**: [pypi.org/project/sardis](https://pypi.org/project/sardis/)
- **npm**: [npmjs.com/package/@sardis/mcp-server](https://www.npmjs.com/package/@sardis/mcp-server)
- **Context7**: [context7.com/efedurmaz16/sardis](https://context7.com/efedurmaz16/sardis)

---

<p align="center">
  <strong>Sardis</strong> — The Payment OS for the Agent Economy
  <br/>
  Non-Custodial | MCP Native | Financial Hallucination Prevention
  <br/><br/>
  &copy; 2026 Efe Baran Durmaz
</p>
