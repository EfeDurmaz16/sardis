# SARDIS -- Payment OS for the Agent Economy

> "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust."

---

## Problem

AI agents are becoming autonomous economic actors -- booking services, purchasing resources, paying vendors. But giving an agent direct wallet access means uncontrolled spending with no guardrails. Today, there is no infrastructure for **policy-controlled agent payments**. Developers either give agents full custody (dangerous) or keep humans in the loop for every transaction (defeats the purpose of autonomy).

## Solution

Non-custodial wallets with **deterministic spending policies**.

> "Allow up to $50/day on cloud services, require human approval above $100, block all gambling-related merchants."

Sardis provides the governance layer between AI agents and real money: MPC wallets where agents can transact within defined policy boundaries, with approval workflows, kill switches, and anomaly detection -- all without Sardis ever holding custody of funds.

## Cross-Rail Moat

Sardis works across Stripe, Base, Tempo, and Visa simultaneously. Incumbents only control their own walled gardens. Enterprises do not want Stripe lock-in for their AI policy layer.

## Proof of Build

48 packages, 50K+ installs, first mainnet payment executed on Tempo ($1 USDC, Turnkey MPC signed). 24 pay-per-request API endpoints live via Stripe MPP — earning machine-to-machine revenue today. All built solo.

## Key Metrics

| Metric | Value |
|--------|-------|
| SDK installs | 50,000+ (PyPI + npm), $0 marketing |
| Published packages | 48 |
| Mainnet | First payment executed on Tempo (chain 4217) |
| Paid API endpoints | 24 MPP-gated, earning per-request revenue |
| Framework integrations | 18+ (CrewAI, AutoGPT, OpenAI Agents, Google ADK, Vercel AI SDK, etc.) |
| Stripe MPP | Production access granted |
| Wallet funding | 3 channels active (Coinbase, Stripe Crypto, Relay bridge) |
| Policy engine | 12-check pipeline per transaction |

## Design Partners

| Partner | Relevance | Status |
|---------|-----------|--------|
| Activepieces (workflow automation) | Distribution through automation users | LIVE, fully integrated |
| AutoGPT (180K GitHub stars) | Largest open-source agent framework | In talks with founding engineer |
| CrewAI | Multi-agent developer base | PR submitted |
| Stripe MPP | Agent payment protocol | Production access granted |
| OpenClaw | Claude Code skill marketplace | 8 skills published |

## Pricing

Open source to developers, SaaS seat licenses for the CFO who manages approvals, and BPS on cleared volume.

| Tier | Price |
|------|-------|
| Free | $0 (open source SDK, testnet, 1 agent, community support) |
| Dev | $49/mo (mainnet access, 2 agents, basic dashboard) |
| Starter | $199/mo (25 agents, compliance dashboard, audit trail) |
| Growth | $499/mo (100 agents, priority support, custom policies) |
| Enterprise | Custom (unlimited + BPS on volume) |

Additionally, 24 API endpoints earn per-request revenue via MPP ($0.001-$0.10/call) from unauthenticated agents — zero-friction acquisition that converts to subscriptions.

## "What You Need to Believe"

AI agents will become the primary economic actors of the next decade, and existing payment rails will never build cross-platform deterministic controls for them. If you do not believe that, save us both the Zoom.

## Tech Stack

- **Wallets:** Safe Smart Accounts v1.4.1 + Turnkey MPC (non-custodial)
- **Chains:** Tempo (mainnet), Base, Ethereum, Polygon, Arbitrum, Optimism, Arc (Circle L1)
- **Tokens:** USDC, USDT, EURC, PYUSD
- **Protocols:** AP2, TAP, x402, UCP, MPP, A2A, FIDES, OSP
- **Trust Stack:** FIDES (agent identity) + AGIT (policy versioning) + OSP (service provisioning) + Sardis (policy enforcement)
- **Stack:** Python 3.12, FastAPI, PostgreSQL, Solidity, React, TypeScript

## Team

**Efe Baran Durmaz** -- Solo founder, age 20. Built the entire stack: 48 packages, 18+ framework integrations, 8 protocol implementations, first mainnet payment on Tempo. Also built: OSP (open alternative to Stripe Projects, 10K-line spec), a Rust package manager (23x faster than npm), and AgentGit (version control for AI agent state). Bilkent University (full merit scholarship, top 0.04% national exam). Nokia AI Engineer.

## The Ask

**Raising a $3M Seed.** I have out-shipped entire engineering teams solo to build the core infrastructure. This capital buys the one thing I cannot code: enterprise GTM and compliance credibility. Use of funds: Forward Deployed Engineer, Enterprise GTM Lead, and Tier-1 Security Audits.

**Series A readiness:** $50-75K MRR + governing $10M+ in monthly agent spend.

---

**Contact:** Efe Baran Durmaz | efe@sardis.sh | [sardis.sh](https://sardis.sh)
