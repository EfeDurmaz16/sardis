# Launch Day Plan

Updated: 2026-03-24 | Day: Tuesday (highest HN + PH engagement)

## Hour-by-Hour Schedule

| Time (ET) | Action | Channel |
|-----------|--------|---------|
| 00:01 | PH listing goes live (scheduled) | Product Hunt |
| 08:00 | DM 20 supporters to upvote PH at 9 AM | Twitter DMs |
| 09:00 | Twitter thread drops (10 tweets below) | X/Twitter |
| 09:05 | HN "Show HN" post | Hacker News |
| 09:15 | Reddit posts (r/artificial, r/LocalLLaMA, r/cryptocurrency) | Reddit |
| 09:30 | LinkedIn announcement | LinkedIn |
| 10:00 | Email blast to waitlist | Email |
| 10:30 | Discord announcement in AI/crypto communities | Discord |
| 12:00 | Respond to all PH comments (every single one) | Product Hunt |
| 14:00 | Second Twitter post with demo GIF | X/Twitter |
| 16:00 | HN engagement — respond to comments | Hacker News |
| 18:00 | PH final push tweet asking for support | X/Twitter |
| 21:00 | Day-1 metrics summary tweet | X/Twitter |

## Twitter Launch Thread (10 Tweets)

Tweet 1 (Hook):
AI agents can reason, browse, and code. But they cannot be trusted with money. Today we launch Sardis — the Payment OS for the Agent Economy. One API call. Policy-enforced. Non-custodial. Auditable. sardis.sh

Tweet 2 (Problem):
The problem: agents retry failed API calls and overspend. They misparse decimals. They pay the wrong merchant. We call this "financial hallucination." It is not hypothetical — it is happening in production today.

Tweet 3 (Solution):
sardis.pay() — one call that handles everything:
- Policy check (12-point pipeline)
- Chain routing (cheapest path)
- MPC signing (non-custodial)
- Settlement (USDC on Base)
- Audit trail (Merkle-anchored)
Your agent gets a budget, not a balance.

Tweet 4 (NLP Policies):
Set spending rules in English: "Max $500/day on dev tools, no single payment above $100, block weekends." Sardis parses it into machine-enforced rules. Confirmation required before activation. No ambiguity.

Tweet 5 (Scale):
225K lines of production code. 55 distinct capabilities. 18+ framework integrations. Live on Base and Tempo mainnet. 70K+ SDK installs. Stripe MPP early access partner. Built solo in 12 months. Not a pitch deck — a product.

Tweet 6 (Integrations):
Works with your stack: LangChain, CrewAI, AutoGPT, OpenAI Agents SDK, Claude Agent SDK, Google ADK, Coinbase AgentKit, Browser Use, Composio, Stagehand, Vercel AI SDK, n8n, Activepieces, MCP server. pip install sardis. Done.

Tweet 7 (Compliance):
Enterprise compliance from day 1: KYC/KYB (Didit), AML/Sanctions (6 providers), SAR auto-filing, MiCA (EU), Merkle-anchored audit trail. Most Series B fintechs do not have this stack.

Tweet 8 (Demo):
See it work: [3-min demo video link]. Signup -> API key -> mandate -> payment -> on-chain receipt. Under 5 minutes.

Tweet 9 (Pricing):
Free tier: 10 tx/day, testnet, 1 agent. Developer: $29/mo — mainnet, 100 tx/day. Growth: $199/mo — unlimited everything. 0.1-0.5% per transaction. No setup fees. No minimum.

Tweet 10 (CTA):
We are looking for design partners — teams building AI agents that need to handle money safely. Try it: sardis.sh. Docs: sardis.sh/docs. Built by @EfeDurmaz16. Ask me anything.

## Hacker News "Show HN" Post

Title: Show HN: Sardis — Policy-controlled payment wallets for AI agents

Body:
Sardis gives AI agents non-custodial wallets with natural language spending policies.

The problem: AI agents can now autonomously browse, code, and interact with APIs. But giving them financial access is dangerous — retry loops overspend, decimal parsing errors drain wallets, and there is no audit trail.

sardis.pay(to="0x...", amount=100, currency="USDC", chain="base", mandate_id="mnd_abc")

Every payment goes through a 12-check policy pipeline before MPC signing. If it violates the mandate, it is blocked. No money moves.

What is different:
- NLP policy engine: "Max $500/day on AWS" becomes machine-enforced rules
- Non-custodial: MPC signing via Turnkey, never store private keys
- 15 framework integrations (OpenAI, Claude MCP, CrewAI, LangChain, etc.)
- Compliance: KYC, AML, sanctions screening, Merkle-anchored audit trail
- 6 chains: Base, Polygon, Ethereum, Arbitrum, Optimism, Tempo

Stack: Python 3.12/FastAPI (backend), Solidity/Foundry (contracts), React/Next.js (dashboard), TypeScript (SDKs).

225K LOC, 55 capabilities, 70K+ SDK installs, live on Base and Tempo mainnet, Stripe MPP early access partner. Built solo in 12 months. Open-core (SDKs are MIT).

Looking for design partners. Try it: sardis.sh | Docs: sardis.sh/docs

## Reddit Posts

r/artificial — "We built policy-controlled wallets for AI agents (open-core)"
r/LocalLLaMA — "Show: sardis.pay() — one API call to give your local LLM agent a payment wallet"
r/cryptocurrency — "Sardis: non-custodial MPC wallets with NLP spending policies for AI agents (USDC, 6 chains)"
r/SideProject — "Solo founder, 20yo, 225K LOC in 12 months: the Payment OS for AI agents"

## 7-Day Follow-Up Content Calendar

| Day | Content | Channel |
|-----|---------|---------|
| D+1 | "What we learned from launch day" thread | Twitter |
| D+2 | Tutorial: "Add payments to your CrewAI agent in 5 minutes" | Blog + Twitter |
| D+3 | Metrics update (signups, payments, feedback) | Twitter |
| D+4 | Tutorial: "sardis.pay() with OpenAI Agents SDK" | Blog + Twitter |
| D+5 | "5 things that surprised us about AI agent payment failures" | HN + Twitter |
| D+6 | Partner highlight (Activepieces integration live) | Twitter + LinkedIn |
| D+7 | Week 1 retrospective + roadmap preview | Blog + Twitter + Email |
