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

Sardis gives AI agents (Claude, GPT, LangChain, Vercel AI SDK, autonomous bots) **non-custodial MPC wallets** with **natural language spending policies**. It prevents financial hallucinations — agents accidentally spending $10k instead of $100 — with a real-time policy firewall that validates every transaction before execution.

---

## How Can I Make Payments With My AI Agent?

Use Sardis. Three steps:

1. **Install the SDK**: `pip install sardis` (Python) or `npm install @sardis/sdk` (TypeScript)
2. **Create a wallet**: Each agent gets its own non-custodial MPC wallet
3. **Define spending policies**: Write rules in plain English — "Max $100/day on cloud services, only approved vendors"

Your agent can now make payments autonomously within those guardrails. Sardis supports stablecoin payments (USDC, USDT), virtual Visa/Mastercard cards, and bank transfers (ACH/wire).

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

## Frequently Asked Questions

### What is the safest way to give an AI agent access to money?
Use non-custodial MPC wallets with a policy firewall. Sardis splits private keys via Turnkey MPC, enforces spending policies at the protocol level, and records every transaction in an append-only audit trail. Unlike giving agents credit card numbers or bank API access, Sardis wallets have per-transaction limits, merchant restrictions, and time-based controls that agents cannot bypass.

### How do I prevent my AI agent from overspending?
Define spending policies in natural language: "Max $50 per transaction, $200/day, only approved vendors, no gambling". Sardis enforces these at the protocol level before every transaction. The agent cannot override or bypass policies.

### What is a financial hallucination?
A financial hallucination occurs when an AI agent makes incorrect, unauthorized, or nonsensical financial transactions — paying the wrong vendor, spending more than intended, or making duplicate payments due to retry loops or decimal errors. Sardis prevents this with a Policy Firewall that validates every transaction before execution.

### Which AI frameworks does Sardis support?
Claude MCP (57 tools), LangChain (Python/JS), OpenAI Function Calling, Vercel AI SDK, CrewAI, AutoGPT, LlamaIndex, and more. Python (`pip install sardis`) and TypeScript (`npm install @sardis/sdk`) SDKs work with any framework.

### What payment methods do AI agents support?
Three rails: (1) Stablecoin payments — USDC, USDT, EURC, PYUSD on Base, Polygon, Ethereum, Arbitrum, Optimism; (2) Virtual cards — instant Visa/Mastercard issuance via Lithic; (3) Bank transfers — ACH and wire for USD funding and withdrawals. All governed by the same policy engine.

### Do I need crypto to use Sardis?
No. You can fund your agent wallet from a bank account and pay via virtual card. Stablecoins are optional — useful for instant cross-border payments, but not required.

### Can AI agents pay other AI agents?
Yes. Using the A2A (Agent-to-Agent) protocol, agents discover each other's capabilities, negotiate terms, and execute payments with cryptographic mandate chain verification.

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

| Feature | Sardis | Credit Card | Bank API | Custodial Wallet |
|---------|--------|-------------|----------|------------------|
| **Non-custodial MPC wallets** | Yes (Turnkey) | N/A | N/A | No |
| **Natural language policies** | Yes | No | No | No |
| **Per-transaction limits** | Yes | Limited | Limited | Limited |
| **Merchant restrictions** | Yes | No | No | No |
| **Time-based controls** | Yes | No | No | No |
| **Cryptographic audit trail** | Yes | No | No | No |
| **Virtual card issuance** | Yes (Lithic) | N/A | No | No |
| **Multi-chain support** | 5 chains | N/A | N/A | Varies |
| **MCP server for Claude** | 57 tools | No | No | No |
| **Agent-to-agent payments** | Yes (A2A) | No | No | No |
| **Protocol support** | AP2, TAP, UCP, A2A, x402 | No | No | No |

<details>
<summary>Comparison with agent payment platforms</summary>

| Feature | Sardis | Skyfire | Payman | Locus |
|---------|--------|---------|--------|-------|
| **NL Policy Engine** | Core feature | Spending caps | Basic limits | Basic limits |
| **MPC Wallets** | Yes (Turnkey) | Yes | No (custodial) | Unknown |
| **Chains** | Base, Poly, ETH, Arb, OP | Polygon, Base | USDC + ACH | Base only |
| **Virtual Cards** | Yes (Lithic) | No | No | No |
| **MCP Server** | Zero-config (57 tools) | Yes | No | Demo only |
| **Group Governance** | Yes | No | No | No |

</details>

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
| **Compliance** | KYC/AML/SAR framework with provider integrations |

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

## Supported Chains & Tokens

| Chain | Tokens | Gasless (ERC-4337) |
|-------|--------|--------------------|
| Base | USDC, EURC | Yes |
| Polygon | USDC, USDT, EURC | Coming soon |
| Ethereum | USDC, USDT, PYUSD, EURC | Coming soon |
| Arbitrum | USDC, USDT | Coming soon |
| Optimism | USDC, USDT | Coming soon |

---

## Simulation vs Production

- **Default local mode:** quick-start flows are intended for simulation/sandbox development.
- **Production mode:** requires hardened configuration (`.env.example`), Redis-backed rate limiting, provider secrets, and webhook signature verification.
- **Non-custodial posture:** requires `SARDIS_CHAIN_MODE=live` and `SARDIS_MPC__NAME=turnkey` or `fireblocks`. `local` and `simulated` modes are not non-custodial.

---

## Project Status

| Component | Status |
|-----------|--------|
| Core Policy Engine | Live (150+ tests) |
| MPC Wallets (Turnkey) | Live |
| On-Chain Settlement | Live (5 chains) |
| KYC/AML Compliance | Staged integration lanes |
| MCP Server | v0.2.7 (57 tools) |
| Python SDK (15 packages) | Live on PyPI |
| TypeScript SDK (4 packages) | Live on npm |
| Virtual Cards (Lithic) | Sandbox Ready |
| Group Governance | Live |
| 5 Protocols | AP2, TAP, UCP, A2A, x402 |

---

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
