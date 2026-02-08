# Sardis Launch Day - Ready-to-Post Content

**Launch Date:** [TBD]
**Timezone:** All times in UTC

---

## Pre-Launch Checklist

- [ ] All social accounts verified and warmed up
- [ ] Waitlist page live at sardis.sh
- [ ] Analytics tracking enabled
- [ ] Team on standby for engagement
- [ ] Discord ready for community
- [ ] GitHub repos public (if applicable)

---

## Launch Day Schedule

| Time (UTC) | Platform | Action |
|------------|----------|--------|
| 06:00 | Twitter | Teaser post |
| 09:00 | Twitter | Main launch thread |
| 09:05 | LinkedIn | Launch post |
| 09:15 | Reddit r/artificial | Launch post |
| 09:30 | Reddit r/LocalLLaMA | Technical post |
| 12:00 | Twitter | Engagement check + reply to comments |
| 14:00 | Twitter | Behind-the-scenes post |
| 18:00 | Twitter | Thank you + metrics update |
| 21:00 | Twitter | Global audience recap |

---

## Twitter Posts

### 6:00 AM - Teaser

```
Something's launching today.

AI agents are about to get a lot more capable.

9 AM UTC.

sardis.sh
```

---

### 9:00 AM - Main Launch Thread

**Tweet 1:**
```
AI agents can book flights, manage calendars, and write code.

But they still can't safely spend money.

Until now.

Introducing Sardis - the Payment OS for the Agent Economy.

sardis.sh
```

**Tweet 2:**
```
The problem is simple:

When you give an AI agent payment access, you choose between:

- Full access (one hallucination away from disaster)
- Manual approval for everything (defeats automation)

There's no middle ground.

Until now.
```

**Tweet 3:**
```
Sardis is a financial firewall for AI agents.

Every transaction passes through your policy engine before execution.

Define rules in plain English:

"Max $50/day on subscriptions"
"Only approved vendors"
"Require approval over $200"
```

**Tweet 4:**
```
The architecture:

- Non-custodial MPC wallets (your keys, always)
- Real-time policy enforcement
- Multi-chain (Base, Polygon, Ethereum)
- USDC, USDT, EURC, PYUSD
- Full audit trail

You stay in control.
Agents stay productive.
```

**Tweet 5:**
```
Works with your stack:

- Claude Desktop / Cursor (MCP Server)
- LangChain (Python SDK)
- Vercel AI SDK (TypeScript)
- OpenAI Functions
- Any agent framework

One npm install. Zero config.

npm install @sardis/mcp-server
```

**Tweet 6:**
```
Built on industry standards:

- AP2 (Google/PayPal/Visa/Mastercard protocol)
- TAP for cryptographic identity
- A2A for agent-to-agent payments
- UCP for commerce flows

We're implementing the protocols that matter.
```

**Tweet 7:**
```
Use cases we're seeing:

- Agents managing cloud spend
- Automated subscription renewals with caps
- Research assistants with API budgets
- Multi-agent systems with shared wallets
- Enterprise expense automation
```

**Tweet 8:**
```
Open core model:

- SDKs are open source
- Self-host or use managed service
- Free tier: 100 transactions/month
- Pro: $49/month unlimited

We win when you ship.
```

**Tweet 9:**
```
Why now?

AI agents will manage $1T+ in transactions by 2027.

The question isn't IF agents will handle money.

It's WHO will make it safe.

That's us.
```

**Tweet 10:**
```
Join the waitlist for early access:

sardis.sh

We're here all day for questions.

Let's build the financial layer for the agent economy.
```

---

### 2:00 PM - Behind the Scenes

```
3 hours since launch. Here's what we're seeing:

- [X] waitlist signups
- Top use case: [insight]
- Most asked question: [question]

Building in public means sharing the real numbers.

More updates tonight.
```

---

### 6:00 PM - Thank You Post

```
6 hours of Sardis being public.

[X] people on the waitlist.
[X] messages in our inbox.
[X] hours until we start onboarding.

Thank you for the support.

The agent economy is inevitable. We're just building the rails.

sardis.sh
```

---

### 9:00 PM - Global Recap

```
As North America wraps up, here's where we stand:

Waitlist: [X]
Most excited about: [insight]
Already shipping: [feature/integration]

If you missed the thread this morning:

[QRT main thread]
```

---

## LinkedIn Post (9:05 AM)

```
Today, we're publicly launching Sardis - the Payment OS for the Agent Economy.

Here's why this matters:

AI agents have crossed a capability threshold. They can research, code, manage projects, and make complex decisions.

But there's one thing they still can't do safely: spend money.

The current solutions are inadequate:

1. Give agents your credit card (dangerous)
2. Approve every transaction manually (defeats automation)
3. Hope nothing goes wrong (not a strategy)

Sardis provides the missing layer: a policy engine that sits between agents and money.

What makes us different:

- Non-custodial architecture (we never hold your funds)
- Natural language policies ("Max $100/day, no gambling sites")
- Built on AP2/TAP standards (Google, PayPal, Visa backing)
- Multi-chain support (Base, Polygon, Ethereum)
- Works with any agent framework

We're looking for design partners who are building agent-powered products and need secure payment capabilities.

Early access: sardis.sh

The agent economy needs financial infrastructure. We're building it.

#AI #Fintech #Payments #AgentEconomy
```

---

## Reddit Posts

### r/artificial (9:15 AM)

**Title:** We built a financial firewall for AI agents - here's why it matters

```
Hey r/artificial,

Just launched Sardis - a policy engine that sits between AI agents and payments.

The problem we're solving:

AI agents are getting autonomous. They can research, code, manage tasks. But giving them payment access is still terrifying. They hallucinate. They misunderstand context. They optimize for the wrong thing.

Current options:
1. Give agents raw API keys (risky)
2. Approve everything manually (defeats the purpose)

Our approach:

1. Agents get their own wallet (non-custodial, MPC-based)
2. You define spending policies in plain English
3. Every transaction is checked against your rules before execution
4. Full audit trail of what was spent and why

Example policies:
- "Max $50/day on SaaS subscriptions"
- "No transactions over $200 without approval"
- "Only pay vendors on this whitelist"

Technical stack:
- Works with Claude, GPT, LangChain, any framework
- Multi-chain (Base, Polygon, Ethereum)
- Stablecoins (USDC, USDT, etc.)
- Built on AP2/TAP protocols

We're early and want feedback.

Questions for the community:
- What policies would you want for your agents?
- What use cases are we missing?
- What's your biggest concern about agent financial autonomy?

Link: sardis.sh

Happy to answer technical questions.

(Disclosure: I'm one of the founders)
```

---

### r/LocalLLaMA (9:30 AM)

**Title:** Self-hosted payment infrastructure for local AI agents

```
For those running local models that need to interact with the real world:

We just released our Python SDK for Sardis - a payment policy engine for AI agents.

The core problem: Your local agent needs to buy API credits, pay for services, make real transactions. But you don't want to give it raw access to your cards/accounts.

What we built:

1. Non-custodial wallets (you control keys via MPC)
2. Policy engine (spending limits, category restrictions, time windows)
3. Audit logging
4. Multi-chain support

Self-hostable components:
- Policy engine (Python)
- SDK integrations
- Logging

Managed (or bring your own):
- MPC key management (we use Turnkey)
- Chain execution
- Compliance checks

Works with any local model/agent framework. Just wraps your existing logic with safety rails.

Code example:

```python
from sardis import Wallet, Policy

policy = Policy(
    max_per_transaction=100,
    daily_limit=500,
    allowed_categories=["software", "apis"]
)

wallet = Wallet(policy=policy)

# Agent tries to pay
result = await wallet.pay(
    to="api-provider.com",
    amount=50
)  # Allowed

result = await wallet.pay(
    to="random-site.com",
    amount=1000
)  # Blocked by policy
```

GitHub: [link]
Docs: sardis.sh/docs

Looking for feedback from the local-first community. What would make this more useful for self-hosted setups?
```

---

### r/startups (Optional - Post Day 2)

**Title:** Looking for design partners - building payment infrastructure for AI agents

```
Hey founders,

We just launched Sardis - programmable wallets with policy enforcement for AI agents.

Think "Brex for bots."

Quick context: AI agents are getting good at tasks, but they hit a wall when money is involved. Either you give them full access (risky) or approve everything manually (slow).

We're looking for design partners who:
- Are building agent-powered products
- Need agents to make purchases autonomously
- Want to avoid the "agent spent $10k on my card" nightmare

What we offer early partners:
- Direct Slack/Discord access to our team
- Custom policy development
- Free tier during beta
- Input on roadmap

Current integrations:
- LangChain
- Claude (MCP Server)
- OpenAI
- Vercel AI SDK

If this sounds relevant, drop a comment or DM.

sardis.sh
```

---

## Hacker News (Optional - Post Day 2-3)

**Title:** Show HN: Sardis - Payment OS for AI Agents

```
Hi HN,

We built Sardis, a policy engine that lets AI agents make payments safely.

The problem: When agents need to buy things (API credits, subscriptions, services), you either give them full access or approve everything manually. Neither works at scale.

Our solution: Non-custodial wallets with spending policies.

Example:
```python
policy = Policy(
    max_daily=500,
    require_approval_above=200,
    allowed_merchants=["aws.amazon.com", "openai.com"]
)
```

Technical details:
- MPC wallets via Turnkey (non-custodial)
- Multi-chain (Base, Polygon, Ethereum)
- Stablecoins (USDC, USDT)
- Built on AP2/TAP protocols
- Python + TypeScript SDKs

Open core: SDKs are open source. Managed service for infrastructure.

What we'd love feedback on:
1. Policy language - is plain English better than code?
2. Which chains/tokens should we prioritize?
3. What compliance requirements matter to you?

Link: https://sardis.sh
GitHub: [link]
Docs: https://sardis.sh/docs
```

---

## Discord Announcement (Internal Community)

```
@everyone

We're live! Sardis is now public.

What's launching:
- Waitlist at sardis.sh
- Open source SDKs
- Documentation
- Discord community (you're here!)

How you can help:
1. Share the launch on your socials (main thread linked below)
2. Upvote on Reddit if you find it useful
3. Invite other agent builders to Discord

Links:
- Twitter thread: [link]
- LinkedIn: [link]
- Reddit: [link]
- Website: sardis.sh

Thank you for being early supporters. The agent economy starts now.
```

---

## Response Templates for Launch Day

### Positive Comment
```
Thank you! Really appreciate the support. Let us know if you have questions as you explore.
```

### Question About Pricing
```
Free tier: 100 transactions/month. Pro: $49/month unlimited. Enterprise: custom. All details at sardis.sh/pricing

Happy to chat about what fits your use case.
```

### Question About Security
```
Non-custodial architecture - we never hold funds. MPC via Turnkey for key management. Full audit logging. Happy to dive deeper on specifics if helpful.
```

### "How is this different from X?"
```
Great question. [Competitor] focuses on [their focus]. We're specifically built for agent autonomy with policy enforcement. The key difference is [specific differentiator]. Happy to compare in detail if helpful.
```

### Technical Question
```
[Answer]. Full technical docs at sardis.sh/docs. Also happy to jump on a quick call if you want to discuss implementation.
```

### Partnership/Integration Request
```
Love to explore this. Drop us a line at [email] or DM here. We're actively looking for integration partners.
```

---

## Metrics to Track (Real-time on Launch Day)

| Metric | Check Every | Target |
|--------|-------------|--------|
| Waitlist signups | 1 hour | 500 first day |
| Twitter impressions | 2 hours | 50K+ |
| Tweet engagement rate | 2 hours | 5%+ |
| Reddit upvotes | 2 hours | 100+ |
| Direct messages | Continuous | Respond within 2h |
| Mentions | Continuous | Respond within 1h |

---

## Post-Launch Day (Day 2-7)

### Day 2
- Thank you thread with real numbers
- r/startups post
- Highlight interesting comments/questions

### Day 3
- Hacker News post
- First "what we learned" thread
- Product update based on feedback

### Day 4-5
- Continue engagement
- Reach out to influencers who engaged
- Start working waitlist for calls

### Day 6-7
- Week 1 recap thread
- LinkedIn article on launch learnings
- Community spotlight

---

**Ready to execute. All posts can be scheduled in Typefully or your preferred scheduler.**
