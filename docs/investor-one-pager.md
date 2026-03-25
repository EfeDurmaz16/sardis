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

47+ API endpoints and 21 published packages at v1.1.0, all built solo. We have the foundational control plane shipped while competitors are still writing whitepapers.

## Key Metrics

| Metric | Value |
|--------|-------|
| SDK installs | 50,000+ (PyPI + npm) |
| Marketing spend | $0 -- all organic |
| Published packages | 21 at v1.1.0 |
| Production API endpoints | 47+ |
| Framework integrations | 15 (CrewAI, AutoGPT, LangChain, OpenAI Agents, Google ADK, Vercel AI SDK, etc.) |
| Agent Auth Protocol | Supported |
| sardis.pay() | Phase 1-3 shipped |
| Listed on mpp.dev/services | Yes |
| Commits | 1,800+ |
| Policy engine checks | 12-check pipeline per transaction |

## Design Partners

| Partner | Relevance | Status |
|---------|-----------|--------|
| Activepieces (workflow automation) | Distribution through automation users | LIVE, fully integrated |
| AutoGPT (180K GitHub stars) | Largest open-source agent framework | In talks with founding engineer |
| CrewAI | Multi-agent developer base | PR submitted |
| Stripe MPP | Agent payment protocol | Early access granted |

## Pricing

Open source to developers, SaaS seat licenses for the CFO who manages approvals, and BPS on cleared volume.

| Tier | Price |
|------|-------|
| Dev | Free (open source SDK, testnet) |
| Business | $199/seat/mo (mandate management, compliance dashboard, audit trail) |
| Enterprise | BPS on total payment volume governed (alignment with value delivered) |

## "What You Need to Believe"

AI agents will become the primary economic actors of the next decade, and existing payment rails will never build cross-platform deterministic controls for them. If you do not believe that, save us both the Zoom.

## Tech Stack

- **Wallets:** Safe Smart Accounts v1.4.1 + Turnkey MPC (non-custodial)
- **Chains:** Base, Ethereum, Polygon, Arbitrum, Optimism, Arc (Circle L1)
- **Tokens:** USDC, USDT, EURC, PYUSD
- **Protocols:** AP2, TAP, x402, UCP, MPP, A2A, FIDES
- **Stack:** Python 3.12, FastAPI, PostgreSQL, Solidity, React, TypeScript

## Team

**Efe Baran Durmaz** -- Solo founder, age 20. Built the entire stack: 1,800+ commits, 21 published packages, 47+ API endpoints, 15 framework integrations, 7 protocol implementations. Bilkent University (full merit scholarship, top 0.04% national exam). Nokia AI Engineer.

## The Ask

**Raising a $3M Seed.** I have out-shipped entire engineering teams solo to build the core infrastructure. This capital buys the one thing I cannot code: enterprise GTM and compliance credibility. Use of funds: Forward Deployed Engineer, Enterprise GTM Lead, and Tier-1 Security Audits.

**Series A readiness:** $50-75K MRR + governing $10M+ in monthly agent spend.

---

**Contact:** Efe Baran Durmaz | efe@sardis.sh | [sardis.sh](https://sardis.sh)
