# First X Thread — Sardis Introduction

**Account:** @sardis_sh (or Efe's personal)
**When to post:** Weekday, 9-10 AM EST (US tech audience waking up)
**Pin this thread after posting**

---

## THE THREAD

**Tweet 1 (Hook)**

I've been building payment infrastructure for AI agents for the last 6 months.

Here's the problem nobody's solving properly:

AI agents can book flights, write code, and manage your calendar — but the moment they need to spend $5 on an API call, everything breaks.

**Tweet 2 (The Reality)**

Right now, companies giving AI agents financial access do one of these:

- Share a corporate credit card (zero controls)
- Hard-code API keys with unlimited spend
- Route every $2 transaction through a human approval queue

None of these scale. None of these are safe.

**Tweet 3 (The Insight)**

The core problem: payment infrastructure was built for humans.

Humans authenticate with passwords. Agents don't have passwords.
Humans review charges monthly. Agents make 10,000 transactions/day.
Humans understand context. Agents need explicit policy boundaries.

Agents need their own financial identity.

**Tweet 4 (What I Built)**

So I built Sardis — a payment OS for AI agents.

Every agent gets:
- Its own wallet (non-custodial, MPC key management)
- Spending policies in plain English ("max $500/day, only whitelisted vendors")
- Virtual cards via Lithic for fiat purchases
- Optional on-chain settlement via USDC
- Full audit trail for every transaction

**Tweet 5 (How It Works)**

The flow is simple:

1. Agent decides to buy something
2. Sardis checks the spending policy
3. If approved → issues a one-time virtual card or executes on-chain
4. Receipt logged, audit trail updated
5. If denied → agent gets a clear reason why

No human in the loop. Policy-enforced autonomy.

**Tweet 6 (MCP Server)**

We built an MCP server with 36 tools.

If you use Claude Desktop, your agent can:
- Create wallets
- Set spending policies in natural language
- Execute payments
- Check balances
- Query transaction history

One config line in your claude_desktop_config.json.

**Tweet 7 (Why Non-Custodial Matters)**

Most competitors hold your agent's funds (custodial).

Sardis uses MPC — the private key is split across multiple parties. Neither Sardis, nor the agent, nor the developer holds the full key.

Why it matters: if we get hacked, your funds are still safe. That's the whole point.

**Tweet 8 (The Stack)**

Full stack if you're curious:

- Custody: Turnkey (MPC)
- Cards: Lithic (virtual Visa/Mastercard)
- KYC: Persona
- AML: Elliptic
- Chains: Base, Polygon, Ethereum, Arbitrum, Optimism
- SDKs: Python + TypeScript
- Protocols: AP2 (Google/Visa/MC/PayPal) + x402 (Coinbase) settlement

**Tweet 9 (Where I Am)**

Solo founder, building from Istanbul.

Testnet is live. Onboarding design partners now — companies whose AI agents need to handle money.

If your agents are spending on API credits, processing refunds, managing procurement, or executing trades — this is for you.

**Tweet 10 (CTA)**

If this resonates:

- Follow for build updates (posting the journey openly)
- Check sardis.sh for docs
- Book a 30-min call if you want to integrate: cal.com/sardis/30min

DMs open. Especially interested in talking to anyone building AI agents that touch financial workflows.

---

## ALT: SHORT VERSION (if you prefer fewer tweets)

**Tweet 1**

I'm building payment infrastructure for AI agents.

The problem: agents can do everything except spend money safely.

Companies either share corporate cards (no controls) or route every $2 through human approval (doesn't scale).

**Tweet 2**

Sardis gives every AI agent its own financial identity:

- Virtual cards (Visa/Mastercard via Lithic)
- Spending policies in plain English
- Non-custodial MPC wallets
- Full audit trail

Agent decides to buy → policy check → virtual card issued → done.

**Tweet 3**

Built an MCP server with 36 tools for Claude Desktop.

Python + TypeScript SDKs for everything else.

Solo founder, Istanbul. Testnet live, onboarding design partners now.

sardis.sh
cal.com/sardis/30min

DMs open.

---

## FOLLOW-UP TWEETS (Post over next 2-3 days, keep the momentum)

**Day 2 — Technical depth**

Building non-custodial wallets for AI agents using MPC (multi-party computation).

Quick explainer on why this matters:

Custodial = company holds your keys. If they get hacked, your money is gone.

MPC = key is split. No single party has the full key. Even if Sardis gets compromised, funds are safe.

This is the same tech that Fireblocks uses for institutional custody. We're bringing it to AI agents.

**Day 2 — Engagement bait**

Honest question for builders:

If your AI agent had a $500/day budget to spend autonomously — what would it buy first?

Curious what use cases people are thinking about.

**Day 3 — Competitor awareness**

There are now 5+ companies building "payment infra for AI agents."

The split:
- Custodial (they hold your agent's money)
- Non-custodial (nobody holds the full key)

I'm building non-custodial. Here's why that matters for enterprise adoption...

[thread about why enterprises won't trust custodial agent wallets]

**Day 3 — Design partner social proof (when you get one)**

First design partner signed.

[Company X] is integrating Sardis so their AI agents can [specific use case].

Onboarding more this month. DM if your agents need to handle money.
