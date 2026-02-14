# Social Media Launch Kit

> **Positioning:** Developer Preview on testnet. Looking for design partners.
> **Key message:** We built the infrastructure. Now we need teams building AI agents to shape it with us.

## Pre-Launch Tweets (3 Days Before)

### Day -3 (Saturday)
> AI agents can now reason, browse, and code.
>
> But can you trust them with your money?
>
> Something's coming Tuesday.

### Day -2 (Sunday)
> The #1 risk in the agent economy isn't hallucinated text.
>
> It's hallucinated transactions — retry loops that spend $10k instead of $100. Decimal errors. Agents paying the wrong merchant with full confidence.
>
> We built the fix. Launching Tuesday on @ProductHunt.

### Day -1 (Monday)
> Tomorrow we launch Sardis on @ProductHunt.
>
> What it does: Gives AI agents policy-controlled wallets with natural language spending policies.
>
> Instead of code — just say: "Max $100/day, only SaaS, block weekends"
>
> We're live on testnet and looking for design partners.
>
> Set your reminder: [PH upcoming link]

---

## Launch Day X/Twitter Thread

### Tweet 1 (Main)
> We just launched Sardis on @ProductHunt
>
> The Payment OS for the Agent Economy.
>
> AI agents can reason, but they can't be trusted with money. Sardis is how they earn that trust.
>
> We're on testnet and looking for design partners. Here's what we built:

### Tweet 2
> The problem: Financial Hallucination
>
> Agents confidently make wrong financial decisions:
> - Retry loops: $10k instead of $100
> - Decimal errors: 10x overpayment
> - Wrong merchant: funds sent to the wrong address
>
> These are real failure modes in autonomous agent systems.

### Tweet 3
> The solution: A policy firewall for agent payments.
>
> Natural language spending rules:
> "Max $100/day, only approved SaaS vendors, require approval over $50, block weekends"
>
> Every transaction is checked before the MPC signing ceremony begins. Fail = blocked. No money moves.

### Tweet 4
> What's working today (on testnet):
>
> - Non-custodial MPC wallets in live MPC mode (Turnkey)
> - Natural language policies (not just spending caps)
> - 52 MCP tools — zero-config for Claude/Cursor
> - Group governance — shared budgets across agent teams
> - 19 packages on npm + PyPI (MIT licensed)
>
> `npx @sardis/mcp-server start`

### Tweet 5
> Group governance for multi-agent teams:
>
> 3 agents, 1 shared budget:
> - Researcher finds tools ($50 limit)
> - Purchaser executes ($200 limit)
> - Auditor reviews (read-only)
>
> Group enforces $1000/day across all agents. No single agent can overspend the team.

### Tweet 6
> Where we are:
>
> - Live on testnet (Base Sepolia)
> - 19 packages published (npm + PyPI)
> - 52 MCP tools working
> - 7K+ monthly installs
>
> What's next: Mainnet, virtual cards (Lithic), KYC/AML (Persona + Elliptic)
>
> We're building in public and looking for **design partners**.

### Tweet 7
> If you're building AI agents that will need to handle money — we want to build with you.
>
> Become a design partner: sardis.sh
> GitHub: github.com/EfeDurmaz16/sardis
> Docs: sardis.sh/docs
>
> [ProductHunt link]

---

## Reddit Posts

### r/artificial
**Title:** We built a "policy firewall" for AI agent payments — looking for design partners to test on testnet

**Body:**
Hey r/artificial,

We just launched Sardis on Product Hunt — infrastructure that will let AI agents make real financial transactions safely.

**The problem:** Agents hallucinate financial decisions. Retry loops, decimal errors, wrong merchants. We call it "financial hallucination."

**What we built:** Policy-controlled wallets with natural language spending policies. In live MPC mode (Turnkey/Fireblocks), the wallet posture is non-custodial. Instead of code, you write: "Max $100/day, only SaaS vendors, block weekends." Every transaction is policy-checked before execution.

**Where we are:** Live on testnet (Base Sepolia) with full SDK coverage. 19 packages on npm + PyPI, 52 MCP tools. We're looking for **design partners** — teams building AI agents that need payment capabilities.

Key features working today:
- Natural language policy engine (not just spending caps)
- Non-custodial MPC wallets in live MPC mode (Turnkey)
- MCP native — zero-config for Claude/Cursor
- Group governance for multi-agent teams

Open-core: SDKs are MIT licensed.

GitHub: github.com/EfeDurmaz16/sardis
Docs: sardis.sh/docs

If you're building agents that need to handle money, we'd love to work together. What spending policies would you set for your agents?

### r/LocalLLaMA
**Title:** Open-source payment infrastructure for AI agents — live on testnet, looking for design partners

**Body:**
For those building autonomous agents that need to handle money — we built Sardis, an open-core payment OS.

The MCP server works with any LLM (Claude, local models via Cursor, etc.):
```
npx @sardis/mcp-server start
```
52 tools, zero config. Your agent gets a wallet with policy enforcement on testnet.

Python SDK:
```python
from sardis import SardisClient
client = SardisClient()  # simulated mode, no API key needed
wallet = client.wallets.create(chain="base_sepolia", policy="Max $50/day")
```

Currently on testnet — looking for design partners before mainnet launch. MIT licensed SDKs, 19 packages on npm + PyPI.

GitHub: github.com/EfeDurmaz16/sardis

### r/ChatGPT
**Title:** Built a system that prevents AI agents from accidentally spending your money — looking for early testers

**Body:**
AI agents are getting better at autonomous tasks, but trusting them with real money is risky. Retry loops can spend $10k instead of $100. Decimal errors cause 10x overpayments.

We built Sardis — it gives agents wallets with natural language spending rules:

"Max $100 per transaction, only SaaS vendors, block gambling, require approval over $50"

Currently live on testnet (Base Sepolia) — you can try everything with test tokens. We're looking for teams building AI agents who want to be design partners as we move to mainnet.

Works with Claude (via MCP), OpenAI agents, LangChain, CrewAI, and more.

Website: sardis.sh
GitHub: github.com/EfeDurmaz16/sardis

### r/programming
**Title:** Sardis: Open-core payment infrastructure for AI agents — testnet live, looking for design partners

**Body:**
We've been building Sardis — payment infrastructure designed for AI agent transactions. Currently live on testnet (Base Sepolia), looking for design partners before mainnet.

Architecture: Agent -> SDK/MCP -> Policy Engine -> MPC Signing (Turnkey) -> Chain Settlement

What's working today:
- Non-custodial MPC wallets in live MPC mode via Turnkey threshold signatures
- Natural language policy parsing -> structured rule enforcement
- 52 MCP tools (zero-config for Claude/Cursor)
- Group governance with shared budgets across agent teams
- Append-only audit ledger

Stack: Python 3.12 (FastAPI), TypeScript, Solidity + Foundry, PostgreSQL (Neon).

What's coming: Mainnet deployment, virtual cards (Lithic), KYC/AML (Persona + Elliptic), fiat on/off ramp (Bridge.xyz).

Open-core: SDKs and MCP server are MIT. 19 packages published.

GitHub: github.com/EfeDurmaz16/sardis
Docs: sardis.sh/docs

---

## Hacker News

**Title:** Show HN: Sardis – Payment OS for AI Agents (testnet live, looking for design partners)

**Body:**
Sardis gives AI agents policy-controlled wallets with natural language spending policies.

The problem: "financial hallucination" — agents confidently making wrong financial decisions (retry loops, decimal errors, wrong merchants).

How it works:
1. Create a wallet: `client.wallets.create(chain="base_sepolia", policy="Max $100/day, SaaS only")`
2. Agent requests payment -> policy engine checks NL rules
3. If approved -> MPC signing ceremony executes
4. If denied -> transaction blocked, no money moves

Currently live on testnet (Base Sepolia). We're looking for design partners — teams building AI agents that need payment capabilities.

Technical details:
- MPC custody via Turnkey in live mode (non-custodial, threshold signatures)
- 52 MCP tools (zero-config for Claude/Cursor)
- Group governance for multi-agent shared budgets
- 5 protocols (AP2, TAP, UCP, A2A, x402)

Coming soon: Mainnet, virtual cards (Lithic), KYC/AML (Persona + Elliptic).

Open-core: MIT licensed SDKs, 19 packages on npm + PyPI.

https://sardis.sh
https://github.com/EfeDurmaz16/sardis

---

## Discord Announcement

> **Sardis is live on Product Hunt!**
>
> We'd love your support today — every upvote and comment helps!
>
> **[ProductHunt link]**
>
> **What's live on testnet:**
> - Policy-controlled wallets with NL spending policies (non-custodial in live MPC mode)
> - Group governance: shared budgets across multi-agent teams
> - 52 MCP tools — zero-config for Claude/Cursor
> - 19 packages on npm + PyPI
>
> We're looking for **design partners** — teams building AI agents that need payment capabilities. If that sounds like you, let's talk.

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
> What we've built (live on testnet):
> -> Non-custodial MPC wallets in live MPC mode (Turnkey)
> -> Natural language spending policies — "Max $100/day, only SaaS, block weekends"
> -> MCP native — one command for Claude/Cursor integration
> -> Group governance — shared budgets across multi-agent teams
> -> 19 packages on npm and PyPI, MIT licensed SDKs
>
> **Where we are:** Developer preview on Base Sepolia testnet. 7K+ monthly installs. Looking for design partners.
>
> **What's next:** Mainnet deployment, virtual cards (Lithic), KYC/AML integration.
>
> We're looking for teams building AI agents that need payment capabilities. If that's you — I'd love to connect.
>
> [ProductHunt link]
>
> #AIAgents #Fintech #Web3 #AgentEconomy #ProductHunt
