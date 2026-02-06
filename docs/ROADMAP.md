# Sardis Development Roadmap
## Programmable Stablecoin Payment Protocol for AI Agents

---

## Executive Summary

Sardis is the **first programmable stablecoin payment protocol** purpose-built for AI agents. It provides financial identity, governance, and settlement infrastructure that enables autonomous software to execute payments, manage escrow, enforce spending policies, and participate in agent-to-agent commerce.

This roadmap outlines Sardis's evolution from a **backend-first payment abstraction layer** to a **hybrid on-chain/off-chain financial operating system** for the autonomous economy.

### Latest Update (2026-02-06)

Current focus is **protocol conformance hardening** before production expansion:

- AP2 payment semantics hardened with explicit `ai_agent_presence` and `transaction_modality`
- TAP validation tightened with algorithm allowlists and linked-object signature checks
- Protocol source governance added: `docs/release/protocol-source-map.md`
- Conformance release note: `docs/release/2026-02-06-protocol-conformance-hardening.md`

---

## Phase 1: Backend-First Payment Protocol (Present State)

### Strategic Rationale

The decision to launch Sardis as a **backend-first abstraction layer** is deliberate and strategically sound:

- **Rapid iteration** over a fast-moving AI agent ecosystem
- **Simple integration** via HTTP/SDK instead of direct on-chain logic
- **Flexible compliance** and policy enforcement at the API layer
- **Multi-chain abstraction** behind a single payment interface

### Current Capabilities

Sardis already delivers a **Stripe-like payment layer for AI agents** with the following primitives:

- **Mandate system (AP2)**
  - Intent → Cart → Payment mandate chain
  - Typed models for `IntentMandate`, `CartMandate`, `PaymentMandate`, `MandateChain`
  - Cryptographic binding via VC proofs and nonces

- **Agent wallets & spending policies**
  - Multi-token balances (USDC, USDT, PYUSD, EURC)
  - Trust tiers with per-tx, daily, weekly, monthly, and total limits
  - Merchant allow/deny rules, category filters, scope-based permissions
  - Policy evaluation before execution via wallet policy engine

- **Holds & pre-authorization**
  - Create, capture, and void holds
  - Configurable hold duration and max hold hours

- **Compliance engine**
  - Token allowlisting and amount thresholds
  - GENIUS Act-aligned monitoring hooks
  - Provider/Rule metadata attached to each decision

- **Ledger system**
  - Append-only transaction log with deterministic receipts
  - Audit anchors linking mandates, chain receipts, and ledger entries

- **A2A marketplace primitives**
  - Service listings, offers, milestones, and reviews
  - Foundation for agent-to-agent service discovery and contracting

- **Cross-chain execution**
  - Routing across multiple EVM chains (Base, Ethereum, Polygon)
  - Stablecoin-focused settlement layer for agents

Sardis at this stage already acts as:

- A **Stripe-like payment layer** for AI agents
- The **first financial identity and governance system** for autonomous software

---

## Phase 2: Sardis Escrow Smart Contract (Three-Month Horizon)

### Rationale for Escrow as the First Contract

Escrow is the ideal first smart contract primitive for Sardis because it:

- Provides **transparent and verifiable settlement** for agent-to-agent commerce
- Reduces **counterparty risk** by locking funds under predefined conditions
- Enables **milestone-based work agreements** with partial, conditional releases
- Has a **limited and auditable attack surface**, making it suitable for early on-chain rollout

Sardis will start by deploying a **minimal, trustless escrow contract** on a single chain such as **Base**, then generalize to additional chains.

### Contract Design and Flows

The `SardisEscrow` contract (already implemented in this repository) supports:

- **Lifecycle states**
  - `Created` → `Funded` → `Released`
  - Dispute path: `Funded` → `Disputed` → `Resolved`
  - Refund / expiry: `Funded` → `Refunded` / `Expired`

- **Core flows**
  - `createEscrow` / `createEscrowWithMilestones`
  - `fundEscrow` (buyer deposit)
  - `confirmDelivery` (seller confirms delivery)
  - `approveRelease` and `release` (funds to seller + fee to Sardis)
  - `refund` (buyer refund post-deadline, if seller has not confirmed)
  - Milestone completion and release per milestone
  - Dispute raise and arbiter-driven resolution

- **Multi-party roles**
  - **Buyer** — funding the escrow and approving releases
  - **Seller** — delivering work and confirming completion
  - **Arbiter (Sardis)** — resolving disputes with configurable split

### Linking On-Chain Settlement to Sardis Backend

On-chain escrow settlement is anchored back into Sardis via:

- **Ledger entries** that reference:
  - Escrow ID
  - Chain ID and tx hash
  - Buyer and seller agent IDs / wallets
  - Amount, fee, and milestone breakdowns

- **Mandate records** tying the on-chain escrow to:
  - The original AP2 mandate chain
  - TAP identities and VC proofs
  - Compliance decisions and policies applied

This phase shifts Sardis from a **purely backend engine** to a **hybrid model** where:

- The **backend orchestrates** policy, identity, mandates, and compliance
- The **chain provides final settlement guarantees** and public verifiability

---

## Phase 3: Mandate Verification Contract (Six-Month Horizon)

### Purpose

The next logical on-chain primitive is a **mandate verification contract** that:

- Validates **signatures, proofs, and VC bundles** generated by AI agents
- Ensures that **mandate parameters** (issuer, subject, amount, destination, expiry, nonce) have not been tampered with
- Provides an **on-chain attestation standard** for AP2/TAP-based payments

### Effects on Trust Model

With mandate verification on-chain:

- AI agent payments become **trust-minimized**, because any integrator can:
  - Recompute the mandate hash
  - Verify signatures against TAP identity keys
  - Validate nonce usage and expiry
  - Check VC bundle integrity

- Sardis becomes the **verification layer for autonomous commerce**, allowing:
  - Third-party platforms to verify payment authorization **without trusting Sardis backend logic**
  - Other protocols to integrate AP2 mandates natively

- Compliance and attestation become **portable**, as VC bundles can be reused:
  - Identity VCs (KYC, sanctions)
  - Policy VCs (spending scope, limits, merchant restrictions)
  - Audit VCs (prior transaction history, risk scoring)

### Role in the Ecosystem

The mandate verification contract effectively:

- Hardens the **authorization boundary** for all Sardis-driven payments
- Exposes a **standard interface** for:
  - dApps
  - Settlement protocols
  - Other agent platforms

This reinforces Sardis as:

- The **canonical validator of agent payment intent**
- A **shared compliance substrate** for the broader agent economy

---

## Phase 4: Wallet Architecture Evolution (One-Year Horizon)

### Long-Term Wallet Strategy

Over a one-year horizon, Sardis can gradually introduce **on-chain or MPC-backed programmatic wallets** for agents. This evolution is **optional in the very near term**, but strategically important long-term:

- Today, wallets can be modeled primarily in the backend (custodial or semi-custodial)
- Over time, control shifts towards:
  - **MPC-backed keys** (e.g., Turnkey/Fireblocks) for non-custodial semantics
  - **Smart contract wallets** that encode policies and identity on-chain

### Capabilities of Evolved Wallets

- **Native fund custody** by agents, not only Sardis-managed accounts
- **Cross-agent asset flows** through direct wallet-to-wallet transfers
- **Modular on-chain interactions** with DeFi, liquidity, and other stablecoin protocols
- **On-chain policy enforcement** for:
  - Spending rules
  - Rate limits
  - Allowed tokens and destinations

- **Identity binding in decentralized form**:
  - Wallets map to TAP identities
  - VC roots (Merkle roots) anchored in wallet state
  - Trust levels and compliance status reflected in on-chain metadata

### Resulting Primitive

The end-state is a **financial identity primitive** for autonomous systems:

- Each agent has a **durable, programmable wallet identity**
- Payments, escrows, mandates, and policies converge around this identity
- Sardis becomes the **default financial OS** for agents across chains

---

## Growth Strategy After the Four Phases

Once the hybrid architecture is established, Sardis can scale as the **default payment and identity layer for AI agents**.

### 1. Integration with AI Agent Platforms

Sardis becomes the built-in payment layer for major agent frameworks and platforms:

- Mindra
- LangChain
- AutoGen
- CrewAI
- Llama Stack
- Reka and similar enterprise stacks

#### Integration Pattern

Platforms integrate Sardis via a **simple, high-level primitive** like `agent.pay()`:

- Under the hood, this call:
  - Constructs an AP2 mandate chain (Intent → Cart → Payment)
  - Applies TAP identity binding and VC proofs
  - Routes through Sardis backend for policy + compliance
  - Optionally uses escrow and cross-chain settlement

Result:

- Platform developers never have to deal with:
  - Raw chain RPCs
  - Stablecoin contract quirks
  - Mandate/VC formats

They simply:

- Configure Sardis API keys
- Call a single SDK method to **trigger payments, escrow agreements, or cross-chain transfers**

### 2. Developer Ecosystem and SDKs

Sardis invests in first-class SDKs for:

- **Python** — primary language for AI agents
- **Go** — backend services and high-throughput systems
- **TypeScript** — Node and edge runtimes

SDKs provide:

- **One-liner integration** for common flows (pay, hold, refund, escrow)
- Client-side handling of:
  - Wallet creation and registration
  - Mandate construction and signing
  - VC proof packaging
  - Idempotency and retries

Developers integrate Sardis with **a few lines of code**, while the SDKs handle:

- Policy enforcement hooks
- Proof and signature workflows
- Error handling and retries

### 3. Sardis Dashboard and Console

The Sardis Dashboard evolves into a **unified console** where operators can:

- View **wallets** and balances
- Inspect **agents** and identity status
- Configure **spending limits** and policies
- Browse **transactions**, **mandates**, and **escrow agreements**
- Manage **marketplace** offers and reviews
- Monitor **compliance logs** and SAR hooks
- Configure and debug **webhooks** and integrations

This console becomes the **control plane** for all agent-related financial operations.

### 4. Sardis Explorer

The Sardis Explorer becomes the **transparency portal** for:

- On-chain escrow contracts and their state
- Mandate verification events and proofs
- Ledger anchoring (Merkle roots and chain tx hashes)

By exposing a public, queryable view of:

- Escrow lifecycles
- Verified mandates
- Anchored ledger entries

Sardis creates a **public audit layer** that:

- Enhances trust in the protocol
- Provides regulators and partners with verifiable data
- Makes Sardis the **source-of-truth explorer for the agent economy**

### 5. AI Agent Marketplace Economy

Marketplaces can build on Sardis primitives to enable **autonomous buying and selling of services** between agents:

- **Offers and milestones** provide a structured negotiation + delivery flow
- **Escrow** ensures that funds are locked during work
- **Reviews and ratings** create a reputation graph for agents

This combination establishes the **first true economic layer for AI-to-AI commerce**, where:

- Agents discover each other
- Negotiate terms
- Execute work
- Settle payments with minimal human intervention

### 6. Positioning Sardis as the Standard

As these layers mature, Sardis becomes the **default standard** for:

- **Financial identity** of autonomous agents
- **Authorization and settlement** of agent-driven payments
- **Compliance and verification** of on-chain and off-chain flows

Network effects emerge from:

- More platforms integrating Sardis SDKs
- More agents using Sardis wallets and mandates
- More marketplaces standardizing on Sardis escrow and offers

This creates **long-term defensibility** via:

- Deep integration into agent ecosystems
- A rich identity and transaction graph
- Regulatory and compliance moats

---

## Conclusion

This roadmap takes Sardis from a **backend-first payment abstraction layer** to a **hybrid, verifiable, and programmable financial operating system for AI agents**.

Across the four phases, Sardis:

- Solidifies its **backend mandate + wallet + compliance engine**
- Adds **on-chain escrow** for trustless settlement
- Introduces a **mandate verification contract** as a shared attestation standard
- Evolves to **on-chain and MPC-backed agent wallets** as the native financial identity primitive

On top of this, a robust growth strategy around **integrations, SDKs, dashboards, explorers, and marketplaces** positions Sardis as the **default financial identity, settlement, and authorization layer for autonomous agents**.
