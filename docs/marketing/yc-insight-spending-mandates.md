# YC Insight: What We Understand That Others Don't

## The One-Liner

**The hard part of agent payments is not access to money. It is controlling authority over money.**

## The Insight

Most people think agent payments need a wallet or a new rail. We think the missing primitive is a **machine-readable spending mandate**: who an agent can pay, for what, up to what amount, on which rail, and when it must stop and ask a human.

## Why This Matters

Every major payment network is independently converging on the same conclusion:

- **Stripe** built Shared Payment Tokens — seller-scoped, amount-bounded, expirable permission objects. Not raw credentials. Not broad access. Scoped authority.
- **Visa** built the Trusted Agent Protocol — recognizing and authenticating trusted agents in commerce flows. Not giving agents credit cards.
- **Mastercard** built Agent Pay — trusted, tokenized agent transactions within an acceptance framework. Not raw PAN delegation.
- **Google** built AP2 — a cross-rail payment protocol for AI agents that works across cards, stablecoins, and bank transfers. Not a single-rail solution.
- **OpenAI** designed their commerce protocol around delegated payment through compliant PSPs. Not giving agents API keys to payment processors.

They're all saying the same thing: **raw credential delegation is the wrong model for agent payments.**

## What We Built

Sardis is the **cross-rail authorization and execution layer** for agent payments. We don't just give agents wallets. We give them **spending mandates** — structured permission objects that define:

- **Principal:** Who the agent acts for
- **Agent identity:** Which agent is authorized (with cryptographic binding)
- **Merchant scope:** Who the agent can pay (allowlist, blocklist, MCC codes)
- **Amount controls:** Per-transaction, daily, weekly, monthly, and total limits
- **Rail permissions:** Card, USDC, bank transfer — the mandate is portable across rails
- **Time bounds:** When the mandate activates, when it expires
- **Approval mode:** Auto-approve, threshold-based human review, or always-human
- **Revocation:** Instant invalidation with reason tracking and audit trail

Every payment passes through a 12-check policy pipeline that is **fail-closed** — if any check fails or the system is unreachable, the payment is rejected. This is non-negotiable for enterprise deployment.

## Why Competitors Are Solving the Wrong Problem

The market is splitting into two camps, and both are incomplete:

**Camp 1: "Give the agent a wallet"** (Skyfire, Crossmint, Coinbase AgentKit)
- Solves access to money, but not authority over money
- No natural language policies, no approval workflows, no cross-rail portability
- Equivalent to giving an intern a company credit card with no limits

**Camp 2: "Build a new rail"** (stablecoin-only solutions, x402 protocol)
- Solves settlement programmability, but not acceptance, compliance, or dispute handling
- Doesn't work for merchants that only accept cards
- Doesn't solve the enterprise requirement: "show me the audit trail and spending controls"

**Sardis takes the third path:** We don't care which rail the money moves on. We own the **authorization layer** — the mandate that says "this agent can spend up to $500 at approved merchants, on any rail, with human approval above $200, and I can revoke it instantly."

That's the layer that ages well regardless of which rails win.

## Why Now

The timing convergence is unprecedented:

1. **Protocol standardization is happening now.** AP2 launched September 2025 with 60+ partners. Agent Pay and TAP launched in 2025. The window to become the default authorization layer is 12-18 months.

2. **Enterprise demand is real.** Companies deploying AI agents (Salesforce Agentforce, SAP Joule, ServiceNow) need spending controls before their CFOs will greenlight production deployment.

3. **The developer ecosystem is ready.** LangChain, CrewAI, OpenAI Agents SDK, Vercel AI SDK — all shipping agent capabilities. None of them solve payments. We integrate with all of them.

4. **Market size is validated.** McKinsey: $3-5T in agentic commerce by 2030. Gartner: $15T in B2B agent-mediated spending by 2028. Even capturing 0.1% of payment infrastructure = multi-billion dollar market.

## The Bridge to Payment Tokens

The spending mandate is not just today's product. It's the **architectural bridge** to the payment token future:

- **Phase 1 (now):** Mandates enforced off-chain by the Sardis API
- **Phase 2 (6-12 months):** Mandates encoded as ERC-20 transfer hooks — the token itself enforces spending rules
- **Phase 3 (12-18 months):** Native payment tokens with embedded mandate semantics, portable across chains

Every feature we ship today is composable with the on-chain future without a rewrite. The mandate is the invariant; the enforcement layer is the variable.

## Traction

- 50,000 SDK installs (zero marketing spend)
- Integrations with 10+ agent frameworks (LangChain, CrewAI, OpenAI, Google ADK, Vercel AI, Browser Use, AutoGPT, Composio)
- Advisory from leaders at Coinbase, Stripe, Circle, Base, Lightspark, Solana, Bridge
- 500K+ lines of production code, 68 API endpoints, 9 smart contracts, 194 test files
- Built by a solo 20-year-old founder

## The Punchline

The future of agent payments is not a wallet war or a rail war. It is an **authorization-layer war.**

We're building the authorization layer.
