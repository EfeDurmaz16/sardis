# Sardis Pre-Launch Content Plan

> **Hybrid Approach: 2-3 Week Pre-Launch → Product Hunt**

---

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│  WEEK 1: Problem Awareness                                  │
│  "AI agents have a money problem"                           │
│  → Build credibility, start conversations                   │
├─────────────────────────────────────────────────────────────┤
│  WEEK 2: Solution Teasing                                   │
│  "We're building something..."                              │
│  → Create anticipation, collect waitlist                    │
├─────────────────────────────────────────────────────────────┤
│  WEEK 3: Product Hunt Launch                                │
│  "It's here."                                               │
│  → Full launch with warm audience                           │
└─────────────────────────────────────────────────────────────┘
```

---

# WEEK 1: Problem Awareness

## Day 1 (Monday) - Twitter Thread #1: The Problem

```
1/ AI agents are getting scary good at:

• Booking flights
• Managing calendars
• Writing code
• Research & analysis

But there's one thing they still can't do safely:

Spend money. 🧵

2/ Here's the reality:

Your AI agent needs to:
- Buy API credits when they run out
- Pay for SaaS subscriptions
- Order supplies
- Book services

But HOW do you let it pay?

3/ Option 1: Give it your credit card

"Here's my card number, go wild"

Result: Agent "optimizes" by upgrading everything to enterprise tiers

$3,000 bill. In one night.

(Yes, this happened to me)

4/ Option 2: Approve everything manually

Agent: "Can I buy this $5 API credit?"
You: "Yes"
Agent: "Can I renew this $12 subscription?"
You: "Yes"
Agent: "Can I..."
You: "I THOUGHT YOU WERE AUTONOMOUS"

Defeats the entire purpose.

5/ Option 3: API keys with spending limits

Better, but:
- Limits are crude (just $ amounts)
- No context awareness
- No time-based rules
- No merchant restrictions
- No audit trail

Still scary.

6/ The real problem:

AI agents don't understand money the way humans do.

They don't know:
- "That's too expensive"
- "We don't buy from that vendor"
- "Not on weekends"
- "Check with me first if it's over $100"

7/ What we actually need:

Wallets for AI agents with POLICIES.

Not just spending limits.

Real policies like:
- "Max $50/day on cloud services"
- "Only approved vendors"
- "Require human approval over $200"
- "No transactions after business hours"

8/ This is the missing infrastructure layer.

AI agents are ready.
Payment rails exist.

But the TRUST layer in between?

That's what's missing.

9/ We're working on this.

More soon.

If you're building AI agents that need to handle money, I'd love to hear your horror stories.

What's the worst thing your agent has spent money on?
```

---

## Day 2 (Tuesday) - Reddit Post #1

**Subreddit:** r/artificial

**Title:** How are you handling payments in your AI agents? Current solutions seem broken

```
Hey r/artificial,

I've been building AI agents for a while and keep hitting the same wall: payments.

My agent needs to autonomously:
- Purchase API credits when they run low
- Pay for web scraping services
- Manage subscription renewals
- Buy data from various providers

The current options all suck:

**Option 1: Full credit card access**
Gave my agent my card details. It decided to "optimize costs" by upgrading my OpenAI account to the highest tier. $500 surprise.

**Option 2: Pre-paid accounts everywhere**
Works but incredibly tedious. Need separate accounts for every service. Agent can't adapt to new services.

**Option 3: Manual approval**
"Hey, can I spend $3?" Yes. "Can I spend $7?" Yes. Repeat 50x daily. Why do I even have an agent?

**Option 4: API keys with limits**
Better, but limits are too crude. Can't say "only for these merchants" or "not after 6pm" or "ask me if it's over $100."

---

**What I think we need:**

Some kind of agent-specific wallet with policy enforcement. Where you can set rules in plain English:

- "Max $100/day on infrastructure"
- "Only these approved vendors: [list]"
- "Require approval for anything over $50"
- "No gambling, adult, or crypto purchases"

And get a full audit trail of what the agent spent and why.

---

**Questions for this community:**

1. How are you solving this today?
2. Would you use something like this if it existed?
3. What policies would you want to set?
4. Any horror stories to share?

Genuinely trying to understand if this is a common pain point or just me.
```

---

## Day 3 (Wednesday) - Twitter Thread #2: Horror Stories

```
1/ I asked AI developers about their agent payment horror stories.

The responses were... concerning. 🧵

2/ @developer1 (anonymized):

"My research agent decided the best way to gather data was to buy premium subscriptions to 14 different services.

Monthly recurring.

Found out 3 months later."

Damage: $2,400

3/ @developer2:

"Gave my agent access to AWS.

It 'optimized for speed' by spinning up GPU instances.

I got an email from Amazon about unusual spending.

$8,000 in 4 hours."

4/ @developer3:

"My booking agent found a 'great deal' on flights.

Business class. Refundable.

'Refundable means no risk, right?'

It booked 6 flights I didn't need."

Damage: Credit card limit

5/ @developer4:

"Agent needed to buy API credits.

Bought credits on 3 different platforms.

'For redundancy.'

I only use one of them."

6/ The pattern is clear:

AI agents optimize for their goal.

They don't understand:
- Budget constraints
- Approval workflows
- Vendor policies
- Time restrictions
- Common sense

7/ The solution isn't to remove payment access.

Agents NEED to spend money to be useful.

The solution is GUARDRAILS.

Policies that the agent cannot override.

8/ Imagine:

"This wallet has a max of $50/day. Only for these 5 vendors. Require human approval over $25. Log everything."

Agent can operate freely WITHIN those bounds.

But can't go rogue.

9/ This is what we're building.

More details coming soon.

Follow for updates. DMs open if you have your own horror story to share.
```

---

## Day 4 (Thursday) - LinkedIn Post #1: Thought Leadership

```
The $1.7 trillion problem nobody's talking about.

AI agents are transforming how we work. They can research, code, analyze, and automate complex tasks.

But there's a fundamental capability we've been avoiding:

Letting them spend money.

---

Here's why this matters:

McKinsey projects that AI agents will manage over $1.7 trillion in transactions by 2030.

But today? We're stuck choosing between two bad options:

1. Give agents full access to payment methods (terrifying)
2. Require human approval for every transaction (defeats automation)

Neither works at scale.

---

What's needed is a trust layer.

Not just spending limits – real policies:

• "Max $500/day on approved vendors"
• "Require approval for transactions over $200"
• "Only during business hours"
• "Full audit trail for compliance"

Think of it like corporate expense policies, but enforced in real-time for AI agents.

---

The companies that solve this will unlock the next wave of AI automation.

The ones that don't will either:
- Limit their agents' capabilities
- Accept significant financial risk
- Burn resources on manual approvals

---

This is the infrastructure gap I'm most excited about right now.

Who else is thinking about this problem?

#AI #Fintech #AgentEconomy #Automation
```

---

## Day 5 (Friday) - Twitter Thread #3: The Market

```
1/ AI agents managing money isn't science fiction.

It's happening NOW.

Here's what the data says: 🧵

2/ Transaction volume through AI agents grew 35,000% in the last 30 days.

(Source: industry reports)

Not a typo. Thirty-five thousand percent.

3/ Google, PayPal, Mastercard, and Visa just announced the Agent Payment Protocol (AP2).

60+ partners.

They're not building this for fun. They see what's coming.

4/ OpenAI and Stripe are working on ACP (Agentic Commerce Protocol).

Coinbase launched x402 for agent micropayments.

Every major player is racing to build agent payment rails.

5/ Why?

Because AI agents are only as useful as what they can DO.

And in the real world, doing things costs money.

Research? Costs money.
APIs? Cost money.
Services? Cost money.
Goods? Cost money.

6/ The problem:

Rails are being built.
Agents are ready.
But the TRUST layer is missing.

How do you let an agent spend money without giving it unlimited access?

7/ This is what we're working on.

Non-custodial wallets for AI agents.
Natural language spending policies.
Real-time enforcement.
Complete audit trail.

8/ If you're building agents that need to handle money, I want to talk.

What policies would YOU need?

DMs open.

More details dropping next week.
```

---

## Day 6 (Saturday) - Reddit Post #2

**Subreddit:** r/LocalLLaMA

**Title:** Building payment infrastructure for local AI agents - looking for technical feedback

```
Hey r/LocalLLaMA,

Working on something I think this community might find interesting, and I'd love technical feedback.

**The Problem:**

I run local agents that need to interact with the real world - buying API credits, paying for services, etc. The current solutions are all either:

1. Custodial (some company holds my funds) - no thanks
2. Give raw card access to the agent - terrifying
3. Manual approval for everything - defeats automation

**What I'm Building:**

A wallet system for AI agents where:

- **Non-custodial**: Uses MPC (multi-party computation) so you always control the keys
- **Policy engine**: Set rules in plain English like "max $50/day on cloud services"
- **Local-first**: Python SDK that works with any agent framework
- **Audit trail**: Complete log of what was spent and why

**Technical approach:**

```python
from sardis import Sardis

client = Sardis(api_key="...")

wallet = client.create_wallet(
    chain="base",  # or polygon, ethereum
    policy={
        "max_daily": "100.00",
        "max_per_tx": "25.00",
        "allowed_merchants": ["openai.com", "anthropic.com"],
        "require_approval_above": "50.00"
    }
)

# Agent can now spend within these bounds
result = wallet.pay(
    to="0x...",
    amount="10.00",
    memo="API credits"
)
```

**What I'm looking for:**

1. Does this architecture make sense?
2. What policies would you want?
3. Any security concerns I should address?
4. Would you use something like this?

The SDK will be open source. Core infra is managed but we're considering self-host options for the paranoid (respect).

Happy to answer technical questions.
```

---

## Day 7 (Sunday) - Twitter Thread #4: Why Now

```
1/ "Why are you building agent payment infrastructure NOW?"

I get this question a lot.

Here's my answer: 🧵

2/ Three things just happened:

A) AI agents got good enough to be trusted with complex tasks

B) Major players started building agent payment protocols (AP2, ACP, x402)

C) MPC custody became production-ready

The timing is perfect.

3/ On agent capability:

2023: Agents could chat
2024: Agents could use tools
2025: Agents can complete complex workflows

We're past the "can agents do useful things?" debate.

They can. They are.

4/ On payment protocols:

Google + 60 partners → AP2 (Agent Payment Protocol)
OpenAI + Stripe → ACP
Coinbase → x402

When Google, PayPal, Visa, Mastercard, OpenAI, and Coinbase all build the same thing?

The market is telling you something.

5/ On MPC custody:

Multi-party computation used to be:
- Expensive
- Slow
- Hard to implement

Now it's:
- Commodity
- Fast
- Production-ready

Non-custodial agent wallets are finally practical.

6/ The window is NOW.

Too early? Agents couldn't do enough.
Too late? Market is dominated.

Right now? Infrastructure is ready, protocols are emerging, but the trust layer is missing.

That's the gap we're filling.

7/ What we're building:

- Non-custodial MPC wallets for agents
- Natural language spending policies
- Works with AP2, TAP, x402
- Python & TypeScript SDKs
- Full audit trail

8/ Launching soon.

Follow for updates.

If you're building agents that need to spend money, DM me for early access.

The future is autonomous. Let's make it safe.
```

---

# WEEK 2: Solution Teasing

## Day 8 (Monday) - Teaser Tweet + Waitlist

```
We've been working on something for the last few months.

AI agents that can safely spend money.

Non-custodial wallets.
Natural language policies.
Real-time enforcement.

Early access opening soon.

Like this + drop a "🔐" to get on the list.
```

**Follow-up tweet (same thread):**

```
What you'll get with early access:

✅ First to use the SDK
✅ Direct line to our team
✅ Input on features
✅ Free tier during beta
✅ Exclusive Discord

Launching on Product Hunt in [2 weeks].

Early access = head start.
```

---

## Day 9 (Tuesday) - Demo GIF Tweet

```
POV: Your AI agent just made its first purchase.

Within the spending limits YOU set.
With full audit trail.
Without ever touching your credit card.

[DEMO GIF: Agent requesting payment → policy check → approval → transaction → confirmation]

This is Sardis.

Early access: [waitlist link]
```

---

## Day 10 (Wednesday) - Feature Highlight: Policies

```
"Max $50/day on OpenAI"
"Only approved vendors"
"Require my approval over $100"
"No transactions on weekends"

This is how you control AI agent spending with Sardis.

Plain English. Real-time enforcement.

No more hoping your agent doesn't go rogue.

[SCREENSHOT: Policy editor UI]

Early access: [link]
```

---

## Day 11 (Thursday) - Technical Thread

```
1/ How we built non-custodial wallets for AI agents.

A technical thread for the curious: 🧵

2/ The challenge:

Agents need to spend money autonomously.
But users need to stay in control.

Traditional custody doesn't work.
Giving agents raw keys is insane.

3/ Our approach: MPC + Policy Layer

MPC (Multi-Party Computation) means:
- Private key is split across multiple parties
- No single party can sign alone
- User always maintains control

4/ The policy engine sits between the agent and the wallet.

Every transaction request goes through:

Agent → Policy Check → MPC Signing → Blockchain

If policy fails? Transaction blocked.

No exceptions. No overrides.

5/ Policies are defined in natural language:

"max $100/day on infrastructure costs"

We parse this into structured rules:

{
  "type": "daily_limit",
  "amount": 100.00,
  "category": "infrastructure"
}

6/ Why natural language?

Because policies should be readable by humans.

Your CFO should be able to audit agent spending rules.

Not just your engineers.

7/ The audit trail:

Every transaction logged:
- What was requested
- Which policy was checked
- Whether it passed/failed
- Full transaction details
- Agent reasoning (if provided)

8/ Multi-chain support:

- Base (fast, cheap, Coinbase)
- Polygon (established, MATIC)
- Ethereum (when you need L1)
- More coming

Stablecoins: USDC, USDT, EURC

9/ SDK is simple:

```python
wallet = sardis.create_wallet(
    policy="Max $50/day, only approved vendors"
)

result = wallet.pay(
    to=merchant,
    amount=25.00,
    memo="API credits"
)
```

10/ Launching soon on Product Hunt.

If you're building agents that need payment capabilities:

Early access: [link]

Technical questions? I'm here.
```

---

## Day 12 (Friday) - Influencer DMs

**Template for AI Framework Developers:**

```
Hey [Name],

Big fan of your work on [specific project/content].

We're building Sardis - payment infrastructure for AI agents. Non-custodial wallets with natural language spending policies.

Would love to give you early access before our PH launch next week.

What we offer:
- Priority access to SDK
- Direct support from our team
- Your feedback shapes the product

If it's useful for [their framework/project], we'd love to explore an integration.

No pressure either way. Just thought you'd find it interesting.

[Your name]
```

**Template for AI Influencers:**

```
Hey [Name],

Your content on [specific topic] has been super helpful.

We're launching Sardis next week - the missing piece for AI agents that need to spend money.

Non-custodial wallets + natural language policies.

Would love to give you a demo and early access if you're interested.

Happy to answer any questions about the agent payment space in general too.

[Your name]
```

**Template for Developers with Agent Projects:**

```
Hey [Name],

Saw your [project name] - really cool implementation.

Quick question: how are you handling payments/purchases for the agent?

We just built something that might help - agent wallets with spending policies. Launching on PH soon.

Happy to give you early access if useful.

Either way, [project name] is awesome. Keep building.

[Your name]
```

---

## Day 13 (Saturday) - Integration Teaser

```
Sardis works with:

🔷 Claude Desktop (MCP server)
🦜 LangChain
▲ Vercel AI SDK
🤖 OpenAI Functions
🐪 LlamaIndex

One SDK. Every framework.

Your agent can start spending safely in 5 minutes.

Launching Tuesday on @ProductHunt

Early access: [link]

[IMAGE: Integration logos grid]
```

---

## Day 14 (Sunday) - Pre-Launch Hype

```
48 hours until launch.

Sardis: The Payment OS for the Agent Economy

🔐 Non-custodial MPC wallets
📝 Natural language spending policies
⚡ Real-time policy enforcement
🔗 Multi-chain (Base, Polygon, Ethereum)
🔌 Works with Claude, LangChain, OpenAI

Ready to let your AI agent spend money safely?

See you Tuesday on @ProductHunt.

[Pre-launch page link]
```

**Follow-up tweet:**

```
What we're NOT:

❌ Custodial (we never hold your funds)
❌ Just another payment API
❌ Crypto-first (stablecoins + virtual cards)
❌ Code-only policies (plain English)

What we ARE:

The trust layer between AI agents and your money.

Tuesday. Product Hunt.

LFG.
```

---

# Additional Content Assets

## Twitter Bio Update (Week 2)

```
Building @SardisPayments - Payment OS for the Agent Economy 🔐

Non-custodial wallets for AI agents. Natural language spending policies.

Launching soon 👇
```

---

## Pinned Tweet (Week 2)

```
AI agents can reason, but they can't be trusted with money.

We're building Sardis to change that:

🔐 Non-custodial MPC wallets
📝 Natural language spending policies
⚡ Real-time enforcement
🔗 Multi-chain support

Launching soon on @ProductHunt

Join the waitlist: [link]
```

---

## Email to Waitlist (Day before launch)

**Subject:** We launch tomorrow - here's how you can help 🚀

```
Hey [Name],

Tomorrow at 12:01 AM PT, Sardis goes live on Product Hunt.

You signed up early, so I wanted to give you a heads up.

**3 ways to help (if you want to):**

1. Upvote on Product Hunt when it goes live
2. Leave a comment with your thoughts/questions
3. Share with anyone building AI agents

**The link will be:** [PH link]

**What you get for supporting:**

- Priority access to the SDK
- 3 months free on Pro tier
- Direct Slack channel with our team
- Input on the roadmap

Thank you for believing in this early.

Let's show the world that AI agents can be trusted with money.

See you tomorrow.

[Your name]

P.S. - Reply to this email if you want early SDK access TODAY, before the public launch.
```

---

## Waitlist Landing Page Copy

**Headline:**
```
AI agents can reason.
Now they can safely spend.
```

**Subhead:**
```
Non-custodial wallets with natural language spending policies.
The payment infrastructure AI agents need.
```

**Bullet points:**
```
🔐 Non-custodial MPC wallets - you always control the funds
📝 Policies in plain English - "max $50/day on approved vendors"
⚡ Real-time enforcement - agent can't override your rules
🔗 Multi-chain - Base, Polygon, Ethereum, more coming
🔌 Every framework - Claude, LangChain, OpenAI, Vercel AI
```

**CTA:**
```
Join the waitlist for early access

[Email input] [Get Early Access]

Launching on Product Hunt [date]
```

---

## Content Calendar Summary

| Day | Platform | Content Type | Goal |
|-----|----------|--------------|------|
| 1 (Mon) | Twitter | Thread: The Problem | Awareness |
| 2 (Tue) | Reddit | Discussion: r/artificial | Engagement |
| 3 (Wed) | Twitter | Thread: Horror Stories | Social proof |
| 4 (Thu) | LinkedIn | Thought Leadership | B2B credibility |
| 5 (Fri) | Twitter | Thread: The Market | Validation |
| 6 (Sat) | Reddit | Technical: r/LocalLLaMA | Developer cred |
| 7 (Sun) | Twitter | Thread: Why Now | Momentum |
| 8 (Mon) | Twitter | Teaser + Waitlist | Conversion |
| 9 (Tue) | Twitter | Demo GIF | Visual proof |
| 10 (Wed) | Twitter | Feature: Policies | Education |
| 11 (Thu) | Twitter | Technical Thread | Developer trust |
| 12 (Fri) | DMs | Influencer Outreach | Partnerships |
| 13 (Sat) | Twitter | Integration Teaser | Ecosystem |
| 14 (Sun) | Twitter | Pre-Launch Hype | Final push |
| 15 (Mon) | Email | Waitlist Reminder | Activation |
| 16 (Tue) | ALL | Product Hunt Launch | 🚀 |

---

## Metrics to Track

### Week 1 Targets
- Twitter followers gained: +200-500
- Total impressions: 50K+
- Reddit upvotes: 100+
- Reddit comments: 50+
- LinkedIn engagement: 50+ reactions

### Week 2 Targets
- Twitter followers gained: +500-1000
- Waitlist signups: 300-500
- Influencer responses: 10+
- Demo video views: 5K+
- Pre-launch PH saves: 100+

---

*Ready to execute. Adjust timing and specific details as needed.*
