# First Reddit Posts — Sardis

**Rule #1:** Don't sell. Start a discussion. Provide value. Mention Sardis naturally.
**Rule #2:** Different angle for each subreddit — same product, different audience.
**Rule #3:** Engage in comments. Reply to everyone.

---

## POST 1: r/artificial

**Best for:** Broad AI audience, discussion-driven, "thought leadership"

**Title:** AI agents are starting to handle money — and the infrastructure doesn't exist yet

**Body:**

Been working on AI agent infrastructure for the past 6 months and wanted to share something I keep running into.

AI agents are getting deployed for increasingly complex tasks — customer support, procurement, research, code generation. But the moment an agent needs to make a financial transaction (buy API credits, process a refund, pay a vendor), everything falls apart.

The current workarounds are all bad:

1. **Shared corporate card** — agent has unlimited access to a card with no per-agent controls. No audit trail tied to the specific agent.
2. **Human-in-the-loop approval** — every $2 API purchase gets routed to a human. Defeats the purpose of automation.
3. **Hard-coded API keys** — agent has access to payment APIs with no spending limits. One hallucination away from draining the budget.

The fundamental issue: payment infrastructure was designed for humans who authenticate with passwords, review charges manually, and understand context. Agents need something different — explicit spending policies, per-agent financial identities, and real-time policy enforcement.

I've been building a payment OS that tries to solve this. The approach:

- Each agent gets its own wallet with spending policies defined in natural language ("max $500/day, only approved vendors, no transactions over $100 without human approval")
- Virtual cards for fiat purchases (standard Visa/Mastercard rails)
- Non-custodial key management (MPC — no single party holds the full key)
- Full audit trail

Curious what this community thinks:

1. Are you seeing AI agents deployed in financial workflows? What's the current approach?
2. What's the right trust model? Should agents have autonomous spending authority, or should humans always be in the loop for money?
3. Is "natural language spending policies" the right abstraction, or do you need something more structured?

Happy to answer questions about the technical architecture if anyone's interested.

---

## POST 2: r/ClaudeAI

**Best for:** Claude users, MCP-focused, practical and hands-on

**Title:** I built an MCP server with 36 tools that gives Claude agents the ability to handle payments

**Body:**

Hey r/ClaudeAI,

I've been building payment infrastructure for AI agents and recently shipped an MCP server specifically for Claude Desktop.

**What it does:** Gives Claude the ability to create wallets, set spending policies, execute payments, check balances, and query transaction history — all through natural language.

**The 36 tools include things like:**
- `create_wallet` — create a new agent wallet
- `set_spending_policy` — define limits in plain English ("max $200/day, only from these vendors")
- `execute_payment` — pay via virtual card (Visa/MC) or on-chain (USDC)
- `get_balance` — check wallet balance
- `list_transactions` — query transaction history with filters

**Setup** is one config block in your claude_desktop_config.json:

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}
```

**Example conversation with Claude after setup:**

> You: "Create a wallet for my research agent with a $50/day budget, only allowed to buy from arxiv, openai, and anthropic APIs"
>
> Claude: [calls create_wallet, set_spending_policy] "Done. Wallet created with ID xxx. Policy set: $50/day max, whitelisted vendors: arxiv.org, api.openai.com, api.anthropic.com"

**Why I built this:** I kept seeing people give Claude access to payment APIs with zero guardrails. Shared API keys, no spending limits, no audit trail. This is fine for demos, but not for anything real. The MCP server approach means Claude operates within explicit policy boundaries.

Currently testnet-only — we're onboarding design partners to test on mainnet. If you're building Claude-powered workflows that need to handle money (API purchases, subscription management, refund processing), I'd love to hear how you're currently handling it.

More details at sardis.sh. Happy to answer technical questions.

---

## POST 3: r/LangChain

**Best for:** LangChain developers, integration-focused, code-first

**Title:** Built a payment tool for LangChain agents — agents can now execute transactions within spending policies

**Body:**

Hey r/LangChain,

I've been building payment infrastructure for AI agents and wanted to share something that might be useful for anyone building LangChain agents that need to handle money.

**The problem I kept hitting:** LangChain agents can call APIs, search the web, write code — but when the workflow involves a payment (buying API credits, processing a refund, paying a vendor), you have to either:

1. Hard-code payment API keys into the agent's tools (no spending limits)
2. Break out of the agent loop and handle payment manually
3. Build custom payment guardrails from scratch

**What I built:** A payment SDK (Python + TypeScript) that works as a LangChain tool. The agent gets a wallet with natural language spending policies.

```python
from sardis import SardisClient
from langchain.tools import Tool

sardis = SardisClient(api_key="sk_...")

# Create a payment tool with built-in policy enforcement
payment_tool = Tool(
    name="execute_payment",
    description="Pay for a service or product. Wallet has policy: max $100/tx, $500/day, whitelisted vendors only.",
    func=lambda query: sardis.payments.execute(
        wallet_id="agent_wallet_123",
        description=query
    )
)

# Add to your agent's toolkit
agent = initialize_agent(
    tools=[search_tool, code_tool, payment_tool],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS
)
```

**How it works under the hood:**

1. Agent calls the payment tool with a natural language description
2. Sardis parses the intent, matches against the wallet's spending policy
3. If approved → issues a one-time virtual card (Visa/MC) or executes on-chain (USDC)
4. Returns receipt to agent
5. If denied → returns reason ("exceeds daily limit" / "vendor not whitelisted")

**Key design decisions:**
- **Non-custodial** — MPC key management, no single party holds the full key
- **Virtual cards as primary rail** — works anywhere Visa/Mastercard is accepted
- **Natural language policies** — "max $500/day, only approved vendors" instead of JSON config
- **Audit trail** — every transaction logged with agent ID, policy check result, timestamp

Currently testnet — looking for LangChain developers who are building agents with financial workflows to test with. If you're interested: sardis.sh or cal.com/sardis/30min

What financial operations are your agents currently doing? Curious how people are handling the payment piece today.

---

## POST 4: r/startups

**Best for:** Founder community, story + strategy angle

**Title:** Solo founder, 6 months in — building payment infrastructure for AI agents. Lessons from 150+ cold outreach emails.

**Body:**

Hey r/startups,

Solo founder here, building from Istanbul. 6 months into building Sardis — payment infrastructure for AI agents. Wanted to share some raw lessons since this sub helped me a lot during the early days.

**What I'm building:** When AI agents need to spend money (buy API credits, process refunds, pay vendors), they currently use shared credit cards or hard-coded API keys with no controls. I'm building the infrastructure that gives each agent its own financial identity — wallets, spending policies, virtual cards.

**Where I am:**
- Testnet live
- 150+ cold outreach emails sent (design partners + investors)
- Pre-seed raising $1.5-2M
- Solo founder

**Lessons from the last 6 months:**

**1. "Too early" is relative.** Everyone told me the AI agent economy is too early. Meanwhile, 5+ competitors appeared in the same space, two raised $10M+. Early for enterprise adoption ≠ early for building.

**2. Cold email works if you're specific.** Generic "let's connect" emails get 0% reply. "[Company], your agents handle invoice processing — here's how they could execute payments within policy limits" gets replies.

**3. Solo founder isn't the disadvantage people say.** Less coordination overhead. Faster iteration. The downside is loneliness and context-switching between code and GTM, but the speed advantage is real.

**4. Istanbul is both an advantage and disadvantage.** Advantage: low burn rate, unique perspective, no SF echo chamber. Disadvantage: timezone gap with US, "where are you based?" becomes a recurring question in investor calls.

**5. Your positioning matters more than your product at pre-seed.** Nobody's testing my MPC wallet implementation yet. They're buying the thesis: "AI agents will be economic actors. They need financial infrastructure." If the thesis resonates, the product gets a chance.

Currently looking for:
- Design partners (companies with AI agents that handle money)
- Pre-seed investors who understand payments + AI infrastructure

If anyone here is building AI agents that touch financial workflows, I'd genuinely love to hear how you're handling the payment piece today. It helps me build a better product.

Happy to answer any questions about the space or the solo founder journey.

sardis.sh

---

## POST 5: r/SaaS

**Best for:** SaaS builders, practical problem angle

**Title:** How are you handling payments in AI agent workflows?

**Body:**

Building AI agent features into a SaaS product and running into a specific problem: payment execution.

Our AI agents can do everything — triage support tickets, research solutions, draft responses. But when the resolution requires money (issuing a refund, buying a replacement, upgrading a subscription), the agent hits a wall and hands off to a human.

For context, I've been building infrastructure to solve this (payment OS for AI agents — virtual cards, spending policies, audit trail). But before I go deeper, I'm genuinely curious:

1. **How are you handling AI agent payments today?** Shared API keys? Human-in-the-loop? Something else?
2. **What's the trust threshold?** At what dollar amount would you let an AI agent transact autonomously vs. requiring human approval?
3. **Is the bottleneck technical or organizational?** Is it that the tools don't exist, or that management won't approve autonomous agent spending regardless?

Not trying to sell anything here — genuinely trying to understand where the market is.

If you're curious about what I'm building: sardis.sh. But I'm more interested in hearing your current pain points.

---

## POST 6: r/cryptocurrency (Optional — lighter touch)

**Best for:** Crypto audience, but position as payments infra not "crypto project"

**Title:** Building non-custodial wallets for AI agents — MPC + spending policies

**Body:**

Working on something at the intersection of crypto infrastructure and AI agents.

The idea: AI agents are starting to transact autonomously (buying API credits, managing subscriptions, executing trades). They need wallets. But giving an AI agent a hot wallet with full key access is a terrible idea — one hallucination and it drains the wallet.

So I'm building wallets with:
- **MPC key management** (Turnkey) — key is split, no single party holds it. Similar to what Fireblocks does for institutional custody.
- **Natural language spending policies** — "max $500/day, only USDC, only whitelisted addresses"
- **Virtual cards via Lithic** — for fiat purchases (yes, agents can use Visa/Mastercard)
- **Multi-chain** — Base, Polygon, Ethereum, Arbitrum, Optimism
- **USDC-native settlement** — stablecoins as the default rail for on-chain transactions

The non-custodial piece is important: even if the platform gets compromised, nobody has the full key to drain agent wallets.

Currently testnet. Looking for projects building autonomous agents that need to handle funds.

sardis.sh

Interested in the community's take: is MPC the right approach for agent wallets, or is there a better custody model?

---

## POSTING SCHEDULE

| Day | Platform | Post | Purpose |
|-----|----------|------|---------|
| Day 1 (Mon) | X/Twitter | Full 10-tweet thread | Establish presence, pin to profile |
| Day 1 (Mon) | r/artificial | Problem awareness post | Start discussion, credibility |
| Day 2 (Tue) | r/ClaudeAI | MCP server post | Practical, hands-on audience |
| Day 3 (Wed) | r/LangChain | Integration post | Developer audience, code-first |
| Day 4 (Thu) | r/startups | Founder journey post | Community, honest lessons |
| Day 5 (Fri) | r/SaaS | Question post | Market research + awareness |
| Day 6 (Sat) | X/Twitter | Follow-up tweets | Engagement, respond to DMs |
| Day 7 (Sun) | r/cryptocurrency | Technical post (optional) | Crypto audience, MPC angle |

---

## ENGAGEMENT RULES

1. **Reply to every comment** within 2-4 hours
2. **Don't be defensive** — if someone critiques, acknowledge and learn
3. **Never say "we"** — you're a solo founder, own it. "I built this" is stronger than "we launched"
4. **Link to sardis.sh only when asked** — don't spam the link
5. **Ask follow-up questions** — "What's your current approach to X?" creates conversation
6. **Upvote and engage with other posts** in these subreddits before and after posting (don't be a drive-by poster)
7. **If a post gets traction** — edit to add "EDIT: Wow, this blew up. A few answers to common questions..." and address the top themes
