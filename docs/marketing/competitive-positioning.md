# Competitive Positioning — Sardis vs. The Market

Updated: 2026-03-24 | Status: ACTIVE

---

## Full Competitive Matrix

| Dimension | Sardis | Ramp Agent Cards | Alter | Stripe MPP | Coinbase AgentKit |
|-----------|--------|-----------------|-------|------------|-------------------|
| **What it is** | Full-stack Payment OS for AI agents | Fiat corporate cards for agents | Zero-trust identity + access control | Payment protocol (HTTP 402) | On-chain wallet toolkit |
| **Payment rails** | Stablecoin (USDC/EURC, 6 chains) + virtual cards (Laso) | Fiat only (Visa) | None — identity only | Fiat + stablecoin via directory | On-chain only (CDP wallets) |
| **Policy engine** | NLP mandates ("max $500/day on AWS"), 12-check pipeline | Merchant category codes + hard limits | Access control policies | None — buyer builds own controls | None |
| **Compliance** | 15 modules: KYC, KYB, AML (6 providers), SAR, MiCA, PEP, travel rule, Merkle audit | Corporate card compliance only | Identity attestation | PCI compliance | Minimal |
| **Custody model** | Non-custodial (Turnkey MPC) | Custodial (Ramp holds funds) | N/A | Custodial (Stripe holds) | Non-custodial (CDP) |
| **Audit trail** | Merkle-anchored, tamper-evident, on-chain proof | Transaction history | Authorization logs | Stripe dashboard logs | On-chain (public ledger) |
| **Cross-border FX** | USDC/EURC atomic swap — 5-15 bps, 1.5s settlement | Standard FX — 1-3%, 2-3 days | None | Standard FX rates | On-chain only |
| **Framework integrations** | 18+: LangChain, CrewAI, AutoGPT, OpenAI Agents SDK, OpenAI direct, Claude Agent SDK, Google ADK, Google A2A, Coinbase AgentKit, Browser Use, Composio, OpenClaw, Stagehand, Vercel AI SDK, Activepieces, n8n, E2B, GPT Actions, MCP server (Claude/Cursor/Windsurf) | REST API only | SDK | MPP directory (100+ services) | AgentKit SDK |
| **Developer experience** | pip install sardis + sardis.pay() — 5 min to first payment | Dashboard + API key | SDK integration | MPP client integration | AgentKit ActionProvider |
| **Pricing** | Free / $29 / $199 / $499 / Enterprise + 0.1-0.5% per tx | Enterprise custom (high ACV) | Enterprise custom ($40M raised) | Per-transaction | Free (chain gas fees) |
| **Stage** | Pre-revenue, 70K+ SDK installs, live on Base and Tempo mainnet, Stripe MPP early access partner | Live (March 2026) | $40M raised, live | Live (March 2026) | Live |

---

## Head-to-Head Positioning

### vs. Ramp Agent Cards

**Their strength:** Live product with enterprise brand recognition. Fiat rails work with existing vendor infrastructure. Tokenized per-transaction credentials reduce card fraud.

**Their weakness:** Fiat-only — cannot do stablecoin payments, cross-chain transfers, or on-chain settlement. No NLP policy engine. Custodial model. Compliance limited to card-level controls. No framework integrations beyond REST API.

**Our positioning:** "Ramp gives agents a credit card. Sardis gives agents a policy-controlled wallet that works on any rail — stablecoin, fiat, cross-chain — with 15 compliance modules built in. We are the operating system; they are one payment method."

**When to recommend Sardis:** Prospect needs stablecoin payments, cross-border FX at low cost, programmable policy enforcement, Merkle-anchored audit trails, or deep AI framework integration.

=======
---

>>>>>>> 9399f9cb (feat(docs): create competitive positioning document)
### vs. Alter

**Their strength:** $40M funding. Strong security narrative (zero-trust for AI agents). Enterprise focus on agent identity and access control.

**Their weakness:** Identity and access control only — no payment execution, no settlement, no FX, no compliance stack. You still need a payment system after Alter tells you who the agent is.

**Our positioning:** "Alter answers 'who is this agent?' Sardis answers 'what can this agent spend, where, when, and how much — and here is the cryptographic proof.' Identity is one layer. We provide the full payment stack."

**When to recommend Sardis:** Always. Alter is complementary, not competitive. Position as "Alter + Sardis = complete agent financial infrastructure."

<<<<<<< HEAD
### vs. Stripe MPP (Merchant Payment Protocol)

**Their strength:** Stripe brand. 100+ services in MPP directory. Visa, Lightspark, and VGS as partner extensions. First-mover on HTTP 402 payment protocol.

**Their weakness:** MPP is a protocol, not a platform. No policy engine — the buyer must build their own spending controls. No compliance modules. No wallet management. No audit trail beyond Stripe dashboard.

**Our positioning:** "MPP is the highway. Sardis is the vehicle with airbags, GPS, and insurance. We are MPP-native (early access) — we make MPP safe for autonomous agents by adding policy enforcement, compliance, and audit on top."

**When to recommend Sardis:** Position as complement, not competitor. "Use MPP for service discovery and payment initiation. Use Sardis for policy enforcement, compliance, and settlement."

=======
---

>>>>>>> 9399f9cb (feat(docs): create competitive positioning document)
### vs. Coinbase AgentKit

**Their strength:** Coinbase ecosystem. CDP wallets are non-custodial. Free to use. Strong developer community.

**Their weakness:** Toolkit, not a platform. No spending policies, no compliance modules, no cross-chain routing, no NLP mandates, no audit trail beyond on-chain records. Developer must build everything above raw wallet access.

**Our positioning:** "AgentKit gives agents a wallet. Sardis gives agents a wallet with spending mandates, compliance, FX, and a tamper-evident audit trail. We integrate with AgentKit — it is a distribution channel for us, not a competitor."

**When to recommend Sardis:** When prospect needs policy controls, enterprise compliance, or managed infrastructure beyond raw wallet access.

---

## One-Line Differentiators by Audience

<<<<<<< HEAD
- **Crypto-native:** "We handle compliance so you do not need a compliance team. 15 modules — KYC, AML, SAR, MiCA, Merkle audit — all production-grade."
- **Fiat-native:** "We settle in 1.5 seconds at 5-15 basis points. Not 2-3 days at 1-3% through SWIFT."
- **Identity-only:** "Identity tells you who. Policy tells you what, when, and how much. We enforce the rules and prove it cryptographically."
- **Developer-first:** "pip install sardis. sardis.pay(). Five minutes to your first policy-controlled payment. Works with OpenAI, Claude, CrewAI, LangChain, and 11 more frameworks."

---

## Competitive Moats (Defensibility)

| Moat | Description | Time to replicate |
|------|-------------|-------------------|
| **NLP policy engine** | Natural language to machine-enforced spending rules. No competitor accepts English as policy. | 6-12 months |
| **15 compliance modules** | KYC, KYB, AML, PEP, SAR, MiCA, travel rule, risk scoring, fraud rules, adverse media, Merkle audit, policy bundles, agent identity, compliance reports, TAP signatures | 12-18 months |
| **15 framework integrations** | Pre-built tools for every major AI framework. Network effect: more frameworks = more agents = more payments. | 3-6 months per integration |
| **Merkle-anchored audit trail** | Tamper-evident proof of every spending decision. On-chain anchoring means even Sardis cannot alter records. | 3-6 months |
| **Goal drift detection** | Per-agent behavioral baselines with statistical anomaly detection (K-S test, chi-squared). | 6-9 months |
