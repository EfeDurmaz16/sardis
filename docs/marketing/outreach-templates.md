# Cold Outreach Templates — Per Wedge

Updated: 2026-03-24 | 4 wedges, each with initial email + Day 3 follow-up
Rule: Under 140 words each. Problem-first framing. No jargon.

## Wedge A: Secure AI Payments
Buyer: Head of AI Automation. Subject: [Company] AI agents + payment safety

### Initial Email
Hi [First Name],
Your AI agents handle real money. What happens when one retries a failed API call 10 times?
Most teams discover the answer on their credit card statement. Retry overspend, decimal parsing errors, and payments to wrong endpoints are the three ways agents lose money.
Sardis prevents this. sardis.pay() gives your agent a policy-controlled wallet:
- Spending rules in plain English ("max $500/day on dev tools")
- 12-check policy pipeline before every transaction
- Non-custodial MPC signing — you never store private keys
- Cryptographic audit trail
Live on mainnet. 15 framework integrations (OpenAI, Claude, CrewAI, LangChain).
Worth 15 minutes this week?
— Efe Baran Durmaz, Founder, Sardis | sardis.sh

### Day 3 Follow-Up
Hi [First Name],
Following up briefly. Agent payment failures cluster around three patterns: retry overspend, decimal drift, and vendor mismatch. Each one is preventable with structured spending mandates. Happy to share how other teams handle it. — Efe

---

## Wedge B: Automated API Payments
Buyer: API Developer / SaaS Founder. Subject: Monetize your API for AI agents (zero-friction)

### Initial Email
Hi [First Name],
AI agents consume APIs without a human in the loop. Stripe checkout does not work when your "customer" is a GPT-4 agent.
Sardis solves this with x402 API gating. Your API returns HTTP 402, the agent wallet pays automatically, you receive USDC settlement in real-time.
How it works: 1) Add one header to your API response 2) Agent wallet auto-pays (policy-checked, audited) 3) You receive USDC settlement 4) Full transaction log in your dashboard.
Integrated with Stripe MPP (early access). 50K agents already have Sardis wallets.
Worth 10 minutes?
— Efe Baran Durmaz, Founder, Sardis | sardis.sh

### Day 3 Follow-Up
Hi [First Name],
Every agent payment through your API gets AML-screened automatically, plus a Merkle-anchored audit trail. If agent-to-API payments are on your roadmap, happy to share market insights. — Efe

---

## Wedge C: Cross-Border Payments
Buyer: CFO / Head of Treasury. Subject: USDC/EURC instant settlement (skip SWIFT)

### Initial Email
Hi [First Name],
[Company] operates across US and EU markets. Cross-border via SWIFT: 2-3 days, 1-3% fees.
Sardis settles USDC-to-EURC in 1.5 seconds at 5-15 basis points:
- Atomic FX swap across 3 venues (Tempo DEX, Uniswap V3, Circle Mint)
- Settlement in seconds, not days
- MiCA-compliant audit trail for EU regulatory requirements
- KYB, AML/sanctions, SAR auto-filing built in
Your treasury deposits USDC, sets a mandate, Sardis handles FX + settlement + compliance.
Would a 15-minute walkthrough help?
— Efe Baran Durmaz, Founder, Sardis | sardis.sh

### Day 3 Follow-Up
Hi [First Name],
We support MiCA compliance out of the box — Article 66 reporting, 72-hour SAR filing, CASP tracking. If expanding EU operations, this saves 3-6 months of compliance buildout. — Efe

---

## Wedge D: Compliance Infrastructure
Buyer: CCO / Head of Risk. Subject: Agent compliance infrastructure (KYC + AML + audit)

### Initial Email
Hi [First Name],
As [Company] deploys AI agents with financial access, regulators ask: "Who is the agent? What can it spend? Where is the audit trail?"
Sardis provides the full compliance stack:
- KYC/KYB verification (Didit)
- Real-time AML/sanctions screening (6 providers, OFAC/EU/UN)
- Know Your Agent — identity attestation + trust scoring
- SAR auto-filing (FinCEN Form 111 XML export)
- MiCA compliance (EU CASP tracking)
- Merkle-anchored audit trail — tamper-evident, any auditor can verify
15 production-grade compliance modules. Most Series B fintechs do not have this stack.
— Efe Baran Durmaz, Founder, Sardis | sardis.sh

### Day 3 Follow-Up
Hi [First Name],
Regulatory landscape for AI agents is moving fast — NIST published agent standards in February, MiCA enforcement is live. We built this from day one so teams do not retrofit later. — Efe
