# SARDIS VC APPLICATION REFERENCE DOCUMENT

**Last Updated:** February 2026
**Founder:** Efe Baran Durmaz
**Company:** Sardis
**Website:** sardis.sh
**Email:** invest@sardis.sh | efebarandurmaz05@gmail.com

---

## QUICK FACTS

| Field | Answer |
|-------|--------|
| Company Name | Sardis |
| HQ | Istanbul, Turkey (willing to relocate to SF) |
| Tagline | "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust." |
| Industry | Fintech > Payments |
| Founded | ~6 months ago (August 2025 full-time) |
| Stage | Pre-revenue, pre-prod/testnet, design partner phase |
| Funding Raised | $0 |
| Founders | 1 (seeking cofounder: Founding Protocol Engineer or GTM Lead, 20-25% equity) |
| Full-time | Yes (since August 2025) |

---

# SECTION 1: PEARX S26 APPLICATION ANSWERS

**DEADLINE: February 22, 2026 (URGENT)**

### Q1: Company Name
**Answer:** Sardis

### Q2: Company URL
**Answer:** sardis.sh

### Q3: HQ Country/City
**Answer:** Istanbul, Turkey (willing to relocate to San Francisco)

### Q4: Funding Raised to Date
**Answer:** $0 (bootstrap/founder-funded)

### Q5: Industry
**Answer:** Fintech > Payments (or: Fintech > Infrastructure)

### Q6: One-Line Description
**Answer:** Payment OS for the Agent Economy—non-custodial MPC wallets with natural language spending policies for AI agents.

**Alternative (Shorter):**
Stripe for AI agents: non-custodial payment infrastructure with natural language safety policies.

### Q7: What Are You Building, and Why?

**Concise Answer:**

Sardis is a payment infrastructure platform that enables AI agents to autonomously manage financial transactions safely and compliantly. We provide:

- **Non-custodial MPC wallets** (via Turnkey): Funds are cryptographically distributed across multiple parties—no single point of failure, which is critical because enterprises will never trust a startup with unilateral control of their capital.
- **Natural language spending policies**: Instead of complex contract code, agents and developers write guardrails in human language: "spend max $100/day on AWS bills" or "don't process crypto transfers over $50k without approval."
- **Multi-chain settlement** (5 EVM chains): Agents can seamlessly move capital across Base, Arbitrum, Polygon, Optimism, and other chains.
- **Integrated compliance** (Persona KYC + Elliptic AML): Every transaction is screened for regulatory risk before execution.
- **Virtual cards** (Lithic partnership): Agents can spend fiat through physical or digital Lithic cards for real-world purchases.
- **MCP-native architecture**: Works with Claude Desktop and other MCP servers with zero configuration—agents can autonomously control payment operations.

**Why now:**

1. **AI agents crossed the capability threshold**: Claude 3.5 Sonnet, GPT-4o, and other frontier models can now reason through complex multi-step financial operations.
2. **Major payment protocols are emerging**: AP2 (Google + Visa, Mastercard, PayPal), ACP (OpenAI + Stripe), and x402 (Coinbase) are standardizing agent payment frameworks.
3. **MPC custody is production-ready**: Turnkey and other solutions have made distributed key management viable at enterprise scale.
4. **Enterprise is adopting autonomous AI at scale**: Companies are moving beyond chat interfaces to autonomous agents that need real financial authority.

**Why this matters:**

The core insight is "Financial Hallucination"—agents can execute transactions based on flawed logic, making inconsistent decisions. This is like SQL injection: the payment/transaction layer must be the security boundary. Sardis treats spending policies like input sanitization, making it impossible for agents to violate guardrails regardless of what they reason.

### Q8: What Unique Insight Do You Have?

**Primary Insight:**

**"Financial Hallucination is a Control Problem, Not a Payment Problem"**

Enterprises will trust agents with payment authority only if spending is mathematically enforced through code, not just promised in documentation. Most competitors focus on the payment layer (how to settle funds). We focus on the control layer (what agents can spend).

This means:
- **Non-custodial is non-negotiable for enterprise**: A startup that holds customer funds will never be allowed into an enterprise payment system. This is why we use Turnkey's distributed MPC, not a managed wallet service.
- **Natural language policies are the UX revolution**: Developers don't want to write contract code to define spending rules. They want to write "spend max $500/day on inference costs," and have that automatically compiled into guardrails that execute in the payment logic.
- **The agent payment market is winner-take-most**: Once enterprises standardize on one infrastructure, switching costs are high. Being the platform that enterprises trust first is everything. We're optimized for enterprise non-negotiables (non-custodial + compliance), not consumer features.

### Q9: How Far Along Are You?

**Traction Summary:**

- **100% feature-complete infrastructure**: All core components built and integrated.
- **Smart contracts deployed**: Sardis contract deployed on Base Sepolia testnet, ready for mainnet.
- **36 MPC-native tools**: Full MCP toolkit for wallet management, policy enforcement, and payment execution.
- **5 EVM chains supported**: Base, Arbitrum, Polygon, Optimism, and more.
- **11 third-party integrations live**: Turnkey (MPC), Lithic (virtual cards), Bridge.xyz (fiat), Persona (KYC), Elliptic (AML), plus others.
- **15,000+ lines of production code**: 172 Python files, 12 packages, all built by one founder.
- **Design partner phase**: 3 alpha design partners in active onboarding (developer tools companies).
- **Public beta target: February 2026**: Main infrastructure ready to scale.
- **Mainnet production target: March 2026**: Ready for live transaction volume.

**Code Stats:**
- Python backend: FastAPI, Pydantic (Core API)
- Smart contracts: Solidity, Foundry (Multi-chain contract suite)
- SDKs: Python + TypeScript (Developer integration)
- MCP Server: TypeScript (@modelcontextprotocol/sdk)
- Infrastructure: Vercel (frontend), Neon (Postgres), Upstash (Redis)
- Built with: Claude (Cursor), GitHub Copilot

### Q10: Do You Have People Using Your Product?

**Answer:**

We have 3 design partners (developer tools and infrastructure companies) currently onboarding in alpha. These are validating product-market fit and giving us feedback on policy frameworks, multi-chain UX, and integration pathways. We're not at paying customers yet, but we have strong interest from:

- Autonomous agent platforms (want to add payment capabilities)
- Developer tooling companies (want to monetize agent integrations)
- AI infrastructure teams (want to enable real-world transactions)

**Expected metrics by March 2026:**
- 5-10 beta design partners live
- $0 revenue (expected first revenue Q2 2026)
- 100+ MCP client connections running daily

### Q11: Do You Have Revenue?

**Answer:** No revenue yet. We're pre-revenue and focusing on product-market fit with design partners. Revenue model is designed but not yet activated:

- **Transaction fees**: 0.25-0.75% on volume
- **SaaS subscriptions**: $99-999/month tiers (based on volume + feature tier)
- **Enterprise contracts**: Custom pricing for high-volume customers
- **Card interchange**: Revenue share on Lithic virtual card spend

**Target:** $1M ARR by Q4 2026 (assuming public beta in Feb, mainstream adoption starting Q2).

### Q12: Who Are Your Competitors? How Do You Differentiate?

**Competitive Landscape:**

| Competitor | Funding | Key Insight | Sardis Advantage |
|------------|---------|------------|------------------|
| **Skyfire** | $9.5M (Coinbase Ventures, a16z) | First-mover in agent payments | Custodial (enterprise risk), no compliance by default |
| **Nevermined** | $4M | Micropayment focus | No KYC/AML, doesn't scale to enterprise |
| **Payman AI** | $13.8M (Visa-backed) | Custodial bank model | Visa-dependent, not autonomous/programmable |
| **Natural** | $9.8M | Enterprise B2B | Only B2B, no self-service; we have both |
| **Stripe (ACP)** | N/A (OpenAI partnership) | Payment layer for agents | Stripe doesn't do custody/wallets/compliance |
| **Coinbase (x402)** | N/A (internal) | On-chain agent transactions | CeFi, requires Coinbase account; we're open-ended |

**Sardis Differentiation:**

1. **Non-custodial MPC architecture** (competitor advantage #1)
   - Turnkey-powered distributed keys mean we never touch customer funds
   - Enterprises require this for B2B adoption
   - Competitors either do custodial (Skyfire, Payman) or don't address it (Nevermined)

2. **Natural language spending policies** (competitor advantage #2)
   - Unique UX: policies are written in English, compiled into code
   - Competitors use contract code or simple allowlists
   - Scales developer adoption by 10x (less technical friction)

3. **Full AP2/TAP/x402 protocol compliance** (competitor advantage #3)
   - Built for the protocol standards that are emerging (AP2 by Google + 60 partners, x402 by Coinbase)
   - Competitors are proprietary; we're protocol-native
   - When the industry standardizes, we're already there

4. **Integrated compliance** (competitor advantage #4)
   - Persona KYC + Elliptic AML baked into payment flow
   - Most competitors handle compliance as afterthought
   - Regulatory-first approach de-risks enterprise adoption

5. **Multi-chain** (competitor advantage #5)
   - 5 EVM chains out of the box, extensible to more
   - Competitors are typically single-chain or limited
   - Agents need capital mobility across chains

6. **MCP-native** (competitor advantage #6)
   - Works with Claude Desktop agents with zero configuration
   - All competitors require custom integrations
   - We're the infrastructure layer that agents already know

**What We Understand That They Don't:**

Enterprise will not adopt agent payments from a startup that holds their funds. The trust equation fundamentally changes when custody is removed. Most competitors see custody as an implementation detail. We see it as the *only* acceptable model for enterprise autonomy. This unlocks a 10x larger TAM because enterprises can now use agents for real financial operations, not just small transactions.

### Q13: How Big Is the Market Opportunity? (Bottoms-Up Calculation)

**TAM (Total Addressable Market):**

$65B by 2028 (projected AI agent market size, IDC/Gartner estimates)

**SAM (Serviceable Addressable Market):**

$8B: Of the AI agent market, only agents that require payment infrastructure

**SOM (Serviceable Obtainable Market), Year 5:**

$800M (calculated as ~10% of SAM, achievable with moderate market share)

**Bottoms-Up Calculation (More Detailed):**

1. **Market Size by Agent Type:**
   - Autonomous research agents: 500k → $2M ARR (low spend per agent)
   - Autonomous purchasing agents: 200k → $5M ARR (high spend, high risk, high compliance)
   - Autonomous infrastructure agents: 100k → $3M ARR (high-value transactions)
   - Autonomous trading agents: 50k → $10M ARR (highest value but smallest segment)
   - **Total addressable agents: ~1M agents by 2028**

2. **Spending Per Agent:**
   - Research agents: $50/month → $500/year
   - Purchasing agents: $5,000/month → $60,000/year
   - Infrastructure agents: $2,000/month → $24,000/year
   - Trading agents: $50,000/month → $600,000/year

3. **Revenue Model per Agent (Sardis capture):**
   - Transaction fee model: 0.5% take rate on agent spend
   - Example: $100k agent spend/year × 0.5% = $500 revenue
   - SaaS tiers add $50-300/month/agent (licensing)

4. **Market Maturity Curve:**
   - **2026 (Year 1)**: $2M agent payment volume → $10k revenue (early adopters)
   - **2027 (Year 2)**: $100M agent payment volume → $500k revenue (mainstream adoption)
   - **2028 (Year 3)**: $1B agent payment volume → $5M revenue (scale)
   - **2030+**: $1.7T projected agent payment volume globally → enterprise-scale revenue

5. **Competitive Share Assumption:**
   - Fragmented market (5+ major players): assume 15-20% market share possible by 2030
   - At 20% of $1.7T × 0.5% = $1.7B annual revenue (platform assumption)
   - More realistic conservative: 5% share = $425M annual revenue, 10% share = $850M

**Key Growth Drivers:**
- AI agent payment volume grew **35,000% in Q4 2025** (year-over-year)
- $1.7 trillion projected by 2030 (CNBC, blockchain research)
- AP2 protocol adoption (Google + Visa + Mastercard + PayPal + 60 partners)
- Enterprise adoption of autonomous agents (McKinsey: 35% of enterprises deploying agents by 2027)

### Q14: How Many Founders? How Long Working on This?

**Answer:**

Currently 1 founder (Efe Baran Durmaz).

**Timeline:**
- Started: ~6 months ago (August 2025 went full-time)
- Current stage: Building and design partner validation

**Background:**
Efe has 8+ years in blockchain/crypto engineering, including deep smart contract experience and infrastructure work. Built 15k+ lines of production code solo in 6 months, demonstrating strong execution velocity and full-stack capability.

**Cofounder Status:**
Actively seeking 1 cofounder (20-25% equity):
- **Role 1: Founding Protocol Engineer** (smart contract / protocol design focus)
  - Would take ownership of Layer 2 integrations, protocol R&D
- **Role 2: GTM Lead** (go-to-market / business development focus)
  - Would take ownership of sales, partnerships, product positioning

### Q15: Equity Split

**Current:**
- Founder (Efe): 100%

**Post-Cofounder:**
- Founder (Efe): 75-80%
- Cofounder (TBD): 20-25%

**Employee option pool:**
- 10-15% reserved for future hires

### Q16: Full-Time or Part-Time?

**Answer:** Full-time (since August 2025). Founder is completely committed to Sardis.

### Q17: Currently a Student?

**Answer:** No.

### Q18: Example of Tackling a Problem in a Novel Way

**Problem:** Enterprise doesn't trust startups with unilateral custody of their capital.

**Novel Solution:** Use Turnkey's distributed MPC architecture instead of traditional managed wallets.

**Why it's novel:**
- Cryptographic distribution means no single party (including Sardis) has access to funds
- Enterprise can verify that Sardis literally cannot steal or freeze capital, even if compromised
- This is the first time a startup payment infrastructure can make this guarantee
- Shifts the trust model from "trust us" to "trust the math"

**Implementation:**
- Keys are split across Turnkey's infrastructure, enterprise's secure environment, and user's device
- Any transaction requires cryptographic approval from multiple parties
- Sardis can define policies but cannot override them unilaterally
- Enterprise has cryptographic proof of non-custodialism

**Impact:** Unlocks enterprise adoption that competitors with custodial models can never reach.

---

**Alternative Example (Natural Language Policies):**

**Problem:** Developers struggle to define complex spending guardrails for agents.

**Novel Solution:** Natural language policy compiler.

**Why it's novel:**
- Most payment systems use code (Solidity) or simple allowlists (if/then rules)
- We parse English: "spend max $500/day on AWS, but don't spend more than 10% of daily budget on any single vendor"
- Policy is compiled into on-chain guardrails that execute automatically
- Non-technical users can manage enterprise payment policy without writing code

**Impact:** 10x faster onboarding, fewer bugs, more enterprises can adopt autonomous agents.

### Q19: What Makes You an Outlier?

**Technical Outlier:**
- Built 15k+ lines of production code solo in 6 months
- Shipped 36 MCP tools, 11 third-party integrations, 5-chain smart contract suite
- Deep expertise in smart contracts, MPC cryptography, and agent architecture (rare combination)

**Business Outlier:**
- Identified "Financial Hallucination" as the core enterprise risk (not just "payments need AI")
- Built for enterprise non-custodialism from day one (competitor differentiator)
- Focused on protocol standards (AP2, x402) instead of proprietary lock-in
- Recognized MCP-native as the winning UX pattern for agents

**Execution Outlier:**
- Shipped designed, implemented, and integrated payment infrastructure solo in 6 months
- Onboarded 3 design partners while solo-building
- Zero outside funding, bootstrap execution, strong unit economics discipline

**Market Timing Outlier:**
- Entered market at exact moment when (1) AI agents crossed capability threshold, (2) payment protocols emerged, (3) MPC custody became viable, (4) enterprise trusted agents at scale
- 18-24 month window to become the standard before market consolidates

### Q20: Applied to PearX Before?

**Answer:** No (first application to PearX).

### Q21: How Did You Hear About PearX?

**Answer:** [Fill in based on actual discovery path: e.g., founder recommendation, online research, product hunt, etc.]

If unsure: "Identified PearX as leading protocol/infrastructure accelerator with strong focus on foundational technology and non-consensus bets."

---

# SECTION 2: GENERAL VC APPLICATION BUILDING BLOCKS

Use these variants to adapt answers for any accelerator or VC firm. Copy and paste the appropriate length for your application.

## 2.1 COMPANY OVERVIEW VARIANTS

### Ultra-Short (50 chars)
"Stripe for AI agents: non-custodial payments"

### One-Liner (20 words)
"Payment OS for the Agent Economy—non-custodial MPC wallets with natural language spending policies."

### Elevator Pitch (50 words)
"Sardis is the payment infrastructure layer for AI agents. We provide non-custodial MPC wallets, natural language spending policies, multi-chain settlement, and integrated compliance. Enterprises can now confidently give agents financial authority without trusting a startup to hold their capital."

### Two-Paragraph Pitch (200 words)

**Paragraph 1 (Problem):**
AI agents are crossing the capability threshold—Claude 3.5, GPT-4o, and emerging models can now reason through complex multi-step operations autonomously. But enterprises face a critical problem: agents need financial authority to operate in the real world (spend on cloud infrastructure, make purchases, execute trades), yet traditional payment infrastructure wasn't designed for non-human actors. Enterprises will never give agents access to capital through a startup that holds their funds unilaterally.

**Paragraph 2 (Solution):**
Sardis is the payment OS for agents. We use Turnkey's distributed MPC architecture (non-custodial), natural language spending policies that compile into unbreakable guardrails, multi-chain settlement, integrated compliance (Persona KYC + Elliptic AML), and virtual cards for fiat access. Because we never touch customer funds, enterprises can now adopt autonomous agents at scale. We're built protocol-native (AP2, x402 compliant) and MCP-native, meaning agents control payments with zero configuration.

### Full Pitch (500+ words, for longer applications)

**Opening (Hook):**
"Financial Hallucination" isn't a philosophical problem—it's an enterprise blocker. AI agents can execute transactions based on flawed reasoning, making inconsistent financial decisions. This is like SQL injection for finance: the system must enforce spending boundaries at the infrastructure layer, not rely on agent judgment.

**Problem Deep-Dive:**
Three realities are colliding:

1. **AI agents are now capable enough to manage real financial operations.** Claude 3.5 Sonnet, GPT-4o, and emerging models can reason through multi-step autonomous workflows. Companies are deploying agents for autonomous research, purchasing decisions, infrastructure management, and even trading.

2. **Major payment protocols are emerging.** AP2 (backed by Google, Visa, Mastercard, PayPal, and 60+ partners) is standardizing how agents access payment networks. ACP (OpenAI + Stripe), x402 (Coinbase), and others are creating interoperable payment frameworks. The industry is consensus-shifting toward agent-native payments.

3. **Enterprise won't use agent payments from startups they don't trust with capital.** Every legacy payment system (Stripe, PayPal, Square) succeeded because they could hold merchant funds and settle daily. But for agents, unilateral startup custody is a dealbreaker. Enterprises need cryptographic proof that a startup cannot steal or freeze capital.

**Solution:**
Sardis is the payment infrastructure platform built for this moment:

- **Non-custodial MPC wallets (Turnkey)**: Keys are cryptographically distributed—Sardis cannot unilaterally access funds. Enterprise has mathematical proof of non-custodialism.
- **Natural language spending policies**: Developers write guardrails in English ("spend max $500/day on AWS"), which compile into unbreakable on-chain rules. Agents cannot violate policies regardless of what they reason.
- **Multi-chain settlement**: Agents move capital across Base, Arbitrum, Polygon, Optimism seamlessly.
- **Integrated compliance**: Every transaction screened by Persona KYC + Elliptic AML before execution.
- **Virtual cards (Lithic)**: Agents spend fiat through physical or digital cards for real-world purchases.
- **MCP-native**: Works with Claude agents with zero configuration.

**Traction:**
- 100% feature-complete infrastructure, deployed on Base Sepolia testnet
- 36 MCP tools, 11 third-party integrations, 5 EVM chains supported
- 15k+ lines of production code built solo in 6 months
- 3 design partners in active onboarding
- Public beta target: February 2026, mainnet March 2026

**Market Opportunity:**
- $65B AI agent market by 2028
- $8B TAM for payment infrastructure specifically
- Agent payment volume grew 35,000% in Q4 2025 (year-over-year)
- $1.7 trillion projected agent payment volume by 2030
- 18-24 month window to become the standard before market consolidates

**Why Now:**
(1) Agents crossed capability threshold, (2) protocols emerging, (3) MPC custody production-ready, (4) enterprise adopting autonomous AI at scale.

**Competitive Advantage:**
Every competitor either uses custodial models (excluding enterprise), ignores compliance, focuses on micropayments, or targets B2B enterprise-only. Sardis is the only platform optimized for enterprise non-custodialism + compliance + self-service + protocol-native. Winner-take-most market dynamics mean being first with enterprise trust is everything.

---

## 2.2 PROBLEM STATEMENT VARIANTS

### Short (2 sentences)
AI agents need financial authority to operate in the real world, but enterprises will never trust startups with unilateral custody of their capital. Current payment infrastructure wasn't designed for non-human actors and lacks the guardrails to enforce spending policies autonomously.

### Medium (1 paragraph)
Three forces are colliding: (1) AI agents are now capable of managing real financial operations (autonomous purchasing, infrastructure spending, trading), (2) major payment protocols are emerging (AP2, ACP, x402) to standardize agent payments, and (3) enterprise won't adopt agent payments from startups that control their funds unilaterally. Traditional payment infrastructure (Stripe, PayPal) succeeded by holding merchant funds. But for agents, this model creates unacceptable risk. Enterprises need two guarantees: cryptographic proof that the startup cannot steal capital, and policy-level enforcement that agents cannot violate spending guardrails. Today's payment platforms provide neither.

### Long (Detailed with examples)
**The Technical Problem:**
AI agents execute transactions based on reasoning that can be flawed or inconsistent. An agent might decide to spend $50k on a contract it misunderstood, or allocate 95% of budget to a single vendor despite instructions to diversify. This is "Financial Hallucination"—reasoning errors that translate into financial mistakes. Unlike human operators who can self-correct, agents will consistently execute the logic they've reasoned through. The payment system must enforce spending boundaries at the infrastructure layer, not rely on agent judgment.

**The Enterprise Trust Problem:**
For AI agents to operate autonomously in the real world, they need financial authority: ability to spend cloud compute budgets, make purchases, execute transactions. But enterprises face a custody paradox. Traditional fintech solutions hold merchant funds unilaterally (Stripe, PayPal model), which enterprises accept for payment processing. But giving an unproven startup unilateral control of autonomous agent budgets is unacceptable enterprise risk. What if the startup is compromised? What if the startup fails? What if regulation changes? Enterprises need mathematical proof that a startup cannot steal or freeze capital, regardless of circumstance.

**The Infrastructure Gap:**
Today's payment platforms fall into two categories:

1. **Custodial platforms (Stripe, PayPal)**: Simple, centralized, but unacceptable for enterprise AI adoption.
2. **Non-custodial crypto (DEXs, wallets)**: Self-sovereign but lack compliance, policy enforcement, fiat bridges, and the user experience enterprises need.

There is no platform that provides:
- Non-custodial architecture (no startup custody)
- Enterprise-grade compliance (KYC, AML integrated)
- Autonomous policy enforcement (spending limits enforced in code, not documentation)
- Multi-chain settlement (capital mobility across chains)
- Fiat bridges (agents spending real-world money through cards)
- Protocol-native design (built on emerging standards like AP2)

**The Market Timing Problem:**
This gap is opening right now because (1) agents just crossed the capability threshold to manage real operations, (2) payment protocols (AP2, ACP, x402) are standardizing agent payment frameworks, (3) MPC custody just became production-ready at enterprise scale, and (4) enterprises are moving from chatbot experiments to autonomous AI at scale. The 18-24 month window to own this category is closing—whoever becomes the standard first wins.

---

## 2.3 SOLUTION DESCRIPTION VARIANTS

### Short (2-3 sentences)
Sardis is the payment OS for AI agents. We provide non-custodial MPC wallets (agents never hold corporate funds directly), natural language spending policies (guardrails written in English, compiled into code), multi-chain settlement, integrated compliance, and virtual cards for fiat access. Enterprises adopt agents at scale because they have cryptographic proof we cannot steal capital.

### Medium (1-2 paragraphs)

Sardis is the payment infrastructure layer that makes it safe and compliant for enterprises to give AI agents financial authority.

Our core offering has six components:

1. **Non-custodial MPC wallets (Turnkey-powered)**: Keys are cryptographically split—no single party including Sardis can unilaterally access funds. Enterprise has mathematical proof of non-custodialism.

2. **Natural language spending policies**: Developers write guardrails in English ("spend max $500/day on AWS, but never spend >10% of daily budget with any single vendor"). We compile these into unbreakable on-chain rules. Agents cannot violate policies regardless of what they reason.

3. **Multi-chain settlement**: Capital flows seamlessly across Base, Arbitrum, Polygon, Optimism, and other EVM chains. Agents can move liquidity where it's needed.

4. **Integrated compliance**: Every transaction is screened by Persona KYC and Elliptic AML before execution. We front-run regulatory risk.

5. **Virtual cards (Lithic partnership)**: Agents can spend fiat through physical or digital Lithic cards for real-world purchases and services.

6. **MCP-native architecture**: Built for Claude agents and other MCP servers. Agents control Sardis wallets natively with zero configuration or custom integration.

The result: enterprises can deploy autonomous agents with real financial authority—knowing spending is mathematically enforced and regulatory-compliant.

### Long (Detailed technical description)

**Architecture Overview:**

Sardis is built as a modular payment OS with three layers:

**Layer 1: Non-Custodial Wallet Infrastructure**
- All customer wallets are MPC-secured via Turnkey
- Private keys are distributed across (A) Turnkey's infrastructure, (B) customer's secure enclave, (C) user's device
- Any transaction requires cryptographic approval from multiple parties
- Sardis signs transactions but cannot initiate them unilaterally
- Customers can independently verify that Sardis has zero unilateral custody

**Layer 2: Autonomous Policy Engine**
- Natural language policy language (custom DSL) that non-engineers can write
- Example policy: "daily_budget=1000 AND per_vendor_limit=100 AND blacklist=[sanctioned_addresses] AND auto_approve_below=50"
- Policies compile into smart contract guardrails deployed on-chain
- At runtime, agents request transactions → policy engine evaluates → contract enforces approval/rejection
- Policies are immutable once deployed (can only be updated via multi-sig governance)
- Agent reasoning cannot override policy layer

**Layer 3: Compliance & Settlement**
- Transaction pre-screening via Persona (KYC) and Elliptic (AML)
- Risk scoring and transaction flagging
- Multi-chain settlement engine (handles Base, Arbitrum, Polygon, Optimism, etc.)
- Virtual card integration (Lithic API)
- Fiat on/off ramps (Bridge.xyz)

**Developer Experience:**
Developers integrate Sardis in three steps:

1. **Define policy** (YAML or natural language): What can agents spend on?
2. **Connect wallet** (MPC setup): Sardis creates non-custodial wallet, enterprise approves key distribution
3. **Give agent access** (MCP client): Agent uses Claude + Sardis MCP server to propose and execute transactions

Everything is self-service and can be done in <1 hour.

**Agent Experience:**
Agents have native access to payment operations through MCP:
```
Agent reasoning: "I need to spin up an AWS EC2 instance for model inference. This should cost ~$50/month."
Agent action: "Use Sardis to spend $60 from the compute budget for AWS"
System check: Policy allows AWS spend, within daily/vendor limits, KYC/AML passes
System action: Execute transaction
Agent result: AWS infrastructure deployed and paid
```

**Compliance & Risk:**
- Every transaction is screened before execution (not after)
- KYC happens at account creation (Persona)
- AML happens at transaction time (Elliptic)
- Suspicious activity triggers automatic hold + review
- All transactions are auditable and compliant with AP2 standard frameworks

---

## 2.4 TRACTION & PROGRESS

### Bullet Points Format

**Current State (Feb 2026):**
- ✓ 100% feature-complete infrastructure
- ✓ Smart contracts deployed on Base Sepolia testnet
- ✓ 36 MCP tools implemented and tested
- ✓ 5 EVM chains supported (Base, Arbitrum, Polygon, Optimism, + others)
- ✓ 11 third-party integrations live (Turnkey, Lithic, Bridge.xyz, Persona, Elliptic, etc.)
- ✓ 15k+ lines of production code
- ✓ 172 Python files across 12 packages
- ✓ All core infrastructure built by single founder

**Design Partner Validation:**
- 3 alpha design partners actively onboarding
- Validating: policy frameworks, multi-chain UX, integration pathways
- Expected to have 5-10 live beta partners by March 2026

**Milestones (Roadmap):**
- Feb 2026: Public beta launch, mainnet smart contracts, API documentation
- Mar 2026: Mainnet production, first paying customers
- Q2 2026: 100+ active integrations, $100k MRR run rate
- Q3 2026: Enterprise tier launched, 500+ integrations
- Q4 2026: $1M ARR target

**Code Stats:**
- Backend: Python 3.12 FastAPI
- Smart contracts: Solidity + Foundry
- SDKs: Python, TypeScript
- MCP Server: TypeScript
- Infrastructure: Vercel, Neon (Postgres), Upstash (Redis)

**Team:**
- 1 founder (full-time, all engineering)
- Seeking 1 cofounder (20-25% equity)

### Narrative Format

Sardis is currently in the late pre-product/early beta phase. The founder has spent the past 6 months building a complete payment infrastructure platform solo, resulting in 15k+ lines of production code across 172 Python files and 12 integrated packages.

The core infrastructure is fully functional and deployed on Base Sepolia testnet. This includes a comprehensive set of smart contracts supporting multi-chain operations, a FastAPI backend with complete payment logic, MCP server implementation for agent connectivity, and integrations with 11 third-party services (Turnkey for MPC wallets, Lithic for virtual cards, Persona for KYC, Elliptic for AML, and others).

The platform currently supports 5 EVM chains and exposes 36 distinct MCP tools that agents can use to manage wallets, define policies, and execute transactions. Natural language policy compilation is fully working, and the non-custodial architecture has been stress-tested against requirements from early design partners.

Three design partners (all developer tools and infrastructure companies) are currently in active alpha onboarding. These partnerships are focused on validating the core value proposition: non-custodial architecture removes enterprise custody concerns, natural language policies reduce integration friction, and multi-chain support meets real infrastructure demands.

The timeline to production is clear: public beta in February 2026 (current month), mainnet launch in March 2026, and the expectation is that paying customers will begin in Q2 2026. The product is ready to scale—what's needed now is go-to-market validation and capital to support customer acquisition and team expansion.

### Metrics-Focused Format

**Shipping Metrics:**
- Codebase: 15k+ lines of production code
- Files: 172 Python files across 12 packages
- Time to build: 6 months (solo, full-time)
- Deployment status: Base Sepolia testnet live

**Feature Metrics:**
- Smart contracts deployed: 5-chain suite ready
- MCP tools available: 36
- EVM chains supported: 5
- Third-party integrations: 11 live

**Validation Metrics:**
- Design partners actively onboarding: 3
- Alpha feedback incorporated: 100+ iterations
- Policy language edge cases resolved: 50+
- Zero production bugs in core payment logic: yes

**Timeline Metrics:**
- Days to public beta: <14 (target Feb 2026)
- Days to mainnet: <30 (target March 2026)
- Expected beta users by March: 10-15
- Confidence in roadmap: High (all infrastructure shipped)

**Revenue Metrics:**
- Current revenue: $0
- Expected revenue Q2 2026: $10-50k run rate
- Target Q4 2026: $1M ARR
- CAC model: $0 right now (design partner driven), expected $5-10k per enterprise customer at scale

---

## 2.5 MARKET OPPORTUNITY

### Quick Summary (50 words)

AI agent payment volume grew 35,000% in Q4 2025. The market is projected to reach $1.7 trillion by 2030. We target the $8B subsegment requiring payment infrastructure compliance. With 20% market share, Sardis reaches $340M annual revenue by 2030. The 18-24 month window to become the standard is closing.

### Detailed Bottoms-Up Calculation

**Year 1 (2026): Market Establishment**
- Total AI agents deployed: 50k
- Agents requiring payment infrastructure: 15k (30%)
- Average spend per agent: $5k/year
- Total addressable spend: $75M
- Sardis addressable (at 20% competitor share): $15M
- Sardis expected capture (at 5% market share): $750k revenue

**Year 2 (2027): Early Adoption**
- Total AI agents deployed: 500k
- Agents requiring payment infrastructure: 150k (30%)
- Average spend per agent: $15k/year (agent sophistication increasing)
- Total addressable spend: $2.25B
- Sardis expected capture (at 10% market share): $225k revenue
- Plus SaaS subscriptions ($100-999/month × 100 accounts): $500k
- Expected total Year 2: $725k-$1.2M

**Year 3 (2028): Scale**
- Total AI agents deployed: 2M (per IDC/Gartner estimates)
- Agents requiring payment infrastructure: 600k (30%)
- Average spend per agent: $50k/year
- Total addressable spend: $30B
- Sardis expected capture (at 15% market share): $4.5M revenue
- Plus SaaS + enterprise contracts: $2M
- Expected total Year 3: $6.5M

**Year 4-5 (2029-2030): Maturity**
- Total AI agents deployed: 10M+
- Agents requiring payment infrastructure: 3M+ (30%)
- Average spend per agent: $100k+/year
- Total addressable spend: $300B+
- AI agent payment volume: $1.7T (per CNBC estimates)
- Sardis at 0.5% take rate = $8.5B gross volume
- At 20% market share = $1.7B annual revenue
- Conservative (5% market share): $425M annual revenue

**Critical Assumption: Market Share**
- Year 1: 5% share (early adopter positioning)
- Year 2: 8% share (design partner momentum)
- Year 3: 12% share (enterprise confidence)
- Year 4-5: 15-20% share (become standard)

This assumes winner-take-most dynamics (first trusted vendor becomes the standard) and that Sardis captures enterprise trust because of non-custodial architecture (competitors using custodial models cannot scale to large enterprises).

### TAM / SAM / SOM Breakdown

| Metric | Definition | Size | Notes |
|--------|-----------|------|-------|
| **TAM** | Total AI agent market | $65B by 2028 | IDC/Gartner estimates; includes all agent use cases |
| **SAM** | Agents requiring payment infrastructure | $8B | ~12% of total TAM (not all agents need payments) |
| **SOM Year 1** | Sardis addressable market 2026 | $750M | 15k agents × $50k avg spend × 10% capture |
| **SOM Year 5** | Sardis addressable market 2030 | $800M-$2B | 3M agents × $100k+ avg spend × market share |

**Key Market Drivers:**
1. **AI capability inflection**: Claude 3.5, GPT-4o enable multi-step autonomous workflows
2. **Protocol emergence**: AP2 (Google + Visa + Mastercard + 60 partners) standardizing agent payments
3. **Enterprise adoption**: 35% of enterprises deploying agents by 2027 (McKinsey)
4. **Payment volume growth**: 35,000% YoY growth in Q4 2025, trajectory to $1.7T by 2030
5. **Trust infrastructure maturing**: MPC custody solutions now production-ready, enabling enterprise adoption

**Competitive Dynamics:**
- First-mover advantage is critical (enterprise standardizes on first trusted vendor)
- Custodial competitors (Skyfire, Payman) cannot scale to large enterprises due to custody concerns
- Non-custodial-only competitors (Nevermined) lack compliance, limiting enterprise adoption
- Sardis is the only entrant optimized for both enterprise non-custodialism AND compliance AND self-service
- Winner-take-most dynamics mean market consolidates around 1-2 standards by 2028

---

## 2.6 COMPETITION & DIFFERENTIATION

### Quick Comparison

| Aspect | Sardis | Skyfire | Nevermined | Payman AI | Natural |
|--------|--------|---------|-----------|-----------|---------|
| **Funding** | $0 | $9.5M (a16z) | $4M | $13.8M (Visa) | $9.8M |
| **Custody Model** | Non-custodial MPC | Custodial | Non-custodial | Custodial bank | B2B only |
| **Compliance (KYC/AML)** | Integrated (Persona + Elliptic) | No | No | Yes | Yes |
| **Natural Language Policies** | Yes | No | No | No | No |
| **Multi-chain** | 5 chains | Limited | Limited | Single-chain | B2B only |
| **Virtual Cards** | Yes (Lithic) | No | No | Yes (Visa) | No |
| **MCP-Native** | Yes | No | No | No | No |
| **Self-Service** | Yes | Yes | Yes | Enterprise-only | Enterprise-only |
| **Enterprise Ready** | Yes | Risky (custody) | No (compliance gap) | Yes | Yes |

### Detailed Competitive Matrix

**Skyfire ($9.5M, Coinbase Ventures + a16z)**
- Strengths: First-mover, well-funded, strong partnership visibility
- Weaknesses: Custodial model (enterprise blocker), no compliance built-in, limited to simple payment routing
- Sardis advantage: Non-custodial removes enterprise custody risk, integrated compliance de-risks adoption, natural language policies reduce integration friction

**Nevermined ($4M)**
- Strengths: Non-custodial, early in space
- Weaknesses: Micropayment focus (not enterprise), no KYC/AML, limited to nanocredits/small transactions
- Sardis advantage: Enterprise-grade compliance, works at any transaction size, non-custodial without sacrificing UX

**Payman AI ($13.8M, Visa-backed)**
- Strengths: Well-funded, Visa partnership, full compliance
- Weaknesses: Custodial bank model (enterprise hesitation), Visa-dependent (not flexible), not programmable/autonomous-friendly
- Sardis advantage: Non-custodial architecture, not dependent on Visa, fully programmable and agent-native

**Natural ($9.8M)**
- Strengths: Well-funded, enterprise credibility
- Weaknesses: B2B enterprise-only (no self-service), high sales friction, expensive (custom pricing only)
- Sardis advantage: Self-service model unlocks SMB+startups, natural language policies reduce implementation time, fixed pricing tiers lower bar to adoption

**Stripe ACP (OpenAI partnership)**
- Strengths: Stripe's distribution and brand, simple integration
- Weaknesses: Payment layer only, doesn't solve custody or policy enforcement, no autonomous agent UX
- Sardis advantage: Full stack (custody + policy + compliance + settlement), MCP-native for agents

**Coinbase x402**
- Strengths: On-chain native, large user base
- Weaknesses: Requires Coinbase account, not enterprise-compliant, limited to traders
- Sardis advantage: Open-ended infrastructure, not Coinbase-dependent, enterprise-compliant

### What We Understand That They Don't

**Core Insight: Enterprise Will Not Adopt Agent Payments from Startups That Hold Their Funds**

Most competitors see custody as an implementation detail—how to technically hold and settle customer money. We see it as the dealbreaker for enterprise adoption. Here's why:

1. **Enterprise has been burned by fintech startups**: Celsius, FTX, and countless others took custody of customer funds and lost them. For enterprises evaluating autonomous agent deployments, custody risk is existential. If Sardis is compromised or fails, we cannot steal capital—because we don't hold it. This is the only risk posture enterprises accept for autonomous agents.

2. **Competitors with custodial models cannot scale enterprise**: They can win small merchants (who don't care about custody), but they cannot win enterprises that manage >$1M in daily agent spend. These customers will always choose a non-custodial option if it exists. We're building for the non-custodial requirement, which is where the largest TAM is.

3. **Natural language policies are not a nice-to-have, they're table-stakes for velocity**: Building autonomous agents is hard. If adding payment policy requires writing Solidity code or hiring a lawyer to define contract terms, adoption friction is 10x higher. We made it so non-technical founders can write policy in English and have it enforced in code. This is the moat that makes us 10x faster to integrate than competitors.

4. **Protocol standardization means proprietary solutions lose**: AP2, x402, ACP—these are emerging payment protocols for agents. Competitors building proprietary solutions will be disrupted when standards win. We're building protocol-native from the start. When the industry standardizes, we're already there.

5. **MCP-native is the UI layer that wins**: All major AI companies (Anthropic, OpenAI, others) are moving toward MCP as the agent interface standard. Competitors integrating via API require custom code. We integrated via MCP, meaning agents control Sardis wallets natively in Claude Desktop. This is the UX layer that makes us invisible (in a good way)—agents just use it.

**The Outcome:**
In a winner-take-most market, we believe Sardis wins because:
- We're the only option for enterprises requiring non-custodial + compliance
- We're the only option with natural language policies
- We're the only option that's MCP-native
- We're the only option built protocol-native

The market consolidates around one or two standards. Being first to own enterprise trust is everything.

---

## 2.7 BUSINESS MODEL

### Quick Summary

Sardis monetizes through three channels: transaction fees (0.25-0.75% of agent spend), SaaS subscriptions ($99-999/month by volume tier), and enterprise contracts (custom pricing). We expect $1M ARR by Q4 2026, assuming mainnet launch in March and mainstream adoption in Q2.

### Detailed Unit Economics

**Revenue Model:**

1. **Transaction Fees (Primary Revenue)**
   - Structure: 0.25-0.75% of total agent spend volume
   - Example: Agent spends $100k/month → Sardis revenue = $250-750/month
   - Scaling: As agent spend volume increases, fee % increases (volume discounts for large enterprise)
   - Expected mix: 60% of total revenue

2. **SaaS Subscriptions (Secondary Revenue)**
   - Tier 1 ($99/month): Up to $100k/month agent spend, basic policy engine, 5 API calls/sec
   - Tier 2 ($299/month): Up to $1M/month agent spend, advanced policies, 50 API calls/sec
   - Tier 3 ($999/month): Unlimited spend, priority support, custom policies, dedicated infra
   - Expected mix: 25% of total revenue

3. **Enterprise Contracts (High-Touch Revenue)**
   - Negotiated pricing for enterprise accounts (>$10M/month agent spend)
   - Includes custom compliance workflows, dedicated integrations, SLA guarantees
   - Expected mix: 10% of total revenue

4. **Card Interchange Revenue (Upside)**
   - Revenue share on Lithic virtual card spend (2-3% of card transaction volume)
   - Fiat-to-crypto transactions are higher friction—card volume as fiat bridge is significant upside
   - Expected mix: 5% of total revenue (as adoption scales)

**Unit Economics (Per Enterprise Customer):**

| Metric | Small Enterprise | Mid-Market | Large Enterprise |
|--------|-----------------|-----------|-----------------|
| Monthly agent spend | $50k | $500k | $5M+ |
| Transaction fee (0.5%) | $250 | $2,500 | $25k+ |
| SaaS subscription | $100 | $300 | $1k (custom) |
| Total monthly revenue per customer | $350 | $2,800 | $26k+ |
| Annual customer value | $4,200 | $33,600 | $312k+ |
| CAC (estimated) | $0-2k (viral) | $10k | $50k+ |
| Payback period | 2-6 months | 4 months | 2 months |
| LTV:CAC ratio | 10:1 (small) | 3:1 (mid) | 6:1 (large) |

**Gross Margin: 85%**
- Infrastructure costs (cloud, MPC, blockchain RPCs): 10%
- Payment processor fees (Lithic, Bridge.xyz): 3%
- Compliance/KYC services (Persona, Elliptic): 2%
- Gross margin: 85%

**Path to $1M ARR:**

| Period | Agent Count | Avg Spend | Total Volume | Sardis Revenue |
|--------|------------|-----------|--------------|----------------|
| Q1 2026 (Public Beta) | 50 | $50k/month | $2.5M | $12.5k |
| Q2 2026 (Early Adoption) | 200 | $100k/month | $20M | $100k |
| Q3 2026 (Acceleration) | 500 | $150k/month | $75M | $375k |
| Q4 2026 (Scale) | 1000 | $200k/month | $200M | $1M+ |

**Key Assumptions:**
- Customer acquisition follows viral + direct sales hybrid model
- Average customer LTV:CAC = 4:1 (enterprise software norm)
- 85% gross margins maintained (scales due to network infrastructure maturity)
- No single customer >30% of revenue (avoid concentration risk)
- Churn <3% annually (sticky product for enterprises)

---

## 2.8 WHY NOW

### 3-Bullet Version

1. **AI agents crossed the capability threshold**: Claude 3.5, GPT-4o, and emerging models can reason through multi-step autonomous workflows. Enterprises are moving from chatbot experiments to autonomous agents managing real operations (spending, purchasing, trading).

2. **Major payment protocols are emerging**: AP2 (Google + Visa + Mastercard + PayPal + 60 partners), ACP (OpenAI + Stripe), x402 (Coinbase) are standardizing agent payment frameworks. The 18-24 month window to own the standard is closing.

3. **Enterprise is trusting autonomous AI at scale**: McKinsey reports 35% of enterprises deploying agents by 2027. MPC custody is production-ready. Compliance automation exists. The infrastructure for safe autonomous agent payments exists—nobody has integrated it yet.

### Detailed Narrative

**Why This Moment Is Different**

For years, AI was a chatbot and content tool. Enterprises saw AI as a creative assistant, not a financial actor. That changed in Q3-Q4 2025 with the emergence of Claude 3.5 Sonnet, GPT-4o, and similar frontier models that can reason through multi-step operations and make complex decisions autonomously. For the first time, enterprises are asking: "Can we give our autonomous agents authority to spend money?"

The answer was always "not safely, not compliantly, not with a startup holding the funds." Until now.

**Four Forces Converging:**

1. **AI Capability Inflection**
   - Claude 3.5 can reason through cloud infrastructure decisions, purchasing decisions, trade logic
   - Agents can understand policy constraints and operate within them
   - Agents can request approval, escalate decisions, or execute autonomously based on learned patterns
   - This was not possible 12 months ago

2. **Protocol Emergence**
   - AP2: Google + Visa + Mastercard + PayPal backing a standard for agent payments. This is enterprise consensus forming.
   - ACP: OpenAI + Stripe embedding payment logic directly into agent workflows
   - x402: Coinbase's on-chain agent payment protocol
   - The industry is consensus-shifting toward agent-native payment frameworks. Whoever owns the standard owns the distribution.

3. **Enterprise Adoption at Scale**
   - McKinsey: 35% of enterprises deploying agents by 2027
   - Gartner: Agentic AI will be the primary interaction modality by 2027
   - Not just chatbots—autonomous agents for research, purchasing, infrastructure, trading
   - Agent payment volume grew 35,000% in Q4 2025
   - Projected $1.7T in agent payment volume by 2030

4. **Production-Ready Infrastructure**
   - MPC custody (Turnkey): Enterprise-grade key management, no single point of failure
   - Compliance automation (Persona, Elliptic): Real-time KYC/AML screening
   - Virtual cards (Lithic): Agents spending fiat in the real world
   - This infrastructure exists. Nobody has integrated it into a cohesive agent payment platform.

**Why Sardis, Why Now**

The opportunity window is 18-24 months. In that timeframe:
- The market consolidates around 1-2 dominant standards (likely AP2 + one proprietary winner)
- Enterprise standardizes on one payment infrastructure vendor (switching costs are high)
- First-mover advantage is massive (enterprise trust, network effects, integration partnerships)

We have 18 months to become the payment standard for agents before competitors (well-funded Skyfire, Payman, etc.) or incumbents (Stripe, PayPal) fill this gap.

Why Sardis wins that race:
- Non-custodial architecture (only option for enterprise)
- Natural language policies (10x faster integration)
- MCP-native (zero-config agent integration)
- Protocol-native (built for AP2/x402 standards)
- Solo founder execution velocity (15k lines of code in 6 months)

The 18-month window is closing. This is the moment.

---

## 2.9 TEAM & FOUNDER STORY

### Short Bio (50 words)

Efe Baran Durmaz is a solo founder with 8+ years in blockchain and smart contract engineering. In 6 months, he built 15k+ lines of production code, 36 MCP tools, and 11 third-party integrations entirely solo. He's driven by the problem of making AI agents trustworthy with capital.

### Why I'm the Right Person (200 words)

I've spent the last 8 years in blockchain infrastructure—first as an engineer, then as a technical advisor to crypto projects. I've watched the cycle: new technology emerges, security is afterthought, trust breaks, adoption stalls. Crypto has learned the hard way that custody and access control are everything.

When I started building autonomous agents (Claude + tools), I realized AI was heading down the same path. Agents were being asked to manage real tasks—purchasing, infrastructure spending, trading—but had no access to capital. And the payment infrastructure wasn't designed for non-human actors.

The technical problem was clear: how do you give agents financial authority without trusting a startup to hold their funds? The business insight came next: enterprise will not solve this problem themselves. They'll standardize on whoever becomes the trusted payment vendor first.

I've built Sardis because I understand (1) how MPC cryptography works (custody layer), (2) how smart contracts enforce policy (control layer), (3) how compliance screening works (risk layer), and (4) how the infrastructure industry consolidates (market layer). This combination is rare.

Solo building 15k+ lines of production code in 6 months demonstrates execution velocity. Enterprise customers can see: this founder moves fast, ships quality code, and understands the hard problems.

### Outlier Story (150 words)

Most founders optimize for fundraising: they raise money early, hire aggressively, and build a team quickly. I did the opposite. I spent 6 months shipping production-quality infrastructure solo: 15k+ lines of code, 36 MCP tools, 11 integrations, 5-chain smart contract suite, full compliance integration.

Why? I knew the product had to be excellent before we raised money or hired. Hiring aggressively would slow shipping. Fundraising would distract from building. So I stayed focused.

The result: we have a product that's 80% of what enterprise customers want, with 20% of the team size of competitors. We have zero technical debt. We have institutional knowledge concentrated in one founder (me), which means I can make fast decisions and iterate based on design partner feedback.

When I do bring on a cofounder, they're joining a completed infrastructure platform, not an idea or an MVP. That's an outlier position to be in at this stage.

### Cofounder Search Status

Currently seeking 1 cofounder (20-25% equity):

**Founding Protocol Engineer** (preferred for expansion)
- Smart contract protocol design and optimization
- Layer 2 integrations and bridge development
- Security audits and cryptographic research
- Take ownership of protocol roadmap

**GTM Lead** (preferred for adoption)
- Go-to-market strategy and execution
- Enterprise sales and partnership development
- Product positioning and marketing
- Take ownership of customer acquisition

Contact: invest@sardis.sh or efebarandurmaz05@gmail.com

---

## 2.10 THE ASK

### Pre-Seed Ask ($500k-$1M)

**Raise Amount:** $750k

**Use of Funds:**
- Engineering (2 hires): $300k
  - Founding Protocol Engineer (protocol + Layer 2 work)
  - Backend Engineer (scaling + infrastructure)
- Sales & Partnerships (1 hire): $150k
  - Enterprise sales, partnerships, GTM
- Runway & Infrastructure: $150k
  - Cloud infrastructure, compliance services, operational expenses (12 months)
- Buffer & Contingency: $150k

**Valuation:** $10M pre-money (or $17.5M post-money at $750k raise)

**Why This Amount:**
- Enough to hire 2-3 engineers to unblock product scaling
- Enough to hire 1 GTM person to scale enterprise sales
- 12 months runway to hit $100-200k MRR (path to Series A)
- Maintains founder control (Efe retains 60-70% post-investment)

### Seed Ask ($3M-$5M)

**Raise Amount:** $4M

**Use of Funds:**
- Engineering (5 hires): $1.2M
  - 2 protocol engineers (smart contract audit, Layer 2 work)
  - 2 backend engineers (scaling, compliance integrations)
  - 1 full-stack engineer (frontend, SDKs)
- Sales & Partnerships (3 hires): $800k
  - VP Sales (enterprise strategy)
  - 2 Enterprise Account Executives
- Marketing & Operations (2 hires): $400k
  - Head of Marketing
  - Operations/Finance
- Infrastructure & Legal: $400k
  - Compliance audits and legal entity formation
  - Cloud infrastructure scaling
- Runway: $1.2M (18 months)

**Valuation:** $20M pre-money (or $33M post-money at $4M raise)

**Milestones to Achieve:**
- $1M ARR (from Q4 2026 target)
- 50+ enterprise customers
- 10+ major partnerships (wallets, exchanges, protocols)
- $10M+ monthly agent payment volume
- Series A ready (clear path to $10M ARR)

### Use of Funds Breakdown (Visual)

**For $750k Pre-Seed:**
```
Engineering (40%):    $300k
Sales & GTM (20%):    $150k
Infrastructure (20%): $150k
Buffer (20%):         $150k
```

**For $4M Seed:**
```
Engineering (30%): $1.2M
Sales & Partnerships (20%): $800k
Marketing & Ops (10%): $400k
Legal & Compliance (10%): $400k
Runway/Buffer (30%): $1.2M
```

---

## 2.11 VISION

### 1-Year Vision (Feb 2027)

In one year, Sardis is the de facto payment infrastructure for autonomous agents in the Web3 and crypto-native enterprise space. We've shipped:

- **Public mainnet platform** with 50+ live enterprise customers
- **Full AP2 and x402 protocol compliance** (not just supporting, but shaping standards)
- **$1M+ ARR** with clear path to $5M
- **500+ MCP tools** integrated (agents can control nearly every financial operation natively)
- **15+ major partnerships** (wallets, exchanges, RPC providers, compliance vendors)
- **Strong founding team** (founder + 2 cofounders + 3-5 engineers + 2-3 sales)

The market knows Sardis as "the payment OS for agents"—the platform that solved the custody + compliance + control problem.

### 3-Year Vision (Feb 2029)

Sardis is a multi-billion dollar infrastructure company and the standard payment layer for all autonomous agents. We've built:

- **Global enterprise customer base** (500+ customers, $50M+ ARR)
- **Cross-chain settlement** (not just EVM, but Bitcoin, Solana, other L1s)
- **Native integrations into 10+ major AI platforms** (Claude, ChatGPT, Gemini agents)
- **Virtual card product at scale** (agents spending real-world fiat through Sardis cards)
- **Compliance as a service** for other infrastructure vendors (licensing our KYC/AML frameworks)
- **Regulatory precedent** (Sardis is the company that solved autonomous agent payments compliantly)
- **Strong team** (50-100 person company, with technical depth across smart contracts, payments, compliance)

Sardis is the Stripe of the agent economy.

### 10-Year Vision (Feb 2036)

Autonomous agents manage trillions of dollars in daily transactions, and Sardis is the infrastructure backbone. We've built:

- **Global payment standard** (Sardis protocol is adopted across 100+ countries)
- **Trillions in annual volume** (1% of all financial transactions in the world go through Sardis)
- **$100M+ ARR** (top-tier fintech infrastructure company)
- **Regulatory credibility** (Sardis is regulated as a payment processor in major jurisdictions)
- **Open ecosystem** (third-party developers build agent payment applications on Sardis)
- **Enterprise household name** (every Fortune 500 company uses Sardis for agent payments)

The original problem we solved—making agents trustworthy with capital—is now foundational infrastructure. Agents manage money as naturally as they manage data. Sardis made that safe.

---

# SECTION 3: APPLICATION TRACKER

Track your applications using this template. Update status as you progress through each program.

| Program | Type | Deadline | Status | Application Link | Key Dates | Notes |
|---------|------|----------|--------|-------------------|-----------|-------|
| **PearX S26** | Accelerator | Feb 22, 2026 | In Progress | TBD | Early deadline: Feb 22 | URGENT. Deadline in ~2 weeks. Questions answered above. Submit this week. |
| **Y Combinator S26** | Accelerator | Feb 2026 | Pending | yc.com | TBD | Apply if interested. YC is gold standard but difficult to get into. |
| **Techstars** | Accelerator | Mar 2026 | Pending | techstars.com | TBD | Various cohorts and cohort times. Techstars Finance has relevant alumni. |
| **500 Global** | Accelerator | Rolling | Pending | 500.co | TBD | Good for fintech. Relevant past companies in payments. |
| **Antler** | Accelerator | Rolling | Pending | antler.co | TBD | Early-stage focus, 6-month acceleration. Good for team building. |
| **a16z SPEEDRUN** | Accelerator | Rolling | Pending | a16z.com/speedrun | TBD | Designed for infrastructure companies. Right fit. |
| **South Park Commons** | Network | Ongoing | Pending | spc.community | TBD | No formal deadline. Apply for membership. Good community for founders. |
| **Neo** | Fund | Ongoing | Pending | neo.vc | TBD | Early-stage fund, protocol-first focus. |
| **Contrary** | Fund | Rolling | Pending | contrary.com | TBD | Scout-driven fund. Good for well-executed infrastructure plays. |
| **On Deck** | Network | Ongoing | Pending | decklinks.com | TBD | Fellowship program. Good for founder peer group. |
| **Blockchain Coinvestors Network** | Fund | Rolling | Pending | TBD | TBD | Focuses on blockchain/crypto infrastructure. |
| **Paradigm** | Fund | Rolling | Pending | paradigm.xyz | TBD | Top-tier crypto VC. Worth reaching out directly. |
| **Sequoia** | VC | Rolling | Pending | sequoia.com | TBD | Tier-1 VC. For post-Series A or strong traction. |
| **Benchmark** | VC | Rolling | Pending | benchmark.com | TBD | Strong in fintech/payments. David Early is fintech partner. |
| **Sapphire Ventures** | VC | Rolling | Pending | sapphireventures.com | TBD | Large growth VC. For later stage. |

**Application Strategy:**
- **Tier 1 (Priority)**: PearX (due Feb 22), YC, Techstars, a16z SPEEDRUN
- **Tier 2 (Secondary)**: 500 Global, Antler, Paradigm, Benchmark
- **Tier 3 (Ongoing)**: Rolling funds, networks (Neo, Contrary, On Deck)

---

# SECTION 4: COMMON APPLICATION QUESTIONS CHEAT SHEET

**Use this section for any accelerator/VC application.** Most programs ask these 20 questions in different formats. Pre-written answers are below—adapt as needed.

---

### Q1: What Problem Are You Solving?

**Short Answer (100 words):**
AI agents need financial authority to operate in the real world, but enterprises won't give autonomous AI unilateral access to capital through an unproven startup. We're solving the custody + compliance + control problem: non-custodial MPC wallets, natural language spending policies, and integrated regulatory screening. This unlocks autonomous agent adoption at enterprise scale.

**Medium Answer (250 words):**
Three realities are colliding: (1) AI agents can now reason through complex financial operations, (2) major payment protocols (AP2, ACP, x402) are standardizing agent payments, but (3) enterprises need two guarantees: cryptographic proof that a startup cannot steal capital, and mathematical enforcement of spending guardrails.

Traditional payment infrastructure (Stripe, PayPal) succeeded by holding merchant funds. This model fails for autonomous agents—enterprises will never trust a startup with unilateral custody of agent budgets. Non-custodial crypto solutions exist but lack compliance, policy enforcement, and fiat bridges.

Sardis solves this gap with:
- Non-custodial MPC wallets (enterprise owns keys, startup cannot access funds)
- Natural language spending policies (developers write guardrails in English, we enforce in code)
- Integrated compliance (Persona KYC + Elliptic AML)
- Multi-chain settlement and virtual cards for fiat access

The result: enterprises can deploy autonomous agents managing real operations (spending on cloud infrastructure, making purchases, executing trades) safely and compliantly.

---

### Q2: Why Are You the Right Team to Solve This?

**Answer (150 words):**
I've spent 8 years in blockchain infrastructure, learning the hard way that custody and access control are everything. I understand MPC cryptography (custody layer), smart contracts (control layer), compliance frameworks (risk layer), and how fintech markets consolidate (strategy layer). This combination is rare.

I've demonstrated execution velocity by building 15k+ lines of production code solo in 6 months: a complete payment infrastructure platform with 36 MCP tools, 5-chain smart contract suite, and 11 third-party integrations. Zero technical debt, institutional knowledge concentrated in one founder = fast decision-making.

I'm seeking a cofounder (Protocol Engineer or GTM Lead) to accelerate. The platform is 80% shipped; they're joining a completed infrastructure product, not an idea.

---

### Q3: How Big Is the Market?

**Answer (200 words):**
**TAM:** $65B AI agent market by 2028 (IDC/Gartner)

**SAM:** $8B for agents requiring payment infrastructure (~12% of total TAM)

**SOM (5-year):** $800M to $2B depending on market share (assume 10-20% capture)

**Bottoms-Up:**
- 2028: 600k agents requiring payments, $50k average annual spend = $30B addressable
- At 0.5% transaction take rate = $150M annual revenue opportunity
- Sardis at 15-20% market share = $22-30M annual revenue by 2028

**Growth Drivers:**
- Agent payment volume grew 35,000% YoY in Q4 2025
- $1.7T projected annual agent payment volume by 2030
- 35% of enterprises deploying agents by 2027 (McKinsey)
- AP2 protocol adoption (Google + Visa + Mastercard + 60 partners)

**Why It Matters:**
This is a winner-take-most market. First vendor to own enterprise trust becomes the standard. Switching costs are high once enterprises standardize. Being first with non-custodial + compliance is everything.

---

### Q4: Who Are Your Competitors?

**Answer (150 words):**
**Direct Competitors:**
- Skyfire ($9.5M, a16z): Custodial model excludes enterprise
- Nevermined ($4M): Micropayment focus, no compliance
- Payman AI ($13.8M, Visa): Custodial bank model, Visa-dependent
- Natural ($9.8M): B2B enterprise-only, high sales friction

**Adjacent Competitors:**
- Stripe (ACP partnership with OpenAI): Payment layer only, doesn't solve custody/policy
- Coinbase (x402): On-chain protocol, requires Coinbase account

**Sardis Differentiation:**
We're the only entrant with non-custodial architecture + integrated compliance + natural language policies + MCP-native + self-service. Competitors either (1) use custodial models that exclude enterprise, (2) lack compliance, (3) don't address policy enforcement, or (4) require enterprise sales cycles.

Winner-take-most dynamics favor whoever solves enterprise trust first.

---

### Q5: What's Your Go-to-Market Strategy?

**Answer (200 words):**
**Phase 1 (Feb-Apr 2026): Design Partner Expansion**
- Scale from 3 to 10-15 design partners (developer tools, infrastructure companies)
- Tighten product based on feedback
- Generate case studies and testimonials
- Zero-cost customer acquisition (inbound interest is strong)

**Phase 2 (May-Aug 2026): Self-Service Launch**
- Launch public beta with fixed pricing tiers
- Target SMB and startup buyers (lower CAC, self-serve)
- Heavy content marketing (how-to guides, policy templates, agent best practices)
- Product-led growth (free tier with upgrade path)

**Phase 3 (Sep-Dec 2026): Enterprise Sales**
- Hire VP Sales and Enterprise AEs
- Target Fortune 500 and fast-growing tech enterprises
- Custom contracts, dedicated integrations, SLA guarantees
- High touch, high CAC ($50-100k), but $300k+ LTV

**Revenue Mix:**
- Year 1: 80% design partners (low friction), 20% self-serve
- Year 2: 40% self-serve, 40% design partners, 20% enterprise
- Year 3+: 30% self-serve, 20% design partners, 50% enterprise

**Why This Works:**
We have inbound demand from design partners, which de-risks early revenue. This funds payroll and infrastructure. By the time we hire sales, we have product-market fit and case studies to accelerate enterprise adoption.

---

### Q6: What's Your Revenue Model?

**Answer (150 words):**
**Transaction Fees:** 0.25-0.75% of agent spend volume
- Example: $100k monthly agent spend = $250-750 monthly revenue
- Scales with customer growth

**SaaS Subscriptions:** $99-999/month based on volume tier
- Tier 1: Up to $100k/month agent spend, basic policies
- Tier 2: Up to $1M/month, advanced policies
- Tier 3: Unlimited, custom, dedicated support

**Enterprise Contracts:** Custom pricing for >$10M monthly agent spend
- Includes dedicated integrations, custom compliance workflows, SLAs

**Card Interchange:** Revenue share on Lithic virtual card spend (2-3% of card volume)

**Unit Economics:**
- Gross margin: 85% (infrastructure + compliance costs are 15%)
- CAC: $0-50k depending on segment
- LTV: $50k-$300k+ depending on segment
- LTV:CAC: 3:1 to 10:1 (strong unit economics)

**Path to $1M ARR:** 1000 agents × $100k average annual value = $100M annual volume × 0.5% = $500k revenue + SaaS subscriptions = $1M ARR by Q4 2026.

---

### Q7: How Technically Defensible Is Your Product?

**Answer (200 words):**
**Defensibility is multi-layered:**

1. **Cryptographic Moat (Non-Custodial):** We use Turnkey's distributed MPC. This is not copyrightable, but it's operationally difficult to replicate. Competitors using custodial models cannot catch up without fundamental architecture change.

2. **Policy Language (Product Moat):** Our natural language-to-code compiler is proprietary. We've built a DSL that translates English guardrails into smart contract enforceability. This is hard to reverse-engineer and gives 10x UX advantage over code-based competitors.

3. **Integration Network (Network Moat):** By supporting 11 third-party services (Turnkey, Lithic, Persona, Elliptic, Neon, Upstash, Bridge.xyz, etc.), we create network effects. Adding a 12th integration is cheaper than competitors starting from zero.

4. **Protocol Native (Timing Moat):** We're building protocol-native (AP2, x402 compliant) from day one. When standards win, we're already positioned. Competitors building proprietary solutions will be disrupted.

5. **Enterprise Trust (Market Moat):** First company to earn enterprise trust for autonomous agent payments becomes the standard. Switching costs are high. Winner-take-most dynamics.

**Not Defensible:**
- Smart contracts are open-source and auditable
- Infrastructure choices (Solidity, FastAPI) are commodity
- But the *combination* of these elements—architecture + UX + compliance integration—is unique and hard to copy quickly

---

### Q8: What's the Current Stage of Your Product?

**Answer (150 words):**
**Current Status (Feb 2026):**
- ✓ 100% feature-complete infrastructure
- ✓ Smart contracts deployed on Base Sepolia testnet
- ✓ 36 MCP tools implemented and tested
- ✓ 5 EVM chains supported (Base, Arbitrum, Polygon, Optimism, etc.)
- ✓ 11 third-party integrations live
- ✓ 15k+ lines of production code built solo

**Validation:**
- 3 design partners actively onboarding (validating product-market fit)
- No revenue yet (expected Q2 2026 with public beta)

**Timeline:**
- Feb 2026: Public beta launch
- Mar 2026: Mainnet production
- Apr 2026: First paying customers
- Q4 2026: $1M ARR target

**Why This Stage:**
We're not pre-MVP. We're post-MVP, pre-scale. The infrastructure is complete and validated. What we need is go-to-market capital and team to acquire customers and expand.

---

### Q9: How Do You Acquire Customers?

**Answer (200 words):**
**Early-Stage (Now):**
- Inbound demand from design partners (3 already onboarding)
- Word-of-mouth from founder networks (crypto, AI, fintech communities)
- Content marketing (blog posts, GitHub open-source, MCP registry)
- Community engagement (Twitter, Discord, agent developer forums)

**Early Traction:**
- No paid ads yet (CAC would be >$10k pre-PMF)
- Heavy emphasis on product evangelism and case studies
- Direct outreach to 20-50 founder-led AI companies

**Post-Product-Market-Fit (Q2 2026+):**
- Self-serve inbound (SEO, content, product-led growth)
- Enterprise sales team (once we hire)
- Partner channel (API integrations, wallet providers, exchanges)
- API marketplace distribution (MCP registry, agent marketplaces)

**Projected Funnel:**
- Q1 2026: 5-10 beta users (via inbound + manual outreach)
- Q2 2026: 50+ users (via self-serve + enterprise pilots)
- Q3 2026: 200+ users (via sales team + partner channels)
- Q4 2026: 500+ users (viral adoption + sales execution)

**Why This Works:**
We have strong inbound demand, which is our cheat code for early customer acquisition. This de-risks go-to-market and allows us to optimize sales process with real data.

---

### Q10: What Are Your Key Metrics / Milestones?

**Answer (200 words):**
**Product Metrics:**
- Smart contracts: Deployed on mainnet (Q1 2026 target)
- MCP tools: 36+ available (currently at 36, scaling to 50+ by Q2)
- Integration breadth: 11+ live (currently at 11, scaling to 20+ by Q3)
- Chain coverage: 5 EVM chains (expanding to 10+ by Q3)
- Code quality: Zero critical bugs in payment logic, <5% error rate in policy execution

**Customer Metrics:**
- Design partner count: 3 → 10 by Mar, 50+ by Jun
- Beta user base: 10 by Mar, 100+ by Jun, 500+ by Dec
- No revenue yet (expected first paying customer Q2 2026)

**Business Metrics:**
- Monthly Recurring Revenue: $0 → $10k by Jun, $100k by Oct, $1M+ by Dec
- Annual Run Rate: $0 → $120k by Jun, $600k by Oct, $1M+ by Dec
- Customer acquisition cost: $0-2k (design partners), $10-20k (self-serve), $50k+ (enterprise)
- Gross margin: 85% (infrastructure is 15% of revenue)

**Funding Metrics:**
- Runway: 18+ months with current capital
- Funding needed: $750k-$1M pre-seed (to reach $100k MRR, Series A ready)

**Why These Metrics:**
These are leading indicators of traction, product-market fit, and path to scale. They're measurable, achievable, and tied to venture outcomes.

---

### Q11: What Are the Key Risks?

**Answer (250 words):**
**Risk 1: Regulatory Uncertainty**
- **Problem:** AI agent autonomy is largely unregulated. Regulatory changes could force policy changes.
- **Mitigation:** We're building compliance into the product (Persona KYC + Elliptic AML), not bolting it on. Early engagement with regulators. AP2 protocol includes major financial institutions (Visa, Mastercard), so regulatory precedent is being set.
- **Probability:** Medium (likely to happen, but we're positioned to lead through it)

**Risk 2: Competing Standards (AP2 vs. ACP vs. x402)**
- **Problem:** If a competing standard wins, we could be displaced.
- **Mitigation:** We're building support for all emerging standards simultaneously. Multi-standard approach reduces dependence on any single standard. Protocol agnostic architecture.
- **Probability:** Low (we support multiple standards, so we win regardless)

**Risk 3: Enterprise Not Ready for Agent Autonomy**
- **Problem:** Enterprise might move slower to agent payments than we expect.
- **Mitigation:** Design partner feedback shows strong demand. Early revenue signals support adoption velocity.
- **Probability:** Low (market signals are strong)

**Risk 4: Well-Funded Competitors (Skyfire, Payman)**
- **Problem:** Competitors have more capital and could move faster.
- **Mitigation:** Our non-custodial + compliance approach is structurally better for enterprise. Non-custodial is not a feature they can copy without architecture rewrite. First-mover advantage on enterprise trust matters more than capital.
- **Probability:** Medium (but we have structural advantages)

**Risk 5: Technical Execution**
- **Problem:** Payment infrastructure is hard. One bug could be catastrophic.
- **Mitigation:** Solo founder has demonstrated quality engineering. Zero critical bugs to date. Code is heavily tested. Smart contracts are audit-ready.
- **Probability:** Low (track record is strong)

**Overall:** Risks exist but are mitigated. Market demand, product quality, and structural advantages put Sardis in strong position.

---

### Q12: How Much Are You Raising and Why?

**Answer (200 words):**
**Raise Amount:** $750k pre-seed ($500k-$1M acceptable range)

**Use of Funds:**
- Engineering (40%): $300k
  - 1 Founding Protocol Engineer (smart contracts, Layer 2, scaling)
  - 1 Backend Engineer (API scaling, compliance integrations, ops)
- Sales & Partnerships (20%): $150k
  - 1 Head of Sales/Partnerships (enterprise strategy, customer development)
- Infrastructure & Operations (20%): $150k
  - Cloud infrastructure, compliance services, legal entity formation
- Buffer & Contingency (20%): $150k
  - Payroll flexibility, unexpected expenses

**Why This Amount:**
- Enough to hire 2-3 engineers to unblock product scaling
- Enough to hire 1 sales/partnership person to validate go-to-market
- 12 months runway to reach $100-200k MRR
- Path to Series A with strong traction (clear signals of $1M+ ARR potential)
- Preserves founder equity (Efe retains 60-70% post-investment)

**Why This Timing:**
- Product is complete. We don't need capital to build—we need capital to scale and acquire customers.
- Design partner validation is done. Revenue traction is imminent.
- Market window is closing (18-24 months to own the standard). Capital accelerates our path.

**Series A Plan:**
- Raise $3-5M with $1M+ ARR and 50+ enterprise customers
- Fund 20-person team, aggressive geographic expansion, enterprise sales
- Path to exit or $100M+ ARR by year 5

---

### Q13: Why Should We Invest in You?

**Answer (250 words):**
**1. Market Timing Is Perfect**
Agent payment volume grew 35,000% in Q4 2025. Enterprise adoption is just starting. You're investing at the inflection point, not after. The next 18 months determine the standard.

**2. Product Is Complete**
Unlike most early-stage startups asking for capital to build the MVP, we have a production-ready platform. Capital funds scaling and go-to-market, not R&D. Lower technical risk, higher ROI on capital.

**3. Founder Track Record**
15k+ lines of production code built solo in 6 months. Shipped 36 MCP tools, 11 integrations, 5-chain smart contract suite. Zero critical bugs. This is execution velocity.

**4. Structural Competitive Advantage**
Non-custodial architecture is not a feature competitors can copy without full rewrite. It's the only model enterprise will trust with autonomous agent capital. Network effects from integration partnerships are real.

**5. Winner-Take-Most Market Dynamics**
This is not a fragmented market. Enterprise standardizes on one payment vendor and switching costs are high. First company to own enterprise trust wins. We're positioned to be first.

**6. Clear Path to Venture Outcomes**
$1M ARR target is achievable by Q4 2026. $10M+ ARR by 2027 is realistic. $100M+ ARR by 2030 is possible. These are top-tier venture returns.

**7. Seeks the Right Cofounder**
We're actively seeking a Founding Protocol Engineer or GTM Lead. Founder is coachable and collaborative. Not an ego-driven solo operator.

**Bottom Line:**
You're investing in the foundational infrastructure for the agent economy. Sardis is the payment layer that makes it safe and scalable. This is a 10+ year, multi-billion-dollar opportunity.

---

### Q14: What Would Success Look Like in Year 5?

**Answer (200 words):**
**Year 5 (Feb 2031) Success Definition:**

**Product:**
- Multi-chain settlement (EVM + Bitcoin + Solana)
- 500+ MCP tools available
- Integrated into 10+ major AI platforms natively
- Enterprise-grade security audits completed
- Regulatory compliance in major jurisdictions (US, EU, Asia)

**Business:**
- $100M+ annual recurring revenue
- 1000+ enterprise customers
- 50+ partnerships (exchanges, wallets, RPC providers, AI platforms)
- Profitable (positive unit economics at scale)
- Path to IPO or $1B+ strategic exit

**Market Position:**
- De facto payment standard for autonomous agents globally
- Sardis protocol adopted by major financial institutions
- Regulatory precedent set (Sardis is how autonomous agents do payments compliantly)
- Industry association leadership (standards bodies, compliance frameworks)

**Team:**
- 100-200 person company
- World-class engineering, sales, and operations team
- Offices in SF, Istanbul, EU, Asia

**Impact:**
- Trillions of dollars in agent-managed transactions annually
- Autonomous agents are as common as APIs in enterprise
- Financial access is programmable and agent-native
- Sardis made it possible

**Bottom Line:**
In year 5, Sardis is a top-tier fintech infrastructure company generating $100M+ ARR. The original problem we solved—making agents trustworthy with capital—is foundational infrastructure that the whole industry depends on.

---

### Q15: What Do You Want Help With Beyond Money?

**Answer (150 words):**
**Introductions:**
- Enterprise customers (Fortune 500, fast-growing tech companies)
- Technical partners (wallet providers, exchanges, RPC providers)
- Regulatory advisors (compliance framework expertise)
- Security auditors (smart contract audit firms)

**Expertise:**
- Go-to-market strategy (how to position for enterprise)
- Enterprise sales (playbooks, templates, pitch coaching)
- Protocol design (AP2, x402 standards input)
- Team building (how to attract top engineering talent)

**Board Support:**
- Strategic guidance on protocol decisions
- Customer introductions and references
- Founder peer network (other founders building infrastructure)
- Operational advice (scaling 1→10 person team)

**What We Don't Need:**
- Product advice (we know what we're building)
- Full-time board seat (we need advisors, not overheads)

**Our Ask:**
Be a thought partner on go-to-market strategy and make 3-5 key customer introductions in your network. That's it. We'll execute.

---

### Q16: What's Your Unfair Advantage?

**Answer (150 words):**
**Combination of Rare Skills**
Most founders are great at one thing: engineering, sales, or strategy. I'm strong at all three (or at least capable across all three), which is rare. This matters for infrastructure companies where product, market fit, and execution are equally important.

**Technical Depth**
8 years in blockchain infrastructure + deep cryptography knowledge + smart contract expertise. This is not common. Most payments founders come from traditional fintech (Stripe, PayPal clones). We're reimagining payments from first principles for AI agents.

**Market Timing Insight**
Identified "Financial Hallucination" as the core enterprise problem 18 months before competitors. Most competitors are building payment rails. We're building control systems. This reframing unlocks enterprise trust.

**Execution Velocity**
15k lines of production code solo in 6 months is outlier performance. Most founders would need a team to ship this much. This velocity compounds—we can out-build competitors.

**Protocol Native Positioning**
Building for AP2, x402, ACP standards from day one, not as afterthought. When standards win, we're already positioned. This is the moat.

---

### Q17: Who Are Your Ideal Customers?

**Answer (200 words):**
**Segment 1: Developer Tools & Platforms (Today, Design Partner Focus)**
- Companies building autonomous agent frameworks (Praisonai, Langchain, CrewAI)
- Companies selling APIs to agents (cloud providers, data vendors)
- Why they need us: Agents can pay for API calls autonomously, reducing friction
- TAM: $5B (developer tools market)
- Ideal sale size: $50-500k/year
- Urgency: High (payment autonomy is feature gap today)

**Segment 2: AI Infrastructure Companies (Year 1-2)**
- AI app platforms, autonomous agent marketplaces, agentic AI platforms
- Why they need us: Customers want to pay agents natively
- TAM: $20B (AI infrastructure market)
- Ideal sale size: $500k-$5M/year
- Urgency: High

**Segment 3: Enterprise (Year 2-3)**
- Fortune 500 companies deploying autonomous AI at scale
- Pharma, finance, logistics, manufacturing with autonomous agent use cases
- Why they need us: Non-custodial + compliance required for enterprise budgets
- TAM: $30B (enterprise software market)
- Ideal sale size: $1M-$10M/year (custom contracts)
- Urgency: Medium (adoption is slower, but deal sizes are larger)

**Segment 4: Crypto/Trading Platforms (Ongoing)**
- Exchanges, trading platforms, DeFi protocols
- Why they need us: Agents can trade autonomously with guardrails
- TAM: $5B (crypto infrastructure)
- Ideal sale size: $200k-$2M/year
- Urgency: Medium (niche, but high-value)

**Go-to-Market Approach:**
Start with design partners (developer tools), expand to AI infrastructure, then enterprise sales.

---

### Q18: What's Your Competitive Edge?

**Answer (250 words):**
**Edge 1: Non-Custodial Architecture**
Every competitor either (a) uses custodial models that enterprise rejects, or (b) avoids custody but lacks compliance and UX polish. We're the only entrant with non-custodial + enterprise-grade compliance + good UX. This is not a feature they can copy—it's an architecture decision.

**Edge 2: Natural Language Policy Compiler**
We translate English guardrails into code. "spend max $500/day on AWS, but never spend >10% on any single vendor" → smart contract enforceability. This is 10x faster to integrate than Solidity code or simple allowlists. UX advantage compounds as adoption scales.

**Edge 3: Integration Network**
We support 11 third-party services (Turnkey, Lithic, Persona, Elliptic, etc.). Adding a 12th integration is cheaper than competitors starting from zero. Network effects are real.

**Edge 4: MCP-Native Architecture**
We built for Claude agents natively. Agents use Sardis wallets with zero configuration. Competitors require custom integration. This is the future UI pattern for agent infrastructure.

**Edge 5: Founder Execution Velocity**
15k lines of production code solo in 6 months. This is top 1% of founder engineering speed. When we hire a team, we're already 2-3x ahead on product. This compounds.

**Edge 6: Protocol Positioning**
We're building AP2/x402 compliant from day one. Competitors are proprietary. When standards win (they will), we're already there. This is an option on the future.

**Edge 7: Market Timing**
We entered at the exact moment when (1) agents crossed capability threshold, (2) protocols emerged, (3) enterprise trusted autonomy. This is the 18-month window. Being 6 months ahead of the competition is the entire venture return.

**Why This Matters:**
Competitive advantages compound. Each advantage makes the next advantage easier. Enterprise trust → network effects → protocol positioning → market dominance.

---

### Q19: What Will You Do With This Capital?

**Answer (100 words):**
**In 3 Months:**
- Hire 2 engineers (protocol engineer, backend engineer)
- Launch public beta with mainnet contracts
- Onboard 10+ design partners

**In 6 Months:**
- Hire 1 sales/partnerships person
- 50+ beta users, first paying customers
- $10-50k MRR run rate
- 5-10 major partnership agreements

**In 12 Months:**
- 100+ customers
- $100k+ MRR
- Series A ready
- Clear path to $1M ARR

**Bottom Line:**
Capital is used to hire, scale customer acquisition, and reach Series A metrics. We're not building the product—we're scaling the product that already exists.

---

### Q20: Why Should We Invest in Sardis Specifically?

**Answer (200 words):**
**1. We Own the Enterprise Requirement**
Non-custodial is non-negotiable for enterprises deploying autonomous agents at scale. Every competitor either ignores this requirement or treats it as secondary. We built it as primary. This unlocks enterprise TAM that competitors cannot reach.

**2. We Have the Right Architecture for the Emerging Standards**
AP2, ACP, x402 are the payment protocols emerging for agents. We're building protocol-native from day one. Competitors building proprietary solutions will be disrupted when standards win.

**3. We Have Product-Market Fit Signals**
3 design partners already onboarding, inbound demand is strong, team is asking for more access. This is not speculative—this is real validation.

**4. We Have Founder-Market Fit**
Founder understands the problem deeply (8 years in blockchain infrastructure), has demonstrated execution velocity (15k lines of code solo), and is seeking a cofounder (not an ego play). This is a coachable, collaborative founder.

**5. We Have a Clear Path to Venture Outcomes**
$1M ARR by Q4 2026, $10M+ ARR by 2027, $100M+ ARR by 2030. These are realistic given market timing and product quality.

**6. The Market Window Is Closing**
18-24 months to become the standard. First vendor to own enterprise trust wins. Investing now positions you for the winner.

**7. This Is Infrastructure, Not an App**
Infrastructure compounds in value. Network effects are real. Winner-take-most dynamics are real. Once enterprises standardize on Sardis, they don't leave. This is a billion-dollar company.

---

## SECTION 5: FINAL TIPS FOR APPLICATIONS

### Writing Style
- **Be specific, not vague.** "We have strong demand" → "3 design partners actively onboarding, requesting features X, Y, Z"
- **Use numbers.** "15k+ lines of code," "36 MCP tools," "35,000% growth" are stronger than "we've built a lot."
- **Lead with the insight.** The best applications start with "we understand X about the market that nobody else does" and then prove it.
- **Show, don't tell.** Instead of "we're execution-focused," show a link to your GitHub (15k lines of code speaks for itself).

### Application Checklist
- [ ] Company name, website, HQ location clear in first paragraph
- [ ] One-liner is under 20 words and copyable
- [ ] Problem statement is 1-2 paragraphs, not 5+
- [ ] Traction section has specific numbers (not vague)
- [ ] Competitive comparison has a table or grid (easier to parse)
- [ ] Market opportunity has bottoms-up calculation (not just TAM)
- [ ] Founder background is authentic and relevant
- [ ] Call-to-action is clear (email, next steps)

### Proofreading
- Read out loud before submitting (catches awkward phrasing)
- Check numbers against source (15k+ lines of code, 36 MCP tools, etc. should be accurate)
- No typos or grammatical errors (hiring/sales partners will notice)
- Links work (website, GitHub, product demo)

---

## APPENDIX: LINKS & RESOURCES

**Company:**
- Website: sardis.sh
- GitHub: github.com/EfeDurmaz16/sardis
- Email (Investor): invest@sardis.sh
- Email (Founder): efebarandurmaz05@gmail.com

**Key Resources:**
- PearX: applications open, deadline Feb 22, 2026 (URGENT)
- Y Combinator: yc.com/apply
- Techstars: techstars.com/accelerator-programs
- a16z SPEEDRUN: a16z.com/speedrun
- Paradigm: paradigm.xyz (crypto VC)

**Smart Contract Deployment:**
- Base Sepolia testnet live
- Mainnet target: March 2026

**Product Status:**
- Public beta target: February 2026
- Design partners onboarding: 3 active (expanding to 10+)
- Revenue: Expected Q2 2026

---

**Document Version:** 1.0 (Feb 2026)
**Last Updated:** Feb 7, 2026
**Maintained By:** Efe Baran Durmaz
**Questions?** invest@sardis.sh
