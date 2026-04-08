# Sardis: The Payment OS for the Agent Economy
## Pitch Deck v2 (A+ Grade)
### March 2026

---

## Slide 1 -- Title

**Sardis: Compliance-First Financial Infrastructure for AI Agents**

AI agents are becoming the new financial operators. They need trust, control, and auditability before they can move money. Sardis is the governance layer that makes that possible.

- **Company:** Sardis Labs, Inc. (sardis.sh)
- **Founder:** Efe Baran Durmaz
- **Stage:** Live on Base mainnet, pre-revenue, seed raise
- **Category:** Agentic Finance Infrastructure

One line: "Alloy and Persona built identity verification for humans. Sardis builds payment governance for AI agents."

---

## Slide 2 -- Problem (Make Fear Visceral)

**AI agents are going live. Payment governance infrastructure does not exist.**

This is what happens when an enterprise deploys an agent without deterministic controls:

```
#incidents | CRITICAL
Agent "procurement-bot" executed 847 API calls in 12 minutes
Total spend: $47,291.03
Authorized limit: $500/day
Status: NO POLICY ENGINE CONFIGURED
```

This is not hypothetical. This is the default state of every AI agent with payment access today. There is no middleware between "agent wants to spend" and "money moves." The entire stack assumes a human is making the decision.

| How companies handle agent payments today | What goes wrong |
|-------------------------------------------|-----------------|
| Shared corporate card with agent access | No per-agent limits. No audit trail. A single prompt injection can drain the card. |
| Manual approval queues for every transaction | Defeats the purpose of autonomous agents. Humans become the bottleneck. |
| Custom-built internal guardrails | Every company rebuilds the same thing. Brittle, unaudited, no compliance evidence. |
| No payment capability at all | Agents cannot operate independently. Humans do the last mile manually. |

The deeper problem is structural. Human payment systems assume a human is making the decision. They have no concept of scoped, time-limited, revocable authority for a non-human actor. There is no "power of attorney" primitive for machines.

---

## Slide 3 -- Solution

**Sardis is the deterministic governance layer between AI intent and financial execution.**

Sardis does not process payments. It decides whether a payment is allowed to happen. Then it routes to licensed partners for execution.

Three core primitives:

**1. Spending Mandates**
A machine-readable "power of attorney" for agents. Defines seven dimensions of authority: WHO can spend, WHAT they can buy, HOW MUCH (per-tx, daily, monthly, lifetime), ON WHICH RAILS (card, USDC, bank), FOR HOW LONG, WITH WHAT APPROVAL (auto, threshold, always-human), and WITH WHAT REVOCATION. Full lifecycle: draft, active, suspended, revoked, expired, consumed. Every state transition is audited.

**2. 12-Check Policy Engine**
Every payment passes through 12 sequential, deterministic checks before money moves. First failure short-circuits with a denial reason. No LLM in the execution path. Amount validation, scope check, MCC filtering, per-tx limits, aggregate limits, time-window caps, on-chain balance verification, merchant rules, goal drift detection, merchant trust scoring, approval threshold routing, and KYA attestation verification.

**3. Non-Custodial MPC Wallets**
Sardis never holds funds. Never touches private keys. Turnkey MPC handles custody. This is not a feature preference. It is a regulatory architecture decision: Sardis does not need money transmitter licenses because it never has custody.

The agent proposes. Sardis filters. Licensed rails only see transactions that have cleared every check.

---

## Slide 4 -- How It Works

**From agent intent to settled transaction in seven phases.**

```
Phase 0:    KYA Verification
            Is this a legitimate agent? Who authorized it?
            Agent identity, liveness check, code hash attestation.

Phase 0.5:  Mandate Validation
            Does an active spending mandate exist for this agent?
            Is this payment within the mandate's scope, limits, and rail permissions?

Phase 1:    Policy Validation (12-check engine)
            Amount, scope, MCC, per-tx limit, aggregate limits,
            time-window caps, on-chain balance, merchant rules,
            goal drift, merchant trust, approval routing, KYA level.

Phase 1.5:  Group Policy
            Multi-agent budget enforcement.
            Most-restrictive-wins across agent groups and departments.

Phase 2:    Compliance Check
            KYC (Didit), sanctions screening (Elliptic), AML.
            Fail-closed: no compliance clearance = no execution.

Phase 3:    Chain Execution
            Route to appropriate rail: USDC on Base/Polygon/Ethereum,
            virtual card via Stripe Issuing, or bank transfer.
            MPC signing via Turnkey. On-chain settlement with confirmation.

Phase 3.5:  Policy State Update
            Atomic DB update with SELECT FOR UPDATE.
            Decrement remaining budget. Update velocity counters.

Phase 4:    Ledger Append
            Merkle-tree anchored, append-only audit trail.
            SardisLedgerAnchor.sol stores roots on-chain.
            Tamper-evident by construction.
```

Revenue capture happens at Phase 3: BPS on cleared volume, plus SaaS seat licenses for the management layer.

**Developer integration is three lines of code:**
```python
agent = sardis.create_agent(
    name="procurement-bot",
    policy="max $1000/day, only SaaS and cloud vendors"
)
agent.pay(to="openai.com", amount=50, currency="USD")
```

---

## Slide 5 -- Market Size (Logical Absolute, Not Gartner TAM)

**If you believe every major software platform will launch an AI agent by 2026, you must also believe they are terrified of letting them spend money.**

Sardis is the infrastructure that resolves that terror.

The market sizing is a logical absolute, not a Gartner extrapolation:

1. Every enterprise deploying AI agents needs payment governance. There is no alternative to governance -- the only question is build vs. buy.
2. Every agent framework (CrewAI, AutoGPT, LangChain, OpenAI Agents, Google ADK) needs a payment primitive. None of them have one.
3. Every payment rail adding agent support (Stripe MPP, Coinbase x402, Google A2A, Visa AP2) needs a cross-rail policy layer. None of them will build it across each other's rails.

**The wedge:** Sardis is the only cross-rail governance layer. Stripe only controls Stripe. Coinbase only controls Coinbase. Visa only controls Visa. The CFO wants one policy layer, not four.

**Key market signals:**

- Stripe launched MPP (Machine Payments Protocol) March 18, 2026. Sardis has early access.
- Coinbase shipped x402. Google launched A2A with 50+ partners. Visa/Google/PayPal/Mastercard published AP2.
- 40% of enterprise apps will include task-specific AI agents by end of 2026 (Gartner).
- Stablecoin B2B settlement is accelerating. Every stablecoin B2B payment by an agent routes through Sardis policy.

---

## Slide 6 -- Business Model and Pricing

**Open source to developers, SaaS seat licenses for the CFO, BPS on cleared volume.**

### Three-Tier Pricing

| Tier | Price | What You Get |
|------|-------|-------------|
| **Dev** | Free | Open source SDK, testnet access, community support, all framework integrations |
| **Business** | $199/seat/mo | Mandate management dashboard, compliance dashboard, full audit trail, SSO, priority support |
| **Enterprise** | BPS on total payment volume governed | Custom policies, dedicated support, SLA, on-prem option, alignment with value delivered |

### Unit Economics per $100 Transaction (Enterprise)

| Line Item | Amount |
|-----------|--------|
| Transaction fee (1.0%) | $1.00 |
| Interchange share (0.5%) | $0.50 |
| Off-ramp markup (0.3%) | $0.30 |
| **Total revenue** | **$1.80** |

| Cost Item | Amount |
|-----------|--------|
| Off-ramp fee (Coinbase, 0% USDC) | $0.00 |
| Card issuing (amortized) | $0.02 |
| Sanctions check | $0.05 |
| MPC signature (Turnkey) | $0.02 |
| KYC (amortized over ~100 tx) | $0.015 |
| Infrastructure (amortized) | $0.01 |
| **Total cost** | **$0.12** |

| Metric | Value |
|--------|-------|
| **Gross profit per $100 tx** | **$1.68** |
| **Gross margin** | **93%** |

### Why This Pricing Works

- **Dev tier** creates the developer pull (50K+ installs prove this works).
- **Business tier** captures the CFO who needs to manage approvals, audit trails, and compliance across their agent fleet.
- **Enterprise BPS** aligns Sardis revenue with the value delivered: the more agent spend we govern, the more we earn.

No custody. No MTL required. Non-custodial architecture means zero marginal cost on wallet operations.

---

## Slide 7 -- Traction

**50K+ organic SDK installs. $0 marketing spend. Zero paid acquisition.**

| Metric | Number | Source |
|--------|--------|--------|
| SDK installs (cumulative) | 50,000+ | npm + PyPI (verified public numbers) |
| Marketing spend | $0 | All organic developer pull |
| Published packages | 21 at v1.1.0 | Shipped, tested, versioned |
| Production API endpoints | 47+ | Production-grade, no stubs |
| Framework integrations | 15 | CrewAI, AutoGPT, LangChain, OpenAI Agents, Google ADK, Vercel AI SDK, Browser Use, etc. |
| Agent Auth Protocol | Supported | KYA attestation + code hash verification |
| Commits | 1,800+ | Solo founder velocity |
| sardis.pay() | Phase 1-3 shipped | Intent, policy, execution pipeline complete |
| Listed on mpp.dev/services | Yes | Stripe MPP ecosystem directory |
| Supported protocols | 7 | AP2, TAP, x402, UCP, MPP, A2A, FIDES |

### Design Partners and Integrations

| Partner | Status | Relevance |
|---------|--------|-----------|
| Activepieces (workflow automation) | LIVE, fully integrated | Distribution through workflow automation users |
| CrewAI (multi-agent framework) | PR submitted, waiting to merge | Access to CrewAI's multi-agent developer base |
| AutoGPT (180K GitHub stars) | In talks with founding engineer | Largest autonomous agent community |
| Catena Labs | Design partner meeting scheduled | Agent identity and trust |
| Stripe MPP | Early access granted | First-party access to Stripe's agent payment protocol |
| Turnkey (Series B, $52.5M) | Production integration, EWaaS launch case study | Non-custodial MPC for every Sardis wallet across all 15+ SDKs |

### Compliance Readiness

| Certification | Status | Partner |
|---------------|--------|---------|
| SOC2 Type II | In progress | DSALTA (Can Ozguruck, SF) |
| PCI DSS | In progress | DSALTA |
| ISO 27001 | In progress | DSALTA |
| GDPR | In progress | DSALTA |
| AIUC-1 (AI Use Control) | In progress | DSALTA |
| Estimated total cost | ~$15K | 1-year Trust Control Dashboard included |

---

## Slide 8 -- Competition

**Sardis is governance, not rails. That is the key distinction.**

### Positioning Matrix

| Company | Funding | What They Do | What They Miss |
|---------|---------|--------------|----------------|
| Natural | $9.8M | B2B embedded agent payments | No deterministic policy engine. No multi-chain. No compliance stack. Closed source. |
| Sapiom | $15M (Accel, Anthropic) | Agents buying APIs | Single use case (API procurement). No card rails. No general-purpose governance. |
| Crossmint | $41.7M (Series A) | Agent wallets + virtual cards | Custodial architecture (regulatory ceiling). Basic spending limits, not policy engine. No protocol compliance. |
| Skyfire | $9.5M (a16z CSX) | Custodial agent wallets | Custodial (MTL required at scale). Basic limits. No AP2/TAP/x402. No audit anchoring. |
| Kite | $33M (General Catalyst) | Own blockchain for agent identity | Requires bootstrapping a new chain. Locked to Kite chain. No existing-chain compatibility. |
| Ramp Agent Card | N/A | Corporate card with AI features | Card-only. No on-chain. No agent-specific governance. Human-first design adapted for agents. |
| Sponge | YC W26 | Wallets + cards for agents | Custodial. No protocol compliance. No 12-check policy. No audit anchoring. |

### Why Sardis Wins

Every competitor solves one piece: wallets, cards, billing, or a new chain. None solve governance.

**The cross-rail moat:** Sardis works across Stripe, Base, Tempo, and Visa simultaneously. Incumbents only control their own walled gardens. Enterprises do not want Stripe lock-in for their AI policy layer. They want one governance plane that works across every rail their agents touch.

Sardis is the only platform that combines:
- 12-check deterministic policy engine (fail-closed, no LLM in execution path)
- Non-custodial MPC architecture (no MTL, no custody liability)
- 7 protocol implementations (AP2, TAP, x402, UCP, MPP, A2A, FIDES)
- Merkle-anchored append-only audit trail (on-chain, tamper-evident)
- Spending mandates with full lifecycle (7-dimension scoped authority)
- Multi-rail execution under one policy boundary (card + USDC + bank)

**The EWaaS distribution moat:** Sardis is built on Turnkey MPC, the same infrastructure powering Moonshot, Infinex, and Magic Eden. When Turnkey launched Embedded Wallet-as-a-Service in April 2026, Sardis became a launch case study. Every one of our 15+ framework SDKs (CrewAI, LangChain, AutoGPT, Browser Use, Composio, OpenAI Agents SDK, Claude Agent SDK, Vercel AI SDK, n8n, Activepieces, E2B, MCP) spins up Turnkey sub-orgs on behalf of agents. Every new agent using a Sardis SDK is a new wallet on Turnkey's platform. This is a two-sided advantage: we ride Turnkey's Series B-funded security audit and regulatory work, and Turnkey rides Sardis into every major agent framework. Competitors who roll their own MPC take on custody liability and a 12-month audit timeline. Sardis shipped on day one.

**Analogy:** Alloy built identity orchestration for humans across rails. Sardis builds payment governance for AI agents across rails. The value is in the control plane, not the rails themselves.

---

## Slide 9 -- Why Now

**Three forces are converging in 2026. This window will not stay open.**

### 1. Regulatory Signal: Compliance-First AI Is Now Required

- Google, PayPal, Mastercard, and Visa published AP2 (Agent Payment Protocol) as a consortium standard. It requires a mandate chain: Intent, Cart, Payment. Sardis implements full AP2 verification.
- The EU AI Act mandates auditability for high-risk AI applications. Financial transactions are high-risk.
- SOC2 and PCI auditors are already asking "how do you govern AI agent access to payment systems?"

The compliance bar is rising. Whoever builds the compliance-first infrastructure layer now becomes the default.

### 2. Market Signal: Financial Agents Are Going Live

- Stripe launched MPP (Machine Payments Protocol) with Tempo Labs on March 18, 2026. Sardis has early access.
- Coinbase shipped x402 for paid API access by agents. Sardis implements x402 with policy guard.
- Google launched A2A (Agent-to-Agent) protocol with 50+ partners. Sardis implements A2A with escrow.
- 40% of enterprise apps will include task-specific AI agents by end of 2026 (Gartner).

The agents are arriving. The governance layer is missing.

### 3. Settlement Signal: Stablecoins for B2B

- Circle USDC has $60B+ in circulation.
- Base (Coinbase L2) has the cheapest, fastest USDC settlement.
- Agent-to-agent payments are inherently programmable and stablecoin-native.
- Sardis is the governance layer that makes stablecoin settlement by agents auditable and compliant.

**The timing argument:** Building rails is a commodity race. Building governance before the rails mature is a moat. The companies that own the trust and compliance layer during the adoption wave will own it permanently, because switching governance providers is harder than switching rails.

---

## Slide 10 -- Social Proof

**[Design partner quote placeholder] - Title, Company**

> Note to self: Get a real quote from your strongest SDK user this week. Reach out to Activepieces (live integration), AutoGPT (Nicolas), or a top npm/PyPI downloader. One authentic sentence from a real user is worth more than any metric on the previous slide.

47+ API endpoints and 21 published packages, all built solo. The foundational control plane is shipped while competitors are still writing whitepapers.

---

## Slide 11 -- Team

**Solo technical founder. Speed of one, depth of a team.**

**Efe Baran Durmaz, Founder and CEO**
- Age 20. Building full-time since November 2025.
- Bilkent University, BA Information Systems and Technologies (full merit scholarship: tuition + housing + stipend).
- Ranked 1,405th out of 3,527,443 in Turkey's national university entrance exam (top 0.04%).
- 3x High Honor, 3.53 GPA.
- Nokia AI and Backend Engineer (Sep-Dec 2025), Nokia Network Engineer (Jul-Aug 2025).
- 49 public GitHub repos. Polyglot: Python, TypeScript, Rust, Go, Solidity, Java, C++.
- 1,800+ commits, 21 published packages at v1.1.0, 47+ API endpoints, 15 framework integrations, 7 protocol implementations -- all solo.

**Advisory Network:**
Conversations with individuals at Coinbase, Base, Stripe, Bridge, Lightspark, Solana, and Circle.

---

## Slide 12 -- "What You Need to Believe"

**The investment thesis in plain language.**

AI agents will become the primary economic actors of the next decade, and existing payment rails will never build cross-platform deterministic controls for them.

If you do not believe that, save us both the Zoom.

If you do believe it, then you need to also believe:

1. The governance layer must be built before the rails mature, not after.
2. Cross-rail is the only defensible position (Stripe will not build governance for Coinbase, and vice versa).
3. The compliance-first builder who ships the standard before the market needs it owns the category permanently.

Sardis is already there. 50K+ installs, 7 protocol implementations, 15 framework integrations, listed on mpp.dev/services. The foundational control plane is shipped.

---

## Slide 13 -- The Ask

**Raising a $3M Seed.**

I have out-shipped entire engineering teams solo to build the core infrastructure. This capital buys the one thing I cannot code: enterprise GTM and compliance credibility.

### Use of Funds

| Role | Purpose |
|------|---------|
| Forward Deployed Engineer | Convert design partners into paid deployments on-site |
| Enterprise GTM Lead | Enterprise sales motion, CFO-level relationships, pipeline |
| Tier-1 Security Audits | SOC2 completion ($15K DSALTA), code audit ($50K), E&O insurance |

### What You Get

- **Now:** 21-package platform live on Base mainnet. 50K+ SDK installs. 15 framework integrations. 7 protocol implementations. Stripe MPP early access. SOC2/PCI in progress. Listed on mpp.dev/services. sardis.pay() Phase 1-3 shipped.
- **6 months:** First paid enterprise pilots. 5+ design partners converted. SOC2 Type II certified. 3-person team.
- **12 months:** $1M+ ARR trajectory. 50+ paying customers across Dev/Business/Enterprise tiers. Full compliance stack.
- **18 months:** Series A readiness. $50-75K MRR. Governing $10M+ in monthly agent spend.

---

## Slide 14 -- Why Me (Solo Founder Narrative)

**I am 20 years old and I built the entire stack solo while the category was still forming.**

I can out-build a team of 10, but I have never sold enterprise software. I am raising this seed to hire the enterprise adults who will convert this developer obsession into paid deployments.

**The proof is in the build:**
- 1,800+ commits in ~20 weeks
- 21 published packages at v1.1.0
- 47+ production API endpoints
- 15 framework integrations
- 7 protocol implementations (AP2, TAP, x402, UCP, MPP, A2A, FIDES)
- Agent Auth Protocol support
- sardis.pay() Phase 1-3 shipped
- Listed on mpp.dev/services
- $0 marketing spend, 50K+ organic SDK installs

**What I know I need:** Enterprise GTM. Someone who has sold $100K+ annual contracts to CFOs. Someone who has navigated SOC2 procurement cycles. That is what this raise funds.

---

## Slide 15 -- Weakness Weaponization (Verbal Delivery Note)

> This slide is not in the deck. It is for verbal delivery when the investor asks "what is your biggest weakness?"

"If you pattern-match for 2nd-time B2B SaaS founders in their 30s, I am not your guy. If you want the technical obsessive who built the category standard before the incumbents realized what was happening, let's talk."

---

## Slide 16 -- Milestones and Series A Readiness

**Series A readiness: $50-75K MRR + governing $10M+ in monthly agent spend.**

| Milestone | Timeline | Metric |
|-----------|----------|--------|
| First paid enterprise pilot | Month 3 | Revenue > $0 |
| SOC2 Type II certified | Month 4 | Compliance gate cleared |
| 5 paying customers | Month 6 | $10-15K MRR |
| FDE + GTM Lead hired | Month 3-4 | Team of 3 |
| 20 paying customers | Month 9 | $30-40K MRR |
| $10M+ monthly TPV governed | Month 12 | Platform scale proof |
| Series A ready | Month 15-18 | $50-75K MRR, $10M+ monthly TPV |

---

## One-Pager (Integrated Below)

### SARDIS -- Payment OS for the Agent Economy

> "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust."

**Problem:** AI agents are becoming autonomous economic actors. But giving an agent direct wallet access means uncontrolled spending with no guardrails. There is no infrastructure for policy-controlled agent payments.

**Solution:** Non-custodial wallets with deterministic spending policies, approval workflows, kill switches, and anomaly detection. Sardis is the governance layer between AI intent and financial execution.

**Cross-Rail Moat:** Sardis works across Stripe, Base, Tempo, and Visa simultaneously. Incumbents only control their own walled gardens. Enterprises do not want Stripe lock-in for their AI policy layer.

**Proof of Build:** 47+ API endpoints and 21 published packages at v1.1.0, all built solo. We have the foundational control plane shipped while competitors are still writing whitepapers.

**Key Metrics:**

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

**Design Partners:**

| Partner | Status |
|---------|--------|
| Activepieces | LIVE, fully integrated |
| CrewAI | PR submitted |
| AutoGPT (180K GitHub stars) | In talks with founding engineer |
| Stripe MPP | Early access granted |

**Pricing:**

Open source to developers, SaaS seat licenses for the CFO who manages approvals, and BPS on cleared volume.

| Tier | Price |
|------|-------|
| Dev | Free (open source SDK, testnet) |
| Business | $199/seat/mo (mandate management, compliance dashboard, audit trail) |
| Enterprise | BPS on total payment volume governed (alignment with value delivered) |

**"What You Need to Believe" Thesis:** AI agents will become the primary economic actors of the next decade, and existing payment rails will never build cross-platform deterministic controls for them. If you do not believe that, save us both the Zoom.

**Tech Stack:** Safe Smart Accounts v1.4.1 + Turnkey MPC (non-custodial), Base/Ethereum/Polygon/Arbitrum/Optimism, USDC/USDT/EURC, Python 3.12, FastAPI, PostgreSQL, Solidity, React, TypeScript.

**Team:** Efe Baran Durmaz, sole founder, age 20. Built the entire stack solo. Bilkent University (full merit scholarship, top 0.04% national exam). Nokia AI Engineer. 49 public GitHub repos.

**The Ask:** Raising a $3M Seed. I have out-shipped entire engineering teams solo to build the core infrastructure. This capital buys the one thing I cannot code: enterprise GTM and compliance credibility. Use of funds: Forward Deployed Engineer, Enterprise GTM Lead, and Tier-1 Security Audits.

**Series A Readiness:** $50-75K MRR + governing $10M+ in monthly agent spend.

---

**Contact:** Efe Baran Durmaz | efe@sardis.sh | [sardis.sh](https://sardis.sh)
