# Sardis

### The Payment OS for the Agent Economy

[![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow)](https://sardis.sh)
[![License: Open Core](https://img.shields.io/badge/License-Open--Core-blue)](LICENSE.txt)
[![MCP: Native](https://img.shields.io/badge/MCP-Native-orange)](https://modelcontextprotocol.io)
[![npm](https://img.shields.io/npm/v/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![npm downloads](https://img.shields.io/npm/dt/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![PyPI](https://img.shields.io/pypi/v/sardis)](https://pypi.org/project/sardis/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/sardis)](https://pypi.org/project/sardis/)
[![Chains: 5](https://img.shields.io/badge/Chains-5-brightgreen)](https://sardis.sh/docs)
[![Tools: 46](https://img.shields.io/badge/MCP%20Tools-46-blue)](https://sardis.sh/docs)
[![Context7](https://img.shields.io/badge/Docs-Context7-5A67D8)](https://context7.com/efedurmaz16/sardis)

> **AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.**

Sardis gives AI Agents (Claude, Cursor, Autonomous Bots) **non-custodial MPC wallets** with **natural language spending policies**. It's Stripe + IAM + Risk Engine for the Agent Economy.

**The Problem We Solve:** Financial Hallucination — agents accidentally spending $10k instead of $100 due to retry loops, decimal errors, or logic bugs. Sardis prevents this with a real-time policy firewall.

---

## Quick Start

### Python

```bash
pip install sardis
```

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")
wallet = client.wallets.create(name="my-agent", chain="base", policy="Max $100/day")
tx = wallet.pay(to="0x...", amount="25.00", token="USDC")
```

### TypeScript

```bash
npm install @sardis/sdk
```

```typescript
import { Sardis } from '@sardis/sdk';

const client = new Sardis({ apiKey: 'sk_...' });
const wallet = await client.wallets.create({ name: 'my-agent', chain: 'base' });
const tx = await wallet.pay({ to: '0x...', amount: '25.00', token: 'USDC' });
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
| [`@sardis/mcp-server`](https://www.npmjs.com/package/@sardis/mcp-server) | MCP server (46 tools) |
| [`@sardis/ai-sdk`](https://www.npmjs.com/package/@sardis/ai-sdk) | Vercel AI SDK integration |
| [`@sardis/ramp`](https://www.npmjs.com/package/@sardis/ramp) | Fiat on/off-ramp |

---

## Framework Integrations

| Framework | Package | Status |
|-----------|---------|--------|
| **Claude Desktop / Cursor** | `@sardis/mcp-server` | Stable |
| **LangChain** | `sardis-sdk` | Stable |
| **Vercel AI SDK** | `@sardis/ai-sdk` | Stable |
| **OpenAI Functions / Swarm** | `sardis-sdk` | Stable |
| **LlamaIndex** | `sardis-sdk` | Beta |
| **CrewAI** | `sardis-sdk` | Beta |
| **Mastra** | `@sardis/sdk` | Beta |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Non-Custodial MPC** | Keys secured via Turnkey threshold signatures |
| **Natural Language Policies** | "Allow $50/day for SaaS only" |
| **Financial Firewall** | Block hallucinations before they cost money |
| **Virtual Cards** | Instant card issuance for fiat payments (Lithic) |
| **Multi-Chain** | Base, Polygon, Ethereum, Arbitrum, Optimism |
| **5 Protocols** | AP2, TAP, UCP, A2A, x402 |
| **MCP Native** | Zero-integration setup for Claude/Cursor |
| **Compliance** | KYC (Persona), AML (Elliptic), SAR reporting |

---

## Project Status

| Component | Status |
|-----------|--------|
| Core Policy Engine | Live (150+ tests) |
| MPC Wallets (Turnkey) | Live |
| On-Chain Settlement | Live (5 chains) |
| KYC/AML Compliance | Integrated (Persona, Elliptic) |
| MCP Server | v0.2.5 (46 tools) |
| Python SDK (15 packages) | Live on PyPI |
| TypeScript SDK (4 packages) | Live on npm |
| Virtual Cards (Lithic) | Sandbox Ready |
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
