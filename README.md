<div align="center">
  <h1>Sardis</h1>
  <p><strong>Open-source financial authority layer for AI agents</strong></p>
  <p>Sardis lets agents transact only through signed mandates, deterministic policy checks, approval paths, revocation, and audit evidence before any wallet, card, stablecoin, payment API, or provider rail is used.</p>

  <p>
    <a href="https://sardis.sh">Website</a> ·
    <a href="https://sardis.sh/manifesto">Manifesto</a> ·
    <a href="https://docs.sardis.sh">Docs</a> ·
    <a href="https://sardis.sh/playground">Playground</a> ·
    <a href="https://sardis.sh/enterprise">Enterprise</a>
  </p>

  <p>
    <a href="https://www.npmjs.com/package/@sardis/mcp-server"><img src="https://img.shields.io/npm/v/@sardis/mcp-server?label=npm%20%40sardis%2Fmcp-server" alt="npm version"></a>
    <a href="https://pypi.org/project/sardis/"><img src="https://img.shields.io/pypi/v/sardis?label=PyPI%20sardis" alt="PyPI version"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License"></a>
    <a href="https://github.com/EfeDurmaz16/sardis/stargazers"><img src="https://img.shields.io/github/stars/EfeDurmaz16/sardis?style=social" alt="GitHub stars"></a>
    <a href="https://github.com/EfeDurmaz16/sardis/commits/main"><img src="https://img.shields.io/github/last-commit/EfeDurmaz16/sardis" alt="Last commit"></a>
    <a href="https://securityscorecards.dev/viewer/?uri=github.com/EfeDurmaz16/sardis"><img src="https://api.securityscorecards.dev/projects/github.com/EfeDurmaz16/sardis/badge" alt="OpenSSF Scorecard"></a>
    <a href="https://discord.gg/XMA9JwDJ"><img src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

---

## What Sardis Is

Sardis is the open-source financial authority layer for AI agents. It sits between autonomous agents and money-moving systems so every consequential financial action is checked against a mandate, policy decision, approval path, revocation path, and audit packet before execution.

Sardis is not a card wrapper, prepaid wallet, or rail-specific payment app. It governs the authority to spend across stablecoin wallets, card programs, fiat payment APIs, x402-style HTTP payments, AP2/TAP mandates, provider-hosted wallets, and simulator rails.

The core primitive is verifiable authority before an agent can spend, subscribe, purchase, refund, settle, or trigger paid usage. Customers can bring their own providers; Sardis enforces the authority layer above them without needing to custody funds or become the merchant of record.

The deeper thesis is that agents do not just have a capability problem; they have a trust problem. Sardis treats money as the sharpest version of a broader substrate problem: how non-human actors perform consequential actions with explicit authority, reviewable state transitions, and durable evidence.

| Layer | Open source | Hosted / commercial |
|-------|-------------|---------------------|
| Authority model | Mandates, policies, approvals, revocation, audit packets | Same semantics with managed org, RBAC, SSO, retention, and support |
| Provider execution | Adapter interfaces, simulator, BYO credentials | Managed credential vault, webhook handling, alerts, provider routing |
| Developer surface | SDKs, MCP server, examples, protocol adapters | Hosted dashboard, approval inbox, compliance workflows, audit export |

Read the boundaries:

- [Open-core model](OPEN_CORE.md)
- [Provider abstraction](PROVIDER_ABSTRACTION.md)
- [OSS goal](docs/oss/goal.md)
- [Public/private boundary](docs/oss/public-private-boundary.md)
- [Package maturity matrix](docs/packages.md)
- [Legal and compliance disclaimer](DISCLAIMER.md)
- [Agent authority demo](examples/agent-authority-demo/)

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

## What Problems Sardis Solves

AI agents can draft invoices, call paid APIs, buy tools, book travel, issue refunds, subscribe to services, and interact with merchants. The missing layer is not only "payments." It is the authority system that decides whether the agent was allowed to do the financial action in the first place.

Sardis provides:

- **Mandates** -- who delegated authority to the agent, for what scope, under which limits.
- **Policy firewall** -- deterministic checks before execution or signing.
- **Approvals** -- step-up flows for high-risk, high-value, or ambiguous actions.
- **Revocation** -- stop future execution when authority changes.
- **Provider adapters** -- route approved actions to wallets, cards, stablecoins, payment APIs, or simulators.
- **Audit packets** -- immutable evidence for operators, customers, partners, and reviewers.

Sardis can route approved actions to provider adapters. Live-money deployments depend on the configured provider account, jurisdiction, compliance program, and customer policy.

---

## Protocol & Feature Maturity

| Feature | Status | Description |
|---------|--------|-------------|
| Spending Policy Engine | **Implemented** | Deterministic NL-to-policy, atomic spend tracking |
| AP2 Mandate Verification | **Implemented** | Full mandate chain verification with evidence |
| Provider Adapter Model | **Implemented** | Rail-agnostic execution contract and simulator-first semantics |
| Policy Attestation API | **Implemented** | Signed attestation envelopes with Ed25519 |
| PreExecutionPipeline | **Implemented** | Composable hook chain with fail-closed defaults |
| Hosted Checkout | **Pilot** | Merchant checkout flows with session security |
| ERC-8183 Agentic Jobs | **Pilot** | On-chain job escrow (conservative caps: 1% fee, USDC-only) |
| x402 Protocol | **Pilot** | HTTP-native micropayments |
| Card Provider Adapters | **Pilot** | Provider-backed virtual card execution behind explicit capability checks |
| Stablecoin Provider Adapters | **Pilot** | Provider-backed stablecoin execution behind explicit capability checks |
| Multi-chain (Polygon, Arbitrum) | **Experimental** | Chain routing implemented, not production-tested |
| UCP MCP Transport | **Experimental** | Partial implementation |
| FIDES Trust Graph | **Experimental** | DID-based trust federation |

> **Status key:** **Implemented** = code and tests exist in the public repository. **Pilot** = functional with conservative limits and active hardening. **Experimental** = code exists, not production-tested.

---

## Key Features

- **Provider-neutral authority layer** -- govern cards, wallets, stablecoins, payment APIs, x402, AP2, TAP, and simulator rails
- **Mandates and spending policy** -- "Max $50/tx, $200/day, SaaS vendors only"
- **Pre-execution policy firewall** -- fail-closed checks before signing, issuing, paying, refunding, or settling
- **Approval and revocation flows** -- step-up before risky actions, kill switch when authority changes
- **Provider adapter contract** -- capability declarations, idempotency, signed webhooks, revocation windows, audit fields
- **15+ AI framework integrations** -- LangChain, CrewAI, OpenAI Agents, Claude SDK, Google ADK, A2A, AgentKit, Vercel AI SDK, MCP, and more
- **Agent-to-agent escrow** -- Cryptographic mandate chain for A2A payments
- **KYA (Know Your Agent)** -- Trust scoring and behavioral anomaly detection
- **Double-entry audit ledger** -- Append-only transaction history with cryptographic proofs
- **Protocol support** -- AP2 and TAP (production), x402 (pilot), UCP and A2A (partial)

---

## 🚀 Quick Start

### Python (5 lines)

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")
result = client.pay(
    to="merchant@example.com",
    amount="50.00",
    currency="USDC",
    chain="base",
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

**That's it.** Your agent now has a bounded financial authority surface instead of unconstrained payment access.

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

All frameworks use the same policy engine, mandate model, provider adapters, and audit semantics.

---

## Architecture

Every financial action follows a **single authority path** before execution. There are no alternative code paths that bypass policy checks.

```
                         AI AGENT
              (Claude, Cursor, LangChain, OpenAI)
                          |
                     MCP / SDK
                          |
            ┌─────────────┴─────────────┐
            │  FinancialActionOrchestrator│
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
            │   PROVIDER ADAPTER        │
            │   Cards / wallets / APIs  │
            └─────────────┬─────────────┘
                          |
               +──────────┴──────────+
               |                     |
         Stablecoin Rails      Fiat / Card Rails
         Wallet providers      Payment providers
         x402 / AP2 / TAP      BYO provider acct
               |                     |
         ┌─────┴─────┐         ┌────┴────┐
         │  LEDGER   │         │  LEDGER │
         │  Append   │         │  Append │
         │  Only     │         │  Only   │
         └───────────┘         └─────────┘
```

**Key design principles:**
- **Fail-closed** -- Default deny on all policy, compliance, and security checks
- **Provider-neutral** -- Sardis governs execution without requiring one custody, wallet, card, or payment provider
- **Audit everything** -- Append-only ledger with signed attestation envelopes for every decision

---

## 📂 Repository Structure

```
sardis/
├── packages/               # Core monorepo packages
│   ├── sardis-core/        # Domain models, config, database
│   ├── reference-api/      # FastAPI reference API implementation
│   ├── sardis-chain/       # Blockchain execution, chain routing
│   ├── sardis-protocol/    # AP2/TAP protocol verification
│   ├── sardis-wallet/      # Wallet management, MPC
│   ├── sardis-ledger/      # Append-only audit trail
│   ├── sardis-compliance/  # KYC (iDenfy) + AML (Elliptic)
│   ├── sardis-cards/       # Card provider adapter experiments
│   ├── sardis-mcp-server/  # MCP server for Claude/Cursor
│   ├── sardis-sdk-python/  # Full Python SDK
│   ├── sardis-sdk-js/      # TypeScript SDK
│   ├── sardis-cli/         # Command-line tool
│   └── sardis-checkout/    # Merchant checkout flows
├── src/sardis/             # Simple Python SDK (public interface)
├── contracts/              # Solidity smart contracts
│   └── src/
│       ├── SardisWalletFactory.sol
│       ├── SardisAgentWallet.sol
│       └── SardisEscrow.sol
├── apps/
│   ├── landing/            # Public website source
│   └── canvas-site/        # Technical canvas source
├── playground/             # Interactive demo sandbox
├── examples/               # Usage examples
├── demos/                  # Demo applications
├── docs/                   # Public technical documentation
└── tests/                  # Legacy root migration backlog; prefer package tests
```

---

## 📚 Documentation

- **[Getting Started Guide](https://docs.sardis.sh/getting-started)** — First payment in 5 minutes
- **[API Reference](https://docs.sardis.sh/api)** — Complete endpoint documentation
- **[MCP Server Setup](https://docs.sardis.sh/mcp)** — Claude Desktop integration
- **[Policy Language](https://docs.sardis.sh/policies)** — Write spending rules in plain English
- **[Chain Support](https://docs.sardis.sh/chains)** — Supported networks and tokens
- **[Framework Guides](https://docs.sardis.sh/frameworks)** — LangChain, OpenAI, Vercel AI SDK
- **[Security Model](https://docs.sardis.sh/security)** — MPC architecture and threat model
- **[Compliance](https://docs.sardis.sh/compliance)** — KYC/AML/SAR framework
- **[Examples](https://github.com/EfeDurmaz16/sardis/tree/main/examples)** — Code samples for all frameworks
- **[Package Maturity Matrix](docs/packages.md)** — What is core, supported, experimental, demo, or private-candidate
- **[Architecture Package Layout](docs/architecture/package-layout.md)** — Why repo package paths and Python import namespaces are separate
- **[OSS Package Layout Policy](docs/oss/package-layout.md)** — Contributor-facing naming, nesting, and rename rules
- **[Source Layout Policy](docs/oss/source-layout.md)** — API source-tree guardrails and route placement rules
- **[x402 and MPP Boundary](docs/architecture/x402-and-mpp.md)** — How paid HTTP protocol surfaces split across packages
- **[Contribution Map](docs/oss/contribution-map.md)** — Which package to change, what to contribute, and how to validate it
- **[Development Guide](docs/development.md)** — Local setup and contribution checks
- **[Public CI/CD Map](docs/oss/ci-cd.md)** — Which public checks protect the OSS surface
- **[Public Testing Policy](docs/oss/testing.md)** — Maintained test suites and root-test migration policy
- **[Support](SUPPORT.md)** — Where to ask for OSS help and what belongs outside the public repo
- **[Security Policy](SECURITY.md)** — Private vulnerability reporting and payment safety invariants
- **[Code of Conduct](CODE_OF_CONDUCT.md)** — Community expectations for public collaboration

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

**Quick contribution checklist:**
- Fork the repository
- Create a feature branch: `git checkout -b feature/your-feature`
- Make your changes with tests
- Run the contributor gate: `pnpm run check:contributor`
- Submit a pull request

**Development setup:**

```bash
# Clone the repository
git clone https://github.com/EfeDurmaz16/sardis.git
cd sardis

# Install dependencies
pnpm run doctor
uv sync
pnpm install --frozen-lockfile

# Run fast OSS checks
python3 scripts/repo_inventory.py
python3 scripts/oss_surface_check.py
python3 scripts/stale_api_path_check.py
pnpm --filter @sardis/sdk typecheck

# Start local API server
uv run uvicorn --app-dir packages/reference-api server.main:create_app --factory --port 8000
```

---

## 🔗 Links

- **Website**: [sardis.sh](https://sardis.sh)
- **Documentation**: [docs.sardis.sh](https://docs.sardis.sh)
- **Playground**: [sardis.sh/playground](https://sardis.sh/playground)
- **GitHub**: [github.com/EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)
- **Discord**: [discord.gg/XMA9JwDJ](https://discord.gg/XMA9JwDJ)
- **PyPI**: [pypi.org/project/sardis](https://pypi.org/project/sardis/)
- **npm**: [npmjs.com/package/@sardis/mcp-server](https://www.npmjs.com/package/@sardis/mcp-server)
- **Context7 Docs**: [context7.com/efedurmaz16/sardis](https://context7.com/efedurmaz16/sardis)

---

## 📄 License And Open-Core Boundary

The public repository is licensed under the terms in [LICENSE](LICENSE). See [OPEN_CORE.md](OPEN_CORE.md) for the product boundary between the open-source authority layer and the hosted Sardis Cloud operations layer.

The intended split is:

- **Open source** -- mandate semantics, policy evaluation, provider interfaces, simulator providers, SDKs, protocol adapters, examples, and audit schemas.
- **Hosted / commercial** -- dashboard, RBAC/SSO, approval inbox, managed provider credentials, webhook operations, compliance workflows, audit retention, alerts, and support.

---

<div align="center">
  <p>
    <strong>Sardis</strong> -- Open-source financial authority for AI agents
    <br/>
    Mandates | Provider Adapters | Approvals | Revocation | Audit
  </p>
  <p>
    Built for the AI agent ecosystem
    <br/>
    &copy; 2026 Efe Baran Durmaz
  </p>
</div>
