# Sardis Customer Outreach Playbook
## Reusable Templates, Discovery Questions & SPIN Selling Framework

Generated: 2026-03-08
Author: Sardis GTM

---

## Table of Contents

1. Segment-Specific Email Templates (6 segments)
2. Mom Test Discovery Question Bank
3. SPIN Selling Question Bank
4. Objection Handling Playbook
5. Follow-Up Sequence Templates
6. Qualifying Criteria & Scoring

---

## 1. SEGMENT-SPECIFIC EMAIL TEMPLATES

### Template Format Rules
- Under 140 words
- Problem-first opening (observation about their specific workflow)
- Curiosity-driven question (Mom Test style, not leading)
- Sardis value prop (one sentence, workflow-specific)
- 3 bullet traction points
- Sign-off: Best, Efe Baran Durmaz / Founder, Sardis | sardis.sh
- No em-dashes or double hyphens
- Subject format: Sardis // {Company} {workflow topic}

---

### S1: MULTI-VENDOR AI SPEND

**Target persona:** CTO/VP Engineering, Head of AI/ML, CFO
**Core pain:** Reconciling invoices across 5-15+ AI providers with different billing cycles, formats, and pricing models. No single control plane for AI spend.

**Template:**

Subject: Sardis // {Company} multi-provider payments

{First Name},

{Specific observation about their multi-provider AI usage, e.g. "You route inference across OpenAI, Anthropic, and Cohere" or "Your platform lets customers choose from 200+ models across providers"}.

{Pain hypothesis framed as curiosity, e.g. "Curious if reconciling invoices across 10+ AI providers has become a bottleneck" or "Wonder if your enterprise customers have asked for spend controls"}.

Sardis gives AI-heavy teams one policy layer controlling payments to every provider: real-time budget enforcement per model and unified audit trail.

- 25k+ SDK installs in 3 weeks (organic)
- AutoGPT and Helicone-caliber companies committed
- 15+ framework integrations

{Low-friction closing question about their current workflow}.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

**Key angles for S1:**
- Cost attribution per model/provider is manual
- Finance teams cannot approve scaling without budget guardrails
- No unified dashboard across providers
- Variable pricing (per-token, per-call, subscription) creates reconciliation pain

---

### S2: AGENT-ENABLED SPEND

**Target persona:** CEO/Founder, CTO, Head of Product
**Core pain:** AI agents need to make real payments (API calls, SaaS subscriptions, compute) but there is no safe execution layer. Agents cannot hold wallets or enforce spending policies.

**Template:**

Subject: Sardis // {Company} agent payment capabilities

{First Name},

{Observation about their agent capabilities, e.g. "Your agents execute multi-step workflows that eventually trigger real spend" or "Autonomous agents booking and purchasing need payment rails they can use safely"}.

{Pain hypothesis, e.g. "Curious if the gap between agent actions and actual payment execution is slowing production deployment" or "Wonder if customers have asked for agents that can handle money, not just tasks"}.

Sardis gives AI agents non-custodial wallets with plain English spending policies: agents propose, deterministic policy decides, and every transaction gets an auditable proof chain.

- 25k+ organic SDK installs in 3 weeks
- AutoGPT and Helicone committed
- Merchant checkout and 52 MCP tools live

{Low-friction closing question about agent payment needs}.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

**Key angles for S2:**
- Agents that act but cannot pay are incomplete
- No existing payment rail is agent-native
- Trust gap: enterprises will not let agents move money without controls
- Agent-to-agent payments are an unsolved problem

---

### S3: RECURRING PAYOUTS & DISBURSEMENTS

**Target persona:** CFO/Head of Finance, COO, CTO
**Core pain:** High-volume payouts (creator earnings, contractor payments, marketplace disbursements) involve manual processes, delayed settlements, and no policy enforcement at the transaction level.

**Template:**

Subject: Sardis // {Company} payout governance

{First Name},

{Observation about their payout volume, e.g. "You process payouts to thousands of creators on different schedules" or "Your marketplace handles cross-border disbursements to sellers in 50+ countries"}.

{Pain hypothesis, e.g. "Curious if managing payout policies across different tiers and regions is mostly manual today" or "Wonder if reconciling disbursements across multiple payment methods has become a bottleneck"}.

Sardis provides policy-driven payout governance: per-recipient limits, automated compliance checks, and a verifiable audit trail for every disbursement.

- 25k+ organic SDK installs in 3 weeks
- Deterministic policy engine (fail-closed default)
- Multi-rail support: cards, fiat, on-chain

{Low-friction closing about their current payout workflow}.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

**Key angles for S3:**
- Payout fraud is a growing problem at scale
- Per-recipient policy enforcement does not exist in current rails
- Compliance evidence for payouts is generated after the fact
- Cross-border adds FX, tax, and regulatory complexity

---

### S4: B2B AP/AR & INVOICE AUTOMATION

**Target persona:** CFO, Head of Finance, COO, CEO/Founder
**Core pain:** Accounts payable and receivable involve approval chains, compliance checks, and audit requirements that are manual and disconnected. AI is entering AP/AR but without payment-grade controls.

**Template:**

Subject: Sardis // {Company} AP/AR governance

{First Name},

{Observation about their AP/AR workflow, e.g. "Your platform automates invoice processing for enterprises with thousands of monthly invoices" or "AI-driven AP automation still requires manual approval for payment execution"}.

{Pain hypothesis, e.g. "Curious if the gap between invoice approval and actual payment execution is where most delays happen" or "Wonder if customers ask for deterministic controls on payment amounts, not just invoice matching"}.

Sardis adds a governance layer between approval and execution: quorum-based approvals, per-vendor limits, and tamper-evident audit trails for every payment.

- 25k+ organic SDK installs in 3 weeks
- 4-eyes approval orchestration built in
- Merkle-proof compliance evidence

{Low-friction closing about their payment execution workflow}.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

**Key angles for S4:**
- Invoice matching is solved; payment governance is not
- AI entering AP/AR creates new error patterns (goal drift, hallucinated amounts)
- Approval orchestration (quorum, 4-eyes) is critical for enterprise
- Audit trail requirements are getting stricter (SOX, SOC 2)

---

### S5: PLATFORM & ECOSYSTEM ENABLER

**Target persona:** CEO/Founder, CTO, VP Product, Head of Partnerships
**Core pain:** Platforms that connect agents, developers, or services need payment infrastructure as a capability layer. They provide orchestration but cannot offer payment execution with governance.

**Template:**

Subject: Sardis // {Company} payment governance layer

{First Name},

{Observation about their platform role, e.g. "You connect thousands of AI tools under one marketplace" or "Your orchestration layer routes work across agents but payment is external"}.

{Pain hypothesis, e.g. "Curious if adding payment capabilities to your platform has been on the roadmap" or "Wonder if partners have asked for embedded payment controls within your ecosystem"}.

Sardis provides the governance layer above payment rails: deterministic policy, approval orchestration, and verifiable proofs. Platforms embed Sardis so their users get payment controls without building from scratch.

- 25k+ organic SDK installs in 3 weeks
- 52 MCP tools, 15+ framework integrations
- Multi-rail: cards, fiat treasury, on-chain

{Low-friction closing about their platform payment roadmap}.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

**Key angles for S5:**
- Platforms want to own the payment layer but do not want to build compliance
- Governance above rails means platform does not need to become a PSP
- Embedded payment controls increase platform stickiness
- Multi-rail support matters for platforms with diverse user bases

---

### S6: COMMERCE & MERCHANT OPERATIONS

**Target persona:** CTO, VP Engineering, Head of Payments, CEO/Founder
**Core pain:** Commerce platforms handle high-volume payment operations where AI is being introduced for fraud detection, routing optimization, and merchant services. But AI-driven payment decisions lack governance and audit trails.

**Template:**

Subject: Sardis // {Company} payment operations governance

{First Name},

{Observation about their commerce operations, e.g. "You process millions of transactions across global merchants" or "Your platform handles payment routing decisions at scale"}.

{Pain hypothesis, e.g. "Curious if as AI enters payment routing and fraud decisions, the governance gap has become a concern" or "Wonder if merchant compliance evidence is still mostly post-hoc"}.

Sardis provides real-time governance for payment operations: deterministic policy enforcement on every transaction, automated compliance evidence, and fail-closed defaults.

- 25k+ organic SDK installs in 3 weeks
- Deterministic checks (not model-based decisions)
- Secure checkout evidence export with hash-chain integrity

{Low-friction closing about their payment governance needs}.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

**Key angles for S6:**
- AI in commerce payments needs governance, not just optimization
- Real-time policy enforcement vs. post-hoc fraud review
- Merchant compliance evidence should be generated at decision time
- Fail-closed is the only safe default for payment operations

---

## 2. MOM TEST DISCOVERY QUESTION BANK

The Mom Test principle: ask about their life, not your idea. Never mention your solution until you understand their problem.

### Universal Discovery Questions (All Segments)

**Current Workflow:**
- Walk me through how a payment gets from approval to execution today.
- How many people touch a payment before it goes out?
- What does your reconciliation process look like at month-end?
- How do you currently enforce spending limits on teams/agents/users?

**Pain Exploration:**
- What is the most time-consuming part of your payment workflow?
- When was the last time a payment went out that should not have?
- How do you handle exceptions or edge cases in payments today?
- What happens when an approval is needed at 2am?

**Scale & Growth:**
- How does your payment process change as you add more vendors/providers?
- What breaks first when transaction volume doubles?
- Are there payments you avoid automating because of risk?

**Compliance & Audit:**
- How do you generate compliance evidence for payments today?
- What does your auditor ask for that is hardest to produce?
- If a regulator asked "prove this payment was authorized," how long would that take?

---

### S1: Multi-Vendor AI Spend

- How many AI providers are you paying today? How do you expect that to change?
- Who owns the reconciliation of AI provider invoices?
- Can you set per-model or per-team budget caps today, or is that manual?
- What happens when a team exceeds their AI spend allocation?
- How do you decide which provider to route inference to for cost optimization?
- Has unpredictable AI costs ever delayed a project or scaling decision?

### S2: Agent-Enabled Spend

- Do your agents currently trigger any real financial transactions?
- If an agent could make a payment, what controls would you need before allowing that?
- What is the gap between what your agents can do and what they are allowed to do with money?
- Have customers asked for agents that can handle procurement or purchasing?
- How do you think about trust boundaries for autonomous agent actions?
- What would agent-to-agent payments unlock for your use case?

### S3: Recurring Payouts & Disbursements

- How many payouts do you process per month? What is the average size?
- What percentage of payouts require manual review or intervention?
- How do you handle payout disputes or clawbacks today?
- Do you enforce different policies for different payout tiers or regions?
- What is your biggest pain point with cross-border disbursements?
- How do you detect and prevent payout fraud at scale?

### S4: B2B AP/AR & Invoice Automation

- How many invoices does your team process per month?
- What is the time gap between invoice approval and payment execution?
- How many approvers are in your typical payment chain?
- What happens when an invoice amount does not match the PO?
- How do you generate audit evidence for SOX/SOC 2 compliance?
- Is AI involved in any part of your AP/AR workflow today? What controls exist?

### S5: Platform & Ecosystem Enabler

- Have partners or developers asked for payment capabilities within your platform?
- Is there a payment-related feature that keeps coming up in feedback?
- How do your users currently handle payments that originate from your platform?
- What would embedded payment controls do for platform retention?
- Would adding governance (not just payments) differentiate your offering?

### S6: Commerce & Merchant Operations

- Where is AI currently making payment-related decisions in your stack?
- How do you audit AI-driven payment routing or fraud decisions?
- What is your false positive rate on fraud detection, and what does that cost?
- How do you generate compliance evidence for each transaction?
- What is your tolerance for payment decisions that cannot be explained after the fact?

---

## 3. SPIN SELLING QUESTION BANK

SPIN = Situation, Problem, Implication, Need-Payoff

### S1: Multi-Vendor AI Spend

**Situation:**
- How many AI providers are you currently paying?
- What is your monthly AI infrastructure spend?
- Who manages provider billing and reconciliation?

**Problem:**
- Is reconciling invoices across providers a significant time drain?
- Can you attribute AI costs to specific teams or projects in real-time?
- How often do AI costs surprise your finance team?

**Implication:**
- If you cannot control AI spend per team, does that slow down scaling decisions?
- What happens to your margin if AI costs grow 3x but governance stays manual?
- Could unpredictable AI costs cause your finance team to impose blanket restrictions?

**Need-Payoff:**
- If you could set per-model budget caps that enforce automatically, how would that change your scaling timeline?
- Would real-time cost attribution across all providers change how your finance team views AI investment?
- If reconciliation was automated with auditable proofs, how much time would your team recover?

---

### S2: Agent-Enabled Spend

**Situation:**
- What types of tasks do your agents perform autonomously?
- Do agents interact with any financial systems today?
- How do you currently scope what agents are allowed to do?

**Problem:**
- Is the inability to make payments a limitation for agent capabilities?
- Do customers ask for agents that can complete transactions, not just recommend them?
- How do you enforce boundaries on agent actions when they involve money?

**Implication:**
- If agents cannot pay, does that cap the value they can deliver to customers?
- What revenue is left on the table because agents cannot close the loop on purchases?
- If an agent made an unauthorized payment, what would the fallback be?

**Need-Payoff:**
- If agents could make payments within policy-enforced limits, what new use cases would that unlock?
- Would deterministic controls (not model-based) make your enterprise customers more comfortable with agent payments?
- If every agent payment had a verifiable audit trail, would that accelerate enterprise adoption?

---

### S3: Recurring Payouts & Disbursements

**Situation:**
- How many payouts do you process monthly?
- What payment methods do your recipients use?
- How do you enforce payout limits or fraud controls?

**Problem:**
- What percentage of payouts require manual review?
- How do you handle policy exceptions for high-value payouts?
- Is payout fraud a growing concern as you scale?

**Implication:**
- If manual review is the bottleneck, does that delay payouts for all recipients?
- What is the financial exposure if a fraudulent payout goes through undetected?
- Could payout delays cause you to lose top earners or sellers to competitors?

**Need-Payoff:**
- If every payout was checked against deterministic policies in real-time, would that reduce manual review?
- Would automated compliance evidence for each payout simplify your audit process?
- If you could enforce per-recipient and per-region policies automatically, what volume could you safely scale to?

---

### S4: B2B AP/AR & Invoice Automation

**Situation:**
- What is your current invoice-to-payment cycle time?
- How many approvers are in a typical payment chain?
- What ERP or AP system do you use?

**Problem:**
- Where in the process do payments get stuck or delayed?
- How do you ensure payment amounts match approved invoices?
- Is generating audit evidence for SOX/SOC 2 a manual process?

**Implication:**
- If payments are delayed, does that damage vendor relationships or trigger late fees?
- What is the cost of a payment error that passes through the approval chain undetected?
- If AI is automating invoice processing, who governs the AI's payment decisions?

**Need-Payoff:**
- If quorum-based approvals happened in real-time, how would that change your payment cycle?
- Would tamper-evident audit trails reduce your SOX compliance burden?
- If policy enforcement was deterministic and fail-closed, would your team trust AI in the payment chain?

---

### S5: Platform & Ecosystem Enabler

**Situation:**
- Do your users handle payments through your platform or externally?
- Is payment infrastructure part of your product roadmap?
- How do partners currently monetize within your ecosystem?

**Problem:**
- Is the lack of embedded payments a friction point for users?
- Do users leave your platform to handle payment-related tasks?
- Is building payment infrastructure in-house a distraction from your core product?

**Implication:**
- If users leave for payments, does that reduce platform engagement and stickiness?
- What would it cost to build payment governance from scratch?
- If competitors add payment capabilities first, does that threaten your position?

**Need-Payoff:**
- If you could embed payment governance without becoming a PSP, would that accelerate your roadmap?
- Would multi-rail payment controls (cards, fiat, on-chain) make your platform more attractive to diverse users?
- If governance was built in, would that unlock new revenue streams (transaction fees, premium tiers)?

---

### S6: Commerce & Merchant Operations

**Situation:**
- Where does AI currently make payment-related decisions in your stack?
- How do you generate compliance evidence per transaction?
- What is your current fraud detection approach?

**Problem:**
- Can you explain every AI-driven payment decision after the fact?
- Is compliance evidence generated at decision time or reconstructed later?
- What is your false positive rate on fraud, and what does that cost in lost revenue?

**Implication:**
- If regulators audit an AI-driven payment decision, can you prove it was legitimate?
- What happens if your false positive rate increases as AI takes on more payment decisions?
- If compliance evidence is post-hoc, does that create legal exposure?

**Need-Payoff:**
- If every payment decision had a verifiable proof chain generated in real-time, how would that change your compliance posture?
- Would deterministic policy enforcement reduce your false positive rate?
- If fail-closed defaults meant zero unauthorized payments, would that justify the integration effort?

---

## 4. OBJECTION HANDLING PLAYBOOK

### "We already use Stripe/Adyen/Lithic for payments."

Response: Those are excellent rails. Sardis is not a competing payment processor. We are the governance layer above the rails. Think of it this way: Stripe moves money, Sardis decides whether and how money should move. Companies use both.

### "Our agents do not make payments yet."

Response: That is exactly when to build the controls. The worst time to add governance is after an agent makes an unauthorized payment. We are working with companies at the same stage to get the trust layer right before production.

### "We handle this internally."

Response: Makes sense. Curious how many engineer-hours per month go into payment policy enforcement and audit trail generation? Most teams we talk to find that internal tooling covers 60-70% of cases but the edge cases eat disproportionate time.

### "We are too early for this."

Response: Totally fair. We work as design partners with early-stage teams. No commitment, just a shared feedback loop. If you are going to need payment governance eventually, shaping it early is cheaper than retrofitting.

### "How is this different from a policy engine?"

Response: Policy engines evaluate rules. Sardis provides the full execution governance stack: policy enforcement, approval orchestration (quorum/4-eyes), multi-rail payment execution, and Merkle-proof audit trails. It is the difference between a firewall rule and a complete security platform.

### "What about compliance? We need SOC 2 / PCI."

Response: Sardis generates tamper-evident compliance evidence at decision time, not after the fact. Every transaction includes policy snapshot hash, approval context, and hash-chain integrity metadata. This is designed to make your auditor's job easier.

### "Sounds expensive / complex to integrate."

Response: SDK integration is 10-15 lines of code. We have 15+ framework integrations already built (LangChain, CrewAI, Vercel AI SDK, MCP, AutoGPT, and more). Most design partners are live in under a week.

### "We need to think about it."

Response: Of course. Would it be helpful if I sent over a one-pager showing how {similar company in their segment} is using Sardis? That way you have something concrete to evaluate.

---

## 5. FOLLOW-UP SEQUENCE TEMPLATES

### Follow-Up 1 (Day 3 after initial email, no response)

Subject: Re: {Original Subject}

{First Name},

Quick follow-up. I know inboxes are brutal.

The short version: we built the trust layer that lets AI agents make real payments safely. Deterministic controls, not model-based.

Happy to share a 2-minute demo if that is easier than a call.

Best,
Efe

### Follow-Up 2 (Day 7, no response)

Subject: Re: {Original Subject}

{First Name},

One more thought. We just shipped {recent feature or milestone relevant to their segment, e.g. "ERC-4337 production signer support" or "secure checkout evidence export"}.

If {their specific workflow pain} is on your radar, I think we could save your team significant time. If not, no worries at all.

Best,
Efe

### Follow-Up 3 (Day 14, final touch)

Subject: Re: {Original Subject}

{First Name},

Last note from me. If the timing is not right, totally understand.

If payment governance for {agents/AI workflows/payouts/invoices} becomes a priority, Sardis is at sardis.sh. We will be here.

Best,
Efe

---

## 6. QUALIFYING CRITERIA & SCORING

### BANT+ Scoring (0-5 per category, 20 max)

**Budget (0-5):**
- 0: No budget allocated, no plans
- 1: Might have budget in 6+ months
- 3: Budget allocated but not approved
- 5: Budget approved, ready to spend

**Authority (0-5):**
- 0: Spoke to individual contributor only
- 1: IC interested, no exec sponsor
- 3: Director/VP engaged, exec aware
- 5: C-level sponsor, decision maker engaged

**Need (0-5):**
- 0: No identified pain
- 1: Vague awareness of pain
- 3: Clear pain, actively exploring solutions
- 5: Critical pain, current solution failing

**Timeline (0-5):**
- 0: No timeline
- 1: Evaluating in 6+ months
- 3: Evaluating this quarter
- 5: Evaluating now, decision within 30 days

### Lead Priority Tiers

**Tier 1 (Score 16-20): Hot**
- Contact within 24 hours
- Personalized demo prep
- Founder-led discovery call

**Tier 2 (Score 11-15): Warm**
- Contact within 48 hours
- Segment-specific demo
- SDR/founder discovery call

**Tier 3 (Score 6-10): Nurture**
- Add to email sequence
- Share relevant content
- Re-engage quarterly

**Tier 4 (Score 0-5): Archive**
- Log in CRM
- No active outreach
- Re-evaluate in 6 months

---

## APPENDIX: TRACTION PROOF POINTS (Updated 2026-03-08)

Use these in emails, calls, and follow-ups:

- 25,000+ organic SDK installs in 3 weeks (no paid distribution)
- AutoGPT (180k GitHub stars) committed design partner
- Helicone (YC W23) committed design partner
- 15+ framework integrations (LangChain, CrewAI, Vercel AI SDK, MCP, Browser Use, n8n, and more)
- 52 MCP tools live
- 825 tests, 887 total collected
- Merchant checkout live with hash-chain integrity proofs
- ERC-4337 production signer path (Turnkey/Fireblocks)
- Multi-rail: cards (Lithic), fiat treasury, on-chain (6 chains, 6 tokens)
- Deterministic policy engine: fail-closed default, not model-based
- Immutable hard-limit layer with fuzz + property test coverage
- Verifiable audit trail: Merkle-proof export path for compliance evidence

---

*This playbook is a living document. Update traction points and objection responses as Sardis ships new features and closes new customers.*
