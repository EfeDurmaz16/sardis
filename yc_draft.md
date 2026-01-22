# Sardis: YC S26 Application Draft

## Company Name
**Sardis**

## One-Liner (50 chars)
The Payment OS for the Agent Economy.

---

## What is your company going to make?

Sardis is an API-first financial infrastructure that enables AI agents to hold funds and execute payments autonomously using non-custodial MPC wallets.

While agents (Claude, Cursor, etc.) can plan and code, they hit a "payment wall" because they lack financial identity. We provide:

1. **Agent Wallets (IAM):** Non-custodial MPC wallets (via Turnkey) that give agents a distinct financial identity separate from the user's main bank account.

2. **MCP-Native Integration:** We are the first financial server built for the Model Context Protocol. Developers can give an agent a wallet with zero code:
   ```bash
   npx @sardis/mcp-server start
   ```

3. **Risk Engine:** A granular spending firewall to prevent "Financial Hallucinations" (e.g., an agent accidentally spending $10k on a GPU cluster instead of $100).

4. **Programmable Rails:** Automated settlement via USDC/USDT on Base/Polygon/Ethereum, with virtual cards (Lithic) for fiat merchants.

**Analogy:** Stripe + IAM + Risk Engine for AI Agents.

---

## Why did you pick this idea? (Why Now?)

The internet is shifting from human-driven to agent-driven. As LLMs evolve from "Chat" to "Action," the primary bottleneck is the lack of a secure, machine-native payment layer.

- **Traditional Fintech (Stripe/Brex):** Designed to stop bots. Agents are bots. They block agentic traffic as fraud.
- **Crypto Wallets (Metamask):** Too complex for autonomous agents to manage without human signing.
- **The MCP Catalyst:** With the rise of the Model Context Protocol, agents finally have a standard way to connect to tools. Sardis is the missing "Wallet Tool" in this ecosystem.

---

## What is your unique insight?

Most people think the biggest risk in AI is "hallucination in text" (saying something wrong). We believe the bigger, existential risk is **"Financial Hallucination"**—an agent executing a transaction based on flawed logic (e.g., booking a $5,000 flight for the wrong date or spinning up 100 servers in a loop).

Sardis treats agent spending like SQL Injection—it must be sanitized. We built a **Natural Language Policy Engine** that allows humans to define rules verbally (e.g., "Limit spend to $50/day and only allow SaaS payments"), bridging the gap between rigid banking compliance and fluid AI behavior.

---

## Who are your competitors?

**Direct (Agent Wallets):** Skyfire, Payman. They are building "wrappers" or focusing on bank partnerships first. We are developer-first, MCP-native, and open-core.

**Indirect (Rails):** Stripe (Anti-bot), Coinbase (Crypto-only).

**Our Advantage:** We solve the **Control Problem**, not just the Payment Problem. Giving an agent a wallet is easy (and dangerous). Giving an agent a constrained, policy-governed wallet that prevents financial hallucinations is the hard problem. That is our moat.

---

## How do/will you make money?

1. **Transaction Fees:** 0.25% - 0.75% on volume (Stablecoin settlement & Virtual Card interchange).

2. **SaaS (Control Plane):** Tiered subscription for the Policy Engine (e.g., "Enterprise Governance" features like audit logs, multi-sig mandates, and natural language policy builder).

---

## How far along are you?

**Status: Production-Ready Infrastructure (82% Complete)**

I built the entire stack solo to move fast.

| Component | Status |
|-----------|--------|
| Core Policy Engine | ✅ Live (150+ tests) |
| MPC Wallets (Turnkey) | ✅ Live |
| MCP Server | ✅ **Complete** (`@sardis/mcp-server`) |
| Python SDK + Integrations | ✅ Complete (LangChain, OpenAI, LlamaIndex) |
| TypeScript SDK | ✅ Complete (Vercel AI SDK) |
| On-Chain Rails | ✅ Live (Base, Polygon, ETH) |
| KYC/AML Compliance | ✅ Integrated (Persona, Elliptic) |
| Landing Page | ✅ Live (sardis.sh) |
| Virtual Cards (Lithic) | 🟡 Sandbox (Live Feb 2026) |

**Traction:** Onboarding 3 alpha design partners (developer tools companies) to stress-test the policy engine.

**Solo Founder Mitigation:** I am actively recruiting a Founding Protocol Engineer or GTM Lead. I have set aside 20-25% equity for the right partner.

---

## Who writes code?

I write all the code. I built the entire codebase (15k+ lines of Python/TypeScript, 3 Solidity contracts, React dashboard, MCP integration) solo in 2 months. No contractors, no outsourcing.

---

## Are you looking for a cofounder?

**Yes.** I am actively recruiting:
- **Founding Protocol Engineer:** Deep expertise in cryptography/MPC to own the security layer
- **Founding GTM Lead:** Fintech B2B experience to scale partnerships

---

## Demo Video Script (60s)

**0-10s (The Problem):**
Text animation: "Agents can code, but they can't pay."

**10-30s (The Connection):**
Terminal showing `npx @sardis/mcp-server start`
Badge: "Connected to Claude Desktop"

**30-50s (The Prevention):**
- Agent: "Buy Amazon Gift Card ($500)"
- Sardis: **BLOCKED** — "Policy Violation: Merchant not in allowlist"
- Text: "Financial Hallucination PREVENTED"

**50-60s (The Solution):**
- Policy updated: "Allow OpenAI up to $50"
- Agent: "Pay OpenAI ($20)"
- Sardis: **APPROVED** — Card issued
- Logo: Sardis — sardis.sh

---

## Other Ideas Considered

1. **Yula (formerly Aspendos):** Agent OS with neuroscience-inspired memory. $15k MRR. Deprioritized for Sardis.
2. **Maestro:** Deployment readiness orchestrator for agent-written code.
3. **CodeFlow:** Dashboard to monitor all active agents in one place.

---

<p align="center">
<strong>Sardis — The Payment OS for the Agent Economy</strong>
<br/>
sardis.sh | github.com/EfeDurmaz16/sardis
</p>
