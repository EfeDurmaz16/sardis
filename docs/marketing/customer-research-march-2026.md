Now I have enough data to produce the comprehensive analysis. Let me write it up.

---

# SARDIS GTM CUSTOMER RESEARCH: FULL ANALYSIS

## PHASE 1: DEEP PRODUCT UNDERSTANDING

### What is actually being sold?

Sardis is **financial infrastructure middleware** -- a control plane that sits between AI agents and the financial system. It is not a wallet, not a payment processor, not a compliance tool, and not an agent framework. It is all of these composed into a single programmable layer.

**Core value proposition in one sentence:** "Give your AI agent a wallet it cannot abuse."

**What Sardis actually enables:**
1. An AI agent builder can provision a non-custodial MPC wallet for their agent
2. A business operator can define natural language spending policies ("max $500/day on cloud compute, never pay for gambling sites") that are deterministically enforced via a 12-check pipeline
3. The agent can then autonomously spend money -- on-chain via USDC or off-chain via virtual cards -- without any human in the loop for each transaction
4. Every transaction is audit-logged with Merkle anchoring, KYC/AML is handled, and there is a kill switch

**The pain it solves:**
- **For agent builders:** "My agent can reason and act, but the moment it needs to spend money, I have to hard-code payment logic, manage keys, and pray it does not drain the wallet." Sardis removes this entire class of engineering work.
- **For enterprises deploying agents:** "I cannot give an AI agent a credit card. I need policy enforcement, audit trails, compliance, and the ability to shut it down instantly." Sardis provides the trust and governance layer.
- **For compliance/finance teams:** "We have no way to track, limit, or audit what our AI agents are spending." Sardis gives them a dashboard with 40+ pages of observability.

**Emotional/strategic outcomes:**
- Agent builders ship faster (days instead of months to add payment capability)
- Enterprises unblock production deployment of agents that need to transact
- Finance/compliance teams get the controls they need to say "yes" instead of "no" to agent deployment
- Founders/CTOs get to market faster with financial agent products

### What workflows does it insert into?

1. **Agent development workflow:** Developer building an agent adds Sardis SDK (Python/TypeScript), configures policies, and the agent can now spend money
2. **Enterprise agent governance workflow:** IT/compliance team defines spending policies in the dashboard, monitors agent spending, approves/rejects via the approval queue
3. **Merchant checkout workflow:** Merchants accept payments from AI agents via the checkout flow
4. **Multi-agent orchestration workflow:** Multiple agents with different budgets and policies, coordinated through a single dashboard

---

## PHASE 2: INITIAL CUSTOMER PROFILES

### A. Direct Customer Profiles (Companies that would pay Sardis money)

**Profile 1: AI Agent Startup with Financial Workflows**
- **Company type:** Seed-to-Series B startup building AI agents that need to make purchases, payments, or financial transactions
- **Team type:** Small engineering team (5-30), moving fast, building on LangChain/CrewAI/OpenAI Agents SDK
- **Main problem:** They need their agents to spend money but do not want to build wallet infrastructure, policy enforcement, compliance, or audit trails from scratch
- **Workflow insertion:** SDK integration during agent development; replaces hand-rolled payment logic
- **Budget owner:** CTO or CEO (at startup scale these are the same person or adjacent)
- **Champion:** Lead engineer or founding engineer building the agent
- **Blocker:** "Can we just use Stripe?" or "We will build this ourselves"
- **Urgency:** HIGH -- they cannot ship their product without payment capability
- **Pilot likelihood:** 8/10 -- small team, fast decision, technical founder can evaluate quickly
- **Sales difficulty:** LOW -- self-serve or one meeting

**Profile 2: Enterprise Deploying Agents for Internal Operations**
- **Company type:** Mid-market to enterprise company (500-10K employees) deploying AI agents for procurement, travel, expense management, or vendor payments
- **Team type:** IT/Innovation team + Finance/Compliance team
- **Main problem:** They want to deploy agents that can make purchases but cannot give agents credit cards or access to payment systems without governance
- **Workflow insertion:** Sits between the agent platform and the payment rails; provides the policy/governance layer
- **Budget owner:** VP of Engineering, VP of IT, or CFO
- **Champion:** Head of AI/Innovation or the team building the agent
- **Blocker:** Security review, procurement process, "we already have SAP/Coupa"
- **Urgency:** MEDIUM -- enterprises move slowly but the pressure to deploy agents is increasing
- **Pilot likelihood:** 5/10 -- requires multiple stakeholders, longer sales cycle
- **Sales difficulty:** HIGH -- 3-6 month sales cycle, requires security review, SOC 2 questions

**Profile 3: Vertical AI Company (Travel, Procurement, Legal, Customer Support)**
- **Company type:** Vertical AI startup that has built domain expertise and now needs to add payment capability
- **Team type:** Product + engineering team that has built the AI but not the payments
- **Main problem:** Their product is incomplete without the ability to actually execute purchases/payments
- **Workflow insertion:** API/SDK integration into existing agent product
- **Budget owner:** CTO or VP of Product
- **Champion:** Product manager or lead engineer
- **Blocker:** "We want to own the payment stack" or "Our customers want us to use their existing payment rails"
- **Urgency:** HIGH -- payment capability is often the #1 feature request from their customers
- **Pilot likelihood:** 7/10 -- clear pain, technical team can evaluate
- **Sales difficulty:** MEDIUM -- need to prove Sardis is better than building in-house

### B. Enabler / Ecosystem Profiles (Not direct customers -- distribution partners)

**Profile 4: Agent Framework (LangChain, CrewAI, OpenAI, Google ADK, Vercel AI SDK)**
- **Role:** Distribution channel, not customer. They do not pay Sardis; they enable Sardis to reach their users
- **Value to Sardis:** Official integration means every developer using the framework discovers Sardis when they need payment capability
- **Sardis value to them:** "Our framework now supports financial agents" -- competitive differentiation
- **Engagement model:** Partnership, co-marketing, integration docs, joint blog posts

**Profile 5: Workflow Automation Platform (n8n, Activepieces, Zapier, Make)**
- **Role:** Distribution channel. Their users build automations that may need payment steps
- **Value to Sardis:** Access to hundreds of thousands of workflow builders
- **Engagement model:** Build a node/block/action for these platforms; listed in their marketplace

**Profile 6: Observability/DevOps for AI (Helicone, Langfuse, AgentOps)**
- **Role:** Complementary tool, not customer. They monitor agents; Sardis controls agent spending
- **Value to Sardis:** Co-marketing, referrals, joint value proposition ("monitor and control your agents")
- **Engagement model:** Integration partnership, shared content

### C. Long-term but Not First-Customer Profiles

**Profile 7: Large Enterprise (Fortune 500, Banks, Insurance)**
- **Why not first:** They require SOC 2 Type II, enterprise contracts, dedicated support, on-premise options. Sardis cannot serve them today
- **When they become relevant:** After 10-20 paying customers, SOC 2, and case studies
- **Engagement now:** Advisory conversations, design partner agreements for feedback

**Profile 8: Consumer-Facing AI Shopping Agents (Daydream, Phia, OneOff)**
- **Why not first:** B2C companies need different trust models, higher volume/lower margin, and their payment needs are better served by Stripe/PayPal today
- **When they become relevant:** When agentic commerce protocols mature and B2C agents need on-chain payment capability

---

## PHASE 3: DISTINGUISH CUSTOMERS FROM ENABLERS

### Why confusing customers and enablers destroys GTM

This is the single most common mistake for infrastructure companies. Sardis must not confuse the following:

| Entity | Classification | Why |
|--------|---------------|-----|
| LangChain | **Enabler** | LangChain does not pay Sardis. LangChain's *users* pay Sardis. LangChain is a distribution channel. |
| CrewAI | **Enabler** | Same as LangChain. Integration partner, not customer. |
| Helicone | **Enabler** | Complementary tool. They might refer customers but do not buy Sardis themselves. |
| AutoGPT | **Enabler** | Platform whose users might need Sardis. AutoGPT itself does not pay. |
| Composio | **Enabler** | Tool marketplace. Integration partner, not revenue source. |
| Coinbase AgentKit | **Competitor/Ecosystem** | They offer competing wallet infrastructure. Not a customer. |
| Stripe | **Competitor/Ecosystem** | They offer competing payment rails. Sardis uses Stripe Issuing but Stripe is not a customer. |
| Mastercard Start Path | **Accelerator/Enabler** | Potential accelerator program. They invest in Sardis's growth but are not a direct customer. |

**The danger:** If Sardis spends its first 3 months doing integration partnerships with LangChain, Helicone, and n8n instead of finding 10 paying customers, it will have great developer awareness but zero revenue and zero validated learning about what customers actually need.

**The correct order:**
1. Find 5-10 paying customers (Profiles 1-3)
2. Build integrations with enablers (Profiles 4-6) to accelerate distribution
3. Use early customer case studies to approach larger enterprises (Profile 7)

---

## PHASE 4: INITIAL CUSTOMER PROFILE HYPOTHESES

### Hypothesis 1: AI Travel Booking Startup

| Dimension | Detail |
|-----------|--------|
| **Who** | AI travel startups like BizTrip AI, Otto, iWander, or similar |
| **Painful workflow** | Their agent can find and recommend flights/hotels but cannot complete the booking because it cannot pay. Every transaction requires human intervention. |
| **Where Sardis fits** | SDK integration: agent calls Sardis to pay for booking with policy enforcement (e.g., "max $2,000 per booking, only approved airlines") |
| **Trigger** | Customer demo where the agent cannot complete the purchase; enterprise pilot where the travel manager demands policy controls |
| **Buy/pilot likelihood** | 7/10 -- clear pain, immediate value |
| **Painkiller vs vitamin** | **Painkiller** -- they literally cannot ship their product without payment capability |
| **Proof needed** | Working demo of agent completing a booking end-to-end with policy enforcement |
| **Objections** | "We are building with Stripe directly" / "We need card-based payments, not crypto" |

### Hypothesis 2: AI Procurement Agent Startup

| Dimension | Detail |
|-----------|--------|
| **Who** | Startups building autonomous procurement/sourcing agents |
| **Painful workflow** | Agent can find suppliers and negotiate but cannot issue purchase orders or pay vendors without human approval at every step |
| **Where Sardis fits** | Policy-controlled wallet that allows agent to pay vendors up to defined limits, with approval workflows for larger amounts |
| **Trigger** | Enterprise customer demanding governance controls on autonomous purchasing |
| **Buy/pilot likelihood** | 6/10 -- procurement is complex, longer evaluation |
| **Painkiller vs vitamin** | **Painkiller** -- autonomous procurement without payment is just a recommendation engine |
| **Proof needed** | Integration with their procurement workflow, compliance certifications |
| **Objections** | "We need fiat rails, not USDC" / "Our customers require SAP integration" |

### Hypothesis 3: AI Agent Platform Builder (Horizontal)

| Dimension | Detail |
|-----------|--------|
| **Who** | Companies building general-purpose AI agent platforms (Beam AI, Relevance AI, Lyzr, Sola) |
| **Painful workflow** | Their customers want agents that can spend money, but the platform does not offer payment capability |
| **Where Sardis fits** | White-label or integrated payment layer that the platform offers to its customers |
| **Trigger** | Customer churn or feature request volume around "my agent needs to pay for things" |
| **Buy/pilot likelihood** | 7/10 -- platform companies are highly motivated to add capabilities |
| **Painkiller vs vitamin** | **Vitamin becoming painkiller** -- today it is a nice-to-have, but as agentic commerce grows it becomes table-stakes |
| **Proof needed** | Easy integration, white-label capability, multi-tenant support |
| **Objections** | "We will build this ourselves" / "Coinbase AgentKit is free" |

### Hypothesis 4: Enterprise with Internal AI Agents

| Dimension | Detail |
|-----------|--------|
| **Who** | Mid-market companies (500-5K employees) deploying internal AI agents for operations |
| **Painful workflow** | IT team built an agent that should auto-purchase cloud resources, or auto-book travel, or auto-pay invoices, but finance team will not approve without governance controls |
| **Where Sardis fits** | Governance and policy layer that satisfies finance/compliance requirements |
| **Trigger** | Internal AI initiative blocked by CFO/CISO who demands spending controls |
| **Buy/pilot likelihood** | 4/10 -- long sales cycle, but high contract value |
| **Painkiller vs vitamin** | **Painkiller for the project sponsor** -- the AI initiative is dead without compliance approval |
| **Proof needed** | SOC 2, security review, integration with existing systems |
| **Objections** | "We need on-premise" / "We are waiting for our ERP vendor to add this" |

---

## PHASE 5: COMPANY DISCOVERY

### Tier 1: Direct Customer Targets -- AI-Native Startups with Financial Workflows

| # | Company | Website | Classification | Why Relevant | Workflow Insertion | Likely Team | Likely Buyer | Why Now | Fit | Confidence | Reachability | Pilot Likelihood |
|---|---------|---------|---------------|-------------|-------------------|-------------|-------------|---------|-----|------------|-------------|-----------------|
| 1 | **BizTrip AI** | biztrip.ai | Direct Customer | AI corporate travel agent that books autonomously; needs payment rails with policy enforcement | SDK integration for agent to pay for bookings with corporate policy compliance | Engineering (5-15) | CTO/CEO | Enterprise pilots launching Q2 2026; partnership with Sabre | 9 | 8 | 8 | 8 |
| 2 | **Otto** | ottotheagent.com | Direct Customer | AI business travel assistant that plans, books, and manages travel autonomously | Payment layer for autonomous booking completion | Engineering (10-20) | CEO Michael Gulman | Free for 12 months, needs monetization path; backed by Madrona | 8 | 7 | 7 | 7 |
| 3 | **Fairmarkit** | fairmarkit.com | Direct Customer | AI autonomous sourcing for procurement; agents negotiate and award contracts | Payment execution layer for autonomous purchasing after sourcing | Product + Eng | VP Product / CTO | 94% of procurement leaders use AI weekly; autonomous sourcing is their core product | 7 | 6 | 6 | 6 |
| 4 | **Sola AI** | sola.ai | Direct Customer | Agentic process automation platform; customers include Fortune 100, AmLaw 100 | Payment capability for workflows that require financial transactions | Engineering | CTO | $21M raised, rapid growth, enterprise customers demanding more autonomy | 7 | 6 | 6 | 7 |
| 5 | **Beam AI** | beam.ai | Direct Customer | Agentic automation platform with 200+ templates; enterprise customers | Payment module for agent templates that involve purchasing | Product + Eng | VP Product | Moving from automation to full autonomy; payment is the missing piece | 7 | 6 | 6 | 6 |
| 6 | **Lyzr** | lyzr.ai | Direct Customer | Low-code AI agent platform targeting procurement, compliance, and financial workflows | Embedded payment capability for enterprise agent deployments | Engineering | CTO | Actively marketing procurement agents; needs payment completion | 7 | 6 | 7 | 7 |
| 7 | **Relevance AI** | relevanceai.com | Direct Customer | Mid-market AI worker platform with templates for various business functions | Payment capability for agents handling purchasing workflows | Product | Head of Product | Growing customer demand for agents that can transact | 6 | 5 | 6 | 6 |
| 8 | **iWander** | -- | Direct Customer | AI travel agent platform for agencies; chatbots across booking touchpoints | Payment processing for AI-assisted bookings | Engineering | CTO/CEO | Travel AI is exploding; needs payment infrastructure | 7 | 5 | 5 | 6 |
| 9 | **Placeaa** | -- | Direct Customer | AI-powered platform for travel agencies and tour operators | Booking payment completion for AI recommendations | Engineering | CEO | Serves agencies that need automated booking completion | 6 | 4 | 5 | 5 |
| 10 | **Meteor** (browser agent) | -- | Direct Customer | Chrome-alternative browser where agents act as personal assistants, buy things on Amazon | Payment infrastructure for browser agent purchases | Engineering | CTO | Building agents that buy; needs secure payment rails | 7 | 5 | 5 | 6 |

### Tier 2: Direct Customer Targets -- Enterprise / Mid-Market

| # | Company | Website | Classification | Why Relevant | Workflow Insertion | Likely Team | Likely Buyer | Why Now | Fit | Confidence | Reachability | Pilot Likelihood |
|---|---------|---------|---------------|-------------|-------------------|-------------|-------------|---------|-----|------------|-------------|-----------------|
| 11 | **Zip HQ** | ziphq.com | Direct Customer (large) | 50+ AI agents for procurement; OpenAI, Canva, Webflow as early adopters | Payment execution layer for autonomous procurement approvals | Product + Eng | VP Product | 30% of requests handled autonomously by 2026; payment is the next step | 8 | 5 | 4 | 4 |
| 12 | **Tonkean** | tonkean.com | Direct Customer | No-code procurement orchestration; legal, IT, security compliance | Payment completion for automated procurement workflows | Product | VP Product | Procurement orchestration needs payment execution to be complete | 6 | 5 | 5 | 5 |
| 13 | **Levelpath** | levelpath.com | Potential Customer (large) | AI-native procurement; $100M+ raised; Ace Hardware, Amgen, SiriusXM | Payment execution for automated procurement | Product + Eng | VP Product | $55M Series B; scaling rapidly | 6 | 4 | 4 | 3 |
| 14 | **Omnea** | omnea.co | Potential Customer (large) | Procurement orchestration; Spotify, Wise, MongoDB as customers | Payment layer for procurement approvals | Product + Eng | VP Product | $75M+ raised; 5x revenue growth | 6 | 4 | 4 | 3 |
| 15 | **Vertice** | vertice.one | Potential Customer | SaaS management and procurement; software license purchasing | Payment execution for SaaS procurement automation | Product | VP Product | SaaS procurement is a clear use case for autonomous purchasing | 5 | 4 | 5 | 4 |

### Tier 3: Broader Universe -- AI Agent Startups Needing Payments

| # | Company | Website | Classification | Why Relevant | Why Now | Fit | Confidence | Reachability | Pilot Likelihood |
|---|---------|---------|---------------|-------------|---------|-----|------------|-------------|-----------------|
| 16 | **Fellou** | fellou.ai | Direct Customer | AI-native browser for agentic workflows | Agents need to pay for things they discover | 6 | 5 | 5 | 5 |
| 17 | **Browserbase/Stagehand** | browserbase.com | Direct Customer | Headless browser for AI agents; agents interact with web | Web agents need payment capability for checkout | 6 | 5 | 6 | 5 |
| 18 | **Shinkai** | -- | Direct Customer | Onchain AI agents with USDC/x402; just launched v1.0 | Needs wallet infrastructure beyond basic x402 | 7 | 5 | 5 | 6 |
| 19 | **Daydream** | daydream.ing | Long-term | AI shopping; $50M seed; fashion focus | Currently discovery-only, not completing purchases | 5 | 4 | 3 | 3 |
| 20 | **OneOff** | -- | Long-term | AI shopping based on celebrity looks; testing agentic checkout | Early stage, testing checkout | 5 | 4 | 4 | 4 |
| 21 | **Nyne** | -- | Direct Customer | Gives AI agents human context for purchasing decisions | Agents need payment rails with context-aware policies | 6 | 4 | 5 | 5 |
| 22 | **HyperExpense** | hyperexpense.com | Direct Customer | Autonomous expense management | Agents managing expenses need controlled payment capability | 6 | 5 | 5 | 5 |
| 23 | **Vic.ai** | vic.ai | Potential Customer | Autonomous AP/finance platform with corporate cards | Could integrate Sardis for AI-controlled card spending policies | 5 | 4 | 4 | 3 |
| 24 | **AppZen** | appzen.com | Long-term | AI finance automation for enterprises | Established player; may build in-house | 4 | 3 | 3 | 2 |
| 25 | **Procure AI** | procure.ai | Direct Customer | AI-powered procurement platform | Autonomous purchasing needs payment infrastructure | 6 | 5 | 5 | 5 |

### Tier 4: Ecosystem Enablers (NOT Direct Customers)

| # | Company | Website | Classification | Role | Value to Sardis | Engagement Model |
|---|---------|---------|---------------|------|----------------|-----------------|
| 26 | **LangChain** | langchain.com | Enabler | Agent framework | Distribution to 100K+ developers | Integration, co-marketing |
| 27 | **CrewAI** | crewai.com | Enabler | Multi-agent framework | Distribution to collaborative agent builders | Integration, docs |
| 28 | **OpenAI (Agents SDK)** | openai.com | Enabler | Agent framework | Credibility + distribution | Integration |
| 29 | **Google ADK** | cloud.google.com | Enabler | Agent framework | Enterprise distribution | AP2 protocol alignment |
| 30 | **Vercel AI SDK** | vercel.com | Enabler | AI SDK | Frontend developer distribution | Integration |
| 31 | **Composio** | composio.dev | Enabler | Tool marketplace | Listed as payment tool in marketplace | Integration |
| 32 | **n8n** | n8n.io | Enabler | Workflow automation | Access to workflow builders needing payment nodes | Build n8n node |
| 33 | **Activepieces** | activepieces.com | Enabler | Workflow automation | Access to automation builders | Build Activepieces piece |
| 34 | **Helicone** | helicone.ai | Enabler | LLM observability | Co-marketing, referrals | Integration partnership |
| 35 | **Browser Use** | browser-use.com | Enabler | Browser automation (78K stars) | Distribution to browser agent builders | Integration |
| 36 | **Mastercard Start Path** | mastercard.com | Enabler/Accelerator | Startup program | Network, credibility, pilot opportunities | Apply to program |
| 37 | **Visa Intelligent Commerce** | visa.com | Enabler/Ecosystem | Payment network | TAP protocol alignment, sandbox access | Technical partnership |

### Tier 5: Competitors (Watch, Do Not Sell To)

| # | Company | Website | Classification | Funding | Key Differentiator vs Sardis |
|---|---------|---------|---------------|---------|----------------------------|
| 38 | **Skyfire** | skyfire.xyz | Competitor | $9.5M | Crypto-native identity + payments; KYA focus |
| 39 | **Crossmint** | crossmint.com | Competitor | $23.6M | GOAT SDK, Visa virtual cards, 1B+ item catalog |
| 40 | **Catena Labs** | catenalabs.com | Competitor | $18M (a16z) | Regulated AI-native financial institution; USDC focus |
| 41 | **Natural** | natural.co | Competitor | $9.8M | B2B agentic payments; embedded use cases |
| 42 | **Nekuda** | nekuda.co | Competitor | $5M (Visa/Amex) | Agentic mandates; card-network aligned |
| 43 | **Circuit & Chisel** | -- | Competitor | $19.2M | ATXP protocol; micropayments; Stripe alumni |
| 44 | **Payman AI** | paymanai.com | Competitor | $13.8M | Banking AI; Fifth Third Bank custody; fiat-first |
| 45 | **Sponge** | paysponge.com | Competitor | YC W26 | Ex-Stripe; wallet + gateway; fiat + crypto |
| 46 | **AgentaOS/Agentokratia** | agentaos.ai | Competitor | Unknown | Open-source financial OS; self-hosted option |
| 47 | **PolicyLayer** | policylayer.com | Partial Competitor | Unknown | Policy enforcement only (no wallet, no payments) |
| 48 | **Nevermined** | nevermined.ai | Competitor | Unknown | Agent-to-agent payments; micropayments; x402 |
| 49 | **Coinbase AgentKit** | coinbase.com | Competitor (Big Co) | N/A | x402, 50M+ transactions, free, massive distribution |
| 50 | **Ramp Agent Cards** | ramp.com | Competitor (Adjacent) | N/A | Enterprise card-based agent spending with policy controls |

---

## PHASE 6: PRIORITIZE THE FIRST CUSTOMERS

### Top 10 First Sales Targets (Ranked by composite score)

| Rank | Company | Profile | Composite Score | Why First |
|------|---------|---------|----------------|-----------|
| 1 | **BizTrip AI** | Travel AI Agent | 33/40 | Clearest pain (agent cannot complete booking), active enterprise pilots, Sabre partnership proves legitimacy, small enough team to move fast, Andrew Ng backing = credibility reference |
| 2 | **Otto** | Travel AI Agent | 29/40 | Free product needs monetization, Madrona-backed, ex-Expedia/Concur team understands enterprise travel payments deeply |
| 3 | **Sola AI** | Agentic Automation | 27/40 | $21M raised, Fortune 100 customers, workflows that need payment execution, YC + a16z backing |
| 4 | **Lyzr** | Agent Platform | 27/40 | Actively marketing procurement agents, low-code platform needs embedded payment, reachable team |
| 5 | **Beam AI** | Agentic Automation | 25/40 | 200+ templates, enterprise customers, payment is the obvious next capability |
| 6 | **Fairmarkit** | Procurement AI | 25/40 | Autonomous sourcing needs autonomous payment; $30M+ raised; Conduent partnership |
| 7 | **Relevance AI** | Agent Platform | 23/40 | Mid-market focus, template-based approach, payment capability would differentiate |
| 8 | **HyperExpense** | Expense Management | 22/40 | Autonomous expense = autonomous payment; directly in Sardis's wheelhouse |
| 9 | **Fellou** | Browser Agent | 22/40 | AI-native browser; agents browsing web need to complete purchases |
| 10 | **Procure AI** | Procurement AI | 22/40 | AI procurement platform; autonomous purchasing is the endgame |

### Next 20 Targets

| Rank | Company | Profile | Notes |
|------|---------|---------|-------|
| 11 | Browserbase/Stagehand | Browser Infra | Browser agents need checkout capability |
| 12 | Shinkai | On-chain Agents | Already using USDC/x402; natural fit |
| 13 | Nyne | Agent Context | Agents with human context need payment rails |
| 14 | Tonkean | Procurement | No-code procurement orchestration |
| 15 | Meteor | Browser Agent | Personal assistant agent that buys things |
| 16 | iWander | Travel AI | AI travel chatbot for agencies |
| 17 | Placeaa | Travel AI | AI for tour operators |
| 18 | Vertice | SaaS Procurement | SaaS license purchasing |
| 19 | Zip HQ | Procurement (large) | 50+ AI agents; OpenAI as customer |
| 20 | OneOff | Shopping AI | Testing agentic checkout |
| 21 | Vic.ai | Finance AI | Corporate cards + AP automation |
| 22 | Omnea | Procurement (large) | $75M raised; Spotify, Wise as customers |
| 23 | Levelpath | Procurement (large) | $100M+ raised; enterprise procurement |
| 24 | Daydream | Shopping AI | $50M seed; fashion discovery |
| 25 | Procol | Procurement | AI-powered procurement platform |
| 26 | Spendkey | Spend Analytics | AI spend intelligence |
| 27 | Response (procurement) | Procurement | Digital procurement officer |
| 28 | Matchory | Supply Chain | AI-powered procurement for supply chains |
| 29 | Mindtrip | Travel AI | Partnership with PayPal and Sabre |
| 30 | Hyper | Expense AI | Autonomous expense management |

### Top 10 Enablers (Prioritized by distribution value)

| Rank | Company | Type | Distribution Value | Engagement Priority |
|------|---------|------|-------------------|-------------------|
| 1 | **LangChain** | Agent Framework | 100K+ developers | HIGH -- first integration to build |
| 2 | **CrewAI** | Multi-Agent Framework | Growing rapidly | HIGH -- multi-agent = multi-wallet |
| 3 | **OpenAI Agents SDK** | Agent Framework | Massive reach | HIGH -- credibility signal |
| 4 | **Browser Use** | Browser Automation | 78K GitHub stars | HIGH -- browser agents need payments |
| 5 | **n8n** | Workflow Automation | 500+ integrations, 80% AI workflows | MEDIUM -- build node |
| 6 | **Composio** | Tool Marketplace | 500+ apps, growing | MEDIUM -- listed as tool |
| 7 | **Vercel AI SDK** | AI SDK | Frontend developers | MEDIUM -- JS/TS ecosystem |
| 8 | **Google ADK** | Agent Framework | Enterprise reach | MEDIUM -- AP2 alignment |
| 9 | **Mastercard Start Path** | Accelerator | Network + credibility | MEDIUM -- apply for cohort |
| 10 | **Helicone** | LLM Observability | Monitoring + spending = complete picture | LOW -- co-marketing |

---

## PHASE 7: BUYER MAP (Top 5 Targets)

### BizTrip AI
- **Who feels pain first:** The engineering team trying to complete end-to-end booking demos
- **Who owns workflow:** CTO/co-founder (Scott Persinger)
- **Who champions:** Lead agent engineer
- **Who approves budget:** CEO (Tom Romary) -- small startup, CEO decides
- **Who blocks:** Enterprise pilot customers who demand their own payment rails
- **What team says yes:** "This saves us 3 months of building payment infrastructure"

### Otto
- **Who feels pain first:** Product team demoing autonomous booking that stops at payment
- **Who owns workflow:** CEO (Michael Gulman, ex-Expedia)
- **Who champions:** Engineering lead
- **Who approves budget:** CEO + Executive Chairman (Steve Singh, co-founder of Concur)
- **Who blocks:** Madrona portfolio overlap with competitors
- **What team says yes:** "We can ship autonomous payment in weeks instead of building from scratch"

### Sola AI
- **Who feels pain first:** Customers (Fortune 100, AmLaw 100) asking for workflows that include payments
- **Who owns workflow:** CTO
- **Who champions:** Customer success team hearing payment requests
- **Who approves budget:** CEO
- **Who blocks:** "We are focused on process automation, not payments"
- **What team says yes:** "Our customers want this; we cannot build it ourselves fast enough"

### Lyzr
- **Who feels pain first:** Procurement agent users who cannot complete purchases
- **Who owns workflow:** Product team
- **Who champions:** Product manager for procurement vertical
- **Who approves budget:** CTO
- **Who blocks:** "We will build our own Stripe integration"
- **What team says yes:** "Policy enforcement + compliance + audit trail = we do not need to build this"

### Beam AI
- **Who feels pain first:** Enterprise customers whose automation stops at the payment step
- **Who owns workflow:** VP Product
- **Who champions:** Solutions architect working with enterprise customers
- **Who approves budget:** CEO
- **Who blocks:** Build-vs-buy debate; "Ramp Agent Cards exists"
- **What team says yes:** "Payment capability makes our 200+ templates 10x more valuable"

---

## PHASE 8: SALES ANGLE AND LEARNING AGENDA

### Outreach Angles by Profile

**For AI Travel Startups (BizTrip, Otto):**
> "Your agent can find the perfect flight. But it cannot buy it. We make that last mile work -- with spending policies your enterprise customers will actually approve."

**For AI Procurement Startups (Fairmarkit, Procure AI):**
> "Autonomous sourcing without autonomous payment is just a recommendation engine. We add the payment execution layer with the compliance controls your customers require."

**For Agent Platforms (Sola, Beam, Lyzr, Relevance):**
> "Your customers' #1 feature request is 'my agent needs to spend money.' We give you that capability as an SDK integration -- wallets, policies, compliance, audit trail -- so you never have to build it."

### Value Framing

**Do NOT say:** "We are a crypto payment platform" / "We do blockchain-based wallets" / "We are a Web3 company"

**DO say:**
- "Payment infrastructure for AI agents with built-in spending controls"
- "Give your agent a wallet it cannot abuse"
- "Policy-controlled payments for autonomous agents -- on-chain USDC or virtual cards"
- "The trust layer between your AI agent and your company's money"

### Biggest Objections and Responses

| Objection | Response |
|-----------|----------|
| "We will use Stripe directly" | "Stripe handles payment processing. Sardis handles the layer above: who is allowed to spend, how much, on what, with what approvals. Stripe processes the transaction; Sardis decides whether the transaction should happen." |
| "Coinbase AgentKit is free" | "AgentKit gives you a wallet. Sardis gives you a wallet + 12-check policy engine + natural language spending rules + compliance + audit trail + kill switch + dashboard. AgentKit is the engine; Sardis is the whole car." |
| "We do not need crypto/USDC" | "Sardis supports both on-chain USDC and traditional virtual cards via Stripe Issuing. You choose the rails; we provide the governance layer regardless." |
| "We will build this in-house" | "How long will it take to build MPC wallet infrastructure, policy enforcement, KYC/AML, audit logging, and a 40-page dashboard? Sardis gives you all of this via SDK in days." |
| "Do you have SOC 2?" | "Not yet, but our architecture is non-custodial (we never touch your keys), fail-closed (every check must pass), and append-only (immutable audit trail). We are working toward SOC 2 and happy to walk through our security architecture." |

### Learning Agenda: What the First 10-20 Conversations Must Teach

1. **Do customers need USDC, virtual cards, or both?** -- This determines product roadmap priority
2. **Is the buyer the CTO, the product manager, or the finance/compliance team?** -- This determines sales motion
3. **Is "natural language spending policies" a feature that excites buyers or confuses them?** -- This determines messaging
4. **What is the minimum viable compliance posture?** -- Do customers need SOC 2 before piloting, or will they pilot without it?
5. **Is the real blocker technical integration difficulty or organizational trust?** -- This determines whether to invest in easier SDKs or better security documentation
6. **Which agent framework are customers actually using?** -- This determines which integrations to build first
7. **Are customers comparing Sardis to Skyfire/Crossmint/Natural, or do they not know competitors exist?** -- This determines competitive positioning urgency
8. **Is on-chain payment (USDC) a feature or a liability?** -- Some enterprise buyers may see "crypto" as a red flag
9. **What is the price sensitivity?** -- Is $49/month reasonable, or do customers need usage-based pricing?
10. **How do customers currently solve this problem?** -- Are they building in-house, using Stripe, using Ramp, or simply not solving it?

### Validation Signals (Things That Prove the Hypothesis)

- Customer says "we have been looking for something exactly like this"
- Customer asks "can we start a pilot this week?"
- Customer says "our enterprise customers are demanding policy controls on agent spending"
- Customer says "we built a hacky version of this internally and it is terrible"

### Disproval Signals (Things That Kill the Hypothesis)

- Customer says "our agents do not make purchases"
- Customer says "Stripe + Ramp Agent Cards already solved this for us"
- Customer says "we would never use crypto/USDC in production"
- Customer says "our agents only recommend; humans always complete the transaction"
- Multiple customers say "we are not paying for this; we will build it ourselves"

---

## PHASE 9: FINAL RECOMMENDATION

### Who are the best initial customers?

**AI-native startups building agents that must complete financial transactions to deliver their core product value.** Specifically:

1. **AI travel booking startups** (BizTrip AI, Otto) -- Clearest pain, fastest sales cycle, highest urgency. Their agents cannot complete their core workflow without payment capability. Enterprise pilots are launching now.

2. **AI agent platform companies** (Sola AI, Beam AI, Lyzr) -- They serve many customers who each need payment capability. One integration = many end users. Platform economics.

3. **AI procurement/sourcing startups** (Fairmarkit, Procure AI) -- Autonomous sourcing without autonomous payment is incomplete. Clear workflow insertion point.

### Who is only an enabler?

LangChain, CrewAI, OpenAI Agents SDK, Vercel AI SDK, Google ADK, Composio, n8n, Activepieces, Helicone, Browser Use, and Mastercard Start Path are all **enablers, not customers**. They should be pursued for integration partnerships and distribution, but they will never pay Sardis money directly. Do not confuse integration interest with buying interest.

### Which profiles first?

1. **Profile 1 (AI Agent Startup with Financial Workflows)** -- fastest sales, clearest pain, smallest sales cycle
2. **Profile 3 (Vertical AI Company)** -- travel and procurement verticals have the strongest product-market fit signal
3. **Profile 2 (Enterprise)** -- pursue only after having 5-10 startup customers and case studies

### Which accounts first?

**Immediate outreach (this week):**
1. BizTrip AI -- CEO Tom Romary, CTO Scott Persinger
2. Otto -- CEO Michael Gulman
3. Sola AI -- via YC network
4. Lyzr -- via their procurement vertical page
5. Beam AI -- via their agent templates

**Next wave (next 2 weeks):**
6. Fairmarkit
7. HyperExpense
8. Fellou
9. Relevance AI
10. Browserbase/Stagehand

### What to learn from outreach

The first 10-20 conversations should answer: (1) Is the buyer the CTO or the finance team? (2) Do they need USDC, virtual cards, or both? (3) Is "crypto" a feature or a liability in positioning? (4) Can they pilot without SOC 2? (5) What is the competitive alternative they are evaluating today?

---

## FINAL OUTPUT: STRUCTURED COMPANY LIST

### Direct Enterprise Buyers

| Company | Website | Classification | Customer_Profile | Why_Fit | Workflow_Insertion_Point | Likely_Team | Likely_Buyer | Why_Now | Fit_Score | Confidence_Score | Reachability_Score | Pilot_Likelihood_Score | Notes |
|---------|---------|---------------|-----------------|---------|------------------------|-------------|-------------|---------|-----------|-----------------|-------------------|----------------------|-------|
| Zip HQ | ziphq.com | Direct (large enterprise) | Enterprise Procurement | 50+ AI agents, 30% autonomous; OpenAI/Canva/Webflow customers | Payment execution for autonomous procurement | Product + Eng | VP Product | Autonomous procurement scaling rapidly | 8 | 5 | 4 | 4 | Large company; long sales cycle but massive reference value |
| Levelpath | levelpath.com | Long-term enterprise | Enterprise Procurement | $100M+ raised; Ace Hardware, Amgen, SiriusXM | Payment execution for AI procurement | Product + Eng | VP Product | Series B growth | 6 | 4 | 4 | 3 | Too large for first customer; pursue after traction |
| Omnea | omnea.co | Long-term enterprise | Enterprise Procurement | $75M+ raised; Spotify, Wise, MongoDB | Payment layer for procurement | Product + Eng | VP Product | 5x revenue growth | 6 | 4 | 4 | 3 | Same as Levelpath |

### AI-Native Startup Buyers

| Company | Website | Classification | Customer_Profile | Why_Fit | Workflow_Insertion_Point | Likely_Team | Likely_Buyer | Why_Now | Fit_Score | Confidence_Score | Reachability_Score | Pilot_Likelihood_Score | Notes |
|---------|---------|---------------|-----------------|---------|------------------------|-------------|-------------|---------|-----------|-----------------|-------------------|----------------------|-------|
| Sola AI | sola.ai | Direct Customer | Agent Platform | Agentic automation with Fortune 100 customers | Payment capability for automated workflows | Engineering | CTO | $21M raised; enterprise customers demanding payment | 7 | 6 | 6 | 7 | YC + a16z backed; growing fast |
| Beam AI | beam.ai | Direct Customer | Agent Platform | 200+ templates; enterprise customers | Payment module for agent templates | Product + Eng | VP Product | Platform needs payment to complete autonomy promise | 7 | 6 | 6 | 6 | Strong template marketplace model |
| Lyzr | lyzr.ai | Direct Customer | Agent Platform | Low-code agents for procurement and finance | Embedded payment for agent workflows | Engineering | CTO | Actively marketing procurement agents | 7 | 6 | 7 | 7 | Low-code = easy integration story |
| Relevance AI | relevanceai.com | Direct Customer | Agent Platform | Mid-market AI workers with templates | Payment capability for purchasing workflows | Product | Head of Product | Growing demand for transacting agents | 6 | 5 | 6 | 6 | Template-based; good for integration |
| Shinkai | -- | Direct Customer | On-chain Agents | AI agents with USDC/x402 support | Enhanced wallet + policy infrastructure | Engineering | CTO | Just launched v1.0; needs governance | 7 | 5 | 5 | 6 | Strong crypto-native fit |
| Fellou | fellou.ai | Direct Customer | Browser Agent | AI-native browser for agentic workflows | Payment infrastructure for browser purchases | Engineering | CTO | Agents need to pay for what they discover | 6 | 5 | 5 | 5 | Browser agent = needs checkout |
| Nyne | -- | Direct Customer | Agent Context | Gives agents human context for purchasing | Payment rails with context-aware policies | Engineering | CTO | Fresh TechCrunch coverage March 2026 | 6 | 4 | 5 | 5 | Very early stage |
| Meteor | -- | Direct Customer | Browser Agent | Chrome-alternative with purchasing agents | Payment infrastructure for agent purchases | Engineering | CTO | Building agents that buy things | 7 | 5 | 5 | 6 | Interesting use case |

### Procurement / Spend / Travel / Commerce Workflow Buyers

| Company | Website | Classification | Customer_Profile | Why_Fit | Workflow_Insertion_Point | Likely_Team | Likely_Buyer | Why_Now | Fit_Score | Confidence_Score | Reachability_Score | Pilot_Likelihood_Score | Notes |
|---------|---------|---------------|-----------------|---------|------------------------|-------------|-------------|---------|-----------|-----------------|-------------------|----------------------|-------|
| BizTrip AI | biztrip.ai | Direct Customer | Travel AI | Corporate travel agent needs payment for bookings | SDK for agent to complete bookings with policy | Engineering | CEO/CTO | Enterprise pilots Q2 2026; Sabre partnership | 9 | 8 | 8 | 8 | **#1 TARGET** -- clearest pain, best timing |
| Otto | ottotheagent.com | Direct Customer | Travel AI | Business travel assistant needs autonomous payment | Payment layer for booking completion | Engineering | CEO | Free product needs monetization; Madrona-backed | 8 | 7 | 7 | 7 | **#2 TARGET** -- ex-Expedia/Concur team |
| Fairmarkit | fairmarkit.com | Direct Customer | Procurement AI | Autonomous sourcing needs autonomous payment | Payment execution after sourcing decision | Product + Eng | VP Product | Conduent partnership; enterprise demand | 7 | 6 | 6 | 6 | $30M+ raised; clear workflow gap |
| HyperExpense | hyperexpense.com | Direct Customer | Expense AI | Autonomous expense management | Controlled payment for automated expenses | Product | CTO | Autonomous expense = needs payment rails | 6 | 5 | 5 | 5 | Direct alignment with Sardis value prop |
| Procure AI | procure.ai | Direct Customer | Procurement AI | AI procurement platform | Payment execution for purchasing | Engineering | CTO | Autonomous procurement market growing | 6 | 5 | 5 | 5 | Clear use case |
| Tonkean | tonkean.com | Direct Customer | Procurement | No-code procurement orchestration | Payment completion for automated workflows | Product | VP Product | Legal/compliance-driven procurement | 6 | 5 | 5 | 5 | Good compliance story |
| iWander | -- | Direct Customer | Travel AI | AI travel chatbot for agencies | Payment for AI-assisted bookings | Engineering | CTO | Travel AI exploding | 7 | 5 | 5 | 6 | Smaller team, accessible |
| Mindtrip | mindtrip.ai | Long-term | Travel AI | PayPal + Sabre partnership; agentic travel | Already partnered with PayPal for payments | Product | CTO | Q2 2026 launch | 5 | 4 | 3 | 3 | PayPal partnership may preclude Sardis |
| Vertice | vertice.one | Potential Customer | SaaS Procurement | SaaS license purchasing | Payment execution for software procurement | Product | VP Product | SaaS procurement growing | 5 | 4 | 5 | 4 | Niche but clear |

### Agent Framework and Ecosystem Enablers

| Company | Website | Classification | Customer_Profile | Why_Fit | Workflow_Insertion_Point | Likely_Team | Likely_Buyer | Why_Now | Fit_Score | Confidence_Score | Reachability_Score | Pilot_Likelihood_Score | Notes |
|---------|---------|---------------|-----------------|---------|------------------------|-------------|-------------|---------|-----------|-----------------|-------------------|----------------------|-------|
| LangChain | langchain.com | Enabler | Framework | 100K+ developers building agents | Integration as payment tool | DevRel | N/A (partnership) | Dominant framework; payment is missing | 9 | 8 | 7 | N/A | **#1 enabler** -- build integration first |
| CrewAI | crewai.com | Enabler | Framework | Multi-agent = multi-wallet | Integration for agent teams | DevRel | N/A | Growing multi-agent use cases | 8 | 7 | 7 | N/A | Multi-agent uniquely needs Sardis |
| OpenAI Agents SDK | openai.com | Enabler | Framework | Massive developer base | Integration as payment tool | DevRel | N/A | OpenAI pushing agents hard | 8 | 6 | 4 | N/A | Hard to reach but high impact |
| Browser Use | browser-use.com | Enabler | Browser Tool | 78K stars; agents browse and need to pay | Integration for checkout | DevRel | N/A | Browser agents need payment | 8 | 7 | 7 | N/A | Great fit; accessible team |
| n8n | n8n.io | Enabler | Workflow | 80% AI workflows; 500+ integrations | Payment node in workflow builder | DevRel | N/A | Workflow automation + payments | 7 | 6 | 6 | N/A | Build node; list in marketplace |
| Composio | composio.dev | Enabler | Tool Marketplace | 500+ app integrations | Listed as payment tool | DevRel | N/A | Growing marketplace | 6 | 5 | 7 | N/A | Easy integration |
| Vercel AI SDK | vercel.com | Enabler | SDK | Frontend AI developers | Integration as provider | DevRel | N/A | AI SDK growing | 6 | 5 | 5 | N/A | TypeScript ecosystem |
| Google ADK | cloud.google.com | Enabler | Framework | Enterprise agent development | AP2 protocol alignment | DevRel | N/A | AP2 protocol = Sardis differentiator | 7 | 5 | 4 | N/A | AP2 verification is unique Sardis feature |
| Activepieces | activepieces.com | Enabler | Workflow | AI-first automation builder | Payment piece in builder | DevRel | N/A | Growing alternative to n8n | 5 | 5 | 7 | N/A | Already in talks per memory |
| Helicone | helicone.ai | Enabler | Observability | LLM monitoring complements spending control | Co-marketing; "monitor and control" | DevRel | N/A | Complementary tool | 5 | 5 | 8 | N/A | Already in talks per memory |
| Mastercard Start Path | mastercard.com | Enabler/Accelerator | Program | Network, credibility, pilot access | Apply to agentic commerce cohort | CEO | N/A | Applications open for agentic commerce | 7 | 5 | 5 | N/A | Apply immediately; high credibility signal |

---

## BEST FIRST CUSTOMERS vs BEST ENABLERS: RANKED LISTS

### Best First Customers (Pay Sardis Money)

1. **BizTrip AI** -- AI travel agent, enterprise pilots imminent, clearest pain, Andrew Ng backing
2. **Otto** -- AI business travel, ex-Expedia/Concur team, free product needs payment monetization
3. **Sola AI** -- Agentic automation, $21M raised, Fortune 100 customers wanting payment workflows
4. **Lyzr** -- Low-code agent platform, actively marketing procurement agents
5. **Beam AI** -- 200+ agent templates, enterprise customers, payment completes the automation loop
6. **Fairmarkit** -- Autonomous sourcing needs autonomous payment; $30M+ raised
7. **HyperExpense** -- Autonomous expense management; direct Sardis value prop alignment
8. **Fellou** -- AI-native browser; agents need to pay for what they find
9. **Relevance AI** -- Mid-market AI workers; template-based approach for easy integration
10. **Procure AI** -- AI procurement platform; autonomous purchasing endgame

### Best Enablers (Distribute Sardis to Customers)

1. **LangChain** -- dominant agent framework; payment integration would reach 100K+ developers
2. **CrewAI** -- multi-agent framework; multi-wallet is a natural fit
3. **Browser Use** -- 78K GitHub stars; browser agents inherently need payment capability
4. **OpenAI Agents SDK** -- massive reach and credibility signal
5. **n8n** -- 80% of workflows are AI; payment node fills an obvious gap
6. **Mastercard Start Path** -- credibility, network, and pilot access for agentic commerce
7. **Composio** -- tool marketplace; easy listing
8. **Google ADK** -- AP2 alignment is a unique Sardis competitive advantage
9. **Vercel AI SDK** -- TypeScript ecosystem reach
10. **Helicone** -- "monitor your agents + control their spending" joint story

---

Sources:
- [Top AI Agent Startups 2026](https://aifundingtracker.com/top-ai-agent-startups/)
- [From Agentic Payments to AI Infrastructure - PYMNTS](https://www.pymnts.com/artificial-intelligence-2/2025/from-agentic-payments-to-ai-infrastructure-this-weeks-startup-funding/)
- [Hot 25 Travel Startups for 2026: BizTrip AI - PhocusWire](https://www.phocuswire.com/hot-25-travel-startups-2026-biztrip)
- [Sabre and BizTrip AI Partnership](https://www.prnewswire.com/news-releases/sabre-and-biztrip-ai-announce-strategic-partnership-to-deliver-agentic-ai-solutions-for-global-corporate-travel-market-302661145.html)
- [Otto Raises $6M - Business Travel News](https://www.businesstravelnews.com/Technology/Otto-Raises-6M-for-AI-Assisted-Unmanaged-Biz-Travel)
- [Natural Launches with $9.8M - BusinessWire](https://www.businesswire.com/news/home/20251023151615/en/Fintech-Natural-Launches-With-$9.8M-Seed-Round-to-Power-Agentic-Payments)
- [Nekuda Raises $5M - BusinessWire](https://www.businesswire.com/news/home/20250514808097/en/Nekuda-Raises-$5M-Led-by-Madrona-Together-with-Amex-Ventures-and-Visa-Ventures-to-Power-Agentic-Payments)
- [Circuit & Chisel Secures $19.2M - PR Newswire](https://www.prnewswire.com/news-releases/circuit--chisel-secures-19-2-million-and-launches-atxp-a-web-wide-protocol-for-agentic-payments-302562331.html)
- [Catena Labs Raises $18M - PYMNTS](https://www.pymnts.com/news/investment-tracker/2025/catena-labs-raises-18-million-to-build-ai-native-financial-institution-for-agents/)
- [Skyfire Use Cases](https://skyfire.xyz/use-case/)
- [Payman AI](https://paymanai.com/)
- [Crossmint AI Agent Payments](https://www.crossmint.com/solutions/ai-agents)
- [Coinbase Agentic Wallets](https://www.coinbase.com/developer-platform/discover/launches/agentic-wallets)
- [Ramp Agent Cards Launch](https://stabledash.com/news/2026-03-11-ramp-launches-agent-cards-to-enable-secure-autonomous-ai-spending)
- [Paid Raises $10.8M - PYMNTS](https://www.pymnts.com/news/artificial-intelligence/2025/paid-raises-10-million-dollars-scale-financial-infrastructure-ai-agents/)
- [Sola Raises $17.5M](https://www.startuphub.ai/ai-news/funding-round/2025/sola-raises-17-5m-series-a-for-ai-process-automation/)
- [Beam AI](https://beam.ai/)
- [Lyzr Deploy AI Agents](https://www.lyzr.ai/)
- [Fairmarkit Autonomous Sourcing](https://www.fairmarkit.com/)
- [Zip Debuts 50 AI Agents - VentureBeat](https://venturebeat.com/ai/zip-debuts-50-ai-agents-to-kill-procurement-inefficiencies-openai-is-already-on-board)
- [Levelpath Raises $55M](https://www.levelpath.com/articles/levelpath-raises-additional-55m-to-bring-ai-native-procurement-to-the-enterprise/)
- [Omnea Raises $50M](https://www.omnea.co/blog/series-b-announcement)
- [Stripe Agentic Commerce Suite](https://stripe.com/blog/agentic-commerce-suite)
- [Mastercard Start Path Agentic Commerce - PYMNTS](https://www.pymnts.com/mastercard/2026/mastercard-expands-startup-engagement-program-to-include-agentic-commerce/)
- [Visa Intelligent Commerce Partners](https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.21961.html)
- [Firmly Agentic Commerce Platform - PYMNTS](https://www.pymnts.com/artificial-intelligence-2/2025/firmly-launches-platform-that-eases-merchant-adoption-of-agentic-commerce/)
- [Rye Universal Checkout](https://rye.com/)
- [Nevermined AI Payments](https://nevermined.ai/)
- [PolicyLayer](https://www.policylayer.com/)
- [Openfort Agent Wallets](https://www.openfort.io/solutions/ai-agents)
- [AgentaOS / Agentokratia](https://agentaos.ai/)
- [Sponge YC Launch](https://www.ycombinator.com/launches/PTD-sponge-financial-infrastructure-for-the-agent-economy)
- [Fellou AI Browser](https://fellou.ai/)
- [Browserbase](https://www.browserbase.com/)
- [Helicone AI](https://www.helicone.ai/)
- [Composio](https://composio.dev/)
- [n8n AI Workflows](https://n8n.io/ai/)
- [Activepieces](https://www.activepieces.com/)
- [Browser Use](https://browser-use.com/)
- [Y Combinator Agent AI Batches - PitchBook](https://pitchbook.com/news/articles/y-combinator-is-going-all-in-on-ai-agents-making-up-nearly-50-of-latest-batch)
- [Agentic Commerce Landscape - Rye Blog](https://rye.com/blog/agentic-commerce-startups)
- [CB Insights Agentic Commerce Market Map](https://www.cbinsights.com/research/report/agentic-commerce-market-map/)
- [AI Agent Payments Landscape 2026 - Proxy](https://www.useproxy.ai/blog/ai-agent-payments-landscape-2026)
- [Privacy.com AI Agent Payment Solutions Compared](https://www.privacy.com/blog/payment-solutions-ai-agents-2026-compared)
- [Daydream $50M Seed - TechCrunch](https://techcrunch.com/2024/06/20/former-stitch-fix-coo-julie-bornstein-secures-50m-to-build-a-new-age-e-commerce-search-engine/)
- [Nyne - TechCrunch](https://techcrunch.com/2026/03/13/nyne-founded-by-a-father-son-duo-gives-ai-agents-the-human-context-theyre-missing/)
- [HyperExpense](https://www.hyperexpense.com/)
- [Mindtrip + PayPal + Sabre](https://www.hotelmanagement.net/tech/sabre-paypal-and-mindtrip-partner-launch-agentic-ai-travel-booking-platform)
