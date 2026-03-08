# Sardis Traction Snapshot — March 2026

> **The trust and control plane for AI agent payments.**
> AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

---

## Company Overview

- **What:** Infrastructure that lets AI agents make real financial transactions safely — non-custodial MPC wallets, natural-language spending policies, anomaly detection, and compliance in a single API call.
- **Founder:** Solo technical founder, building full-time since November 2025.
- **Stage:** Live on Base mainnet. Revenue flow active (50 BPS per transaction).
- **Development pace:** 1,097 commits in ~14 weeks. Entire platform built by one person.

---

## By The Numbers

| Metric | Count |
|--------|-------|
| Total commits | **1,097** |
| Monorepo packages | **39** |
| Test files | **272** |
| API routers | **63** |
| Database migrations | **52** |
| Smart contracts (Solidity) | **4** |
| Lines of Python | **~290,000** |
| Lines of TypeScript | **~66,000** |
| Lines of Solidity | **~7,500** |
| Total codebase | **~363,000+ lines** |

### Package Breakdown (39 packages)

**Core Infrastructure (7)**
sardis-core, sardis-chain, sardis-wallet, sardis-ledger, sardis-protocol, sardis-zk-policy, sardis-guardrails

**API & Server (3)**
sardis-api (63 routers), sardis-mcp-server, sardis-gpt

**Compliance & Cards (3)**
sardis-compliance, sardis-cards, sardis-ramp

**Checkout & Commerce (3)**
sardis-checkout, sardis-checkout-ui, sardis-ramp-js

**SDKs (4)**
sardis-sdk-python, sardis-sdk-js, sardis-cli, sardis-cli-go (+ sardis-cli-js)

**AI Framework Integrations (12)**
sardis-langchain, sardis-crewai, sardis-openai-agents, sardis-openai, sardis-ai-sdk, sardis-adk, sardis-agent-sdk, sardis-composio, sardis-browser-use, sardis-autogpt, sardis-stagehand, sardis-e2b

**Workflow & Protocol (5)**
n8n-nodes-sardis, sardis-activepieces, sardis-a2a, sardis-ucp, sardis-coinbase

**Smart Contracts (4 .sol files)**
SardisLedgerAnchor, SardisPolicyModule, SardisVerifyingPaymaster, RefundProtocol

---

## Technical Architecture

Sardis is not a payment gateway. It is the **control plane** that sits between an AI agent's intent and the financial system.

### Spending Policy Pipeline (12-check)
Every transaction passes through a deterministic, fail-closed policy engine before execution:

1. Kill-switch check
2. Transaction cap check
3. Token/chain allowlist
4. Merchant allowlist
5. Amount limits (per-tx, daily, monthly)
6. Velocity checks
7. Time-of-day restrictions
8. Anomaly scoring (Bayesian)
9. Confidence-tier routing
10. Multi-sig threshold evaluation
11. Compliance screening (KYC/AML/sanctions)
12. Policy version audit logging

### 4-Tier Confidence Routing
| Tier | Confidence | Action |
|------|-----------|--------|
| Auto-approve | 0.85 - 1.0 | Execute immediately |
| Manager review | 0.60 - 0.84 | Human-in-the-loop approval |
| Multi-sig | 0.30 - 0.59 | Requires N-of-M signatures |
| Block | 0.00 - 0.29 | Reject, alert, freeze |

### Additional Infrastructure
- Anomaly detection with Bayesian learning and goal-drift detection
- Kill switches and circuit breakers at org, agent, and wallet level
- HMAC-SHA256 signed execution receipts with on-chain anchoring
- Outcome tracking with agent and merchant risk profiles
- Provider reliability scorecards with smart routing
- Durable idempotency and side-effect queue
- Policy versioning with immutable audit trail
- ZK policy engine scaffold (Noir circuit + Python simulator)
- Advanced RBAC with custom roles, resource-level permissions, inheritance
- SSO via SAML/OIDC with per-org configuration
- Data governance: PII classification, retention policies, GDPR ops
- Simulation engine for payment dry-runs

---

## Framework & Protocol Coverage

### 12 AI Framework Integrations

| # | Framework | Package | Notes |
|---|-----------|---------|-------|
| 1 | LangChain | sardis-langchain | Tool integration for LangChain agents |
| 2 | CrewAI | sardis-crewai | Multi-agent payment orchestration |
| 3 | OpenAI Agents SDK | sardis-openai-agents | Native OpenAI agent tools |
| 4 | OpenAI (general) | sardis-openai | Function calling integration |
| 5 | Vercel AI SDK | sardis-ai-sdk | Server-side AI payment tools |
| 6 | Google ADK | sardis-adk | Google Agent Development Kit tool |
| 7 | Claude Agent SDK | sardis-agent-sdk | Anthropic agent integration |
| 8 | Composio | sardis-composio | Tool marketplace integration |
| 9 | Browser Use | sardis-browser-use | Browser automation payments (78k stars repo) |
| 10 | AutoGPT | sardis-autogpt | AutoGPT block integration (180k stars repo) |
| 11 | Stagehand | sardis-stagehand | Browserbase integration |
| 12 | E2B | sardis-e2b | Sandbox template with healthcheck |

### 5 Protocol Compliances

| # | Protocol | Status | Description |
|---|----------|--------|-------------|
| 1 | **AP2** (Agent Payment Protocol) | Implemented | Google/PayPal/Mastercard/Visa consortium standard. Full mandate chain verification. |
| 2 | **TAP** (Trust Anchor Protocol) | Implemented | Ed25519 + ECDSA-P256 agent identity attestation. |
| 3 | **x402** | Implemented | Coinbase HTTP payment protocol. |
| 4 | **UCP** (Universal Commerce Protocol) | Implemented | Universal commerce standard. |
| 5 | **A2A** (Agent-to-Agent) | Implemented | Google's agent interoperability protocol. |

### 3 Workflow Platform Integrations

| Platform | Package |
|----------|---------|
| n8n | n8n-nodes-sardis |
| Activepieces | sardis-activepieces |
| ChatGPT Custom GPT | sardis-gpt |

---

## Platform PRs Submitted

Upstream contributions to major open-source AI frameworks:

| # | Target Repository | PR Content | Status |
|---|-------------------|------------|--------|
| 1 | **Significant-Gravitas/AutoGPT** | Sardis payment block for AutoGPT (180k stars) | Submitted |
| 2 | **composiohq/composio** | Sardis integration YAML for Composio marketplace | Submitted |
| 3 | **crewAIInc/crewai-tools** | SardisTool for CrewAI multi-agent payments | Submitted |
| 4 | **langchain-ai/langchain** | Sardis tool documentation page | Submitted |
| 5 | **google/adk-community** | Sardis payment tool for Google ADK | Submitted |
| 6 | **vercel/ai** | Sardis provider for Vercel AI SDK | Submitted |
| 7 | **n8n (awesome-n8n)** | Sardis node listing | Submitted |

---

## Development Velocity

| Period | Commits |
|--------|---------|
| All time (Nov 30 2025 - Mar 9 2026) | **1,097** |
| 2026 YTD | **1,025** |
| February 2026 | **663** (940 since Feb 1 minus 277 in March) |
| March 2026 (9 days) | **277** (~31 commits/day) |

### Last 50 Feature Commits (categorized)

**Control Plane & Policy Engine**
- Kill-switch and transaction cap checks on submit()
- Anomaly engine wired into all ControlPlane call sites
- Unified ExecutionIntent model, ControlPlane, and simulation engine
- Policy decision evidence export with step-by-step audit
- Group policy hierarchies with cascading enforcement
- Policy versioning with immutable audit trail
- Structured policy DSL with compile/decompile/validate
- Policy simulation and dry-run endpoint

**Trust & Anomaly Detection**
- Anomaly tuner, confidence tuner, smart router, learning loop
- Provider health tracking and scorecards
- Outcome tracking with agent/merchant risk profiles
- Goal drift detection with automated policy actions
- FIDES trust graph integrated into KYA trust scoring
- Domain risk profiles integrated into chain executor

**Receipts & Audit**
- Persistent receipt store with verification API
- Execution side-effect queue, durable idempotency, and receipts
- HMAC-SHA256 signed execution receipts

**Checkout & Payments**
- EIP-712 typed session binding for external wallet connect
- Tokenized delegated payment architecture

**Infrastructure & Hardening**
- Health/readiness/liveness probes standardized
- 6 remaining technical hardening gaps closed
- SSO via SAML/OIDC with per-org configuration
- Advanced RBAC with custom roles and resource-level permissions
- Data governance with PII classification and GDPR ops
- ZK policy engine scaffold with Noir circuit

**Framework Integrations & Launch**
- All framework integrations bumped to v1.0.0
- Publish scripts for all framework packages
- Integration smoke tests
- Automated partner onboarding script

**Dashboard**
- Anomaly Detection dashboard
- Exceptions handling page
- Simulation page for payment dry-runs
- Approvals page wired to real API
- Merchants page wired to real API
- Dashboard overview wired to real API data
- Guided 7-beat control plane demo flow

**Landing & Narrative**
- ICP solution pages for agent platforms, procurement, payouts
- Reframed narrative from payment rails to control plane

---

## Competitive Landscape

| Company | Funding | What They Do | Sardis Advantage |
|---------|---------|--------------|------------------|
| **Skyfire** | $9.5M seed | Payment routing for AI agents | Point solution. No policy engine, no cards, no compliance, no anomaly detection. |
| **Locus** | YC F25 | Base-native agent payments | Base-only. No multi-chain, no approval workflows, no spending policies. |
| **Payman** | $13.7M seed+ | Compliance-focused agent payments | No crypto rails, no escrow, no anomaly scoring, no framework integrations. |
| **Paid** | $33.3M | AI billing and invoicing | Different category entirely. No agent wallets, no real-time control. |
| **Natural** | $9.8M seed | Agent payment infrastructure | Early stage, limited public info. No evidence of policy engine or compliance. |

**Key differentiator:** Every competitor is building a payment pipe. Sardis is building the control plane that makes the pipe safe to use. The policy engine, anomaly detection, confidence routing, and kill switches are the product --- not just features bolted on.

---

## Six Moats

### 1. Smart Transaction Scoring
Every payment gets a 0.0 - 1.0 trust score computed from agent history, merchant risk profile, anomaly signals, and policy compliance. Score determines the approval tier automatically.

### 2. Deterministic Policy Enforcement
Spending policies defined in plain English, compiled to a deterministic DSL, evaluated fail-closed. "Max $500/day on SaaS, block crypto exchanges, require approval above $1,000." No ambiguity, no LLM in the loop at execution time.

### 3. Crypto + Fiat in One API
6 chains (Base, Polygon, Ethereum, Arbitrum, Optimism, Arc) with USDC/EURC/USDT/PYUSD support, plus virtual card issuance via Stripe Issuing. One SDK, one policy engine, both rails.

### 4. Agent-to-Agent Escrow
On-chain escrow (Circle RefundProtocol, audited) for inter-agent payments. Milestone-based release, dispute resolution, timeout refunds. Critical for multi-agent workflows where agents transact with each other.

### 5. Compliance Built In
KYC (iDenfy), AML/sanctions screening (Elliptic), Know-Your-Agent trust scoring with FIDES trust graph integration. Append-only audit ledger with on-chain anchoring. Not an afterthought --- it is a first-class subsystem.

### 6. Emergency Controls
Organization-level, agent-level, and wallet-level kill switches. Circuit breakers that auto-trigger on anomaly thresholds. Transaction caps. Freeze-and-investigate workflows. The "oh shit" button that every CFO will demand before letting agents spend money.

---

## Revenue Model

| Component | Detail |
|-----------|--------|
| **Platform fee** | 50 BPS (0.50%) per transaction |
| **Implementation** | Fee split at settlement: merchant receives net, Sardis treasury receives fee |
| **Status** | Fully implemented and activated on mainnet |
| **Future** | Tiered pricing for enterprise volume, premium features (ZK proofs, dedicated compliance) |

### Revenue Scaling Math
| Agent Payments / Month | Monthly Revenue | ARR |
|------------------------|-----------------|-----|
| $1M | $5,000 | $60K |
| $10M | $50,000 | $600K |
| $100M | $500,000 | $6M |
| $1B | $5,000,000 | $60M |

As AI agents handle procurement, SaaS subscriptions, cloud infrastructure, and vendor payments, transaction volume through platforms like Sardis will scale with agent adoption itself.

---

## What Has Been Built (Summary)

| Layer | Status |
|-------|--------|
| Non-custodial MPC wallets (Turnkey) | Production |
| 12-check spending policy engine | Production |
| Anomaly detection + Bayesian learning | Production |
| 4-tier confidence routing | Production |
| Kill switches + circuit breakers | Production |
| On-chain receipt anchoring | Production |
| 63-router REST API | Production |
| React dashboard with real API data | Production |
| Merchant checkout (Pay with Sardis) | Production |
| 12 AI framework SDKs | v1.0.0 published |
| 5 protocol compliances | Implemented |
| Virtual card issuance | Sandbox (Stripe Issuing) |
| KYC + AML + sanctions | Integrated |
| 52 database migrations | Production |
| 272 test files | Active CI |

---

## The Raise

| | |
|---|---|
| **Round** | Seed |
| **Amount** | $9M |
| **Pre-money valuation** | $36M |
| **Use of funds** | Security audits, card program activation, financial licenses (MTL/EMI), fiat on/off-ramp partnerships, hiring (3 engineers + 1 compliance + 1 GTM) |
| **Runway** | 18-24 months |

### Why Now
- AI agent frameworks are shipping payment capabilities in 2026 (OpenAI, Google, Anthropic all moving).
- AP2 protocol (Google/PayPal/Mastercard/Visa) creates a standard that needs infrastructure to serve it.
- No one has built the control plane yet. Everyone is building pipes. The trust layer is the defensible position.
- Solo-founder velocity demonstrates capital efficiency: 363K+ lines of production code, 39 packages, 7 upstream PRs, zero funding to date.

### Why $36M Pre-Money
- 363K+ lines of production code across Python, TypeScript, and Solidity
- 39-package monorepo with 12 framework integrations --- more coverage than any funded competitor
- Live on mainnet with revenue mechanics activated
- 7 upstream PRs to major open-source projects (AutoGPT, LangChain, CrewAI, Vercel AI SDK, Google ADK, Composio, n8n)
- 5 protocol compliances implemented before any competitor
- Solo founder built what funded teams of 5-10 have not

---

*Sardis --- the trust layer for the agent economy.*

*Contact: efe@sardis.sh*
