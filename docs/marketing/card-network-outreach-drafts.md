# Card Network Outreach — Email & LinkedIn Drafts

**Date:** 2026-03-09
**Status:** Ready to send (Week 2-3 per execution plan)

---

## 1. Stripe — Jeff Weinstein (Product Lead, Payments Infrastructure)

### LinkedIn Connection Request (300 char)
```
Hi Jeff — I'm building Sardis, the trust layer for AI agent payments. We're aligned with Stripe's x402 protocol (USDC on Base) and building on top of Stripe's agentic commerce stack. Would love to connect and explore SPT integration.
```

### Email
```
Subject: Sardis — agent payment trust layer + Stripe x402/SPT integration

Hi Jeff,

I'm Efe, founder of Sardis. We're building the trust and control plane
for AI agent payments — deterministic spending policies, risk scoring,
approval workflows, and tamper-evident audit trails, all without holding
private keys.

We're live on Base mainnet with USDC, which makes us natively compatible
with Stripe's x402 protocol. We've also built 9 AI framework integrations
(LangChain, CrewAI, OpenAI Agents SDK, Vercel AI SDK, etc.) that could
serve as distribution for Stripe's Shared Payment Tokens.

What we're exploring:

1. SPT integration — letting agents pay via Stripe's tokenized
   credentials while Sardis enforces spending policies
2. ACP alignment — our policy engine maps cleanly to ACP's
   Delegated Payment Spec
3. x402 native — we're already USDC/Base, the exact stack

Our differentiator: we're not just routing payments — we score every
transaction (0-1.0 trust score), enforce fail-closed policies written
in plain English, and provide kill switches + circuit breakers.
No other agent payment company does this.

Would 15 minutes be useful to explore integration opportunities?

Efe Baran Durmaz
Founder, Sardis
sardis.sh | github.com/EfeDurmaz16/sardis
```

---

## 2. Stripe — Jacob Petrie (Head of Developer Relations)

### LinkedIn Connection Request
```
Hi Jacob — building Sardis (agent payment trust layer). We have 9 AI framework SDK integrations and an MCP server. Strong overlap with Stripe's developer ecosystem — would love to explore partnership.
```

### Email
```
Subject: Sardis — 9 AI framework SDKs + Stripe developer ecosystem overlap

Hi Jacob,

I'm Efe, founder of Sardis — the trust layer for AI agent payments.

Quick context on developer surface:

- 9 AI framework SDKs: LangChain, CrewAI, OpenAI Agents, Claude Agent SDK,
  Vercel AI SDK, Google ADK, Composio, Browser Use, AutoGPT
- MCP server for Claude/Cursor
- PRs submitted to LangChain, Vercel AI SDK, Google ADK, Coinbase AgentKit
- npm + PyPI packages published

Every one of these frameworks has developers who need agents to pay for
things. Right now there's no standard way to do it safely — Sardis
provides the policy engine, and Stripe provides the payment rails.

We've also applied to Tempo x Stripe hackathon and the Partner Intake
program. Would love to explore how Sardis fits into Stripe's agentic
commerce developer story.

15 minutes to chat?

Efe Baran Durmaz
Founder, Sardis
sardis.sh
```

---

## 3. Visa — Rubail Birwadker (SVP, Head of Growth, Products & Partnerships)

### LinkedIn Connection Request
```
Hi Rubail — building Sardis, the trust layer for AI agent payments. We implement the Trusted Agent Protocol and see strong alignment with Visa Intelligent Commerce. Would love to connect.
```

### Email
```
Subject: Sardis — TAP implementation + Visa Intelligent Commerce integration

Hi Rubail,

I'm Efe, founder of Sardis. We're building the financial operating system
for AI agents — and we already implement the Trusted Agent Protocol for
cryptographic agent identity verification.

Sardis provides what VIC needs on the control side:

- Deterministic spending policies — agents can only spend within
  human-defined rules (dollar limits, merchant categories, time windows)
- 4-tier confidence routing — low-risk payments auto-approve,
  unusual ones escalate to human review
- Kill switches — freeze any agent's spending in milliseconds
- Tamper-evident audit trail — every decision logged and signed

We're live on Base mainnet with 9 AI framework integrations. Our MCP
server aligns with Visa's recently launched MCP server for developer
tooling.

Integration opportunity: Sardis as the policy and governance layer
for Visa's agentic tokenization — agents get Visa network tokens,
Sardis enforces the spending rules and provides the audit trail.

Would 20 minutes be valuable to explore this?

Efe Baran Durmaz
Founder, Sardis
sardis.sh
```

---

## 4. Mastercard — Jorn Lambert (Chief Product Officer)

### LinkedIn Connection Request
```
Hi Jorn — building Sardis, the trust layer for AI agent payments. We've applied to Start Path (agentic commerce track) and see strong alignment with Mastercard Agent Pay. Would love to discuss.
```

### Email
```
Subject: Sardis x Mastercard Agent Pay — Start Path application + pilot proposal

Hi Jorn,

I'm Efe, founder of Sardis. We've applied to Mastercard's Start Path
program (agentic commerce track) and wanted to share why we believe
the fit is strong.

Mastercard Agent Pay solves the credential side — giving agents
authenticated, traceable tokens. Sardis solves the governance side —
ensuring agents only spend what they're allowed to.

What Sardis adds to Agent Pay:

1. Policy engine — spending rules in plain English
   ("max $500/day, only SaaS vendors, no gambling")
2. Risk scoring — every transaction gets a 0-1.0 trust score
3. Approval workflows — high-risk payments require human sign-off
4. Goal drift detection — catches agents spending outside their mission
5. Kill switches — instant freeze on any agent

We're the only platform combining all of this with MPC custody,
multi-chain support, virtual cards, KYC/AML, and 9 AI framework SDKs.

Currently live on Base mainnet with active revenue collection.

Happy to walk through a live demo or discuss pilot scope.

Efe Baran Durmaz
Founder, Sardis
sardis.sh
```

---

## 5. Mastercard — Pablo Fourez (Chief Digital Officer)

### LinkedIn Connection Request
```
Hi Pablo — founder of Sardis (agent payment control plane). Applied to Start Path agentic commerce track. Building the governance layer that makes Agent Pay production-safe. Would love to connect.
```

### Email
```
Subject: Sardis — governance layer for Mastercard's agentic commerce vision

Hi Pablo,

I'm Efe, founder of Sardis. We build the trust layer between AI agents
and real money — and we believe this is the missing piece for
Mastercard's agentic commerce rollout.

The challenge: as Agent Pay scales, merchants and enterprises need
assurance that AI-initiated payments are governed, auditable, and
controllable. That's exactly what Sardis provides.

Quick stats:
- 1,095 commits, solo founder, 5 months
- 39 packages in monorepo
- 9 AI framework SDKs (LangChain, CrewAI, OpenAI, etc.)
- 5 protocol compliances (AP2, TAP, x402, UCP, A2A)
- Live on Base mainnet with fee collection
- The only agent payment platform with policy engine + risk scoring
  + kill switches + approval workflows + audit trail

We've applied to Start Path (agentic commerce track). Would welcome
the chance to discuss how Sardis fits into Mastercard's agent commerce
roadmap.

Efe Baran Durmaz
Founder, Sardis
sardis.sh
```

---

## Send Schedule

| Contact | Channel | Target Date |
|---------|---------|-------------|
| Jeff Weinstein (Stripe) | LinkedIn + Email | Week 2 (March 15-21) |
| Jacob Petrie (Stripe) | LinkedIn + Email | Week 2 (March 15-21) |
| Rubail Birwadker (Visa) | LinkedIn + Email | Week 3 (March 22-28) |
| Jorn Lambert (Mastercard) | LinkedIn + Email | Week 3 (March 22-28) |
| Pablo Fourez (Mastercard) | LinkedIn + Email | Week 3 (March 22-28) |

## Follow-up Cadence
- Day 5: Short follow-up if no response
- Day 12: Final touch with new angle (hackathon results, new traction)
