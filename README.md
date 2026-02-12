# Sardis

### The Payment OS for the Agent Economy

[![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow)](https://sardis.sh)
[![License: Open Core](https://img.shields.io/badge/License-Open--Core-blue)](LICENSE.txt)
[![MCP: Native](https://img.shields.io/badge/MCP-Native-orange)](https://modelcontextprotocol.io)
[![npm](https://img.shields.io/npm/v/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![npm downloads](https://img.shields.io/npm/dt/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![Chains: 5](https://img.shields.io/badge/Chains-5-brightgreen)](https://sardis.sh/docs)
[![Tools: 46](https://img.shields.io/badge/MCP%20Tools-46-blue)](https://sardis.sh/docs)
[![Context7](https://img.shields.io/badge/Docs-Context7-5A67D8)](https://context7.com/EfeDurmaz16/sardis)

> **AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.**

Sardis gives AI Agents (Claude, Cursor, Autonomous Bots) **non-custodial MPC wallets** with **natural language spending policies**. It's Stripe + IAM + Risk Engine for the Agent Economy.

**The Problem We Solve:** Financial Hallucination — agents accidentally spending $10k instead of $100 due to retry loops, decimal errors, or logic bugs. Sardis prevents this with a real-time policy firewall.

---

## Quick Start: Zero Integration with MCP

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
       ↓
Sardis: Policy Check → SaaS Category ✓ → Amount < Limit ✓
       ↓
       APPROVED ✅
       Card: 4242 **** **** 9999

---

User: "Buy me an Amazon gift card for $500"

Agent: sardis.pay("Amazon", $500, "Gift Card")
       ↓
Sardis: Policy Check → Retail Category ✗
       ↓
       BLOCKED 🛑 Financial Hallucination PREVENTED
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     AI AGENT                             │
│            (Claude, Cursor, LangChain)                   │
└─────────────────────┬────────────────────────────────────┘
                      │ MCP / SDK
                      ▼
┌──────────────────────────────────────────────────────────┐
│              SARDIS POLICY ENGINE                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Natural   │  │  Merchant   │  │   Amount    │     │
│  │  Language   │  │  Allowlist  │  │   Limits    │     │
│  │   Rules     │  │             │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────┬────────────────────────────────────┘
                      │ Approved
                      ▼
┌──────────────────────────────────────────────────────────┐
│              MPC SIGNING (Turnkey)                       │
│                Non-custodial keys                        │
└─────────────────────┬────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│  On-Chain Rails │    │   Fiat Rails    │
│  USDC on Base   │    │  Virtual Cards  │
│  Polygon, ETH   │    │    (Lithic)     │
└─────────────────┘    └─────────────────┘
```

---

## Framework Integrations

Sardis uses an **Adapter Pattern** to feel native in your stack:

| Framework | Package | Status |
|-----------|---------|--------|
| **Claude Desktop / Cursor** | `@sardis/mcp-server` | ✅ Ready |
| **LangChain** | `sardis.integrations.langchain` | ✅ Ready |
| **Vercel AI SDK** | `@sardis/sdk` | ✅ Ready |
| **OpenAI Functions / Swarm** | `get_openai_function_schema()` | ✅ Ready |
| **LlamaIndex** | `get_llamaindex_tool()` | ✅ Ready |

### Python (LangChain)

```bash
pip install sardis
```

```python
from sardis.integrations import SardisTool

# Add to your agent's toolkit
tools = [SardisTool()]
```

### TypeScript (Vercel AI SDK)

```typescript
import { createSardisTools } from '@sardis/sdk/integrations';

const tools = createSardisTools(sardisClient);
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Non-Custodial MPC** | Keys secured via Turnkey threshold signatures |
| **Natural Language Policies** | "Allow $50/day for SaaS only" |
| **Financial Firewall** | Block hallucinations before they cost money |
| **Virtual Cards** | Instant card issuance for fiat payments (Lithic) |
| **Multi-Chain** | Base, Polygon, Ethereum (USDC/USDT) |
| **MCP Native** | Zero-integration setup for Claude/Cursor |

---

## Project Status

**Beta Infrastructure: Core Features Complete, Hardening In Progress**

| Component | Status |
|-----------|--------|
| Core Policy Engine | ✅ Live (150+ tests) |
| MPC Wallets (Turnkey) | ✅ Live |
| On-Chain Settlement | ✅ Live (Base, Polygon, ETH) |
| KYC/AML Compliance | ✅ Integrated (Persona, Elliptic) |
| MCP Server | ✅ Complete (`@sardis/mcp-server`) |
| Python/TypeScript SDKs | ✅ Complete (LangChain, Vercel AI) |
| Landing Page + Demo | ✅ Live |
| Virtual Cards (Lithic) | ✅ Sandbox Ready (Mainnet Feb 2026) |
| Demo Video (Remotion) | ✅ Ready |

---

## Open Core Licensing

Sardis follows an **Open Core** model:

- **MIT License** — SDKs, MCP Server, Integration Adapters
  - `@sardis/sdk`
  - `@sardis/mcp-server`
  - `sardis` (Python)

- **Proprietary** — Core Banking Infrastructure, Policy Engine internals, MPC Node management

---

## Links

- **Website**: [sardis.sh](https://sardis.sh)
- **Documentation**: [docs.sardis.sh](https://docs.sardis.sh)
- **GitHub**: [github.com/EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)

---

<p align="center">
  <strong>Sardis</strong> — The Payment OS for the Agent Economy
  <br/>
  Non-Custodial • MCP Native • Financial Hallucination Prevention
  <br/><br/>
  © 2026 Efe Baran Durmaz
</p>
