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
[![Tools: 52](https://img.shields.io/badge/MCP%20Tools-52-blue)](https://sardis.sh/docs)
[![Discord](https://img.shields.io/badge/Discord-sardishq-5865F2?logo=discord&logoColor=white)](https://discord.gg/XMA9JwDJ)
[![Context7](https://img.shields.io/badge/Docs-Context7-5A67D8)](https://context7.com/efedurmaz16/sardis)

> **AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.**

Sardis gives AI Agents (Claude, Cursor, Autonomous Bots) **non-custodial MPC wallets** with **natural language spending policies**. It's Stripe + IAM + Risk Engine for the Agent Economy.

**The Problem We Solve:** Financial Hallucination — agents accidentally spending $10k instead of $100 due to retry loops, decimal errors, or logic bugs. Sardis prevents this with a real-time policy firewall.

---

## What's New (Snapshot: 2026-02-13)

- **Group Governance** — Shared budgets across multi-agent teams with per-agent limits
- **MCP Tooling** — `52` tools with definition/handler parity checks in CI/release scripts
- **Protocol Surface** — AP2, TAP, UCP, A2A, x402 modules present and wired in package exports
- **SDK + Docs Contract Tests** — Quick-start/examples now have smoke tests against real SDK methods
- **Security Hardening** — production fail-closed checks for webhook signatures, CORS, and Redis-backed rate limiting

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
    chain="base_sepolia",
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

| Capability | Sardis Approach | Verifiable In-Repo Evidence |
|---------|--------|-------|
| **Policy-First Payments** | Natural language + structured spending policy enforcement before execution | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` |
| **Agent-Native Access** | MCP server + Python/TypeScript SDKs for agent frameworks | `packages/sardis-mcp-server/src/tools/index.ts`, `packages/sardis-sdk-python`, `packages/sardis-sdk-js` |
| **Execution Rails** | On-chain settlement + fiat rails (cards / ramp connectors) behind policy checks | `packages/sardis-chain`, `packages/sardis-cards`, `packages/sardis-ramp`, `packages/sardis-checkout` |
| **Governance + Controls** | Group budgets, holds/approvals, replay protection, and audit-oriented ledger flows | `packages/sardis-api/src/sardis_api/routers/groups.py`, `packages/sardis-api/src/sardis_api/routers/holds.py`, `packages/sardis-ledger` |
| **Claim Verification** | Launch-facing counts validated via repeatable scripts | `scripts/release/readiness_check.sh`, `docs/audits/claims-evidence.md` |

> **Positioning TL;DR:** Sardis is designed as a policy and control plane for AI-agent payments, not only a wallet API or only a payment rail.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Non-Custodial MPC** | Keys secured via Turnkey threshold signatures |
| **Natural Language Policies** | "Allow $50/day for SaaS only" |
| **Financial Firewall** | Block hallucinations before they cost money |
| **Group Governance** | Shared budgets across multi-agent teams |
| **Virtual Cards** | Instant card issuance for fiat payments (Lithic) |
| **Multi-Chain** | Base, Polygon, Ethereum, Arbitrum, Optimism |
| **5 Protocols** | AP2, TAP, UCP, A2A, x402 |
| **MCP Native** | Zero-integration setup for Claude/Cursor |
| **Compliance** | KYC (Persona), AML (Elliptic), SAR reporting |

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
| [`@sardis/mcp-server`](https://www.npmjs.com/package/@sardis/mcp-server) | MCP server (52 tools) |
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
| KYC/AML Compliance | Integrated (Persona, Elliptic) |
| MCP Server | v0.2.7 (52 tools) |
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
