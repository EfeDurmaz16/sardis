<div align="center">
  <h1>Sardis</h1>
  <p><strong>Payment OS for the Agent Economy</strong></p>
  <p>AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.</p>

  <p>
    <a href="https://sardis.sh">Website</a> ·
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

Sardis gives AI agents **non-custodial MPC wallets** with **natural language spending policies**. It prevents financial hallucinations—agents accidentally spending $10k instead of $100—with a real-time policy firewall that validates every transaction before execution.

Your Claude agent, LangChain workflow, or autonomous bot gets its own wallet with programmable guardrails: "Max $100/day on cloud services, only approved vendors, no gambling." The agent cannot override these policies.

Sardis executes **stablecoin payments** (USDC) on **Base** with multi-chain funding via CCTP v2 (Ethereum, Polygon, Arbitrum, Optimism). Virtual cards are available in pilot via Stripe Issuing.

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
- **9 AI framework integrations** -- MCP, LangChain, OpenAI, Vercel AI, CrewAI, LlamaIndex, Mastra
- **Virtual cards (Pilot)** -- Stripe Issuing for agent-controlled fiat payments
- **Agent-to-agent escrow** -- Cryptographic mandate chain for A2A payments
- **KYA (Know Your Agent)** -- Trust scoring and behavioral anomaly detection
- **Base (production) + 4 funding chains** -- Multi-chain funding via CCTP v2
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
    <strong>Sardis</strong> — The Payment OS for the Agent Economy
    <br/>
    Non-Custodial | MCP Native | Financial Hallucination Prevention
  </p>
  <p>
    Built with ❤️ for the AI agent ecosystem
    <br/>
    &copy; 2026 Efe Baran Durmaz
  </p>
</div>
