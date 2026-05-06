<div align="center">
  <h1>Sardis</h1>
  <p><strong>Open-source financial authority layer for AI agents</strong></p>
  <p>Sardis lets agents transact only through signed mandates, deterministic policy checks, approval paths, revocation, and audit evidence before any wallet, card, stablecoin, payment API, or provider rail is used.</p>

  <p>
    <a href="https://sardis.sh">Website</a> ·
    <a href="https://sardis.sh/manifesto">Manifesto</a> ·
    <a href="https://sardis.sh/docs">Docs</a> ·
    <a href="https://sardis.sh/playground">Playground</a> ·
    <a href="https://sardis.sh/enterprise">Enterprise</a>
  </p>

  <p>
    <a href="https://www.npmjs.com/package/@sardis/mcp-server"><img src="https://img.shields.io/npm/v/@sardis/mcp-server?label=npm%20%40sardis%2Fmcp-server" alt="npm version"></a>
    <a href="https://pypi.org/project/sardis/"><img src="https://img.shields.io/pypi/v/sardis?label=PyPI%20sardis" alt="PyPI version"></a>
    <a href="LICENSE.txt"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
    <a href="https://github.com/EfeDurmaz16/sardis/stargazers"><img src="https://img.shields.io/github/stars/EfeDurmaz16/sardis?style=social" alt="GitHub stars"></a>
    <a href="https://github.com/EfeDurmaz16/sardis/commits/main"><img src="https://img.shields.io/github/last-commit/EfeDurmaz16/sardis" alt="Last commit"></a>
    <a href="https://securityscorecards.dev/viewer/?uri=github.com/EfeDurmaz16/sardis"><img src="https://api.securityscorecards.dev/projects/github.com/EfeDurmaz16/sardis/badge" alt="OpenSSF Scorecard"></a>
    <a href="https://discord.gg/XMA9JwDJ"><img src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

---

## 📦 Quick Install

```bash
# MCP Server (Claude, Cursor, ChatGPT)
npx @sardis/mcp-server start

# Python SDK
pip install sardis

# TypeScript SDK
npm install @sardis/sdk

# LangChain
pip install sardis  # Uses sardis-sdk under the hood

# CrewAI
pip install sardis  # Compatible with CrewAI tools

# OpenAI Functions
pip install sardis  # Use with OpenAI function calling

# Gemini / ADK
pip install sardis  # Compatible with Google AI SDKs

# Vercel AI SDK
npm install @sardis/ai-sdk
```

---

## 🤔 What is Sardis?

Sardis is the open-source financial authority layer for AI agents. It sits between autonomous agents and money-moving systems so every consequential financial action is checked against a mandate, policy decision, approval path, revocation path, and audit packet before execution.

Sardis is not a card wrapper, prepaid wallet, or rail-specific payment app. It governs the authority to spend across stablecoin wallets, card programs, fiat payment APIs, x402-style HTTP payments, AP2/TAP mandates, provider-hosted wallets, and simulator rails.

The core primitive is verifiable authority before an agent can spend, subscribe, purchase, refund, settle, or trigger paid usage. Customers can bring their own providers; Sardis enforces the authority layer above them without needing to custody funds or become the merchant of record.

The deeper thesis is that agents do not just have a capability problem; they have a trust problem. Sardis treats money as the sharpest version of a broader substrate problem: how non-human actors perform consequential actions with explicit authority, reviewable state transitions, and durable evidence.

---

## Protocol & Feature Maturity

| Feature | Status | Description |
|---------|--------|-------------|
| Spending Policy Engine | **Production** | Deterministic NL-to-policy, atomic spend tracking |
| AP2 Mandate Verification | **Production** | Full mandate chain verification with evidence |
| USDC Payments (Base) | **Production** | Non-custodial MPC wallet execution |
| Policy Attestation API | **Production** | Signed attestation envelopes with Ed25519 |
| PreExecutionPipeline | **Production** | Composable hook chain with fail-closed defaults |
| Hosted Checkout | **Pilot** | Merchant checkout flows with session security |
| ERC-8183 Agentic Jobs | **Pilot** | On-chain job escrow (conservative caps: 1% fee, USDC-only) |
| x402 Protocol | **Pilot** | HTTP-native micropayments |
| Virtual Cards (Stripe Issuing) | **Pilot** | Agent-controlled virtual card issuance |
| Multi-chain (Polygon, Arbitrum) | **Experimental** | Chain routing implemented, not production-tested |
| UCP MCP Transport | **Experimental** | Partial implementation |
| FIDES Trust Graph | **Experimental** | DID-based trust federation |

> **Status key:** **Production** = deployed, tested, load-bearing. **Pilot** = functional with design partners, conservative limits. **Experimental** = code exists, not production-tested.

---

## Key Features

- **Non-custodial MPC wallets** -- Turnkey integration, zero private key exposure
- **Natural language spending policies** -- "Max $50/tx, $200/day, SaaS vendors only"
- **Financial hallucination prevention** -- Policy firewall blocks invalid transactions
- **15+ AI framework integrations** -- LangChain, CrewAI, OpenAI Agents, Claude SDK, Google ADK, A2A, AgentKit, Vercel AI SDK, MCP, and more
- **Virtual cards (Pilot)** -- Stripe Issuing for agent-controlled fiat payments
- **Agent-to-agent escrow** -- Cryptographic mandate chain for A2A payments
- **KYA (Know Your Agent)** -- Trust scoring and behavioral anomaly detection
- **Base + Tempo (production)** -- Multi-chain settlement via CCTP v2, live on Tempo mainnet since March 2026
- **Double-entry audit ledger** -- Append-only transaction history with cryptographic proofs
- **Protocol support** -- AP2 and TAP (production), x402 (pilot), UCP and A2A (partial)

---

## 🚀 Quick Start

### Python (5 lines)

```python
from sardis import Sardis

sardis = Sardis(api_key="sk_...")
result = sardis.payments.create(
    agent_id="agent_abc",
    amount="50.00",
    token="USDC",
    recipient="merchant@example.com"
)
print(f"Payment: {result.tx_hash}")
```

### TypeScript

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

## 🎯 Framework Integrations

| Framework | Package | Install |
|-----------|---------|---------|
| **MCP** (Claude, Cursor, ChatGPT) | `@sardis/mcp-server` | `npx @sardis/mcp-server start` |
| **LangChain** | `sardis` | `pip install sardis` |
| **CrewAI** | `sardis` | `pip install sardis` |
| **OpenAI Functions** | `sardis` | `pip install sardis` |
| **Gemini / ADK** | `sardis` | `pip install sardis` |
| **Vercel AI SDK** | `@sardis/ai-sdk` | `npm install @sardis/ai-sdk` |
| **Claude Agent SDK** | `sardis` | `pip install sardis` |
| **LlamaIndex** | `sardis` | `pip install sardis` |
| **Mastra** | `@sardis/sdk` | `npm install @sardis/sdk` |

All frameworks use the same policy engine and MPC wallet infrastructure.

---

## Architecture

Every payment follows a **single execution path** through the `PaymentOrchestrator`. There are no alternative code paths that bypass policy checks.

```
                         AI AGENT
              (Claude, Cursor, LangChain, OpenAI)
                          |
                     MCP / SDK
                          |
            ┌─────────────┴─────────────┐
            │    PaymentOrchestrator     │
            │    (single entry point)    │
            └─────────────┬─────────────┘
                          |
            ┌─────────────┴─────────────┐
            │   PreExecutionPipeline    │
            │                           │
            │  Composable hooks:        │
            │  - Policy evaluation      │
            │  - Spend tracking         │
            │  - Dedup check            │
            │  - Compliance gate        │
            │  - KYA trust scoring      │
            │                           │
            │  Fail-closed: any hook    │
            │  failure blocks the tx    │
            └─────────────┬─────────────┘
                          |
            ┌─────────────┴─────────────┐
            │   MPC SIGNING (Turnkey)   │
            │   Non-custodial keys      │
            └─────────────┬─────────────┘
                          |
               +──────────┴──────────+
               |                     |
         On-Chain Rails         Fiat Rails
         USDC on Base          Virtual Cards
         (+ CCTP v2 funding)   (Stripe Issuing)
               |                     |
         ┌─────┴─────┐         ┌────┴────┐
         │  LEDGER   │         │  LEDGER │
         │  Append   │         │  Append │
         │  Only     │         │  Only   │
         └───────────┘         └─────────┘
```

**Key design principles:**
- **Fail-closed** -- Default deny on all policy, compliance, and security checks
- **Non-custodial** -- Private keys never stored; MPC signing via Turnkey
- **Audit everything** -- Append-only ledger with signed attestation envelopes for every decision

---

## 📂 Repository Structure

```
sardis/
├── packages/               # Core monorepo packages
│   ├── sardis-core/        # Domain models, config, database
│   ├── sardis-api/         # FastAPI REST endpoints
│   ├── sardis-chain/       # Blockchain execution, chain routing
│   ├── sardis-protocol/    # AP2/TAP protocol verification
│   ├── sardis-wallet/      # Wallet management, MPC
│   ├── sardis-ledger/      # Append-only audit trail
│   ├── sardis-compliance/  # KYC (iDenfy) + AML (Elliptic)
│   ├── sardis-cards/       # Virtual cards (Stripe Issuing)
│   ├── sardis-mcp-server/  # MCP server for Claude/Cursor
│   ├── sardis-sdk-python/  # Full Python SDK
│   ├── sardis-sdk-js/      # TypeScript SDK
│   ├── sardis-cli/         # Command-line tool
│   └── sardis-checkout/    # Merchant checkout flows
├── sardis/                 # Simple Python SDK (public interface)
├── contracts/              # Solidity smart contracts
│   └── src/
│       ├── SardisWalletFactory.sol
│       ├── SardisAgentWallet.sol
│       └── SardisEscrow.sol
├── dashboard/              # React admin dashboard
├── landing/                # Marketing website
├── mobile/                 # React Native companion app
├── playground/             # Interactive demo sandbox
├── examples/               # Usage examples
├── demos/                  # Demo applications
├── docs/                   # Documentation
│   └── marketing/          # GTM content and strategies
└── tests/                  # Integration tests
```

---

## 📚 Documentation

- **[Getting Started Guide](https://sardis.sh/docs/getting-started)** — First payment in 5 minutes
- **[API Reference](https://sardis.sh/docs/api)** — Complete endpoint documentation
- **[MCP Server Setup](https://sardis.sh/docs/mcp)** — Claude Desktop integration
- **[Policy Language](https://sardis.sh/docs/policies)** — Write spending rules in plain English
- **[Chain Support](https://sardis.sh/docs/chains)** — Supported networks and tokens
- **[Framework Guides](https://sardis.sh/docs/frameworks)** — LangChain, OpenAI, Vercel AI SDK
- **[Security Model](https://sardis.sh/docs/security)** — MPC architecture and threat model
- **[Compliance](https://sardis.sh/docs/compliance)** — KYC/AML/SAR framework
- **[Examples](https://github.com/EfeDurmaz16/sardis/tree/main/examples)** — Code samples for all frameworks

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

**Quick contribution checklist:**
- Fork the repository
- Create a feature branch: `git checkout -b feature/your-feature`
- Make your changes with tests
- Run the test suite: `uv run pytest tests/`
- Submit a pull request

**Development setup:**

```bash
# Clone the repository
git clone https://github.com/EfeDurmaz16/sardis.git
cd sardis

# Install dependencies
uv sync

# Run tests
uv run pytest tests/

# Start local API server
uvicorn sardis_api.main:create_app --factory --port 8000
```

---

## 🔗 Links

- **Website**: [sardis.sh](https://sardis.sh)
- **Documentation**: [sardis.sh/docs](https://sardis.sh/docs)
- **Playground**: [sardis.sh/playground](https://sardis.sh/playground)
- **GitHub**: [github.com/EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)
- **Discord**: [discord.gg/XMA9JwDJ](https://discord.gg/XMA9JwDJ)
- **PyPI**: [pypi.org/project/sardis](https://pypi.org/project/sardis/)
- **npm**: [npmjs.com/package/@sardis/mcp-server](https://www.npmjs.com/package/@sardis/mcp-server)
- **Context7 Docs**: [context7.com/efedurmaz16/sardis](https://context7.com/efedurmaz16/sardis)

---

## 📄 License

This project uses an **open-core licensing model**:

- **MIT License** — SDKs, MCP Server, Integration Adapters, CLI tools
  - `sardis` (Python meta-package)
  - `@sardis/sdk`, `@sardis/mcp-server`, `@sardis/ai-sdk`
  - All integration adapters and examples

- **Proprietary** — Core banking infrastructure, policy engine internals, MPC node management

See [LICENSE.txt](LICENSE.txt) for full details.

---

<div align="center">
  <p>
    <strong>Sardis</strong> — open-source financial authority layer for AI agents
    <br/>
    Non-Custodial | MCP Native | Financial Hallucination Prevention
  </p>
  <p>
    Built with ❤️ for the AI agent ecosystem
    <br/>
    &copy; 2026 Efe Baran Durmaz
  </p>
</div>
