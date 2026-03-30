# YC S26 Application Rewrite, Round 6

**Date:** 2026-03-30
**Status:** Draft — review before sending
**What changed since Round 5:** Mainnet payment executed, Stripe MPP production access, 24 paid API endpoints live, 50K+ installs, 4-layer trust stack narrative.

---

## Final Checks Before Sending

1. **Install count** — 50K+ (verify with npm/PyPI dashboards).
2. **Mainnet TX** — 0x5d304f056868528321d97fc1a5495e2c9ce8eb40b47e7de786d69423a1e2faec on Tempo mainnet.
3. **Revenue claim** — "first machine-to-machine payments via MPP." Not "revenue" in the traditional SaaS sense yet. Be precise.
4. **Trust stack** — mention FIDES/AGIT/OSP only where it adds signal, don't overwhelm. YC cares about one business, not four projects.
5. **Chain count** — Tempo mainnet + Base (via Relay bridge). Don't inflate.
6. **Stripe wording** — "production access granted" not "partnership."

---

## Best One-Line Frame

**API keys are blank checks. Sardis is the policy layer that makes them safe.**

Still the sharpest frame. Round 6 adds proof: the policy layer now runs on mainnet and earns per-request revenue.

---

## Submission-Ready Answers

### Describe what your company does in 50 characters or less.

```text
Safe payments for AI agents
```

### What is your company going to make? Please describe your product and what it does or will do.

```text
Today, giving an AI agent access to money means handing it an API key. API keys are blank checks — there is no built-in concept of "spend up to $100" or "only pay approved vendors." A single prompt injection can drain an account.

Sardis is the policy enforcement layer between AI agents and money. Developers give each agent a wallet and rules like "max $100/day, only AWS and OpenAI, require human approval above $500." Every payment passes through a 12-check policy pipeline before it clears.

If a payment breaks policy, it is blocked instantly and logged. The model never gets unrestricted spending authority; final execution is decided by policy, approvals, and runtime checks. We support stablecoins and virtual cards, so the same controls work across crypto-native and traditional merchants.
```

*[Unchanged from R5 — this answer is strong.]*

### Where do you live now, and where would the company be based after YC?

```text
Ankara, Turkey now. San Francisco after YC.
```

### Explain your decision regarding location.

```text
Turkey lets me build with low burn and high speed. After YC I would move to San Francisco because the companies and teams shaping this stack are there: payments infrastructure, stablecoins, and AI developer platforms.
```

### How far along are you?

```text
Built solo in six months. Live on mainnet:

- First mainnet payment executed on Tempo — $1 USDC, signed via Turnkey MPC, settled on-chain
- 24 pay-per-request API endpoints live via Stripe MPP — policy checks, risk scoring, compliance screening, all earning per-call revenue from machine-to-machine payments
- 48 published packages across npm and PyPI, 50K+ installs with zero paid acquisition
- 15+ framework integrations (Claude MCP, OpenAI Agents, Google ADK, Vercel AI SDK, CrewAI, AutoGPT, Activepieces, and more)
- Stripe granted MPP production access — one of the first developers in the private Machine Payments beta
- 3 wallet funding channels active (Coinbase Onramp, Stripe Crypto Onramp, Relay cross-chain bridge)

Activepieces integration is live in their marketplace. OpenClaw skill published with 8 tools. 12-check policy pipeline enforced on every payment.

We went from testnet to mainnet payments in one week.
```

### How long have each of you been working on this? How much of that has been full-time?

```text
Solo founder. Full-time for six months.

The first two months were customer discovery and ecosystem research. The last four months have been focused on building. I ship unusually fast because I use Claude Code heavily as a development tool.
```

### What tech stack are you using, or planning to use, to build this product? Include AI models and AI coding tools you use.

```text
Python/FastAPI backend, PostgreSQL, Redis, React/TypeScript frontend, and Solidity smart contracts. Turnkey for MPC wallet signing, Stripe for virtual cards and machine payments (MPP), Coinbase and Relay for on/off-ramp and cross-chain bridging, and compliance providers for KYC and sanctions. I use Claude Code heavily for development and OpenAI models for natural-language policy parsing.
```

### Are people using your product?

```text
Yes. Developers are installing the packages, using the MCP server, and testing Sardis in sandbox and staging environments. We also process machine-to-machine payments through 24 MPP-gated endpoints on Tempo mainnet — AI agents pay per request to access policy checks, risk scoring, and compliance data.
```

### How many active users or customers do you have? How many are paying? Who is paying you the most, and how much do they pay you?

```text
50K+ package installs with zero paid acquisition. No traditional SaaS customers yet.

We have a different kind of early revenue: 24 API endpoints that charge per request via Stripe's Machine Payments Protocol. Any AI agent can pay $0.001-$0.10 per call for policy evaluation, risk scoring, or compliance screening — no signup required, just an on-chain micropayment. Authenticated users (API key holders) get the same endpoints free.

This is not meaningful revenue yet, but it proves the model works: AI agents paying for intelligence services, enforced at the protocol level.
```

### Do you have revenue?

```text
Early. We process machine-to-machine micropayments through 24 MPP-gated API endpoints on Tempo mainnet. Per-request pricing ranges from $0.001 (FX rates) to $0.10 (compliance screening). This is protocol-level revenue — agents pay per call without any human signup flow. It is small but real and on-chain.
```

### If you are applying with the same idea as a previous batch, did anything change? If you applied with a different idea, why did you pivot and what did you learn from the last idea?

```text
Same idea, significant progress since last application:

- Mainnet: went from "mainnet is the next milestone" to executed first mainnet payment on Tempo
- Revenue: went from "no revenue" to 24 pay-per-request endpoints processing machine payments
- Stripe: went from "MPP early access" to production access granted
- Installs: went from 15K to 50K+
- Packages: went from 34 to 48
- Funding channels: 3 active (Coinbase, Stripe Crypto, Relay bridge)

The core thesis has not changed. The execution has accelerated.
```

### Why did you pick this idea to work on? Do you have domain expertise in this area? How do you know people need what you're making?

```text
I picked this after building AI agents myself and hitting the same wall every time: the agent could reason and act, but the moment it needed to pay for something, the workflow broke.

Giving an LLM a normal payment credential is unsafe, and requiring manual approval on every purchase defeats autonomy. Sardis exists to let agents spend, but only within clear, enforceable limits.

The timing shifted fast. Stripe launched MPP, Visa launched TAP, Google shipped AP2, Coinbase deployed x402 — all in Q1 2026. They are building rails. The missing piece is the authorization and lifecycle layer above those rails: what is allowed, what needs approval, and what gets blocked. That is the layer Sardis is building.
```

*[Unchanged — still strong.]*

### Who are your competitors? What do you understand about your business that they don't?

```text
Direct competitors include Skyfire ($8.5M raised), Payman ($3M), Sapiom, and Locus. Stripe and Coinbase are building rails, not the control layer.

The real competitor is DIY engineering — startups bounding API keys with prompt instructions that a single prompt injection bypasses.

What we understand: the hard problem is not connecting agents to payment rails. Six companies already do that. The hard problem is controlling authority over money — enforcing what an agent can buy, how much it can spend, when it needs human approval, and proving every action in an audit trail.

We are the only team with a trust stack behind the policy layer: agent identity verification (FIDES), tamper-evident policy versioning (AGIT), and an open service provisioning standard (OSP) where Sardis is the default payment rail. No competitor has all three.

Every new protocol that launches increases the need for an agnostic policy layer. Fragmentation is the moat.
```

### How do or will you make money? How much could you make?

```text
Three revenue lines, one already live:

1. Pay-per-request intelligence (LIVE): 24 API endpoints charge $0.001-$0.10 per call via Stripe MPP. Policy checks, risk scores, compliance screening, audit proofs. Any AI agent can pay without signing up.

2. SaaS: $49-$499/mo for policy engine, approvals dashboard, and full audit trail. Subscribers get the same 24 endpoints free.

3. Transaction fees: 0.1-0.5% per payment processed through our pipeline.

The wedge is pay-per-request: zero friction acquisition. Agents that call our API enough will upgrade to a subscription because it is cheaper. Enterprise customers moving volume through Sardis pay transaction fees on top.
```

### If you had any other ideas you considered applying with, please list them.

```text
OSP (Open Service Protocol): an open standard for AI agents to provision developer services like databases, hosting, and analytics — no browser, no CAPTCHA. Think of it as the open alternative to Stripe Projects. 10 provider integrations, 4 SDKs (Rust, TypeScript, Python, Go). I wrote the 10,000-line protocol spec. OSP feeds directly into Sardis as the default payment rail.

YULA: persistent memory infrastructure for AI agents. I built an earlier version and learned that memory is useful, but payments are the more urgent problem.
```

### Please tell us in one or two sentences about the most impressive thing other than this startup that you have built or achieved.

```text
I ranked 1,405th out of 3.5 million students on Turkey's national university exam and earned a full merit scholarship. I also built a Rust package manager from scratch (23x faster than npm) with enterprise supply-chain security features that no existing tool has — provenance verification, dependency firewalls, and script sandboxing.
```

### Tell us about things you've built before.

```text
I have built developer tools, agent infrastructure, and one shipped game — all solo.

A Rust package manager that installs 23x faster than npm with supply-chain security built in. AgentGit, a version control system for AI agent state with a Rust core and Python/Node bindings. FIDES, a decentralized trust protocol for agent identity. An open protocol spec for AI agent service provisioning (OSP). A multiplayer game released on Steam. At Nokia as an AI Engineer, I rebuilt part of their enterprise RAG indexing pipeline to handle 300K files.

These are not side projects. Each one solves a layer of the same trust problem that Sardis addresses for payments.
```

### Are you looking for a cofounder?

```text
Yes. Priority is a GTM co-pilot — someone who has sold compliance infrastructure or developer tools to enterprises. I can out-build anyone; I need someone who can out-sell. I would also consider a technical cofounder with deep payments or crypto-infrastructure experience.
```

---

## Changes from Round 5

| Field | Round 5 | Round 6 |
|-------|---------|---------|
| Installs | 15K+ | 50K+ |
| Packages | 34 | 48 |
| Mainnet | "next milestone" | First tx executed (0x5d304f...) |
| Revenue | "No" | "Early — 24 MPP endpoints, per-request micropayments" |
| Stripe MPP | "early access" | "production access granted" |
| Framework integrations | 15 | 15+ (OpenClaw skill added) |
| Funding channels | not mentioned | 3 active (Coinbase, Stripe Crypto, Relay) |
| Competitors | listed | added funding amounts, added trust stack differentiator |
| Other projects | brief mention | OSP elevated to "other ideas", better-npm in "impressive thing" |
| Revenue model | theoretical 3 lines | line 1 is LIVE |
| "Same idea, what changed" | N/A (different idea) | Detailed progress diff |

## Tone

Same as R5 but with receipts. Every claim now has proof:
- "We process payments" → mainnet tx hash
- "Stripe relationship" → production access granted
- "Revenue model works" → 24 endpoints live, agents paying per call
- "Trust stack" → FIDES, AGIT, OSP — not just mentioned, integrated

The application should read like:

**"This founder shipped mainnet payments solo in six months, got into Stripe's private beta, and already has protocol-level revenue from machine-to-machine micropayments."**
