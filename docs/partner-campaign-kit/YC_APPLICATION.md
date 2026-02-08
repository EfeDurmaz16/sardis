# Y Combinator Application - Sardis

**Batch:** Spring 2026 (S26)
**Submitted:** [Date]

---

## Founder Information

**Who writes code, or does other technical work on your product? Was any of it done by a non-founder? Please explain.**

I (Efe Baran Durmaz) wrote 100% of the code. The codebase includes 172 Python files across 12 packages, TypeScript SDKs, Solidity smart contracts, and a React landing page—all built solo over the past 6 months.

---

**Are you looking for a cofounder?**

Yes, ideally a technical cofounder with payments/fintech background who can own the infrastructure side while I focus on product and GTM.

---

## Company Information

**Company name:**

Sardis

---

**Describe what your company does in 50 characters or less:**

Payment controls for AI agents. Stripe for bots.

---

**Company URL, if any:**

https://sardis.sh

---

**Demo Video:**

[YouTube Unlisted Link - TO BE ADDED]

---

**Please provide a link to the product, if any:**

- Live Demo: https://sardis.sh/playground
- GitHub: https://github.com/EfeDurmaz16/sardis
- MCP Server: `npx @sardis/mcp-server start`

---

**What is your company going to make? Please describe your product and what it does or will do.**

Sardis is a payment infrastructure for AI agents—like Stripe, but with a "policy firewall" that validates every transaction before it executes.

The problem: AI agents are starting to spend money autonomously (API credits, cloud costs, SaaS subscriptions), but they hallucinate. One retry loop can drain $10,000. A decimal error turns $5 into $5,000. There's no control layer.

Our solution: Natural language spending policies + non-custodial MPC wallets + multi-rail settlement (crypto, cards, bank transfers). You tell Sardis "Allow SaaS vendors up to $100/day, block everything else" and it enforces that in real-time.

We've built:
- 36 MCP tools (works with Claude Desktop out of the box)
- Python + TypeScript SDKs
- Smart contracts deployed on Base Sepolia
- Full compliance stack (KYC via Persona, AML via Elliptic)
- Virtual card issuance (Lithic) and fiat rails (Bridge)

85% complete. Production in Q1 2026.

---

**Where do you live now, and where would the company be based after YC?**

**Now:** Istanbul, Turkey
**After YC:** San Francisco, CA

---

**Explain your decision regarding location.**

SF is where the AI infrastructure companies are (Anthropic, OpenAI, LangChain). I need to be in the room where agent payment standards are being defined. Also: payments requires US banking relationships that are easier to establish in-person.

---

## Progress

**How far along are you?**

Working product. Smart contracts deployed to testnet. MCP server works with Claude Desktop. SDKs built but not yet published to npm/PyPI.

Key metrics (testnet):
- 85% technical completion
- 36 MCP tools implemented
- 5 EVM chains supported
- 11 third-party integrations (Turnkey, Lithic, Bridge, Persona, Elliptic, etc.)

---

**How long have each of you been working on this? How much of that has been full-time? Please explain.**

6 months, 100% full-time since August 2025. I quit my job to build this after seeing the agent payment problem firsthand while building internal tools.

---

**What tech stack are you using, or planning to use, to build this product? Include AI models and AI coding tools you use.**

**Backend:** Python 3.11, FastAPI, Pydantic, SQLAlchemy
**Smart Contracts:** Solidity, Foundry
**SDKs:** Python (httpx), TypeScript (axios)
**MCP Server:** TypeScript, @modelcontextprotocol/sdk
**AI Integration:** OpenAI Instructor (for NL policy parsing), Claude MCP
**Infrastructure:** Vercel (frontend), Neon (Postgres), Upstash (Redis)
**Third-party:** Turnkey (MPC), Lithic (cards), Bridge (fiat), Persona (KYC), Elliptic (AML)

**AI Coding Tools:** Claude (Cursor), GitHub Copilot

---

**Are people using your product?**

Not yet publicly. Have demoed to 5 AI agent developers who all said they'd use it. Currently in private alpha with 3 early testers.

---

**When will you have a version people can use?**

Public beta: February 2026 (4 weeks)
Mainnet production: March 2026 (8 weeks)

---

**Do you have revenue?**

No. Pre-revenue.

---

**If you are applying with the same idea as a previous batch, did anything change?**

First application.

---

**If you have already participated or committed to participate in an incubator, "accelerator" or "pre-accelerator" program, please tell us about it.**

No.

---

## Idea

**Why did you pick this idea to work on? Do you have domain expertise in this area? How do you know people need what you're making?**

I was building an internal AI agent for a fintech company that needed to pay for cloud APIs automatically. Every solution sucked: Stripe requires user interaction, crypto wallets have no spending controls, corporate cards can't be programmatically limited.

I realized AI agents are going to spend trillions of dollars, and there's literally no infrastructure designed for them. It's like if web apps launched in 1995 but Stripe didn't exist until 2025.

Domain expertise: 4 years in fintech (payments, compliance), deep knowledge of MPC wallets and smart contract security. I've shipped payment products before.

Validation: Every AI agent developer I talk to has the same problem. LangChain community members routinely ask "how do I let my agent pay for stuff?" There's no good answer yet.

---

**Who are your competitors? What do you understand about your business that they don't?**

**Competitors:**
- **Skyfire:** Centralized, custodial, no policy engine. Just a payment API.
- **Payman:** Card-only, no crypto rails.
- **Locus:** Enterprise-focused, slow integration.

**What we understand:**
1. **Non-custodial is table stakes.** Enterprise won't trust a startup with their funds. MPC + smart contracts = we never have custody.
2. **Natural language policies win.** Developers hate DSLs. "Allow SaaS up to $100" is 10x faster than JSON schema.
3. **MCP integration is the wedge.** Claude Desktop has millions of users. Zero-integration setup beats SDK-first.
4. **Multi-rail matters.** Agents need to pay crypto APIs AND traditional vendors. One system, all rails.

**TAM:** $30 trillion AI agent spending by 2035 (Gartner)
**SAM:** $100 billion developer-controlled agent transactions
**SOM:** $1 billion (Year 3, 1% of SAM)

---

**How do or will you make money? How much could you make?**

**Revenue model:**
- 0.2% per transaction (minimum $0.001)
- Card/fiat fees passed through
- Enterprise SaaS tier for custom policies + SLAs ($10k/month)

**Unit economics:**
- Average transaction: $50
- Take rate: $0.10
- Gross margin: 80%+ (infrastructure costs minimal)

**Potential:**
- 1M transactions/month = $100k MRR
- 10M transactions/month = $1M MRR
- At scale (1B transactions/year) = $200M ARR

Stripe processes $1T/year. If agents do 10% of that, the market is $100B in transactions = $200M+ in fees at our take rate.

---

**Which category best applies to your company?**

Financial Services

---

**If you had any other ideas you considered applying with, please list them.**

1. **AI Code Review Agent:** Automated PR review with security focus. Decided agent payments was bigger.
2. **Compliance-as-a-Service for Crypto:** KYC/AML API. Realized this is a feature, not a company.
3. **Multi-Agent Orchestration Platform:** Like LangChain but for payments. Pivoted to infra-first approach.

---

## Legal & Funding

**Have you formed ANY legal entity yet?**

No. Planning Delaware C-Corp before YC.

---

**Have you taken any investment yet?**

No.

---

**Are you currently fundraising?**

Not actively. Will raise seed ($2M) post-YC. Using savings + small friends/family bridge (~$50k) until then.

---

## About YC

**What convinced you to apply to Y Combinator? Did someone encourage you to apply? Have you been to any YC events?**

Three reasons:

1. **Network effect:** YC founders are the most likely early customers (AI agent builders).
2. **Fundraising:** Payments infra requires capital for compliance, audits, partnerships.
3. **Signal:** "YC-backed" opens doors with Turnkey, Lithic, Bridge partnerships.

No one encouraged me—applied because it's obviously the right move. Haven't attended events (Istanbul → SF distance).

---

**How did you hear about Y Combinator?**

Been following since 2015. Read every essay, watched every Startup School video. Finally have something worth applying with.

---

## Final

**Which category best applies to your company?**

Financial Services / Developer Tools / AI Infrastructure

---

## Notes for Application

**Key points to emphasize:**
- Solo founder but seeking cofounder (address the concern directly)
- Deep technical execution (172 files, 36 tools, 5 chains)
- Clear understanding of competition and differentiation
- Path to revenue is straightforward (transaction fees)
- Wedge strategy: MCP → SDK → Enterprise

**Things to avoid:**
- Don't oversell traction (be honest about pre-revenue)
- Don't claim "no competition" (acknowledge and differentiate)
- Don't be vague about how you make money

---

*Application prepared: January 25, 2026*
