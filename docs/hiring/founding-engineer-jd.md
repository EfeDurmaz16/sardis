# Founding Engineer #1

## Sardis -- Payment OS for the Agent Economy

---

## About Sardis

AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

We are building the infrastructure that enables AI agents to make real financial transactions safely -- non-custodial MPC wallets, natural language spending policies, virtual card issuance, and multi-chain stablecoin payments. Our platform sits at the intersection of AI agent frameworks (AutoGPT, CrewAI, OpenAI Agents SDK), crypto infrastructure (USDC, Safe accounts, Circle), and traditional fintech (Stripe Issuing, SEPA, ACH).

We are backed by [INVESTORS] and are building the payment layer for the agent economy. Our open-core platform already integrates with 10+ agent frameworks, supports 6 blockchain networks, and has production partnerships with Stripe, Bridge, Striga, Lightspark, Coinbase, and Turnkey.

---

## The Role

You will be the first engineering hire. You will work directly with the founder to own entire systems end-to-end -- from smart contract deployment to API design to production infrastructure. This is not a role where you wait for specs. You will define the architecture, ship the product, and talk to customers.

**What you will build:**
- Core payment orchestration pipeline (policy evaluation, chain execution, settlement)
- Smart contract infrastructure (Safe accounts, Zodiac Roles, on-chain escrow)
- API platform serving AI agent frameworks (FastAPI, async Python)
- SDK packages (Python + TypeScript) used by developers building agentic applications
- Virtual card issuance and management (Stripe Issuing integration)
- Cross-chain settlement and off-ramp infrastructure
- Production monitoring, alerting, and incident response

---

## What We Are Looking For

### Must Have

- **3+ years building production systems** in Python and/or TypeScript
- **Strong async Python** (asyncio, FastAPI or similar ASGI frameworks)
- **Database design** (PostgreSQL -- schema design, query optimization, migrations)
- **API design** (REST, webhooks, idempotency, rate limiting, versioning)
- **Production operational experience** (deployment, monitoring, debugging distributed systems)
- **Ship fast, iterate faster** mentality -- you have shipped products to real users

### Strongly Preferred

- **Fintech experience** -- payment processing, card issuing, banking APIs, or compliance systems
- **Smart contract development** (Solidity, Foundry/Hardhat, ERC-20, Safe/multisig)
- **Blockchain infrastructure** (RPC providers, transaction management, gas optimization)
- **Cryptography fundamentals** (MPC, key management, HMAC, digital signatures)
- **TypeScript/Node.js** for SDK development and frontend work

### Nice to Have

- Experience with AI/ML agent frameworks (LangChain, CrewAI, AutoGPT, OpenAI Agents)
- MCP (Model Context Protocol) or similar AI tool-use protocols
- Infrastructure-as-code (Terraform, Docker, cloud deployment)
- Open-source contributions or maintainership
- Startup experience (seed to Series A)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, asyncpg, Pydantic |
| Database | PostgreSQL (Neon serverless) |
| Cache | Redis (Upstash) |
| Smart Contracts | Solidity 0.8.x, Foundry, OpenZeppelin |
| Wallet Infrastructure | Safe Smart Accounts v1.4.1, Turnkey MPC |
| Frontend | React, Vite, TypeScript |
| SDKs | Python (sardis-sdk-python), TypeScript (sardis-sdk-js) |
| Cards | Stripe Issuing, Striga |
| Off-ramp | Bridge.xyz, Lightspark Grid |
| Deployment | Vercel, Google Cloud Run |
| CI/CD | GitHub Actions |
| Monitoring | [TO_BE_DECIDED -- you will help choose] |

---

## What You Will Do in Month 1

- Get full codebase context (12+ packages, 50+ DB tables, 47+ API routers)
- Ship your first production feature within the first week
- Own the deployment pipeline and production monitoring
- Conduct your first customer integration call
- Identify and fix the top 3 technical debt items

---

## Compensation

This is a founding engineer role with equity-heavy compensation reflecting the early stage and outsized impact opportunity.

| Component | Details |
|-----------|---------|
| Base Salary | $[SALARY_RANGE_LOW] -- $[SALARY_RANGE_HIGH] |
| Equity | [EQUITY_PERCENTAGE]% founding equity (4-year vest, 1-year cliff) |
| Benefits | Health insurance, equipment budget |
| Location | Remote-first (US/EU time zones preferred) |

Equity is meaningful. As the first engineer, your contribution will directly shape the company's trajectory and value.

---

## How We Work

- **Remote-first.** We care about output, not hours or location.
- **High context, low process.** Daily async standups, weekly syncs, quarterly planning. No Jira tickets for tickets' sake.
- **Ship daily.** We deploy to production multiple times per day. Automated tests and CI/CD are non-negotiable.
- **Customer-driven.** Engineers talk to customers. You will understand the problems you are solving.
- **Open-core.** Core infrastructure is open-source. We build in public where possible.

---

## Interview Process

1. **Intro call** (30 min) -- Mutual fit, role overview, your questions
2. **Technical deep-dive** (60 min) -- Architecture discussion, past projects, system design
3. **Take-home or pair programming** (2-3 hours) -- Build a small integration or fix a real issue in our codebase
4. **Founder session** (45 min) -- Vision alignment, working style, equity discussion
5. **Offer** -- Decision within 48 hours of final interview

Total process: 1-2 weeks. We respect your time.

---

## How to Apply

Send an email to [HIRING_EMAIL] with:
- Your resume or LinkedIn
- A brief note on why this role interests you
- One thing you have built that you are proud of (link, repo, or description)

Or open a PR on our GitHub -- that works too.

---

*Sardis is an equal opportunity employer. We evaluate candidates based on their skills, experience, and potential -- nothing else.*
