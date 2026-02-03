# Sardis — Payment OS for AI Agents (YC Spring 2026 Draft)

## One‑liner
Sardis lets AI agents spend real money safely: **policy‑enforced wallets + cards + audit trails** across stablecoins and fiat rails.

## The problem
AI agents can reason, but they can’t be trusted with money:
- Companies want agents to run real workflows (procurement, refunds, subscriptions, ad spend), but giving an agent raw payment credentials is a fraud/compliance nightmare.
- Existing rails (cards, ACH/wires, stablecoins) weren’t built for autonomous actors. They lack native controls like spend policies, approvals, and explainable auditability.

## The solution
Sardis is an infrastructure layer that wraps money movement with **controls and observability**:
- **Non‑custodial agent wallets (MPC via Turnkey)**: agents get addresses and can sign, without private keys ever living in your app.
- **Virtual cards (Lithic)**: for fiat merchants, with spending limits + policy enforcement.
- **Stablecoin rails**: transfers with the same policy gate and on‑chain verifiability.
- **Policy engine**: natural language policies compiled into deterministic checks (limits, merchant categories, allow/deny lists).
- **Audit trail**: immutable ledger + webhook events for every decision and transfer.

## Why now
- Agents are moving from “chat” to “do” (spend, buy, subscribe, settle).
- Stablecoins are becoming real financial infrastructure; the regulatory window is opening for compliant, crypto‑native rails.
- AI‑native companies want to scale revenue per employee; autonomous spending is a bottleneck without guardrails.

## Wedge (what we ship first)
**Fiat rails + policy engine** with **prefunded virtual cards**:
- Fastest path to a compelling demo and early revenue.
- Lets customers adopt Sardis without waiting on on‑chain contract audits or mainnet deployments.

## Expansion (the big market)
Add **stablecoin rails** (starting with Base) and unify:
- “Agent budget” across card spend + stablecoin transfers.
- Cross‑border settlement and faster payouts using stablecoins.

## ICP (who buys first)
- AI‑native agencies automating client work where spend is part of delivery (ads, tooling, contractors).
- AI‑native trading/research teams (strict controls + audit trail).
- B2B SaaS teams embedding “agentic procurement/checkout” into products.

## Business model (directionally)
- Platform fee (per org / per active agent wallet)
- Usage fee (per card tx, per stablecoin transfer)
- Revenue share where applicable (e.g., interchange share on cards)

## What’s defensible
- A unified **policy+payments** control plane across heterogeneous rails (cards + stablecoins).
- A standards‑friendly audit layer (mandates/attestations + deterministic policy decisions).
- Operational learnings: safely running “agents with money” is a new category; it’s not just APIs.

## Demo (investor‑ready, 3–5 minutes)
1) Login to Sardis dashboard  
2) Create an agent wallet (Turnkey)  
3) Set a policy in natural language: “Max $100/tx; block gambling; only software + cloud merchants”  
4) Issue a virtual card (Lithic)  
5) Simulate a purchase with a blocked MCC → policy deny + optional auto‑freeze → transaction log  
6) Stablecoin flow on Base Sepolia:
   - Create a payment mandate → execute → show Basescan tx hash → show ledger entry + audit anchor

## What is real vs simulated (today)
- **Real today**: Turnkey wallet creation + signing; Lithic card issuance (sandbox); policy enforcement; audit trail; API auth hardening.
- **Demo simulated**: “purchase” via simulated webhook/endpoint (to avoid production merchant dependence).
- **Testnet real**: stablecoin transfer on Base Sepolia (USDC test token) with explorer verification.
- **Mainnet**: post‑audit + controlled rollout (Base first).

## Key risks & how we mitigate
- Compliance scope creep → start with prefunded cards + clear limits; add legal/compliance head post‑funding; expand jurisdictions/rails gradually.
- Security → external audit before mainnet; default‑deny auth; webhook signature verification; rate limiting; incident runbooks.

## What we will build next (post‑YC)
- Production multi‑tenancy + org/user RBAC (without slowing demo velocity)
- SDK publishing (Python/TS) + MCP integrations
- Bridge.xyz / ramps, and production settlement flows
- External smart contract audit + mainnet rollout (Base first), followed by other chains

