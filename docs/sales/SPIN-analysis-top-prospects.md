# Sardis SPIN Analysis: Top 50 Prospect Companies

**Date:** March 16, 2026
**Prepared for:** Sardis Launch Sales Campaign
**Framework:** SPIN (Situation, Problem, Implication, Need-Payoff)

---

# TIER 1 -- HIGHEST PRIORITY (Travel + Agent Platforms)

---

## 1. BizTrip AI (biztrip.ai)

### S -- Situation

- **Product:** AI-powered corporate travel intelligence platform that replaces fragmented booking tools with a conversational, policy-smart assistant. Their proprietary Travel LLM and multi-agent platform orchestrates decisions across policy, budget, supplier content, traveler preferences, and payments in real time.
- **Current payment infrastructure:** Relies on Sabre GDS integration for booking and ticketing. Payment flow is: booking -> approval -> ticketing -> expense handoff. They integrate with existing TMC (Travel Management Company) payment rails, meaning the TMC (e.g., Cain Travel) is the merchant of record and handles actual card charging. BizTrip itself does NOT process payments -- it hands off to the TMC layer.
- **Stage:** Pre-seed ($2.5M total across 3 tranches). Led by AI Fund (Andrew Ng), RRE Ventures, with Sabre as strategic investor. Enterprise pilots underway, GA planned Q2 2026.
- **Team:** Founded by Tom Romary (ex-Yapta founder, acquired by Coupa; ex-SVP Deem; ex-VP Marketing Alaska Airlines). Small team, likely 10-15 people.
- **Tech stack:** Proprietary Travel LLM, multi-agent architecture, Sabre GDS integration, calendar connectors.

### P -- Problem

- **Payment gap:** BizTrip's agents can FIND and RECOMMEND travel options, but cannot autonomously BOOK and PAY. The handoff to TMC for payment creates friction, delays, and drops the "agentic" promise.
- **Manual steps:** Every booking still requires human approval of payment credentials, manual entry of corporate card details into TMC systems, and reconciliation between what the agent recommended vs. what was actually booked.
- **Enterprise blocker:** Large enterprises want end-to-end automation -- agent finds flight, checks policy, books, pays, and files expense report -- all without human intervention. BizTrip can do everything EXCEPT the pay step.
- **Policy enforcement on spend:** Their Travel LLM understands policy in natural language, but has no way to enforce spending limits at the payment layer. An approved $500 hotel booking could be changed to $800 between approval and ticketing.

### I -- Implication

- **Revenue at risk:** Without end-to-end booking+payment, BizTrip is a "recommendation engine" not a "travel agent." This limits their value proposition and pricing power vs. incumbents like Navan ($9.4B valuation) that own the full stack.
- **Enterprise deals stalling:** Enterprise pilots will hit a wall when CFOs ask "but who controls the actual spend?" BizTrip has to say "your existing TMC does" -- which means they're a layer, not the platform.
- **Competitive risk:** If Navan, TripActions, or SAP Concur add similar AI recommendation capabilities (which they will), BizTrip's only differentiation is the AI layer -- without payment control, they're easily replicated.
- **GA timeline risk:** Q2 2026 GA with no payment autonomy means launching an incomplete product.

### N -- Need-Payoff

- **Full autonomy:** Sardis gives BizTrip's agents the ability to hold corporate funds in non-custodial wallets with natural language spending policies ("max $500/night hotels, only Marriott/Hilton, no resort fees") and execute bookings autonomously.
- **Revenue unlock:** Moves BizTrip from "AI recommendation" ($5-10/user/month) to "AI travel management" ($50-100/user/month) -- 10x pricing power.
- **Enterprise readiness:** Kill switches, audit trails, and policy enforcement at the payment layer is exactly what enterprise CFOs need to greenlight agent-initiated spend.
- **Competitive moat:** BizTrip + Sardis = the only AI travel platform where the agent can actually spend money safely. Neither Navan nor Concur has this.

### Outreach Strategy

- **Best contact:** Tom Romary, CEO & Co-Founder
- **Best channel:** LinkedIn DM (active poster about corporate travel AI) or warm intro through RRE Ventures / AI Fund network
- **Opening line:** "Tom, I saw BizTrip's Sabre partnership announcement -- congrats. I'm curious: when your agent finds the perfect policy-compliant flight, what happens at the actual booking and payment step? Is that still going through the TMC?"
- **Discovery questions:**
  1. "How do your enterprise pilot customers currently handle the payment step after your agent recommends a booking?"
  2. "Have any enterprise prospects asked about giving your AI agent direct spending authority with guardrails?"
  3. "What percentage of agent-recommended bookings actually get completed vs. dropped because of friction in the payment/approval handoff?"
  4. "How much engineering time has your team spent trying to integrate with TMC payment systems?"
- **What NOT to say:** Avoid "blockchain," "crypto," "USDC," "Web3." Frame everything as "payment infrastructure" and "spending controls." BizTrip's world is GDS, TMCs, and corporate cards.

---

## 2. Otto (ottotheagent.com)

### S -- Situation

- **Product:** AI travel assistant that connects to your calendar, learns preferences, and plans full trips (flights, hotels, loyalty programs). Built on Spotnana's modern travel infrastructure. Targets unmanaged business travel at SMBs.
- **Current payment infrastructure:** Built on Spotnana, which supports central, virtual, individual, and personal cards, cash payments, direct billing, delayed invoicing, and split payments. Spotnana/Stripe processes credit card payments and passes cash payments to airlines, with TMC as merchant of record.
- **Stage:** Seed ($6M from Madrona Venture Group + Direct Travel + angels). Free for individual travelers and SMBs for first 12 months (since Dec 2025). Corporate travel pilots started.
- **Team:** Founded by Michael Gulmann (CEO, ex-CPO Egencia, ex-SVP Expedia Group) and Chundong Wang. Steve Singh (founder of SAP Concur, Madrona MD) serves as Executive Chairman. ~15-25 people estimated.
- **Tech stack:** Built on Spotnana's API infrastructure (NDC fares, GDS inventory, direct supplier APIs). Calendar integration, preference learning engine.

### P -- Problem

- **Spotnana dependency:** Otto's payment capabilities are entirely dependent on Spotnana's payment infrastructure. This means Otto has zero control over payment policies, spending limits, or transaction governance.
- **SMB payment chaos:** Unmanaged business travelers at SMBs typically use personal cards and expense later, or shared company cards with no per-trip controls. Otto can recommend but cannot enforce spend discipline.
- **No agent-level spending controls:** When Otto's AI books a trip, it uses whatever payment method the user has on file. There's no way to say "this AI agent can spend up to $2,000 on this trip, only on flights and hotels."
- **Free model unsustainable:** Currently free -- they need to monetize. Payment infrastructure could be a revenue enabler.

### I -- Implication

- **Corporate pilot risk:** As Otto moves from individual travelers to corporate pilots, companies will demand spending controls, audit trails, and policy enforcement on agent-initiated bookings. Otto can't deliver this through Spotnana alone.
- **Revenue model gap:** Without payment-layer monetization (interchange, transaction fees, premium controls), Otto's path to revenue is limited to subscription fees on a free-to-start product.
- **Competitive squeeze:** Navan, TripActions, and AmTrav all offer integrated payment+booking. Otto's differentiation is AI quality, but that's temporary -- if they don't control payments, they're a feature, not a platform.
- **Trust gap:** Enterprise customers won't let an AI agent autonomously book $3,000 flights without granular spending controls and real-time audit trails.

### N -- Need-Payoff

- **SMB-friendly payment infrastructure:** Sardis provides virtual cards with per-trip budgets and merchant category restrictions -- perfect for the unmanaged SMB travel segment Otto targets.
- **Corporate upgrade path:** When Otto converts free users to paid corporate accounts, Sardis spending policies ("employees can book up to $X per trip, only approved airlines") become the enterprise feature that justifies premium pricing.
- **New revenue stream:** Interchange revenue from Sardis virtual cards gives Otto a payment-layer revenue stream alongside subscriptions.
- **Differentiation:** "The only AI travel assistant where the agent can pay for your trip with built-in spending controls" -- a tagline that sells itself.

### Outreach Strategy

- **Best contact:** Michael Gulmann, CEO & Co-Founder (or Steve Singh, Executive Chairman for a higher-level intro)
- **Best channel:** LinkedIn (Michael is active) or warm intro through Madrona Venture Group
- **Opening line:** "Michael, I noticed Otto moved from beta to public launch in December -- congrats. I'm curious about something: when Otto autonomously books a flight, how does the payment side work? Is the traveler still entering their card details?"
- **Discovery questions:**
  1. "What's the biggest friction point your corporate pilot customers have raised about the booking-to-payment flow?"
  2. "How do SMB customers currently handle spending limits when Otto books on their behalf?"
  3. "Has anyone asked about giving Otto a dedicated budget or virtual card rather than using an employee's personal card?"
  4. "What percentage of Otto's recommended bookings get abandoned because of payment friction?"
- **What NOT to say:** Avoid crypto/blockchain language. Otto's world is Spotnana, GDS, corporate cards. Frame as "virtual card infrastructure" and "AI spending controls."

---

## 3. Sola AI (sola.ai)

### S -- Situation

- **Product:** Agentic process automation platform (YC company) that lets business users record a process once, and Sola turns it into a self-healing bot. Focus areas: invoice reconciliation, order entry, file verification, payment processing -- primarily in legal, financial services, healthcare, and logistics.
- **Current payment infrastructure:** Sola automates AP/AR, cash application, invoice processing, payment reconciliation. But Sola's bots INTERACT with existing payment systems (entering data into ERP, clicking buttons in banking portals) via computer vision and LLMs -- they don't hold or control funds directly.
- **Stage:** Series A ($17.5M led by a16z, $21M total). Fortune 100 companies, AmLaw 100 law firms, billion-dollar healthcare and logistics providers as customers.
- **Team:** Founded by team with strong RPA background. Backed by Sarah Guo at Conviction (seed) and a16z (Series A). Growing engineering and GTM teams.
- **Tech stack:** Computer vision + LLMs for screen interaction, self-healing agents, API integration layer.

### P -- Problem

- **Observe-only problem:** Sola bots can PROCESS invoices and ENTER payment data, but they can't actually EXECUTE payments. They're keyboard-and-mouse automators, not financial actors. When a bot processes an invoice and needs to trigger a $50,000 vendor payment, it still needs a human to authorize the actual fund transfer.
- **Payment error risk:** Bots interacting with payment UIs via screen scraping can misclick, enter wrong amounts, or fail to detect UI changes -- with real financial consequences.
- **No spending governance:** When Sola bots process hundreds of invoices per day, there's no aggregate spending control. A bot could approve $5M in invoices in a day with no circuit breaker.
- **Compliance gap:** Fortune 100 customers in financial services need SOX-compliant audit trails for automated payment processing. Screen-scraping-based automation doesn't provide this.

### I -- Implication

- **Revenue ceiling:** Sola can charge for process automation, but the highest-value automation (actual payment execution) remains off-limits. Payment processing is 10x more valuable than data entry.
- **Enterprise expansion blocked:** Financial services customers (Sola's core via a16z's network) need payment automation with compliance guarantees. Without it, Sola can only automate the "front half" of financial workflows.
- **Liability exposure:** If a Sola bot misclicks and sends $500K to the wrong vendor, who's liable? Without proper payment controls, the liability sits with the customer, making them reluctant to automate payment-adjacent workflows.
- **Competitive risk:** UiPath and Automation Anywhere are both adding payment capabilities to their RPA platforms.

### N -- Need-Payoff

- **Payment execution layer:** Sardis gives Sola bots the ability to actually hold and disburse funds with policy controls ("max $10K per vendor per day, only approved vendors, require 2-of-3 approval above $50K").
- **Compliance-ready:** Sardis audit trails provide SOX-compliant transaction logging for every bot-initiated payment -- critical for Fortune 100 financial services customers.
- **10x value creation:** Moving from "process automation" to "payment automation" could increase Sola's deal sizes by 5-10x.
- **Kill switch:** Sardis kill switches let customers instantly freeze all bot-initiated payments if something goes wrong -- the safety net enterprises need.

### Outreach Strategy

- **Best contact:** CEO/Founder (search for Sola AI founding team on LinkedIn)
- **Best channel:** Warm intro through a16z network (Sardis has advisory connections to crypto/fintech VCs) or YC alumni network
- **Opening line:** "I saw Sola's work automating invoice reconciliation for Fortune 100 companies -- impressive. Quick question: when your bots process an invoice and determine it should be paid, what happens next? Does a human still have to authorize the actual payment?"
- **Discovery questions:**
  1. "What's the most common reason a customer's automated workflow stops short of actually executing a payment?"
  2. "Have any of your financial services customers asked about extending automation all the way through to fund disbursement?"
  3. "How do your enterprise customers currently handle spending limits and approval thresholds for bot-processed payments?"
  4. "What would it mean for your deal sizes if Sola could automate the full invoice-to-payment cycle, not just invoice-to-approval?"
- **What NOT to say:** Avoid crypto terminology entirely. Sola's world is ERP, AP/AR, and enterprise process automation. Frame as "payment execution infrastructure" with "compliance-grade audit trails."

---

## 4. Lyzr (lyzr.ai)

### S -- Situation

- **Product:** Enterprise agentic AI platform ("Agent Studio") that lets developers and no-code users build, deploy, and manage AI agents for banking, insurance, customer support, procurement, HR, marketing, and sales. Positioned as the "Agentic Operating System" for enterprises.
- **Current payment infrastructure:** Lyzr has built banking-specific agents (Amadeo) for customer onboarding, KYC processing, AML, claims processing, and billing workflows. They have a case study automating billing workflows at a global insurance firm. They also have an "AI Loan Servicing Agent" and "Payment Receipt Verification" agents. However, these agents VERIFY and PROCESS payment data -- they don't hold or move money.
- **Stage:** Series A+ ($23.1M total, $14.5M latest round led by Accenture at $250M valuation). 300%+ QoQ revenue growth. 15,000+ builders, 1,800+ organizations. Expect profitability by April 2026.
- **Team:** Founded by Siva Surendira (CEO, ex-APAC #1 AI/ML startup sold to LTI), Ankit Garg, and Anirudh Narayan (CGO). ~40-60 people. Offices in Jersey City.
- **Tech stack:** Low-code Agent Studio, pre-built agent blueprints, multi-LLM orchestration, enterprise integration layer.

### P -- Problem

- **Agents that verify but can't transact:** Lyzr's banking agents can verify payment receipts, process KYC, and reconcile billing -- but they cannot initiate or execute actual financial transactions. The payment receipt verification agent reads receipts but can't send money.
- **Banking customer demand:** Accenture invested specifically to bring agentic AI to banking and insurance. These industries need agents that can execute transactions, not just process documents.
- **Platform limitation:** Lyzr provides the agent framework but no financial infrastructure. Every customer building a finance-related agent has to bring their own payment rails, which is a significant integration burden.
- **Compliance gap for financial agents:** Banking/insurance agents handling financial data need SOC2, PCI-DSS, and regulatory compliance at the payment layer. Lyzr provides agent infrastructure compliance but not payment compliance.

### I -- Implication

- **Capped addressable market:** Without payment execution, Lyzr's banking/insurance vertical (their fastest-growing, Accenture-backed segment) is limited to back-office document processing rather than front-office transaction automation.
- **Accenture relationship at risk:** Accenture invested for banking/insurance use cases. If Lyzr can't deliver end-to-end financial automation (including payments), Accenture may look elsewhere or build in-house.
- **Deal size limitations:** Process automation deals are $50-100K/year. Payment automation deals in banking are $500K-2M/year. Without payment capabilities, Lyzr leaves 10x revenue on the table.
- **Competitive threat from full-stack providers:** Companies like Sola (with a16z backing) and dedicated financial AI platforms are adding payment capabilities.

### N -- Need-Payoff

- **Payment-enabled agents:** Sardis would let Lyzr's Agent Studio users build agents that can hold funds, execute payments, and enforce spending policies -- turning document-processing agents into transaction-executing agents.
- **Banking vertical dominance:** "Lyzr + Sardis = the only low-code platform where you can build AI banking agents that actually move money" -- massive competitive advantage.
- **Accenture amplification:** Accenture can sell "payment-capable AI agents" to their banking/insurance clients at premium pricing, expanding both Lyzr and Sardis reach.
- **10x deal sizes:** Moving from process automation to payment automation unlocks $500K-2M enterprise deals in financial services.

### Outreach Strategy

- **Best contact:** Siva Surendira, CEO & Founder (active on LinkedIn, speaks at FinovateFall)
- **Best channel:** LinkedIn DM or email (s***@lyzr.ai). Could also approach through Accenture Ventures connection or YC network if available.
- **Opening line:** "Siva, congrats on the Accenture round and the $250M valuation -- incredible growth. I read your case study on automating billing workflows at the insurance firm. Curious: when the agent determines a payment should be made, what happens at the actual fund disbursement step?"
- **Discovery questions:**
  1. "How are your banking customers currently handling the gap between agent-processed invoices and actual payment execution?"
  2. "Has Accenture flagged any specific requirements around agent-initiated payments in their banking deployments?"
  3. "What's the most common request from your Agent Studio builders when they're working on financial workflow agents?"
  4. "How much additional revenue per customer do you think you could capture if your agents could execute payments directly?"
- **What NOT to say:** Avoid "crypto," "stablecoin," "on-chain." Frame as "payment infrastructure for AI agents" and "compliant financial execution layer for enterprise." Lyzr's world is enterprise SaaS, banking APIs, and Accenture consulting.

---

## 5. Beam AI (beam.ai)

### S -- Situation

- **Product:** Agentic automation platform with 200+ ready-made agent templates for back-office tasks (data entry, extraction, customer support, HR onboarding, financial workflows). Targets Fortune 500 and mid-market enterprise.
- **Current payment infrastructure:** No native payment capability. Agents automate operational workflows but don't handle financial transactions. Customers in private equity, HR, and sales operations.
- **Stage:** Seed ($132K from Next Commerce Accelerator -- very early stage). $4.5M revenue (as of June 2025). 41 employees. Offices in Berlin, Abu Dhabi, New York, Karachi.
- **Team:** Founded by Jonas Diezun (CEO, ex-co-founder Razor Group, helped build Konux into unicorn) and Aqib Ansari (AI lead). Global team.
- **Tech stack:** AI agent templates, enterprise integration layer, custom agent builder.

### P -- Problem

- **Revenue vs. funding mismatch:** $4.5M revenue on only $132K raised is impressive bootstrapping, but signals they lack the capital to build payment infrastructure internally.
- **Template gap:** 200+ templates but none handle financial transactions. Every finance-adjacent template stops at "extract data" or "generate report" -- never "execute payment."
- **Private equity use case limitation:** Beam's PE use case (fund management automation) requires agents that can process capital calls, distributions, and fee calculations -- all of which eventually need payment execution.
- **Enterprise upmarket challenge:** Moving from mid-market to Fortune 500 requires compliance-grade financial automation, which Beam can't offer without payment rails.

### I -- Implication

- **Template ceiling:** Without payment-enabled templates, Beam's 200+ library misses the entire "financial automation" category -- the highest-value RPA use case.
- **PE vertical incomplete:** Private equity firms automating fund management need end-to-end automation including capital movements. Without payment capability, Beam serves only the "paper-pushing" part.
- **Pricing pressure:** Back-office data entry automation commoditizes quickly (UiPath, Automation Anywhere). Payment automation would create sustainable differentiation.
- **Fundraising challenge:** With $132K raised, Beam may struggle to build payment infrastructure. A partnership is the pragmatic path.

### N -- Need-Payoff

- **Financial automation templates:** Sardis enables Beam to add payment-capable templates (invoice payment, vendor payment, payroll disbursement, capital call processing) -- expanding their library into the most valuable automation category.
- **PE vertical completion:** Beam + Sardis = end-to-end fund management automation, from data extraction through capital movement.
- **Pricing uplift:** Payment-enabled templates command 3-5x higher pricing than data-entry templates.
- **Fundraising narrative:** "200+ automation templates including payment execution" is a much stronger Series A pitch than "200+ data entry templates."

### Outreach Strategy

- **Best contact:** Jonas Diezun, CEO & Co-Founder
- **Best channel:** LinkedIn DM (Jonas is active, Berlin/NYC based) or through the Konux/Razor Group network
- **Opening line:** "Jonas, I noticed Beam has a private equity fund management automation use case -- interesting vertical. When your agents process a capital call or distribution, what happens at the actual money movement step?"
- **Discovery questions:**
  1. "How often do your enterprise customers ask for agents that can go beyond data processing to actually execute financial transactions?"
  2. "In your PE fund management use case, how is the gap between automated processing and actual capital movement handled today?"
  3. "What would adding payment-capable templates do to your average deal size?"
  4. "How much engineering time would it take to build payment infrastructure from scratch, and is that something you've considered?"
- **What NOT to say:** Avoid crypto/blockchain. Frame as "payment execution for automation templates" and "financial transaction infrastructure."

---

# TIER 2 -- STRONG FIT (Procurement + Expense + Browser)

---

## 6. Fairmarkit (fairmarkit.com)

### S -- Situation

- **Product:** AI-powered autonomous sourcing platform for enterprise procurement. Automates the entire RFQ/RFP/RFI process -- finding vendors, evaluating bids, awarding contracts. Multi-model AI network for adaptive sourcing.
- **Current payment infrastructure:** Fairmarkit handles sourcing and vendor selection but does NOT handle payment. After Fairmarkit awards a contract, payment goes through the customer's existing AP/ERP system (SAP, Oracle, Coupa). Fairmarkit is pre-payment in the procurement stack.
- **Stage:** Series C ($78M total from Insight Partners, GGV Capital, OMERS Growth Equity). Named to ProcureTech100. Gartner recognition. Mature product with enterprise customers.
- **Team:** Founded by Kevin Frechette (CEO, ex-IBM, ex-Dell), Victor Kushch (CTO), Tarek Alaruri. Boston-based, ~100-150 employees estimated.
- **Tech stack:** ML recommendation engine, adaptive RFx platform, ERP integrations (SAP, Oracle, Coupa, ServiceNow).

### P -- Problem

- **Ends at award, not payment:** Fairmarkit's "autonomous sourcing" stops at contract award. The actual purchase order issuance and payment still happens in legacy ERP/AP systems with manual processes.
- **Value leakage post-award:** After Fairmarkit saves 15% on sourcing, the payment process adds 5-10 business days of delay, manual PO creation, and potential errors -- eroding the efficiency gains.
- **No real-time spend controls:** Fairmarkit can enforce sourcing policies but cannot enforce payment policies. A sourced-at-$10K item could be invoiced at $12K with no automated detection.
- **"Tail spend" gap:** Their core use case is tail spend management, but tail spend payments are typically the most manual and error-prone.

### I -- Implication

- **Incomplete automation story:** Fairmarkit pitches "autonomous sourcing" but the autonomy ends at award. Enterprises increasingly want source-to-pay automation (see Zip's positioning).
- **Competitive threat from Zip:** Zip ($2.2B valuation, $371M raised) has moved from intake-to-pay including 50+ AI agents. Fairmarkit only covers source-to-award.
- **Revenue ceiling:** Source-only platforms are valued lower than source-to-pay platforms. Without payment capabilities, Fairmarkit's growth ceiling is significantly lower.
- **Customer churn risk:** If enterprises adopt platforms like Zip that offer end-to-end, they may deprioritize point solutions like Fairmarkit.

### N -- Need-Payoff

- **Source-to-pay completion:** Sardis enables Fairmarkit agents to not just award contracts but issue virtual cards or trigger payments to vendors with policy controls ("auto-pay approved vendors under $50K, require human approval above $50K").
- **Competitive response to Zip:** Fairmarkit + Sardis competes with Zip on source-to-pay, but with superior AI sourcing and non-custodial payment infrastructure.
- **Tail spend monetization:** Automated payment of tail spend items (the messiest, most manual payments) creates enormous efficiency gains and new revenue opportunities.
- **NRR improvement:** Adding payment capabilities deepens the platform's value, increasing net revenue retention.

### Outreach Strategy

- **Best contact:** Kevin Frechette, CEO & Co-Founder
- **Best channel:** LinkedIn (Kevin is active, posts about procurement AI frequently) or warm intro through Insight Partners
- **Opening line:** "Kevin, I read your AI Time Journal interview about defining agentic AI in procurement. You mentioned autonomous sourcing -- I'm curious: after Fairmarkit awards a contract autonomously, what does the payment process look like? Is that still manual through the customer's ERP?"
- **Discovery questions:**
  1. "What's the average time between Fairmarkit awarding a contract and the vendor actually getting paid?"
  2. "Have enterprise customers asked about extending Fairmarkit's automation from sourcing through to actual payment?"
  3. "How does Zip's 'intake-to-pay' positioning affect your competitive conversations?"
  4. "What would it mean for your pricing if Fairmarkit could offer source-to-pay automation?"
- **What NOT to say:** Avoid crypto/blockchain. Procurement world speaks ERP, AP automation, PO processing, and virtual cards.

---

## 7. HyperExpense / Hyper (hyperexpense.com)

### S -- Situation

- **Product:** AI-native autonomous expense management platform. TARS engine reads expense policies in plain English and enforces them dynamically. Also offers ExpenseGPT (world's first T&E agent). Additionally runs Hypercard, a consumer credit card (Amex network) that's a hybrid personal/corporate card.
- **Current payment infrastructure:** Has actual payment infrastructure through Hypercard (Amex network). TARS enforces policies on transactions made with Hypercard. Integrations with leading ERP and accounting systems. Automated GL code mapping, instant expense syncing.
- **Stage:** Raised $4.5M (led by Sam Altman). Forbes 30 Under 30 founders (2024). Customers include Lyft and Whatnot.
- **Team:** Founded by Marc Baghadjian and Nikolas Ioannou. NYC-based. Small team (~10-20 estimated).
- **Tech stack:** TARS AI engine, Hypercard (Amex network credit card), ExpenseGPT agentic T&E, ERP integrations.

### P -- Problem

- **Card-dependent model:** Hyper's payment capabilities are tied to their Hypercard (Amex network). This limits them to merchants that accept Amex and to users willing to carry another card.
- **Agent spending limits:** ExpenseGPT can review and validate expenses after the fact, but it can't enforce spending limits BEFORE a purchase is made. The agent audits -- it doesn't control.
- **No multi-rail capability:** Hyper is card-only. They can't handle wire transfers, vendor payments, international transactions, or digital-first payment methods.
- **Scale challenge:** Running a card program (issuing, compliance, disputes, fraud) is enormously expensive and complex for a startup with $4.5M raised.

### I -- Implication

- **Amex acceptance gap:** ~30% of merchants don't accept Amex, creating dead zones in the expense management flow.
- **Post-hoc vs. pre-emptive:** Auditing expenses AFTER they're made (current model) is less valuable than PREVENTING out-of-policy spend before it happens.
- **Card program costs:** Issuing and managing physical/virtual cards requires significant capital, compliance infrastructure, and operational overhead.
- **Enterprise mismatch:** Enterprise customers need programmatic virtual cards with per-transaction controls, not consumer-grade credit cards.

### N -- Need-Payoff

- **Pre-transaction enforcement:** Sardis spending policies enforce limits BEFORE a transaction, not after. "This agent can spend up to $200 on meals, only at restaurants, not bars" -- enforced at payment time.
- **Multi-rail expansion:** Sardis adds USDC on-chain payments and bank account transfers alongside card rails, eliminating the Amex acceptance gap.
- **Infrastructure relief:** Rather than running their own card program, Hyper could use Sardis's virtual card infrastructure (Stripe Issuing-backed) and focus on their AI policy engine.
- **Enterprise upgrade:** Sardis's non-custodial wallets with kill switches and audit trails give ExpenseGPT the enterprise-grade financial controls it needs.

### Outreach Strategy

- **Best contact:** Marc Baghadjian, CEO & Co-Founder
- **Best channel:** LinkedIn or Twitter/X (Marc is active, Forbes 30 Under 30). Direct email also possible.
- **Opening line:** "Marc, I saw the Hypercard + TARS combination -- really clever to pair an AI policy engine with a card program. I'm curious: does TARS enforce spending rules before a purchase is made, or does it catch violations after the transaction?"
- **Discovery questions:**
  1. "How much of your team's time goes into managing the Hypercard card program vs. building the TARS AI engine?"
  2. "What happens when an employee tries to make a purchase at a merchant that doesn't accept Amex?"
  3. "Have enterprise customers asked about giving AI agents (not just employees) their own spending wallets with controls?"
  4. "If you could offload the card infrastructure and focus purely on the AI policy engine, would that change your product roadmap?"
- **What NOT to say:** Hyper is fintech-native, so you CAN mention virtual cards and payment rails. Still avoid "crypto" unless they bring it up. Frame as "programmable payment infrastructure" that complements TARS.

---

## 8. Fellou (fellou.ai)

### S -- Situation

- **Product:** World's first agentic browser -- an AI-native browser that doesn't just search, it acts. Can navigate websites, fill forms, complete purchases, draft emails, schedule meetings. Built on Eko 2.0 open-source framework. 1M+ users since April 2025.
- **Current payment infrastructure:** None. Fellou agents can navigate to checkout pages and fill in payment forms using the user's stored credentials, but there's no programmatic payment infrastructure. The user's credit card number is being entered by an AI bot into website forms -- major security risk.
- **Stage:** Raised $40.4M (LongRiver Investments). 1M+ users. Freemium model. Silicon Valley-based.
- **Team:** Founded by Dominic Xie (CEO, Forbes 30 Under 30 Asia 2021). Global team of LLM and browser experts.
- **Tech stack:** Eko 2.0 framework, proprietary browser engine, LLM agents, computer vision.

### P -- Problem

- **Credit card exposure:** When Fellou's agent completes a purchase, it's typing actual credit card numbers into web forms. This is a massive PCI-DSS violation and security risk. One screenshot, one logging error, and the card is compromised.
- **No spending controls:** Users can tell Fellou "buy me this product on Amazon" but there's no way to set limits ("spend up to $100, only on Amazon, not on third-party sellers").
- **No audit trail:** When Fellou makes a purchase, there's no structured record of what was bought, how much was spent, and whether it was authorized. It's buried in browser history.
- **Enterprise blocker:** No enterprise will let an AI browser agent use corporate cards without spending controls, audit trails, and kill switches.

### I -- Implication

- **Security liability:** A single incident where Fellou exposes a user's credit card could destroy trust and trigger regulatory scrutiny. This is an existential risk.
- **Enterprise market locked out:** 1M consumer users but zero enterprise revenue. Without payment security and controls, the enterprise market (where the real money is) remains inaccessible.
- **Monetization challenge:** Freemium with no payment infrastructure means Fellou captures zero value from the transactions its agents complete. They're driving GMV for Amazon, not for Fellou.
- **Competitive risk:** Other browser agents (Browserbase/Stagehand, MultiOn, OpenAI Operator) are also exploring purchase capabilities. First to solve payment security wins enterprise.

### N -- Need-Payoff

- **Secure agent payments:** Sardis virtual cards give Fellou's agent a disposable, single-use card number for each purchase -- no need to type real credit card numbers into web forms. Eliminates PCI-DSS risk.
- **Purchase controls:** "This browser agent can spend up to $500/day, only at Amazon and Walmart, no subscriptions" -- enforced at the payment layer.
- **Transaction audit trail:** Every Fellou purchase logged with merchant, amount, timestamp, and agent session ID. Enterprise-grade accountability.
- **Monetization unlock:** Fellou can charge for "secure agent shopping" with Sardis-powered virtual cards, creating a premium tier that captures transaction value.

### Outreach Strategy

- **Best contact:** Dominic Xie, Founder & CEO
- **Best channel:** LinkedIn or Twitter/X (Dominic is active, Silicon Valley based)
- **Opening line:** "Dominic, Fellou's browser automation is impressive -- 1M users is a huge milestone. I have a security question: when Fellou completes a purchase on behalf of a user, how do you handle the payment credentials? Is the agent entering the user's actual card number into the checkout form?"
- **Discovery questions:**
  1. "Have you received any enterprise inquiries about using Fellou for purchasing, and what security concerns did they raise?"
  2. "How do you currently handle the liability if a Fellou agent makes an unauthorized or incorrect purchase?"
  3. "What would it take for an enterprise to trust Fellou with their corporate purchasing?"
  4. "If Fellou's agent could use a secure, disposable virtual card for each purchase instead of the user's real card, would that change your product strategy?"
- **What NOT to say:** Avoid blockchain/crypto. Frame as "secure virtual cards for browser agents" and "PCI-compliant payment infrastructure."

---

## 9. Relevance AI (relevanceai.com)

### S -- Situation

- **Product:** AI agent "operating system" / workforce platform. No-code canvas for building teams of AI agents. 40,000+ agents registered in January 2025 alone. Focus on sales, marketing, recruitment, and operations.
- **Current payment infrastructure:** None. Relevance AI provides agent infrastructure (building, deploying, monitoring agents) but no financial capabilities. Agents can interact with tools (Slack, HubSpot, etc.) but cannot spend money.
- **Stage:** Series B ($37M total, $24M latest led by Bessemer Venture Partners). Growing fast. San Francisco + Sydney. Customers include Qualified, Activision, Safety Culture.
- **Team:** Co-founded by Daniel Vassilev (Co-CEO), Jacky Koh (Co-CEO), and Daniel Palmer. ~50-80 employees estimated.
- **Tech stack:** No-code Workforce canvas, multi-agent orchestration, 250+ integrations, visual builder.

### P -- Problem

- **Integration gap at the money layer:** Relevance AI integrates with 250+ tools but zero payment systems. When a sales agent closes a deal, it can update HubSpot but can't process payment. When a recruitment agent hires a contractor, it can't issue payment.
- **Customer demand for financial agents:** As companies build AI workforces, the natural next step is giving those workers budgets. Marketing agents need to buy ads, sales agents need to send gifts, procurement agents need to purchase supplies.
- **Platform completeness:** Competitors like Lyzr (banking agents) and CrewAI (enterprise workflows) are adding financial capabilities. Relevance AI risks being seen as "agents that can do everything except spend money."
- **40K agents, zero transactions:** 40,000+ registered agents with no ability to transact is a massive missed opportunity.

### I -- Implication

- **Revenue ceiling:** Without payment capabilities, Relevance AI's revenue is limited to platform subscription fees. Transaction-based revenue (the model that made Stripe a $95B company) is untapped.
- **Enterprise limitation:** Enterprise customers building AI workforces expect those workers to have financial capabilities (purchasing, invoicing, expense management).
- **Competitive pressure:** As Lyzr and others add financial agent capabilities, Relevance AI risks losing its "complete AI workforce" positioning.
- **Bessemer's expectations:** Bessemer invested for enterprise scale. Enterprise AI workforces need financial agency.

### N -- Need-Payoff

- **Financial agent toolkit:** Sardis integration lets Relevance AI users give their agents wallets, budgets, and spending policies -- completing the "AI workforce" vision.
- **Transaction revenue:** Platform fee + transaction fee = dramatically improved unit economics that Bessemer will love.
- **Enterprise unlock:** "Build AI workers that can actually spend money, safely" -- this is the feature that converts enterprise pilots to contracts.
- **40K agents x payments = massive GMV:** Even if 10% of agents handle $1K/month in transactions, that's $48M/year in GMV flowing through the platform.

### Outreach Strategy

- **Best contact:** Daniel Vassilev, Co-CEO & Co-Founder
- **Best channel:** LinkedIn (Daniel is active, Sydney/SF based) or warm intro through Bessemer Venture Partners
- **Opening line:** "Daniel, congrats on the Bessemer round -- 40,000 agents on the platform is an incredible milestone. I'm curious: as your customers build AI workforces, have any of them asked about giving their agents the ability to make purchases or manage budgets?"
- **Discovery questions:**
  1. "What's the most common request you get from customers who want their agents to do something that requires spending money?"
  2. "How do your marketing/sales agents handle tasks that involve financial transactions, like buying ad space or sending client gifts?"
  3. "Have you explored adding payment or financial capabilities to the Workforce canvas?"
  4. "What would it do to your enterprise conversion rate if AI agents on Relevance AI could safely handle budgets and make purchases?"
- **What NOT to say:** Avoid crypto/blockchain. Frame as "financial infrastructure for AI workforces" and "payment capabilities for your agent canvas."

---

## 10. Procure AI (procure.ai)

### S -- Situation

- **Product:** AI-native procurement platform covering sourcing, contracting, purchasing, and invoice management. 50+ AI agents across three categories: autonomous (execute independently), collaborative (assist humans), and ambient (proactive support).
- **Current payment infrastructure:** Integrates with existing procurement systems (ERP, AP) rather than replacing them. Agents process invoices and purchase orders but rely on customer's existing payment infrastructure for actual fund movement.
- **Stage:** Seed ($13M led by Headline, with C4 Ventures, Futury Capital). 4x revenue growth. 40+ employees across London, Paris, Frankfurt. Expanding from DACH to UK, Nordics, Benelux, France.
- **Team:** Founded by Konstantin von Bueren and Yves Bauer (both Co-CEOs). European-headquartered.
- **Tech stack:** Amazon Web Services, Figma, Canny, Scala, Lua, Google Analytics. AI-native from ground up.

### P -- Problem

- **50 agents, zero payment capability:** Procure AI has autonomous agents for spot-buying, tactical sourcing, and quote-to-order intake, but none can execute payments. "Autonomous Spot-Buy" that can't actually pay is only semi-autonomous.
- **European payment complexity:** Operating across DACH, UK, Nordics, Benelux means dealing with multiple currencies, SEPA transfers, varying VAT requirements. Current ERP-dependent payment approach doesn't scale.
- **Integration burden:** Each customer's ERP has different payment capabilities and APIs. Procure AI agents must be customized per customer's payment infrastructure.
- **Speed-to-value gap:** Procure AI claims 40% reduction in procurement times, but the payment step (3-10 business day AP cycles) adds back most of that time.

### N -- Need-Payoff

- **True autonomous spot-buy:** Sardis-powered virtual cards let Procure AI's agents actually complete purchases autonomously -- buy office supplies, pay for software licenses, order equipment -- with built-in spending controls.
- **European multi-currency:** Sardis multi-rail support (USDC + virtual cards) simplifies cross-border payments across Procure AI's European footprint.
- **ERP-independent payments:** Instead of integrating with each customer's ERP for payments, Procure AI agents use Sardis wallets with policy controls. Simpler integration, faster time-to-value.
- **Differentiation in crowded market:** Procurement AI is crowded (Fairmarkit, Zip, Tonkean, Levelpath). "50 agents that can actually pay vendors" is unique differentiation.

### Outreach Strategy

- **Best contact:** Konstantin von Bueren or Yves Bauer, Co-Founders & Co-CEOs
- **Best channel:** LinkedIn (European founders, active in procurement community)
- **Opening line:** "Konstantin, congrats on the $13M round -- impressive 4x revenue growth. I read about your Autonomous Spot-Buy agent. When that agent identifies the best vendor and gets approval, who actually processes the payment?"
- **Discovery questions:**
  1. "How many different ERP/payment systems do you have to integrate with across your customer base?"
  2. "What does the payment step add in terms of cycle time after your agent has completed the sourcing?"
  3. "Have customers in the DACH region asked about multi-currency payment capabilities within your agents?"
  4. "What would 'truly autonomous' spot-buying look like -- from identification through payment -- and what's blocking it today?"
- **What NOT to say:** Avoid crypto. European procurement world speaks SEPA, wire transfers, PO processing. Frame as "payment infrastructure for autonomous procurement agents."

---

# TIER 3 -- SOLID PROSPECTS

---

## 11. Tonkean (tonkean.com)

### S -- Situation

- **Product:** AI-powered intake and process orchestration platform for enterprise procurement and legal teams. No-code builder with 100+ customizable processes. Recently launched Contracts Hub for contract lifecycle management. Acquired Cinch (AI spend intelligence).
- **Current payment infrastructure:** Orchestrates processes AROUND payment systems (SAP, Oracle, Coupa) but doesn't process payments. Tonkean sits on top of existing tech stacks, automating intake, triage, routing, and approval -- but hands off to AP for payment.
- **Stage:** $83.2M total funding, 4 rounds. $16.2M revenue, 73-93 employees. Acquired Cinch for EMEA expansion and spend intelligence.
- **Team:** Founded by Sagi Eliyahu (CEO). Tel Aviv + US presence.
- **Tech stack:** No-code orchestration, AI agents, 100+ ERP/procurement integrations.

### P -- Problem

- **Orchestration without execution:** Tonkean orchestrates the procurement process beautifully, but the actual payment step is a black hole -- it gets handed to the customer's AP system and Tonkean loses visibility.
- **Cinch acquisition incomplete:** Acquiring Cinch gave Tonkean spend INTELLIGENCE (analytics on what was spent). But spend intelligence without spend EXECUTION is only half the picture.
- **50% cycle time reduction claim incomplete:** Tonkean claims 50% procurement cycle time reduction, but the payment step (which Tonkean doesn't control) is often the longest part.

### N -- Need-Payoff

- **Orchestrate through payment:** Sardis lets Tonkean orchestrate the ENTIRE procurement flow, from intake through actual payment, with no handoff to legacy AP.
- **Spend intelligence + spend control:** Cinch analytics + Sardis payment policies = the only platform that both UNDERSTANDS spending patterns and CONTROLS them in real time.
- **Competitive positioning vs. Zip:** Zip's "intake to pay" positioning is Tonkean's biggest competitive threat. Sardis closes the gap.

### Outreach Strategy

- **Best contact:** Sagi Eliyahu, CEO & Co-Founder (active on LinkedIn and Twitter/X @esbsagi)
- **Opening line:** "Sagi, I saw the Cinch acquisition -- smart move combining spend intelligence with process orchestration. Question: after Tonkean orchestrates a procurement request through approval, what happens at the actual payment step? Does that still go to the customer's AP system?"
- **Discovery questions:**
  1. "How much of the procurement cycle time that Tonkean saves gets eaten back by the AP payment process?"
  2. "Has any customer asked about extending orchestration all the way through to payment execution?"
  3. "How does Zip's 'intake-to-pay' positioning affect your competitive conversations?"

---

## 12. Browserbase (browserbase.com)

### S -- Situation

- **Product:** Cloud-hosted headless browser infrastructure for AI agents. Serverless platform that spins up thousands of browsers in a fraction of a second. Open-source Stagehand SDK for browser automation. New Director tool for non-developers.
- **Current payment infrastructure:** None. Browserbase provides browser infrastructure; its customers build agents that may need to make purchases, but Browserbase doesn't offer payment rails.
- **Stage:** Series B ($40M led by Notable Capital at $300M valuation). 1,000+ customers, 50M sessions in 2025. Founded Jan 2024.
- **Team:** Founded by Paul Klein IV (CEO, ex-Twilio, ex-Mux). Key engineers from Twilio/Mux. Angels include Patrick Collison (Stripe CEO), Jeff Lawson (Twilio), Guillermo Rauch (Vercel).
- **Tech stack:** Chromium-based headless browsers, CDP (Chrome DevTools Protocol), Stagehand SDK, CAPTCHA handling, stealth mode.

### P -- Problem

- **Checkout is the endgame:** Browserbase powers browser agents that navigate the web, but the most valuable web action -- completing a purchase -- requires payment infrastructure that Browserbase doesn't provide.
- **Customer demand:** Browserbase's 1,000+ customers are building agents that need to buy things (e-commerce purchases, software subscriptions, booking travel). They all hit the same wall at checkout.
- **Security gap:** When Browserbase customers build purchasing agents, they're storing credit card numbers in their code or environment variables and having bots type them into checkout forms. This is a PCI nightmare.
- **Patrick Collison connection:** The CEO of Stripe is an angel investor. Payment infrastructure is in Browserbase's DNA but they haven't built it.

### N -- Need-Payoff

- **Checkout completion infrastructure:** Sardis MCP server integration gives Browserbase-powered agents secure virtual cards for every purchase -- no credit card numbers in code.
- **Platform revenue layer:** Browserbase charges per browser session. Adding payment capabilities (via Sardis integration) lets them charge for "checkout-capable sessions" at premium pricing.
- **Stagehand + Sardis SDK:** Natural integration between Stagehand (browser automation) and Sardis SDK (payment execution) creates the definitive "agent shopping" stack.
- **1,000 customers, instant distribution:** Every Browserbase customer building purchasing agents becomes a Sardis user.

### Outreach Strategy

- **Best contact:** Paul Klein IV, Founder & CEO
- **Best channel:** Twitter/X (Paul is active) or warm intro through Patrick Collison / Stripe network
- **Opening line:** "Paul, congratulations on the Series B -- $300M valuation in 16 months is incredible. I'm curious about a pattern I bet you see: when your customers build agents that need to complete a purchase on a website, how do they handle the payment step? Are they putting credit card numbers in their code?"
- **Discovery questions:**
  1. "What percentage of your customers are building agents that need to complete purchases or transactions?"
  2. "Has anyone asked about a secure way to handle payments within Browserbase sessions?"
  3. "What's the biggest security concern your customers raise about browser-based purchasing agents?"
  4. "If Stagehand had a built-in secure payment method for agent checkouts, would that be a feature your customers would pay premium for?"
- **What NOT to say:** Browserbase is developer-infrastructure. Speak their language: SDKs, APIs, MCP servers, developer experience. Avoid crypto unless they bring it up. The Patrick Collison connection means they understand payments deeply.

---

## 13. Shinkai

### S -- Situation

- **Product:** Open-source, local-first AI agent platform with native crypto payments (USDC, Coinbase x402). Built for on-chain AI agents that can earn, spend, and collaborate. Available on desktop and mobile.
- **Current payment infrastructure:** HAS native payment infrastructure -- USDC on-chain payments via Coinbase x402 protocol. Agents can charge for tasks, receive payments, and transact with other agents. 45,000+ installs.
- **Stage:** Backed by Coinbase Ventures, Circle Ventures, Naval Ravikant, Solana Ventures, Archetype, and more. Developed by dcSpark (experienced blockchain team across Ethereum, Solana, Cardano).
- **Team:** Co-founded by Nicolas Arqueros. dcSpark team with deep blockchain expertise.
- **Tech stack:** Peer-to-peer protocols, local AI inference, USDC payments, Coinbase x402, Shinkai AI Store.

### P -- Problem

- **Crypto-only limitation:** Shinkai agents can pay with USDC but can't use virtual cards, bank transfers, or traditional payment rails. This limits them to crypto-accepting merchants and services.
- **No fiat off-ramp:** When agents earn USDC, there's no easy way to convert to fiat for traditional business expenses.
- **Enterprise gap:** Enterprises won't deploy on-chain-only AI agents. They need multi-rail payment options (cards + bank + crypto).
- **KYC/compliance gap:** On-chain payments without KYC/AML compliance make Shinkai unusable for regulated industries.

### N -- Need-Payoff

- **Multi-rail upgrade:** Sardis adds virtual cards and bank transfers to Shinkai's existing USDC capabilities -- making agents that can pay ANYWHERE, not just on-chain.
- **Enterprise bridge:** Sardis KYC/AML compliance + kill switches make Shinkai agents enterprise-ready.
- **Fiat on/off-ramp:** Sardis's Coinbase Onramp integration provides seamless fiat-to-crypto-to-fiat conversion.
- **Complementary, not competitive:** Shinkai already understands agent payments. Sardis extends their capabilities to traditional rails.

### Outreach Strategy

- **Best contact:** Nicolas Arqueros, Co-Founder (or dcSpark team leads)
- **Best channel:** Twitter/X (crypto-native community) or GitHub (open-source collaboration)
- **Opening line:** "Nicolas, Shinkai's x402 integration for agent-to-agent payments is really forward-thinking. Question: when a Shinkai agent needs to pay for something that doesn't accept USDC -- like booking a hotel or buying software with a credit card -- what happens?"
- **Discovery questions:**
  1. "What percentage of transactions your agents need to make can actually be completed with USDC today?"
  2. "Have you had enterprise interest that stalled because they needed traditional payment rails alongside crypto?"
  3. "How do you handle KYC/AML requirements for agent-initiated transactions?"
- **What you CAN say:** Shinkai is crypto-native. You CAN say "USDC," "on-chain," "stablecoins," "multi-rail." Frame Sardis as complementing their crypto rails with card/bank rails.

---

## 14. Zip HQ (ziphq.com)

### S -- Situation

- **Product:** Agentic procurement orchestration platform. 50+ AI agents across procurement, finance, legal, IT, and security. $355B in spend processed, $6B+ in customer savings. Named Gartner Magic Quadrant Visionary.
- **Current payment infrastructure:** Zip offers "global payments" and "vendor cards" as part of their intake-to-pay platform. They have payment capabilities but these are optimized for enterprise procurement (PO-based payments) not for autonomous agent spending.
- **Stage:** Series D ($371M total at $2.2B valuation). 650+ employees. Customers include AMD, Mars, Discover, T-Mobile, OpenAI. Massive scale.
- **Team:** Founded by Rujul Zaparde (CEO, ex-FlightCar founder acquired by Mercedes, ex-Airbnb PM) and Lu Cheng (CTO, ex-Airbnb head of engineering). YC alumni.

### P -- Problem

- **Agent execution gap:** Zip has 50+ agents for procurement orchestration but their agents orchestrate PROCESSES (approvals, routing, compliance), not PAYMENTS. The actual payment execution still goes through traditional AP.
- **Speed of autonomous purchasing:** 30% of requests handled autonomously by agents by 2026 goal, but "handled" means "processed and approved" not "paid." The payment step still takes days.
- **No agent-to-agent payments:** Zip's agents work within their platform. They can't pay external agents, services, or APIs autonomously.

### I -- Implication

- **"Agentic" without agency:** Having 50 agents that can't spend money is like having 50 employees with no credit cards. The "agentic" branding overpromises.
- **Enterprise customers (OpenAI!) need more:** OpenAI is a Zip customer. OpenAI of all companies understands that agents need financial autonomy. This creates internal pressure for Zip to solve agent payments.

### N -- Need-Payoff

- **True agent financial autonomy:** Sardis gives Zip's 50+ agents actual spending capability with per-agent budgets and policies.
- **Instant procurement:** Agent identifies need -> sourcing -> approval -> INSTANT PAYMENT via Sardis virtual card. Reduces procurement cycle from weeks to minutes.
- **Revenue uplift:** Adding payment execution to their 50+ agents increases Zip's value per customer significantly.

### Outreach Strategy

- **Best contact:** Rujul Zaparde, CEO (or product leadership team)
- **Best channel:** Very large company ($2.2B) -- may need to target VP/Director level first. LinkedIn or warm intro through YC network.
- **Opening line:** "Rujul, Zip's 50+ agent suite is the most comprehensive in procurement. I'm curious about one thing: when your agents autonomously process and approve a purchase, how long does the actual payment take? Is that still going through traditional AP?"
- **Note:** Zip is large enough that they may choose to build payment infrastructure in-house. The pitch should emphasize speed-to-market ("we're already built") and non-custodial architecture ("you don't need a money transmitter license").

---

## 15. Mindtrip (mindtrip.ai)

### S -- Situation

- **Product:** AI-powered travel planning and booking platform. Partnership with Sabre (420+ airlines, 2M+ hotels) and PayPal for end-to-end agentic travel experience. Flights launching Q2 2026.
- **Current payment infrastructure:** PayPal is their payment partner. PayPal's digital wallet handles identity verification, checkout, and payment processing. This is a major, locked-in partnership.
- **Stage:** Series A ($22M total from Amex Ventures, Capital One Ventures, United Airlines Ventures, Costanoa, Forerunner). $3.6M revenue. 44 employees.
- **Team:** Founded by Andy Moss (CEO, ex-Roadster founder, ex-FabKids, ex-ShopStyle, ex-PopSugar) and large founding team. Palo Alto-based.
- **Tech stack:** Sabre Mosaic APIs, PayPal integration, AI trip planning engine, group chat feature.

### P -- Problem

- **PayPal lock-in:** Mindtrip is locked into PayPal as their sole payment provider. PayPal takes 2.9% + $0.30 per transaction, and Mindtrip has no alternative payment rail.
- **Consumer-only:** PayPal is great for consumer travel but inadequate for corporate/business travel where companies need spending controls, approval workflows, and corporate card integration.
- **No agent spending controls:** When Mindtrip's AI agent books a $5,000 trip, there's no per-booking budget limit, merchant restriction, or automated approval threshold. PayPal processes whatever the agent submits.
- **Corporate travel gap:** Amex Ventures and Capital One Ventures are investors -- both major corporate card issuers. They likely want Mindtrip to expand into corporate travel, which requires enterprise payment controls.

### N -- Need-Payoff

- **Corporate travel expansion:** Sardis adds enterprise-grade spending controls (per-trip budgets, department limits, approval thresholds) that PayPal can't provide, enabling Mindtrip's expansion into corporate travel.
- **Multi-rail flexibility:** Sardis alongside PayPal gives Mindtrip payment optionality and reduces PayPal dependency.
- **Investor alignment:** Amex Ventures and Capital One Ventures would strongly support adding card infrastructure that complements their products.
- **B2B revenue stream:** Consumer travel is low-margin. Corporate travel with payment controls is 5-10x higher margin.

### Outreach Strategy

- **Best contact:** Andy Moss, CEO & Co-Founder
- **Best channel:** LinkedIn (Andy has 20+ years of e-commerce leadership experience and is well-connected)
- **Opening line:** "Andy, the Sabre + PayPal + Mindtrip partnership is a powerful combination for consumer travel. I'm curious: as you think about corporate travel (especially with Amex Ventures and Capital One Ventures as investors), how would the payment infrastructure need to evolve?"
- **Discovery questions:**
  1. "Have any of your investors asked about expanding into corporate travel? What payment capabilities would that require?"
  2. "How do you handle spending limits when your AI agent books expensive trips? Is that all managed through PayPal?"
  3. "What's the biggest gap between what PayPal provides and what enterprise customers would need?"
  4. "If Mindtrip could offer companies 'AI travel booking with built-in spending controls,' would that open a new customer segment?"
- **What NOT to say:** Avoid crypto/blockchain. PayPal is their partner -- don't position as replacing PayPal, but as complementing it for corporate use cases.

---

# ADDITIONAL COMPANIES (15-35 More Prospects)

---

## Direct Competitors / Partners in Agentic Payments Space

### 16. Sponge (paysponge.com)
- **Description:** Financial infrastructure for the agent economy. YC W26. Agents hold funds, transact with bank accounts, cards, and crypto.
- **Why relevant:** DIRECT COMPETITOR. Founded by ex-Stripe engineers. Nearly identical mission to Sardis. Study their positioning and pricing closely.
- **Fit score:** 2/10 (competitor, not customer)
- **Profile match:** Competitor -- learn from, don't sell to.

### 17. Locus (paywithlocus.com)
- **Description:** Payment infrastructure for AI agents. YC F25. USDC on Base, agent identities, budgets, permissions, audit trails.
- **Why relevant:** DIRECT COMPETITOR. Currently USDC-only on Base (similar to Sardis). Hosting agentic payments hackathon at YC HQ.
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- study their go-to-market and developer community.

### 18. Sapiom (sapiom.ai)
- **Description:** Financial infrastructure for AI agents to autonomously purchase software, APIs, and compute. $15.75M seed led by Accel. Backed by Anthropic and Coinbase Ventures.
- **Why relevant:** DIRECT COMPETITOR. More narrowly focused on API/software purchasing. Strong backing from Anthropic.
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- their narrow focus (API purchases) vs. Sardis's broad focus is a strategic difference.

### 19. Catena Labs (catenalabs.com)
- **Description:** First AI-native financial institution for agents. $18M seed led by a16z. Founded by Sean Neville (Circle co-founder, USDC co-creator).
- **Why relevant:** DIRECT COMPETITOR with significant crypto credibility. Open-source Agent Commerce Kit.
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- their open-source protocol approach could be complementary or threatening.

### 20. Nekuda (nekuda.ai)
- **Description:** Agentic commerce infrastructure. $5M seed led by Madrona, with Amex Ventures and Visa Ventures. Launch partner for Visa Intelligent Commerce.
- **Why relevant:** DIRECT COMPETITOR. Strong card network relationships (Visa, Amex).
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- their Visa partnership is a significant advantage.

### 21. Skyfire
- **Description:** Payment and identity platform for AI agents. $9.5M total. KYAPay protocol for verified agent identity.
- **Why relevant:** DIRECT COMPETITOR. More mature product with "thousands of transactions daily."
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- study their KYA (Know Your Agent) protocol.

### 22. Proxy (useproxy.ai)
- **Description:** Virtual cards and bank accounts for AI agents. MCP server integration. Real-time controls, spend limits, audit trails.
- **Why relevant:** DIRECT COMPETITOR. Very similar feature set to Sardis. MCP server integration mirrors Sardis's approach.
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- closest feature-for-feature competitor.

---

## Potential Customers -- AI Agent Platforms

### 23. CrewAI (crewai.com)
- **Description:** Leading multi-agent orchestration platform. $18M raised. 1.4B agentic automations. Used by PwC, IBM, NVIDIA. ~Half of Fortune 500.
- **Why relevant:** Sardis already has a `sardis-crewai` integration package. CrewAI's enterprise customers need agents that can transact. Deep platform integration opportunity.
- **Fit score:** 9/10
- **Profile match:** AI agent platform whose customers need payment capability.

### 24. Composio (composio.dev)
- **Description:** AI-native integration platform connecting LLMs to 3,000+ apps. $29M raised (Series A led by Lightspeed). OAuth management, sandboxed environments.
- **Why relevant:** Sardis already has a `sardis-composio` integration. Composio connects agents to tools but has no payment tool. Adding Sardis as a "payment tool" in their marketplace is natural.
- **Fit score:** 8/10
- **Profile match:** AI agent platform marketplace needing payment capability.

### 25. Ema (ema.co)
- **Description:** "Universal AI employee" platform. $61M raised. Founded by Surojit Chatterjee (ex-CPO Coinbase, ex-Google VP). Fintech, legal, healthcare, e-commerce deployments.
- **Why relevant:** CEO was CPO of Coinbase -- understands crypto payments deeply. Universal AI employees need to spend money. Fintech deployments need payment execution.
- **Fit score:** 8/10
- **Profile match:** AI agent platform with financial services customers needing payment capability.

### 26. Artisan (artisan.co)
- **Description:** AI employee startup (Ava the AI BDR). $25M Series A. YC-backed. 250 customers, $5M ARR.
- **Why relevant:** As Artisan expands beyond sales (BDR) to other employee types, financial capabilities will be needed. Sales agents need to send gifts, book meetings, purchase licenses.
- **Fit score:** 6/10
- **Profile match:** AI employee company expanding into roles requiring spending.

### 27. OpenClaw (open-source AI agent OS)
- **Description:** Open-source AI agent framework by Peter Steinberger. Agents can execute code, browse web, interact with services. Growing developer community.
- **Why relevant:** OpenClaw agents are already doing commerce (one agent negotiated $4,200 off a car purchase). The developer community needs proper payment infrastructure instead of hacky credit-card-in-code approaches.
- **Fit score:** 7/10
- **Profile match:** Open-source agent framework whose developers need payment capability.

### 28. AutoGPT (agpt.co)
- **Description:** Open-source autonomous AI agent. 180K+ GitHub stars. Sardis already has `sardis-autogpt` integration package.
- **Why relevant:** Largest open-source agent community. Agents need to make purchases, pay for APIs, and transact. Sardis integration already exists.
- **Fit score:** 7/10
- **Profile match:** Open-source agent platform needing payment capability.

---

## Potential Customers -- Vertical AI (Travel)

### 29. Stardrift (YC-backed)
- **Description:** AI travel search for frequent flyers. Complex itinerary planning and booking.
- **Why relevant:** Complex itinerary booking requires payment execution with multi-segment, multi-airline transaction handling.
- **Fit score:** 7/10
- **Profile match:** AI travel startup needing payment infrastructure.

### 30. Roame (YC-backed)
- **Description:** Flight search engine for credit card points/miles redemption.
- **Why relevant:** Points redemption requires payment processing (taxes/fees portion). Integration with card payment systems.
- **Fit score:** 5/10
- **Profile match:** Travel startup with payment adjacency.

### 31. Navan (navan.com)
- **Description:** Business travel and expense platform. Filed S-1 for IPO. $9.4B valuation. Full-stack travel + expense + card.
- **Why relevant:** Too large to be a customer, but a benchmark for what integrated travel+payment looks like. Their AI capabilities are weaker than pure-play AI startups.
- **Fit score:** 3/10
- **Profile match:** Incumbent -- study, don't sell to.

---

## Potential Customers -- Vertical AI (Procurement)

### 32. Levelpath (levelpath.com)
- **Description:** AI-native procurement platform. $100M+ total funding (Series B $55M led by Battery Ventures). Founded by ex-Scout RFP team (acquired by Workday for $540M). AI Agents for sourcing, supplier onboarding, risk assessment.
- **Why relevant:** Well-funded procurement platform with autonomous agents that need payment execution. Enterprise customers (Amgen, SiriusXM, Western Union).
- **Fit score:** 8/10
- **Profile match:** AI procurement platform needing agent payment capability.

### 33. Oro Labs (oro.ai)
- **Description:** AI-powered procurement orchestration. Raised $100M+ (March 2026). Acquired ProcureTech.
- **Why relevant:** Very well-funded, rapidly consolidating the procurement space. If they don't build payments in-house, they'll need a partner.
- **Fit score:** 6/10
- **Profile match:** Large procurement platform potentially needing payment partner.

### 34. Kavida.ai
- **Description:** AI procurement agent for manufacturing (Agent PO). Acquired by QAD/Redzone in Nov 2025. Automates 100+ post-PO procurement tasks.
- **Why relevant:** Now part of QAD -- a larger ERP company. Manufacturing procurement agents need to execute payments to suppliers.
- **Fit score:** 6/10
- **Profile match:** AI procurement agent (now part of larger company) needing payment execution.

### 35. Order.co
- **Description:** B2B e-commerce platform with PO and AP automation. AI-powered recommendations and savings.
- **Why relevant:** B2B purchasing platform where AI agents recommend and could execute purchases. Payment automation is central to their value prop.
- **Fit score:** 7/10
- **Profile match:** B2B purchasing platform needing agentic payment capabilities.

---

## Potential Customers -- Vertical AI (Finance / Expense)

### 36. Ramp (ramp.com)
- **Description:** Corporate card and expense management. $32B valuation. $1B+ ARR. Acquired Jolt AI.
- **Why relevant:** Too large and has its own payment infrastructure. However, Ramp's customers building AI agents on Ramp's platform might need Sardis for agent-specific payments.
- **Fit score:** 3/10
- **Profile match:** Incumbent -- too large, builds in-house.

### 37. Payhawk (payhawk.com)
- **Description:** Spend management platform. $1B valuation, $239M raised. AI-powered automation and control. Physical + virtual cards.
- **Why relevant:** Similar to Ramp -- too large and has own payment infrastructure. However, their AI automation could benefit from agent-specific payment controls.
- **Fit score:** 3/10
- **Profile match:** Incumbent -- study their AI features for competitive intelligence.

### 38. Samaya AI
- **Description:** AI for financial services. $43.5M raised (seed + Series A). Domain-specific AI agents for finance.
- **Why relevant:** Financial services AI agents that need to execute transactions. High-value vertical.
- **Fit score:** 7/10
- **Profile match:** Financial AI vertical needing transaction execution.

### 39. Paid (paid.com)
- **Description:** Results-based billing for AI agents. $33.3M raised ($21.6M seed led by Lightspeed + $10M pre-seed). London-based.
- **Why relevant:** Adjacent/competitor -- handles billing FOR agents, not payments BY agents. Could be partnership (Sardis handles agent spending, Paid handles agent billing).
- **Fit score:** 5/10 (partner potential)
- **Profile match:** Adjacent infrastructure -- partnership opportunity.

---

## Potential Customers -- Browser Agents

### 40. MultiOn
- **Description:** AI agent for web automation. API for reliable, scalable browser agents. Handles auth, CAPTCHAs, dynamic content.
- **Why relevant:** Browser agents that automate purchasing need secure payment infrastructure. Direct competitor to Browserbase in the agent browser space.
- **Fit score:** 8/10
- **Profile match:** Browser agent company whose agents need to complete checkouts.

### 41. Steel (steel.dev)
- **Description:** Managed cloud-hosted browsers for AI agents. Competitor to Browserbase.
- **Why relevant:** Same payment gap as Browserbase -- browser agents that need to make purchases have no secure payment method.
- **Fit score:** 7/10
- **Profile match:** Browser infrastructure needing payment capability for agent checkouts.

### 42. Stagehand (Browserbase's SDK)
- **Description:** Open-source browser automation SDK. v3 launched Feb 2026. AI-native architecture.
- **Why relevant:** Part of Browserbase ecosystem. Stagehand agents doing shopping/purchasing need Sardis virtual cards.
- **Fit score:** 7/10 (part of Browserbase deal)
- **Profile match:** Browser automation SDK needing payment tools.

---

## Potential Customers -- Workflow Automation

### 43. n8n (n8n.io)
- **Description:** AI workflow automation platform. $180M Series C (unicorn). Open-source. Financial AI agent capabilities.
- **Why relevant:** Sardis already has `n8n-nodes-sardis` integration. n8n's AI agents doing financial workflows need payment execution. Razorpay already added a payment node -- Sardis should too.
- **Fit score:** 8/10
- **Profile match:** Workflow automation platform needing payment node for AI agents.

### 44. Activepieces (activepieces.com)
- **Description:** Open-source automation platform. Self-hosted. AI agent capabilities.
- **Why relevant:** Sardis already has `sardis-activepieces` integration. Same opportunity as n8n -- payment capability for automated workflows.
- **Fit score:** 7/10
- **Profile match:** Workflow automation platform needing payment piece.

---

## Potential Customers -- Enterprise AI / Customer Service

### 45. Sierra (sierra.ai)
- **Description:** AI customer service agents. $1B+ valuation. Backed by Sequoia. Handles complex customer interactions including order management and returns.
- **Why relevant:** Customer service agents that handle refunds, process returns, and issue credits need payment execution capability.
- **Fit score:** 6/10
- **Profile match:** Customer service AI needing payment execution for refunds/credits.

### 46. Wonderful (wonderful.ai)
- **Description:** AI customer service agents. $134M raised ($100M Series A). Voice, chat, email agents.
- **Why relevant:** Similar to Sierra -- customer service agents handling financial interactions (refunds, billing adjustments, payment processing).
- **Fit score:** 6/10
- **Profile match:** Customer service AI needing payment execution.

### 47. Decagon (decagon.ai)
- **Description:** AI customer support agents for enterprises. Series B funded.
- **Why relevant:** Customer support agents that need to process refunds, apply credits, or handle billing inquiries.
- **Fit score:** 5/10
- **Profile match:** Customer support AI with payment-adjacent workflows.

---

## Potential Customers -- Emerging / Crypto-Adjacent

### 48. Alinia (alinia.ai)
- **Description:** Compliance infrastructure for AI agents. $7.5M seed. Banking-focused.
- **Why relevant:** Complementary -- Alinia handles compliance, Sardis handles payments. Natural partnership in banking AI deployments.
- **Fit score:** 7/10 (partnership)
- **Profile match:** Compliance infrastructure -- partnership opportunity.

### 49. E2B (e2b.dev)
- **Description:** Sandbox for AI agents. Open-source. Sardis already has `sardis-e2b` integration.
- **Why relevant:** Agents running in E2B sandboxes need secure payment capabilities for testing and production.
- **Fit score:** 6/10
- **Profile match:** Agent sandbox infrastructure -- integration partner.

### 50. Natural (natural.com)
- **Description:** Payments infrastructure for agentic payments. $9.8M seed. Logistics, property management, procurement, healthcare, construction.
- **Why relevant:** DIRECT COMPETITOR focused on specific verticals (logistics, property management).
- **Fit score:** 2/10 (competitor)
- **Profile match:** Competitor -- study their vertical go-to-market.

---

# PRIORITY MATRIX

## Immediate Outreach (This Week)

| Rank | Company | Why Now |
|------|---------|---------|
| 1 | BizTrip AI | Pre-seed, building right now, GA in Q2 2026. Need payment before launch. |
| 2 | Fellou | 1M users, massive security gap at checkout. Urgency is real. |
| 3 | Beam AI | Bootstrapped ($132K raised, $4.5M revenue), can't build payments alone. Need partner. |
| 4 | Sola AI | a16z-backed, Fortune 100 customers hitting payment execution wall. |
| 5 | Lyzr | Accenture relationship depends on banking agent payment capabilities. |

## Near-Term Outreach (Next 2 Weeks)

| Rank | Company | Why Soon |
|------|---------|----------|
| 6 | Otto | Corporate pilots starting, need payment controls for enterprise. |
| 7 | Procure AI | 50 agents with no payment capability. European expansion needs multi-currency. |
| 8 | Browserbase | 1,000+ customers building purchasing agents with credit cards in code. |
| 9 | Relevance AI | 40K agents, zero transactions. Bessemer expects transaction revenue. |
| 10 | HyperExpense | Already has card program but could benefit from multi-rail + agent controls. |

## Strategic Outreach (Next Month)

| Rank | Company | Strategic Value |
|------|---------|-----------------|
| 11 | CrewAI | Sardis integration exists. 1.4B automations. Fortune 500 distribution. |
| 12 | Composio | Sardis integration exists. 3,000+ app marketplace. |
| 13 | n8n | Sardis integration exists. Unicorn. Payment node opportunity. |
| 14 | Levelpath | $100M+ funded. Enterprise procurement needing payment execution. |
| 15 | Ema | CEO is ex-Coinbase CPO. Understands agent payments. $61M raised. |

## Monitor / Research (Ongoing)

| Company | Reason |
|---------|--------|
| Tonkean | Needs payment to compete with Zip. $83M raised. |
| Zip HQ | May build in-house. $2.2B valuation. |
| Mindtrip | Locked into PayPal. Corporate expansion needs more. |
| Shinkai | Crypto-native. Already has USDC payments. Needs card rails. |
| MultiOn | Browser agent needing checkout capability. |
| Fairmarkit | Series C. Source-to-pay gap. |

---

# COMPETITIVE LANDSCAPE SUMMARY

## Direct Competitors (Build Awareness, Not Customers)

| Company | Funding | Key Differentiator | Sardis Advantage |
|---------|---------|-------------------|------------------|
| Sponge (YC W26) | Unknown | Ex-Stripe team, bank+card+crypto | Sardis has multi-chain, MPC wallets, AP2/TAP protocol support |
| Locus (YC F25) | Unknown | USDC on Base, developer hackathons | Sardis has virtual cards + multi-chain + compliance (KYC/AML) |
| Sapiom | $15.75M | API/software purchasing focus | Sardis has broader multi-rail (cards + bank + crypto) |
| Catena Labs | $18M | a16z + Circle co-founder | Sardis is further in product development with production SDK |
| Nekuda | $5M | Visa/Amex partnerships | Sardis has deeper technical infrastructure (MPC, policy engine) |
| Skyfire | $9.5M | KYAPay protocol, live transactions | Sardis has AP2 + TAP protocol support (industry standards) |
| Proxy | Unknown | MCP server, virtual cards | Most similar to Sardis -- differentiate on compliance + multi-chain |
| Natural | $9.8M | Vertical focus (logistics, property) | Sardis is horizontal platform vs. vertical point solutions |

## Key Differentiation for Sardis

1. **Non-custodial MPC wallets** -- No competitor offers this. Sardis never holds private keys.
2. **Natural language spending policies** -- Unique to Sardis. Competitors use JSON/code-based rules.
3. **Multi-rail execution** -- USDC on-chain + virtual cards + bank accounts in one platform.
4. **AP2 + TAP protocol support** -- Industry standard compliance (Google, PayPal, Mastercard, Visa consortium).
5. **KYC/AML built-in** -- iDenfy integration for compliance. Most competitors are compliance-light.
6. **Kill switches** -- Instant transaction freezing. Critical for enterprise adoption.
7. **Existing integrations** -- CrewAI, Composio, AutoGPT, n8n, Activepieces, E2B, MCP server, Browser Use, Stagehand, OpenAI Agents SDK, Vercel AI SDK -- broadest integration ecosystem.
8. **Open-core model** -- SDK is open, infrastructure is commercial. Developer-friendly approach.

---

Sources:
- [BizTrip AI Pre-Seed Funding](https://theaiinsider.tech/2026/02/04/biztrip-ai-secures-1-5m-in-new-pre-seed-funding/)
- [BizTrip AI PhocusWire Hot 25](https://www.phocuswire.com/hot-25-travel-startups-2026-biztrip)
- [BizTrip Sabre Partnership](https://www.sabre.com/releases/sabre-and-biztrip-ai-announce-strategic-partnership-to-deliver-agentic-ai-solutions-for-global-corporate-travel-market/)
- [BizTrip Launch on Skift](https://skift.com/2025/07/21/biztrip-ai-launches-with-bold-goal-corporate-travel-without-the-search-bar/)
- [Otto $6M Funding - Business Travel News](https://www.businesstravelnews.com/Technology/Otto-Raises-6M-for-AI-Assisted-Unmanaged-Biz-Travel)
- [Otto Spotnana Partnership](https://www.spotnana.com/blog/otto-the-agent-announces-ai-travel-assistant-built-on-spotnana/)
- [Otto Madrona Venture Profile](https://www.madrona.com/meet-otto-the-ai-travel-agent/)
- [Otto Public Launch](https://www.businesswire.com/news/home/20251204074992/en/Otto-The-Agent-Launches-to-the-Public-Bringing-an-Executive-Assistant-Experience-to-Every-Business-Traveler)
- [Sola AI Series A - a16z](https://a16z.com/announcement/investing-in-sola/)
- [Sola AI $17.5M Funding](https://siliconangle.com/2025/08/14/sola-solutions-raises-17-5m-enhance-enterprise-process-automation/)
- [Lyzr $250M Valuation - Bloomberg](https://www.bloomberg.com/news/articles/2026-03-09/agentic-ai-startup-lyzr-raises-funds-at-250-million-valuation)
- [Lyzr Accenture Investment](https://newsroom.accenture.com/news/2025/accenture-invests-in-lyzr-to-bring-agentic-ai-to-banking-and-insurance-companies)
- [Lyzr Billing Automation Case Study](https://www.lyzr.ai/blog/automating-enterprise-billing-workflows)
- [Lyzr Payment Receipt Verification](https://www.lyzr.ai/blog/ai-agents-for-payment-receipt-verification)
- [Beam AI $4.5M Revenue](https://getlatka.com/companies/beam.ai)
- [Beam AI Founders](https://beam.ai/media/meet-the-founders)
- [Fairmarkit Series C $35.6M](https://www.businesswire.com/news/home/20220901005138/en/Fairmarkit-Secures-35.6-Million-Series-C-Funding-to-Help-More-Enterprises-Optimize-%E2%80%9CTail-Spend%E2%80%9D)
- [Fairmarkit Gartner Recognition](https://www.businesswire.com/news/home/20251120635979/en/Fairmarkit-Recognized-in-Three-Gartner-Reports-Covering-Agentic-AI-and-AIs-Impact-on-Procurement)
- [HyperExpense TARS Engine](https://www.hyperexpense.com/post/introducing-hyper)
- [Hypercard Forbes 30 Under 30](https://www.hypercard.com/post/hypercard-founders-selected-by-forbes-30-under-30-in-finance)
- [Fellou $40.4M Raised](https://www.businesswire.com/news/home/20250902953779/en/Worlds-First-Spatial-Agentic-Browser-That-Works-While-You-RestFellou-CE-Launches)
- [Fellou TechCrunch Profile](https://techcrunch.com/sponsor/fellou/the-rise-of-fellou-worlds-first-agentic-ai-browser/)
- [Relevance AI $24M Series B](https://techcrunch.com/2025/05/06/relevance-ai-raises-24m-series-b-to-help-anyone-build-teams-of-ai-agents/)
- [Relevance AI PYMNTS Coverage](https://www.pymnts.com/news/investment-tracker/2025/relevance-ai-raises-24-million-to-grow-ai-agent-operating-system/)
- [Procure AI $13M Seed](https://siliconangle.com/2025/11/27/procure-ai-lands-13m-funding-automate-business-procurement-tasks/)
- [Procure AI Platform](https://www.procure.ai/platform)
- [Tonkean Cinch Acquisition](https://www.tonkean.com/blog/tonkean-acquires-ai-spend-intelligence-startup-cinch-doubling-down-on-procurement-finance-and-emea)
- [Tonkean Revenue $16.2M](https://getlatka.com/companies/tonkean)
- [Browserbase $40M Series B](https://www.upstartsmedia.com/p/browserbase-raises-40m-and-launches-director)
- [Browserbase Contrary Research](https://research.contrary.com/company/browserbase)
- [Shinkai v1.0 Launch](https://dailyhodl.com/2025/07/29/shinkai-launches-version-1-0-on-chain-ai-agents-go-live-with-usdc-and-coinbase-x402/)
- [Zip $190M Series D](https://ziphq.com/blog/series-d)
- [Zip 50+ AI Agents - VentureBeat](https://venturebeat.com/ai/zip-debuts-50-ai-agents-to-kill-procurement-inefficiencies-openai-is-already-on-board)
- [Mindtrip Sabre PayPal Partnership - Skift](https://skift.com/2026/02/12/sabre-paypal-mindtrip-agentic-ai-travel-booking-announcement/)
- [Mindtrip $12M Funding](https://www.phocuswire.com/mindtrip-secures-12m-funding-launches-group-chat)
- [Agentic Commerce Landscape 2026 - Rye](https://rye.com/blog/agentic-commerce-startups)
- [AI Agent Payments Landscape 2026 - Proxy](https://www.useproxy.ai/blog/ai-agent-payments-landscape-2026)
- [Sponge YC Launch](https://www.ycombinator.com/launches/PTD-sponge-financial-infrastructure-for-the-agent-economy)
- [Locus YC Launch](https://www.ycombinator.com/launches/Oj6-locus-payment-infrastructure-for-ai-agents)
- [Sapiom $15M Seed - TechCrunch](https://techcrunch.com/2026/02/05/sapiom-raises-15m-to-help-ai-agents-buy-their-own-tech-tools/)
- [Catena Labs $18M - PYMNTS](https://www.pymnts.com/news/investment-tracker/2025/catena-labs-raises-18-million-to-build-ai-native-financial-institution-for-agents/)
- [CrewAI $18M Funding](https://pulse2.com/crewai-multi-agent-platform-raises-18-million-series-a/)
- [Composio $25M Series A](https://siliconangle.com/2025/07/22/composio-raises-25m-funding-ease-ai-agent-development/)
- [Ema $61M Total Funding](https://venturebeat.com/ai/ema-raises-36m-to-build-universal-ai-employees-for-enterprises)
- [Levelpath $55M Series B](https://techcrunch.com/2025/06/30/next-gen-procurement-platform-levelpath-nabs-55m/)
- [n8n $180M Series C](https://tracxn.com/d/companies/n8n/__J5xwUZ9C29t7Du-yVvv0S99EWc7s69t2NGt5YmhQG0A)
- [Nekuda Agentic Commerce Strategy](https://nekuda.substack.com/p/whats-your-2026-agentic-commerce)
- [AI Agent Payment Statistics](https://nevermined.ai/blog/ai-agent-payment-statistics)
- [Agentic Payments Rewriting Spend Management](https://www.apideck.com/blog/agentic-payments-spend-management-ai-agents)
