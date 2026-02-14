# Social Media Launch Kit

## Pre-Launch Tweets (3 Days Before)

### Day -3 (Saturday)
> AI agents can now reason, browse, and code.
>
> But can you trust them with your money?
>
> Something's coming Tuesday. 🧵

### Day -2 (Sunday)
> The #1 risk in the agent economy isn't hallucinated text.
>
> It's hallucinated transactions — retry loops that spend $10k instead of $100. Decimal errors. Agents paying the wrong merchant with full confidence.
>
> We built the fix. Launching Tuesday on @ProductHunt.

### Day -1 (Monday)
> Tomorrow we launch Sardis on @ProductHunt.
>
> What it does: Gives AI agents non-custodial MPC wallets with natural language spending policies.
>
> Instead of code → just say: "Max $100/day, only SaaS, block weekends"
>
> Set your reminder: [PH upcoming link]

---

## Launch Day X/Twitter Thread

### Tweet 1 (Main)
> We just launched Sardis on @ProductHunt 🚀
>
> The Payment OS for the Agent Economy.
>
> AI agents can reason, but they can't be trusted with money. Sardis is how they earn that trust.
>
> 🔗 [ProductHunt link]
>
> Here's what we built 🧵

### Tweet 2
> The problem: Financial Hallucination
>
> Agents confidently make wrong financial decisions:
> • Retry loops → $10k instead of $100
> • Decimal errors → 10x overpayment
> • Wrong merchant → funds sent to scammers
>
> These are common failure modes in autonomous automation systems.

### Tweet 3
> The solution: A policy firewall for agent payments.
>
> Natural language spending rules:
> "Max $100/day, only approved SaaS vendors, require approval over $50, block weekends"
>
> Every transaction is checked before the MPC signing ceremony begins. Fail = blocked. No money moves.

### Tweet 4
> What makes Sardis different:
>
> ✅ Non-custodial MPC wallets (Turnkey)
> ✅ Natural language policies (not just spending caps)
> ✅ Virtual cards (Lithic) for card-rail spending
> ✅ 5 chains: Base, Polygon, ETH, Arbitrum, Optimism
> ✅ MCP native — 1 command for Claude/Cursor

### Tweet 5
> NEW: Group governance for multi-agent teams.
>
> 3 agents, 1 shared budget:
> • Researcher finds tools ($50 limit)
> • Purchaser executes ($200 limit)
> • Auditor reviews (read-only)
>
> Group enforces $1000/day across all agents. No agent can overspend the team.

### Tweet 6
> Open-core & developer-first:
>
> • 19 packages on npm + PyPI
> • 52 MCP tools
> • 5 protocols (AP2, TAP, UCP, A2A, x402)
> • MIT licensed SDKs
> • 5 lines of code to add payments to any agent
>
> pip install sardis
> npx @sardis/mcp-server start

### Tweet 7
> We'd love your support on Product Hunt today:
>
> [ProductHunt link]
>
> And if you're building AI agents that need to handle money — let's talk.
>
> 📖 Docs: sardis.sh/docs
> 🐙 GitHub: github.com/EfeDurmaz16/sardis
> 📦 PyPI: pypi.org/project/sardis

---

## Reddit Posts

### r/artificial
**Title:** We built a "policy firewall" for AI agent payments — natural language spending rules enforced via MPC wallets

**Body:**
Hey r/artificial,

We just launched Sardis — infrastructure that lets AI agents make real financial transactions safely.

**The problem:** Agents hallucinate financial decisions. Retry loops, decimal errors, wrong merchants. We call it "financial hallucination."

**What we built:** Non-custodial MPC wallets with natural language spending policies. Instead of code, you write: "Max $100/day, only SaaS vendors, block weekends." Every transaction is policy-checked before execution.

Key features:
- Natural language policy engine (not just spending caps)
- Non-custodial MPC wallets (Turnkey)
- Virtual cards (Lithic) for card-rail payments
- 5 chains, 5 protocols, MCP native
- Group governance for multi-agent teams

Open-core: SDKs are MIT, 19 packages on npm + PyPI (see docs/audits/claims-evidence.md).

GitHub: github.com/EfeDurmaz16/sardis
Docs: sardis.sh/docs

Would love feedback from this community. What spending policies would you set for your agents?

### r/LocalLLaMA
**Title:** Open-source payment infrastructure for AI agents — MPC wallets + natural language spending policies

**Body:**
For those building autonomous agents that need to handle money — we built Sardis, an open-core payment OS.

The MCP server works with any LLM (Claude, local models via Cursor, etc.):
```
npx @sardis/mcp-server start
```
52 tools, zero config. Your agent gets a wallet with policy enforcement.

Python SDK:
```python
from sardis import SardisClient
client = SardisClient(api_key="sk_...")
wallet = client.wallets.create(chain="base", policy="Max $50/day")
```

MIT licensed SDKs, 19 packages on npm + PyPI.

GitHub: github.com/EfeDurmaz16/sardis

### r/ChatGPT
**Title:** Built a system that prevents AI agents from accidentally spending your money — natural language spending rules

**Body:**
AI agents are getting better at autonomous tasks, but trusting them with real money is risky. Retry loops can spend $10k instead of $100. Decimal errors cause 10x overpayments.

We built Sardis — it gives agents wallets with natural language spending rules:

"Max $100 per transaction, only SaaS vendors, block gambling, require approval over $50"

Works with Claude (via MCP), OpenAI agents, LangChain, CrewAI, and more.

Website: sardis.sh
GitHub: github.com/EfeDurmaz16/sardis

### r/programming
**Title:** Sardis: Open-core payment infrastructure for AI agents — MPC wallets, NL policies, 5 chains

**Body:**
We've been building Sardis for the past few months — payment infrastructure designed for AI agent transactions.

Architecture: Agent → SDK/MCP → Policy Engine → MPC Signing (Turnkey) → Chain Settlement / Virtual Cards (Lithic)

Technical highlights:
- Non-custodial MPC wallets via Turnkey threshold signatures
- Natural language policy parsing → structured rule enforcement
- 5 chains: Base, Polygon, Ethereum, Arbitrum, Optimism
- 5 protocols: AP2, TAP, UCP, A2A, x402
- Append-only audit ledger
- Group governance with shared budgets

Stack: Python 3.12 (FastAPI), TypeScript, Solidity + Foundry, PostgreSQL (Neon).

Open-core: SDKs and MCP server are MIT. 19 packages published (see docs/audits/claims-evidence.md).

GitHub: github.com/EfeDurmaz16/sardis
Docs: sardis.sh/docs

---

## Hacker News

**Title:** Show HN: Sardis – Payment OS for AI Agents (MPC wallets + NL spending policies)

**Body:**
Sardis gives AI agents non-custodial MPC wallets with natural language spending policies.

The problem: "financial hallucination" — agents confidently making wrong financial decisions (retry loops, decimal errors, wrong merchants).

How it works:
1. Create a wallet: `client.wallets.create(chain="base", policy="Max $100/day, SaaS only")`
2. Agent requests payment → policy engine checks NL rules
3. If approved → MPC signing ceremony executes
4. If denied → transaction blocked, no money moves

Technical details:
- MPC custody via Turnkey (non-custodial, threshold signatures)
- Virtual cards via Lithic for card-rail payments
- 5 chains (Base, Polygon, ETH, Arbitrum, Optimism)
- 5 protocols (AP2, TAP, UCP, A2A, x402)
- MCP server with 52 tools (zero-config for Claude/Cursor)
- Group governance for multi-agent shared budgets

Open-core: MIT licensed SDKs, 19 packages on npm + PyPI.

https://sardis.sh
https://github.com/EfeDurmaz16/sardis

---

## Discord Announcement

> **🚀 Sardis is live on Product Hunt!**
>
> We'd love your support today — every upvote and comment helps!
>
> **🔗 [ProductHunt link]**
>
> **What's new since last update:**
> - Group governance: shared budgets across multi-agent teams
> - 52 MCP tools (up from 36)
> - Virtual cards for fiat payments
> - 5 protocols: AP2, TAP, UCP, A2A, x402
>
> If you've been using Sardis, a comment on PH about your experience would mean the world to us. 🙏

---

## LinkedIn Post

> Excited to announce: we just launched Sardis on Product Hunt.
>
> **Sardis is the Payment OS for the Agent Economy.**
>
> As AI agents become more autonomous, they need financial infrastructure built for them — not adapted from human payment systems.
>
> The core problem we solve: **financial hallucination**. AI agents can make wrong financial decisions — retry loops, decimal errors, unauthorized purchases — if no policy controls are enforced.
>
> What we built:
> → Non-custodial MPC wallets (Turnkey) — we never hold private keys
> → Natural language spending policies — "Max $100/day, only SaaS, block weekends"
> → Virtual cards (Lithic) for card-rail payments
> → 5 blockchain networks, 5 payment protocols
> → MCP native — one command for Claude/Cursor integration
> → Group governance — shared budgets across multi-agent teams
>
> Open-core: 19 packages on npm and PyPI (verified in docs/audits/claims-evidence.md). MIT licensed SDKs.
>
> We'd appreciate your support today: [ProductHunt link]
>
> If you're building in the agent economy and need payment infrastructure — I'd love to connect.
>
> #AIAgents #Fintech #Web3 #AgentEconomy #ProductHunt
