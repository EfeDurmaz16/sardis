export function GET() {
  const content = `# Sardis — Complete Documentation

> The Payment OS for the Agent Economy. Non-custodial MPC wallets with natural language spending policies for AI agents.

Sardis is infrastructure that enables AI agents to make real financial transactions safely. It provides non-custodial MPC wallets with natural language spending policies, compliance guardrails, and cryptographic audit trails.

---

## Overview

### What is Sardis?

Sardis solves a fundamental problem: AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

Traditional payment systems (Stripe, PayPal) are designed for human-initiated transactions with human oversight. Sardis is purpose-built for autonomous AI agents that need to make financial decisions independently, within policy guardrails, without human approval for every transaction.

### Core Architecture

1. **Non-Custodial MPC Wallets** — Powered by Turnkey. Private keys are never stored or accessible by Sardis. Agents sign transactions through distributed MPC key shares.
2. **Policy Firewall** — Every transaction is evaluated against natural language spending policies before execution. Policies are compiled into on-chain rules.
3. **Multi-Chain Settlement** — Supports Base, Polygon, Ethereum, Arbitrum, and Optimism. Handles USDC, USDT, EURC, and PYUSD.
4. **Compliance Layer** — KYC via Persona, AML/sanctions screening via Elliptic. Fail-closed by default.
5. **Audit Trail** — Append-only ledger with Merkle anchoring for cryptographic proof of every transaction.

### Key Differentiators

- **Policy-first**: Unlike Stripe or Circle, every transaction must pass natural language policy checks before execution
- **Agent-native**: Built for autonomous agents, not retrofitted from human payment flows
- **Non-custodial**: MPC wallets mean Sardis never holds customer funds
- **Protocol-compliant**: Supports AP2 (Google/PayPal/Mastercard/Visa), TAP, x402, and A2A protocols
- **Framework-agnostic**: Works with any AI framework via SDKs, MCP, or direct API

---

## Quick Start

### Python

\`\`\`python
pip install sardis

from sardis import Sardis

client = Sardis(api_key="sk_...")

# Create an agent with a wallet
agent = client.agents.create(
    name="Procurement Agent",
    chain="base"
)

# Set spending policy in plain English
client.policies.create(
    agent_id=agent.id,
    rules="max $100 per transaction, only approved merchants, daily limit $500"
)

# Agent makes a payment (policy enforced automatically)
payment = client.payments.create(
    agent_id=agent.id,
    to="0x...",
    amount="50.00",
    token="USDC"
)
\`\`\`

### TypeScript

\`\`\`typescript
import { Sardis } from '@sardis/sdk';

const client = new Sardis({ apiKey: 'sk_...' });

const agent = await client.agents.create({
  name: 'Procurement Agent',
  chain: 'base',
});

await client.policies.create({
  agentId: agent.id,
  rules: 'max $100 per transaction, only approved merchants',
});

const payment = await client.payments.create({
  agentId: agent.id,
  to: '0x...',
  amount: '50.00',
  token: 'USDC',
});
\`\`\`

### MCP Server (Claude Desktop / Cursor)

\`\`\`json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}
\`\`\`

The MCP server exposes 52 tools for wallet management, payments, policy configuration, compliance checks, and audit trail queries.

---

## API Reference

### Authentication

All API requests require a Bearer token:

\`\`\`
Authorization: Bearer sk_live_...
\`\`\`

API keys are hashed with SHA-256. Rate limiting is enforced on all endpoints.

### Base URL

\`\`\`
https://api.sardis.sh/api/v2
\`\`\`

### Core Endpoints

#### Agents
- \`POST /agents\` — Create a new agent with a wallet
- \`GET /agents\` — List all agents
- \`GET /agents/:id\` — Get agent details
- \`PATCH /agents/:id\` — Update agent configuration

#### Wallets
- \`GET /wallets/:id\` — Get wallet details and balance
- \`GET /wallets/:id/transactions\` — List wallet transactions
- \`POST /wallets/:id/fund\` — Fund a wallet

#### Payments
- \`POST /payments\` — Create a payment (policy-checked)
- \`GET /payments/:id\` — Get payment status
- \`GET /payments\` — List payments with filters

#### Policies
- \`POST /policies\` — Create a spending policy (natural language)
- \`GET /policies/:id\` — Get policy details
- \`PATCH /policies/:id\` — Update policy rules
- \`DELETE /policies/:id\` — Remove a policy

#### Mandates (AP2)
- \`POST /mandates\` — Create a spending mandate
- \`GET /mandates/:id\` — Get mandate status
- \`POST /mandates/:id/execute\` — Execute a mandated payment

#### Compliance
- \`POST /compliance/kyc\` — Initiate KYC verification
- \`GET /compliance/kyc/:id\` — Check KYC status
- \`POST /compliance/sanctions\` — Screen an address

#### Audit
- \`GET /audit/trail\` — Query the audit trail
- \`GET /audit/trail/:id\` — Get specific audit entry

---

## Spending Policies

### How Policies Work

Spending policies are the core of Sardis. They define what an agent can and cannot do with money.

Policies are written in plain English and compiled into enforceable rules:

\`\`\`
"max $100 per transaction"
"only approved merchants: Amazon, Google Cloud, AWS"
"daily spending limit $500"
"require human approval above $200"
"no international transfers"
"only USDC on Base chain"
\`\`\`

### Policy Evaluation

Every payment request goes through the Policy Firewall:

1. **Parse** — Natural language policy is parsed into structured rules
2. **Evaluate** — Transaction is checked against all active policies
3. **Decide** — ALLOW, DENY, or ESCALATE (require human approval)
4. **Execute** — If allowed, transaction is signed via MPC and broadcast
5. **Audit** — Result is recorded in the append-only audit trail

### Policy Types

- **Amount limits** — Per-transaction, daily, weekly, monthly caps
- **Merchant restrictions** — Allowlists, blocklists, category filters
- **Chain restrictions** — Limit to specific chains or tokens
- **Time restrictions** — Business hours only, no weekends
- **Approval flows** — Require human sign-off above thresholds
- **Velocity checks** — Rate limiting on transaction frequency

---

## Supported Chains & Tokens

| Chain | Tokens | Settlement Time |
|-------|--------|----------------|
| Base | USDC, EURC | ~2 seconds |
| Polygon | USDC, USDT, EURC | ~2 seconds |
| Ethereum | USDC, USDT, PYUSD, EURC | ~12 seconds |
| Arbitrum | USDC, USDT | ~2 seconds |
| Optimism | USDC, USDT | ~2 seconds |

### Cross-Chain Transfers

Sardis supports CCTP V2 (Circle Cross-Chain Transfer Protocol) for USDC transfers between supported chains with unified addresses.

---

## Integrations

### AI Frameworks

| Framework | Package | Install |
|-----------|---------|---------|
| Browser Use | sardis-browser-use | pip install sardis-browser-use |
| CrewAI | sardis-crewai | pip install sardis-crewai |
| OpenAI Agents | sardis-openai-agents | pip install sardis-openai-agents |
| Vercel AI SDK | @sardis/ai-sdk | npm install @sardis/ai-sdk |
| LangChain | sardis-langchain | pip install sardis-langchain |
| AutoGPT | sardis-autogpt | Built-in block |
| Composio | sardis-composio | Via Composio marketplace |

### Workflow Automation

| Platform | Package | Install |
|----------|---------|---------|
| Activepieces | Built-in | Available in Activepieces marketplace |
| n8n | n8n-nodes-sardis | npm install n8n-nodes-sardis |

### MCP Server

52 tools available for Claude Desktop, Cursor, and Windsurf:
- Wallet management (create, fund, balance, transfer)
- Payment execution (send, receive, status)
- Policy configuration (create, update, evaluate)
- Compliance checks (KYC, sanctions, audit)
- Agent management (create, configure, monitor)

---

## Protocols

### AP2 (Agent Payment Protocol)

Consortium standard from Google, PayPal, Mastercard, and Visa for agent-initiated payments.

Mandate chain: Intent → Cart → Payment

Sardis verifies the full mandate chain before executing any transaction. This prevents agents from making payments outside their authorized scope.

### TAP (Trust Anchor Protocol)

Ed25519 and ECDSA-P256 identity verification for agent attestation. Agents prove their identity cryptographically before making payments.

### x402 (HTTP 402 Payment Required)

Standard for machine-to-machine payments over HTTP. When an API returns 402, the agent can automatically pay using Sardis and retry the request.

### A2A (Agent-to-Agent)

Google's agent interoperability protocol. Sardis enables agents to discover payment capabilities and negotiate transactions using A2A.

---

## Security

### Wallet Security
- MPC (Multi-Party Computation) via Turnkey
- Private keys never stored or accessible by Sardis
- Distributed key shares across multiple parties

### API Security
- API keys hashed with SHA-256
- HMAC webhook signatures
- Rate limiting on all endpoints
- Replay protection via mandate cache

### Compliance
- KYC verification via Persona
- AML/sanctions screening via Elliptic
- Fail-closed: default deny on compliance failures
- SOC2 + PCI + ISO + GDPR compliance path

### Audit Trail
- Append-only ledger
- Merkle tree anchoring for tamper-proof records
- Every transaction, policy evaluation, and compliance check is recorded

---

## Pricing

| Plan | Price | Agents | Transactions | Features |
|------|-------|--------|-------------|----------|
| Free | $0/mo | 1 | Sandbox only | SDK access, simulation mode |
| Dev | $49/mo | 2 | 100/mo | Testnet, basic policies |
| Starter | $199/mo | 25 | Unlimited | Production, all policies, audit |
| Growth | $499/mo | 100 | Unlimited | KYB, PEP screening, priority support |
| Enterprise | Custom | Unlimited | Unlimited | White-glove, SLA, custom compliance |

Stablecoin checkout: 0% merchant fee on USDC payments.

---

## Company

- **Name:** Sardis Labs, Inc.
- **Type:** Delaware C-corp
- **Founded:** 2024
- **Founder:** Efe Baran Durmaz
- **Website:** https://sardis.sh
- **Dashboard:** https://app.sardis.sh
- **Documentation:** https://docs.sardis.sh
- **API Docs:** https://api.sardis.sh/api/v2/docs
- **GitHub:** https://github.com/EfeDurmaz16/sardis
- **X/Twitter:** https://x.com/sardisHQ
- **npm:** @sardis/sdk, @sardis/mcp-server
- **PyPI:** sardis, sardis-sdk

---

## Glossary

- **Financial Hallucination** — When an AI agent attempts unauthorized, incorrect, or fabricated financial transactions. Sardis prevents this through policy enforcement.
- **Policy Firewall** — Sardis's real-time transaction evaluation engine that checks every payment against natural language spending policies.
- **Spending Mandate** — A structured authorization that defines what an agent is allowed to spend, on what, and under what conditions.
- **Agent Wallet** — A non-custodial MPC wallet assigned to an AI agent, controlled by policy rules rather than human approval.
- **MPC (Multi-Party Computation)** — Cryptographic technique where private key shares are distributed across multiple parties, so no single party can sign transactions alone.
- **AP2 (Agent Payment Protocol)** — Consortium standard for agent-initiated payments, defining Intent → Cart → Payment mandate chains.
- **TAP (Trust Anchor Protocol)** — Identity verification protocol using Ed25519/ECDSA-P256 for agent attestation.
- **CCTP (Cross-Chain Transfer Protocol)** — Circle's protocol for native USDC transfers between blockchains.
`;

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
