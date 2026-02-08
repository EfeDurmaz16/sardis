# Sardis Marketing & GTM Content

## X (Twitter) Posts

### Launch Thread

```
1/ AI agents can now book flights, manage calendars, and write code.

But they still can't safely spend money.

Until now.

Introducing Sardis — the Payment OS for the Agent Economy 🧵

2/ The problem: When you give an AI agent access to payments, you're trusting it with your money.

But agents hallucinate. They make mistakes. They don't understand "that's too expensive."

One bad API call = your credit card maxed out.

3/ Sardis is a financial firewall for AI agents.

✅ Non-custodial MPC wallets (your keys, always)
✅ Natural language policies: "Max $50/day on subscriptions"
✅ Real-time transaction blocking
✅ Full audit trail

4/ Works with the tools you already use:

• Claude Desktop / Cursor → MCP Server
• LangChain → Python SDK
• Vercel AI SDK → TypeScript
• OpenAI Functions → Native support

Zero config. One npm install.

5/ Multi-chain from day one:

• Base, Polygon, Ethereum
• USDC, USDT, EURC, PYUSD
• Instant virtual cards via Lithic
• Fiat off-ramps

6/ Built on industry standards:

• AP2 (Google/PayPal/Visa/Mastercard protocol)
• TAP for cryptographic identity
• A2A for agent-to-agent payments
• UCP for commerce flows

7/ Open core model:

• SDKs are open source
• Self-host or use our managed service
• Enterprise features for teams

8/ AI agents will manage $1T+ in transactions by 2027.

The question isn't IF agents will handle money.
It's WHO will make it safe.

We're building that trust layer.

→ sardis.sh
```

### Standalone Posts

```
🔥 Hot take: Giving AI agents your credit card is like giving a toddler your car keys.

They might get somewhere. They might also crash.

Sardis = the seatbelt for agent payments.

sardis.sh
```

```
POV: Your AI agent just spent $3,000 on cloud credits because it "optimized" your infrastructure.

This is why we built Sardis.

Natural language spending limits. Real-time blocking. Full audit trail.

Never again.
```

```
"But I already use API keys for payments"

API keys don't understand:
- "Only for work expenses"
- "Max $100 per transaction"
- "No gambling sites"
- "Require approval over $500"

Sardis does.
```

```
New: Sardis MCP Server for Claude Desktop

Your AI assistant can now:
✅ Check wallet balance
✅ Send payments (with policy checks)
✅ Request spending increases
✅ Track transaction history

All without touching your private keys.

npm install @sardis/mcp-server
```

---

## Reddit Posts

### r/artificial

**Title:** We built a "financial firewall" for AI agents - here's why it matters

```
Hey r/artificial,

I've been thinking a lot about agent safety, specifically around money.

Current state: AI agents can browse the web, write code, manage files. But when it comes to payments? We either:
1. Give them raw API keys (dangerous)
2. Require human approval for everything (defeats the purpose)

We built Sardis to solve this. It's essentially a policy engine that sits between your agent and your money.

You write rules in plain English:
- "Max $50/day on SaaS subscriptions"
- "No transactions over $200 without approval"
- "Only pay vendors on this whitelist"

The agent gets a wallet it controls (MPC, non-custodial), but every transaction passes through your policy firewall first.

Technical details:
- Works with Claude, LangChain, OpenAI, Vercel AI SDK
- Multi-chain (Base, Polygon, Ethereum)
- Stablecoins + virtual cards for fiat
- Full audit trail

Open source SDKs, managed service for the infrastructure.

Curious what this community thinks about agent financial autonomy. Is this a real problem you're hitting? What policies would you want?

Link: sardis.sh
```

### r/LocalLLaMA

**Title:** Self-hosted payment infrastructure for local AI agents

```
For those running local agents that need to interact with the real world (buying API credits, paying for services, etc.):

We open-sourced our Python/TypeScript SDKs for Sardis - it's a payment policy engine for AI agents.

The idea: your agent gets a wallet, but transactions must pass policy checks you define. Prevents the "oops my agent spent $5000 on GPU credits" scenario.

Self-hostable components:
- Policy engine (Python)
- SDK integrations
- Audit logging

Managed components (or BYO):
- MPC key management
- Chain execution
- Compliance checks

Works with any agent framework. Happy to answer technical questions.

GitHub: [link]
```

### r/ChatGPT & r/ClaudeAI

**Title:** Gave my AI assistant a spending budget - here's how

```
Wanted to share something I've been using: Sardis lets you give Claude/ChatGPT a wallet with spending rules.

Setup:
1. Install MCP server (for Claude Desktop) or use the API
2. Define policies: "Up to $20/day, only for these categories"
3. Agent can now make purchases within those limits

Use cases I've found useful:
- Letting Claude buy small tools/APIs it needs
- Automated subscription management
- Paying for research resources

The key is it's non-custodial (your keys via MPC) and every transaction is logged. You can see exactly what the agent spent and why.

Anyone else experimenting with giving agents financial autonomy?
```

### r/startups

**Title:** Building payment rails for AI agents - looking for early design partners

```
Hey founders,

Quick context: AI agents are getting good at tasks, but they hit a wall when money is involved. Either you give them full access (risky) or approve everything manually (slow).

We're building Sardis - programmable wallets with policy enforcement for AI agents. Think "Brex for bots."

Looking for design partners who:
- Are building agent-powered products
- Need agents to make purchases autonomously
- Want to avoid the "agent spent $10k on my card" nightmare

What we offer early partners:
- Direct Slack/Discord access to our team
- Custom policy development
- Free tier during beta
- Input on roadmap

If this sounds relevant, drop a comment or DM. Happy to do a quick call.
```

---

## Product Hunt Launch

### Tagline Options

1. "AI agents can reason. Now they can safely spend."
2. "The financial firewall for AI agents"
3. "Give your AI assistant a wallet, not your credit card"

### Description

```
# Sardis - Payment OS for the Agent Economy

AI agents are transforming how we work. They can research, code, and manage complex tasks. But there's one thing they still can't do safely: spend money.

**The Problem**
When you give an agent payment access today, you're choosing between:
- 🔓 Full access (dangerous - agents make mistakes)
- 🔐 Manual approval for everything (slow - defeats automation)

**The Solution**
Sardis is a financial firewall for AI agents. Define spending policies in plain English, and let your agents transact within safe boundaries.

## Key Features

🔐 **Non-Custodial MPC Wallets**
Agents control keys via Turnkey MPC. You never lose custody.

📝 **Natural Language Policies**
"Max $100/day on developer tools, require approval over $50"

⚡ **Real-Time Enforcement**
Every transaction checked against policies before execution.

💳 **Instant Virtual Cards**
Issue cards on-demand for fiat payments via Lithic.

🔗 **Multi-Chain Support**
Base, Polygon, Ethereum with USDC, USDT, EURC.

## Integrations

Works with your existing stack:
- Claude Desktop / Cursor (MCP Server)
- LangChain (Python SDK)
- Vercel AI SDK (TypeScript)
- OpenAI Functions

## Use Cases

- Let Claude manage small purchases autonomously
- Automate subscription renewals with spending caps
- Agent-to-agent payments for multi-agent systems
- Enterprise expense management for AI tools

## Pricing

- **Free**: 100 transactions/month
- **Pro**: $49/month - unlimited transactions
- **Enterprise**: Custom policies, dedicated support

---

Built by developers who got tired of babysitting their AI agents' spending.

Questions? We're here all day! 👇
```

### First Comment (Maker)

```
Hey Product Hunt! 👋

I'm [Name], founder of Sardis.

The idea came from a personal pain point: I gave my Claude assistant access to buy API credits, and it "optimized" by purchasing a $500 enterprise plan I didn't need.

That's when I realized: agents don't understand money the way humans do. They need guardrails.

Sardis is those guardrails. You set the rules, agents follow them, everyone's happy.

A few things I'm proud of:
- Zero-config MCP server for Claude Desktop
- Policies in actual English (not YAML/JSON)
- Full audit trail for every transaction
- Open source SDKs

Would love your feedback on:
1. What policies would you want for your agents?
2. Which integrations should we prioritize?
3. Any edge cases we should handle?

Happy to answer any questions! 🙏
```

---

## GTM & Marketing Strategy

### Phase 1: Developer-First Launch (Months 1-2)

**Channels:**
- Product Hunt launch
- Hacker News "Show HN"
- Dev Twitter/X threads
- r/LocalLLaMA, r/artificial, r/LangChain

**Content:**
- Technical blog posts on agent payment security
- YouTube tutorials: "Add payments to your AI agent in 5 minutes"
- GitHub examples and templates

**Metrics:**
- GitHub stars
- npm/pip downloads
- Discord community size

### Phase 2: Framework Partnerships (Months 2-4)

**Targets:**
- LangChain official integration
- Vercel AI SDK showcase
- Anthropic MCP directory listing
- OpenAI cookbook example

**Activities:**
- Co-marketing with framework teams
- Conference talks (AI Engineer Summit, etc.)
- Guest posts on partner blogs

### Phase 3: Enterprise Outreach (Months 4-6)

**Targets:**
- Companies building agent products
- Enterprises deploying internal agents
- Fintech companies adding AI features

**Activities:**
- Case studies from early adopters
- SOC2 certification
- Enterprise sales team

### Positioning Matrix

| Audience | Pain Point | Message |
|----------|-----------|---------|
| Indie hackers | "Agent spent too much" | "Set it and forget it spending limits" |
| Startups | Integration complexity | "One SDK, all frameworks" |
| Enterprise | Compliance/audit | "Full audit trail, policy governance" |

### Competitive Positioning

```
"We're not competing with Stripe or payment processors.
We're the POLICY LAYER that sits on top of any payment rail.
Think: what Cloudflare is to web traffic, Sardis is to agent payments."
```

---

## Key Messages by Audience

### Technical (Developers)
- Non-custodial MPC via Turnkey
- Open source SDKs
- Multi-chain support
- Framework integrations

### Business (Founders/Executives)
- Reduce risk of agent errors
- Compliance and audit trails
- Cost control and visibility

### End Users (AI Power Users)
- Simple setup
- Natural language policies
- Works with Claude/ChatGPT
