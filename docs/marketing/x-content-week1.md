# X Content Bank - Week 1
# Cumartesi 1 Mart - Cuma 7 Mart 2026

**Account:** @efebarandurmaz (personal founder account)
**Rules:** No em dashes. No AI buzzwords. Human tone. English.
**Daily rhythm:** 3 posts/day + 5-10 strategic replies
**Posting times (TR):** 14:00, 18:00, 22:00

---

## DAY 1 - CUMARTESI 1 MART

Weekend = casual, personal. First impression day.

### Post 1 (14:00) - Introduction / Building in Public

```
I've been building in silence for 5 months.

190,000 lines of code. 23 published packages. 300+ API endpoints. 7 smart contracts. 9 framework integrations.

Solo.

Today I'm going to start talking about what I built and why.

It's called Sardis. It's infrastructure for AI agents to handle real money safely.

More soon.
```

### Post 2 (18:00) - The Problem (Hook)

```
Someone gave their AI agent a credit card last month.

The agent decided a $7,200 domain + online course was a good investment. Overnight. No approval. No spending limit. No kill switch.

The agent said it would pay for itself in 90 days.

This is not a hypothetical. This already happened.
```

### Post 3 (22:00) - The Thesis (Simple)

```
There are 500,000+ developers building AI agents right now.

Most of those agents will need to spend money at some point.

None of them have a safe way to do it.

That's the problem I'm solving.
```

**Reply targets:** Find 3-5 tweets about AI agents, agent frameworks, or AI spending money. Reply with genuine insight, not promotion.

---

## DAY 2 - PAZAR 2 MART

Weekend. More personal, more story.

### Post 1 (14:00) - Why I Built This

```
The moment I knew this had to exist:

I watched a demo where an AI agent booked flights, hotels, and rental cars. Impressive.

Then I asked: "What stops it from booking 50 flights?"

The answer was "nothing."

That's when I started building Sardis.
```

### Post 2 (18:00) - Building in Public (Code)

```
This is what a spending policy looks like on Sardis:

"Max $500 per day. Only SaaS vendors. Block gambling and adult content. Require approval above $200."

Plain English. No code.

The policy engine parses this into deterministic rules and enforces them before any payment executes.

If violated, no money moves. Period.
```

### Post 3 (22:00) - Agent Infra Trilogy Tease

```
Hot take: We talk a lot about making agents smarter.

Nobody talks about the three things agents actually need before they can operate in the real world:

1. Identity (who is this agent?)
2. Memory (what did it do before?)
3. A wallet (how does it pay for things?)

I'm building all three.
```

**Reply targets:** Engage with posts about LangChain, CrewAI, OpenAI agents, Google ADK. Add value, don't pitch.

---

## DAY 3 - PAZARTESI 3 MART

Business day. More technical, more assertive.

### Post 1 (14:00) - Market Validation

```
The market is speaking.

In the last 6 months, $66M+ has been poured into agent payments:

- Skyfire: $9.5M (a16z)
- Payman: $13.8M (Visa)
- Paid: $33.3M (Lightspeed)
- Natural: $9.8M

The category is being defined in real-time. Most solutions focus on the "how" (crypto rails, fiat wrappers) without solving the "who" (agent identity) or the "why" (spending policy).

That's where the real moat is. The logic layer, not just the rail.
```

### Post 2 (18:00) - Technical Credibility

```
What 190,000 lines of production code looks like:

- Policy engine: 150+ tests, 10-step validation, fuzz tested
- 5 blockchains (Base, Polygon, Ethereum, Arbitrum, Optimism)
- 7 smart contracts (ERC-4337, escrow, registry)
- KYC + AML + sanctions screening built in
- Virtual Visa/Mastercard issuance
- 9 framework SDKs (LangChain, CrewAI, OpenAI, Google ADK...)
- MCP server with 52 tools

Solo founder. 5 months.

Not a pitch deck. Not a landing page. Working infrastructure.
```

### Post 3 (22:00) - Hot Take

```
The question I keep getting: "Why not just use Stripe?"

Stripe is incredible. But it was built for a world where a human clicks "Buy."

When software is making 10,000 purchase decisions per hour, you need a different set of primitives:

- Per-transaction policy enforcement
- Agent-level identity verification
- Kill switches
- Audit trails per agent, not per user

Same goal (move money safely). Different architecture.
```

**Reply targets:** Respond to Stripe, PayPal, Coinbase agent payment announcements. Quote tweet with insight.

---

## DAY 4 - SALI 4 MART

AgitGit day. Introduce the second project.

### Post 1 (14:00) - AgitGit Introduction

```
What if every AI agent action was a git commit?

Every decision. Every API call. Every state change. Committed to a DAG with a SHA-256 hash.

Diffable. Revertable. Auditable.

That's AgitGit. Git for AI agents.

Your agent made a bad call? Revert it.
Two agents diverged? Merge their state.
Compliance audit? Here's the full history.

Built the core in Rust. SDKs in Python + TypeScript.
```

### Post 2 (18:00) - Why Agent Audit Trails Matter

```
The biggest unsolved problem with AI agents isn't hallucination.

It's accountability.

When an agent makes 500 decisions in an hour, you need to answer:
- What did it decide?
- Why?
- Can we undo it?

Today the answer to all three is "we don't know."

That has to change before agents get real autonomy.
```

### Post 3 (22:00) - Connecting the Dots

```
Two things I believe will be mandatory for production AI agents within 18 months:

1. Deterministic spending controls (not "the model will be careful")
2. Immutable action logs (not "we'll check the logs later")

Building both.

Sardis handles #1. AgitGit handles #2.
```

**Reply targets:** Engage with agent framework developers, AI safety discussions, enterprise AI threads.

---

## DAY 5 - CARSAMBA 5 MART

FIDES day. Complete the trilogy.

### Post 1 (14:00) - FIDES Introduction

```
Your AI agent has no ID.

No passport. No driver's license. No way to prove it is who it claims to be.

Right now, anyone can spin up an agent and claim it's "CompanyX's purchasing agent." Nothing stops them.

That's why I built FIDES. Decentralized identity for AI agents.

Ed25519 DIDs. HTTP message signatures (RFC 9421). Trust graph with reputation scoring.

Think of it as a passport system. But for software.
```

### Post 2 (18:00) - The Trilogy Complete

```
The Agent Infrastructure Trilogy:

FIDES: "Is this agent who it claims to be?"
AgitGit: "What has this agent done, and can we undo it?"
Sardis: "Can this agent safely spend money?"

Identity. Accountability. Financial trust.

You need all three before an agent can operate autonomously in the real world.

I'm building all three.
```

### Post 3 (22:00) - Why This Matters Now

```
Google, PayPal, Mastercard, and Visa are co-developing AP2. An agent payment protocol.

The biggest payment companies on earth are betting that agents will transact.

The infrastructure they'll transact through doesn't exist yet.

That's the race.
```

**Reply targets:** Engage with identity/auth discussions, Web3 identity threads, agent autonomy debates.

---

## DAY 6 - PERSEMBE 6 MART

Distribution + traction story.

### Post 1 (14:00) - Agent-Native Distribution

```
We got 9,880 package downloads last month. Zero ad spend. Zero marketing budget.

How?

Our docs are indexed on Context7. When a developer asks Cursor or Claude "how do I add payments to my AI agent?", the coding agent pulls our documentation and shows implementation examples.

Agents are selling our product to developers. Without us doing anything.

This is what agent-native distribution looks like.
```

### Post 2 (18:00) - MCP Server

```
I shipped an MCP server with 52 tools.

What this means: any AI agent running in Claude, Cursor, or Windsurf can create wallets, send payments, check balances, and set spending policies.

Without writing a single line of code.

Natural language in. Financial transaction out. Policy enforced.

That's the product.
```

### Post 3 (22:00) - Inbound Payments

```
Last week I shipped something none of our competitors have:

Inbound payments for AI agents.

Agents can now receive money, not just spend it.

Deposits, invoices, payment requests, x402 payee-side verification. Full lifecycle.

This turns an agent from a cost center into a revenue generator.

Agent freelancers. Agent SaaS businesses. Agent-to-agent commerce.

The agent economy just became bidirectional.
```

**Reply targets:** Engage with MCP discussions, Claude/Cursor communities, developer tool threads.

---

## DAY 7 - CUMA 7 MART

Week recap + forward looking.

### Post 1 (14:00) - Week 1 Recap Thread

```
Week 1 of building in public. Here's what I've shared:

1/ The $7,200 problem. AI agents with credit cards and no guardrails.

2/ Sardis. Policy-controlled wallets for AI agents. 190K lines of code, solo.

3/ AgitGit. Git for AI agents. Every action is a commit. Revertable.

4/ FIDES. Decentralized identity for agents. Ed25519 DIDs + trust graph.

5/ 9,880 downloads with zero marketing. Agent-native distribution through Context7 and MCP.

If you're building AI agents that need to handle money, identity, or accountability, I'd love to hear what problems you're running into.

DMs open.
```

### Post 2 (18:00) - Category Definition

```
Agent payments is becoming a real category. That's exciting.

But I think the conversation is too focused on rails (which chain? which card network?) and not enough on governance:

- What stops the agent from overspending?
- How do you verify an agent's identity?
- Where's the per-agent audit trail?

Rails are a commodity. The governance layer is the hard part.

That's what I spend most of my time on.
```

### Post 3 (22:00) - Forward Looking

```
Next week:

- Deep dive into how the policy engine actually works (with code)
- Why non-custodial architecture matters for agent wallets
- The real reason Google, PayPal, Mastercard, and Visa are building AP2 together

If you're working on anything related to AI agents + finance, follow along.

This space is moving fast.
```

**Reply targets:** Engage with weekly roundup threads, AI newsletters, VC tweets about agent economy.

---

## REPLY STRATEGY

### High-Value Accounts to Engage With
- AI framework creators (Harrison Chase/LangChain, Joao Moura/CrewAI)
- AI agent builders sharing demos
- VCs tweeting about agent economy
- Stripe, PayPal, Coinbase agent payment announcements
- Anyone sharing agent failure stories

### Reply Template (not copy-paste, adapt each time)
- Add genuine technical insight
- Share a relevant data point
- Ask a thoughtful question
- Never pitch Sardis directly in replies (first 2 weeks)
- If someone asks "what do you do?", one line: "I build payment infrastructure for AI agents. sardis.sh"

### Quote Tweet Opportunities
- Agent failure stories -> "This is exactly why..."
- Agent payment announcements -> Add context they missed
- "AI will replace X" takes -> "But first, agents need to..."

---

## METRICS TO TRACK (WEEK 1)

- Impressions per post
- Best performing post format (hot take vs code vs story)
- Reply engagement rate
- Follower growth
- DMs received
- Which time slot performs best

Adjust Week 2 content based on these signals.
