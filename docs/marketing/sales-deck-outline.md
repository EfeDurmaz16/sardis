# Sales Deck Outline — 10-Slide Customer Pitch

Updated: 2026-03-24 | Audience: Customers (not investors)
Goal: Design partner signup within 1 week of presentation.

## Slide 1: Title
Sardis — The Payment OS for AI Agents. "Your agents reason. Sardis makes sure they pay safely." sardis.sh

## Slide 2: The Problem
AI agents are going live with financial access. Nobody controls them.
1. Retry overspend — Agent retries a failed API call 10 times. Monthly budget gone in minutes.
2. Decimal drift — Model misparses $1.50 as $150. No safeguard catches it.
3. Vendor mismatch — Agent pays the wrong endpoint. Funds gone, no recourse.
83% of enterprises deploy AI agents. Zero have policy-controlled payment infrastructure.

## Slide 3: The Cost of Doing Nothing
- Manual approval queues -> Agents stall, latency kills automation value
- Ad-hoc amount checks -> One missed edge case = $10K+ loss
- No audit trail -> Failed SOC2 audit, regulatory exposure
- Shared corporate cards -> Cannot track which agent spent what
One agent error costs more than a year of Sardis.

## Slide 4: sardis.pay() — One Call
result = sardis.pay(to="0xMerchant...", amount=100, currency="USDC", chain="base", mandate_id="mnd_abc123")
Policy check (12 gates) -> Route selection -> MPC sign -> Settle -> Audit.
Your agent gets a budget, not a balance.

## Slide 5: Spending Mandates
Input: "Max $500/day on dev tools, no single payment above $100, block weekends"
Output: Daily limit $500, per-tx cap $100, vendor category dev-tools, weekdays only.
Confirmation required. If blocked, human-readable explanation provided.

## Slide 6: Architecture
Agent -> Sardis API -> Policy Engine (12 checks) -> Chain Router (6 chains) -> MPC Signer (Turnkey) -> Audit Trail (Merkle-anchored).
We never store private keys. We never touch your funds. Every decision is cryptographically provable.

## Slide 7: 18+ Framework Integrations
LangChain, CrewAI, AutoGPT, OpenAI Agents SDK, OpenAI direct, Claude Agent SDK, Google ADK, Google A2A, Coinbase AgentKit, Browser Use, Composio, OpenClaw, Stagehand, Vercel AI SDK, Activepieces (LIVE), n8n, E2B, GPT Actions, MCP server (Claude Desktop / Cursor / Windsurf — 40+ tools).
pip install sardis — 5 minutes to first payment. **70K+ SDK installs. 225K LOC. Live on Base and Tempo mainnet. Stripe MPP early access partner.**

## Slide 8: Compliance Built In
15 modules: KYC (Didit), KYB, AML/Sanctions (6 providers), PEP, SAR filing, MiCA, Travel Rule (Notabene), Risk Scoring, Fraud Rules, Merkle Audit Trail, Agent Identity (KYA), Policy Evidence Bundles, Compliance Reports, TAP Signatures, Adverse Media.

## Slide 9: Pricing
Free $0 (10 tx/day, 1 agent, testnet) | Developer $29/mo (100 tx/day, 5 agents, mainnet) | Growth $199/mo (unlimited, KYC, AML, audit) | Business $499/mo (+ KYB, PEP, FX) | Enterprise custom (+ SAR, MiCA, SLA).
Plus usage: 0.1-0.5% per transaction. No setup fees. No minimum commitment.

## Slide 10: Next Steps
1. pip install sardis  2. Create API key  3. Create mandate  4. Run sardis.pay()
Schedule 15-min walkthrough: efe@sardis.sh | Try now: sardis.sh/docs/quickstart
