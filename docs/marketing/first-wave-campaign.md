# Sardis First-Wave Campaign
## 18 Highest-Conviction Targets — Sharpened Cold Emails

Generated: 2026-03-08
Version: 2.0 (post-review rewrite)

**What changed from v1:**
- Smaller, higher-conviction target set (18 vs 92)
- Shorter emails (under 100 words, most under 80)
- Diagnostic tone: ask about their reality, do not assert their pain
- No proof-stack bullets unless directly relevant to their workflow
- Diversified personas: not just CEO/Founders
- Each segment tied to one concrete demo scenario

---

## Selection Criteria

Leads were scored on four dimensions:

1. **Pain proximity** — Does this company have a workflow today where payment governance is a real, active gap (not a theoretical future need)?
2. **Buyer reachability** — Can we reach a decision-maker or strong champion who would feel this pain personally?
3. **Stage fit** — Is the company at a stage where they would actually evaluate and adopt infrastructure like Sardis (not too early, not too late/bureaucratic)?
4. **Integration surface** — Does Sardis already have a framework integration or technical hook that reduces friction?

---

## Demo Scenarios by Segment

| Segment | Demo Scenario | What You Show |
|---------|--------------|---------------|
| S1: Multi-Vendor AI Spend | "Policy layer across 3 providers" | Set per-model budget caps across OpenAI + Anthropic + Cohere. Show real-time enforcement when a team exceeds allocation. Show unified invoice reconciliation. |
| S2: Agent-Enabled Spend | "Agent proposes, policy decides" | Agent tries to make a purchase. Policy evaluates. Approve/deny/escalate in real time. Show the kill switch. Show the audit trail. |
| S3: Payouts & Disbursements | "Anomaly detection on payout batch" | Process a batch of 500 payouts. Flag anomalous amounts. Require approval for flagged items. Generate compliance evidence per payout. |
| S4: AP/AR Governance | "Unknown vendor escalation" | Invoice arrives from new vendor. Sardis enforces quorum approval. 4-eyes check. Amount matches PO or escalates. Tamper-evident evidence generated. |
| S5: Platform Enabler | "Embedded governance for platforms" | Show how a platform embeds Sardis so their users get policy controls without the platform becoming a PSP. Multi-rail routing demo. |
| S6: Commerce Ops | "Real-time decision governance" | Payment routing decision made by AI. Sardis enforces policy, generates proof chain. Show fail-closed default when policy is ambiguous. |

---

## THE 18 FIRST-WAVE TARGETS

---

### 1. CrewAI — João Moura (Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** Multi-agent framework where agents coordinate tasks. Direct integration exists. Agents that act but cannot pay is the exact gap.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // CrewAI agent payments

João,

When CrewAI agents finish a task that requires a purchase, what happens next?

Right now the human steps in. Curious if closing that loop programmatically is something your enterprise users have asked about, or if it has not come up yet.

We built an execution layer for that handoff. Happy to show you a 2-minute demo if it is relevant.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 2. LangChain — Harrison Chase (Co-Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** Largest agent framework. Already integrated. Enterprise customers building production agents need payment controls.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // LangChain agents and payment execution

Harrison,

LangChain agents can call tools, browse the web, and execute code. But when a workflow ends at "make a payment," the chain breaks.

Has that come up from enterprise teams building production agents? Or is payment execution not on their radar yet?

We have a LangChain integration that closes that gap. Would love to hear how you think about it.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 3. Composio — Karan Vaidya (Co-Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** Tool marketplace for AI agents. Sardis integration exists. Adding payment as a "tool" is a natural extension.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // payments as a Composio tool

Karan,

Composio gives agents access to 250+ tools. Is "make a payment" one of them yet?

Curious if agent developers have asked for financial tools in the marketplace, or if that is still too early for most use cases.

We built Sardis as a payment execution tool that agents can call with built-in policy controls. Might be a natural fit for the catalog.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 4. n8n — Jan Oberhauser (Founder & CEO)
**Segment:** S5 (Platform Enabler)
**Why first wave:** Open-source workflow automation. Sardis n8n node already exists. Workflows that end at payment execution are a known gap.
**Demo:** Embedded governance for platforms

**Subject:** Sardis // payment node for n8n workflows

Jan,

n8n workflows automate everything up to the payment step. Then the human takes over.

Is that a friction point users have flagged, or do most workflows not touch money?

We built an n8n node that adds governed payment execution to workflows. Policy-enforced, auditable. Curious if it is useful.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 5. E2B — Vasek Mlejnsky (Co-Founder & CEO)
**Segment:** S5 (Platform Enabler)
**Why first wave:** Cloud sandboxes for AI agents. Sardis E2B template exists. Agents in sandboxes need safe financial capabilities.
**Demo:** Agent proposes, policy decides (inside sandbox)

**Subject:** Sardis // financial capabilities inside E2B sandboxes

Vasek,

E2B gives agents a safe execution environment for code. But if an agent needs to spend money inside that sandbox, what happens?

Is that something developers have asked about, or is financial execution outside the scope of what sandboxes handle?

We have an E2B template that adds policy-controlled payment execution to sandboxes. Happy to share if relevant.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 6. Helicone — Scott Nguyen (Co-Founder & CEO)
**Segment:** S1 (Multi-Vendor AI Spend)
**Why first wave:** Already committed design partner. Multi-provider observability means they see the cost problem firsthand.
**Demo:** Policy layer across 3 providers

**Subject:** Sardis // Helicone next steps

Scott,

Following up on our earlier conversations. As Helicone customers route across more providers, the cost governance question keeps growing.

What is the most common way your customers handle budget enforcement across providers today? Is it mostly manual, or have you seen tooling emerge?

Would love to sync on where Sardis fits in that workflow.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 7. Humanloop — Raza Habib (Co-Founder & CEO)
**Segment:** S1 (Multi-Vendor AI Spend)
**Why first wave:** YC company, AI evaluation platform. Teams using Humanloop test across providers and need cost visibility.
**Demo:** Policy layer across 3 providers

**Subject:** Sardis // cost governance for multi-model teams

Raza,

Humanloop helps teams evaluate and deploy across models. When teams run production workloads on 3 or 4 providers simultaneously, who owns the cost governance?

Is that a problem your customers solve internally, or does it fall through the cracks?

We are building the policy layer for exactly that junction. Curious if it resonates.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 8. Lindy AI — Flo Crivello (Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** AI assistant platform where agents perform real tasks. Agents booking travel, purchasing, and managing expenses is a natural use case.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // Lindy agents and payment execution

Flo,

Lindy agents handle scheduling, research, and workflows. When one of those workflows ends at "book this" or "buy this," does the agent handle the payment, or does the user step back in?

Curious if that handoff is something you have thought about automating, or if it is not a priority yet.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 9. Dust — Stanislas Polu (Co-Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** Ex-OpenAI, building enterprise AI assistants. Enterprise customers need governed agent actions.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // agent actions with financial controls

Stan,

Dust builds enterprise AI assistants that take real actions. When those actions involve money (procurement, vendor payments, expense approvals), how do your enterprise customers handle the governance piece?

Is that something they build internally, or does it not come up often enough yet?

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 10. Ramp — Eric Glyman (Co-Founder & CEO)
**Segment:** S4 (AP/AR Governance)
**Why first wave:** AI-first corporate card and AP platform. Already using AI in expense management. Payment governance is adjacent to their core product.
**Demo:** Unknown vendor escalation

**Subject:** Sardis // governance layer for AI-driven AP

Eric,

Ramp uses AI across expense management and bill pay. When AI processes an invoice from a new vendor or an unusual amount, what does the approval chain look like?

Curious if the governance for AI-initiated payments is handled differently than human-initiated ones, or if it is the same flow.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 11. Zip — Rujul Zaparde (Co-Founder & CEO)
**Segment:** S4 (AP/AR Governance)
**Why first wave:** Intake-to-procure platform. Procurement workflows are exactly where payment governance matters most.
**Demo:** Unknown vendor escalation

**Subject:** Sardis // payment execution after procurement approval

Rujul,

Zip handles the intake-to-approval part of procurement beautifully. But after an approval is granted, how does the actual payment execution happen?

Is there a governance gap between "approved" and "paid," or is that tightly controlled today?

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 12. Mercury — Immad Akhund (Co-Founder & CEO)
**Segment:** S3 (Payouts & Disbursements)
**Why first wave:** Startup banking platform. High-volume payroll and vendor payments. Policy enforcement on outflows is a natural extension.
**Demo:** Anomaly detection on payout batch

**Subject:** Sardis // payout governance for Mercury

Immad,

Mercury handles banking for thousands of startups. When a startup processes a batch of vendor payments or contractor payouts, how much policy enforcement happens at the transaction level?

Is per-recipient or per-category governance something your customers have asked about, or is it mostly handled at the account level?

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 13. Airwallex — Jack Zhang (Co-Founder & CEO)
**Segment:** S3 (Payouts & Disbursements)
**Why first wave:** Global payment infrastructure. Cross-border disbursements at scale with compliance requirements.
**Demo:** Anomaly detection on payout batch

**Subject:** Sardis // cross-border payout governance

Jack,

Airwallex processes cross-border payments across 150+ countries. When a platform customer sends a batch of international disbursements, how is per-recipient policy enforcement handled?

Is compliance evidence generated per transaction at execution time, or reconstructed for audits later?

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 14. Lithic — Bo Jiang (Co-Founder & CEO)
**Segment:** S5 (Platform Enabler)
**Why first wave:** Virtual card infrastructure. Sardis already uses Lithic for cards. Governance above the card rails is the exact value prop.
**Demo:** Embedded governance for platforms

**Subject:** Sardis // governance layer above Lithic rails

Bo,

Lithic provides the card rails. But when a platform issues cards to AI agents or automated systems, who enforces spending policies beyond basic card controls?

Is that something your platform customers handle themselves, or is there demand for a governance layer above the card?

We are building exactly that layer, and we already use Lithic under the hood.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 15. Bridge — Zach Abrams (Co-Founder & CEO)
**Segment:** S5 (Platform Enabler)
**Why first wave:** Stablecoin payment infrastructure (acquired by Stripe). On-chain payment rails where governance is underdeveloped.
**Demo:** Embedded governance for platforms

**Subject:** Sardis // governance for stablecoin payments

Zach,

Bridge provides stablecoin payment rails. When a platform routes USDC payments through Bridge, what governance layer sits between the platform's intent and the execution?

Is there demand from your customers for deterministic policy enforcement on stablecoin flows, or is that still managed ad hoc?

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 16. Fireblocks — Michael Shaulov (Co-Founder & CEO)
**Segment:** S5 (Platform Enabler)
**Why first wave:** Enterprise digital asset custody. MPC wallets and policy engine overlap. Natural partnership or integration discussion.
**Demo:** Embedded governance for platforms

**Subject:** Sardis // agent-level governance for Fireblocks

Michael,

Fireblocks provides institutional-grade custody and MPC. As AI agents start needing to move digital assets, does the existing policy engine cover agent-specific controls (spending limits per agent, approval escalation, kill switches)?

Or is agent governance a separate problem from institutional custody governance?

Curious how you see that evolving.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 17. AgentOps — Alex Reibman (Co-Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** Agent observability platform. They see agent failures and gaps firsthand. "Agent tried to pay but could not" is an observable event.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // payment failures in agent traces

Alex,

AgentOps monitors agent executions. Do you see traces where agents attempt a financial action (purchase, payment, subscription) and hit a wall because there are no payment capabilities?

Curious how common that pattern is across your user base. We are building the execution layer for that exact gap.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

### 18. Activepieces — Ashraf Samhouri (Co-Founder & CEO)
**Segment:** S2 (Agent-Enabled Spend)
**Why first wave:** Open-source automation platform. Sardis Activepieces piece already exists. Workflow-to-payment gap is identical to n8n.
**Demo:** Agent proposes, policy decides

**Subject:** Sardis // payment piece for Activepieces

Ashraf,

Activepieces automates workflows across hundreds of apps. When a workflow needs to trigger a payment (vendor payment, subscription renewal, purchase order), how do users handle that today?

Is it a manual step, or have you seen demand for an automated payment piece with built-in controls?

We built one. Happy to show you if it is useful.

Best,
Efe Baran Durmaz / Founder, Sardis | sardis.sh

---

## FIRST-WAVE SUMMARY

| # | Company | Segment | Contact | Why High-Conviction |
|---|---------|---------|---------|-------------------|
| 1 | CrewAI | S2 | João Moura, CEO | Direct integration. Agents that act but cannot pay. |
| 2 | LangChain | S2 | Harrison Chase, CEO | Largest agent framework. Integration exists. |
| 3 | Composio | S2 | Karan Vaidya, CEO | Tool marketplace. Payment as a tool. |
| 4 | n8n | S5 | Jan Oberhauser, CEO | Workflow platform. Node exists. |
| 5 | E2B | S5 | Vasek Mlejnsky, CEO | Sandbox for agents. Template exists. |
| 6 | Helicone | S1 | Scott Nguyen, CEO | Committed design partner. |
| 7 | Humanloop | S1 | Raza Habib, CEO | YC. Multi-model evaluation. Cost governance gap. |
| 8 | Lindy AI | S2 | Flo Crivello, CEO | AI assistant that performs real tasks. |
| 9 | Dust | S2 | Stanislas Polu, CEO | Ex-OpenAI. Enterprise AI assistants. |
| 10 | Ramp | S4 | Eric Glyman, CEO | AI-first AP. Governance for AI-initiated payments. |
| 11 | Zip | S4 | Rujul Zaparde, CEO | Procurement. Approval-to-payment gap. |
| 12 | Mercury | S3 | Immad Akhund, CEO | Startup banking. Payout governance. |
| 13 | Airwallex | S3 | Jack Zhang, CEO | Cross-border disbursements at scale. |
| 14 | Lithic | S5 | Bo Jiang, CEO | Virtual card rails. Already integrated. |
| 15 | Bridge | S5 | Zach Abrams, CEO | Stablecoin rails. Governance gap. |
| 16 | Fireblocks | S5 | Michael Shaulov, CEO | MPC custody. Agent governance extension. |
| 17 | AgentOps | S2 | Alex Reibman, CEO | Agent observability. Sees payment failures. |
| 18 | Activepieces | S2 | Ashraf Samhouri, CEO | Automation platform. Piece exists. |

**Segment distribution:** S1: 2, S2: 7, S3: 2, S4: 2, S5: 5

**Note on S6 (Commerce Ops):** Intentionally excluded from first wave. The commerce and merchant ops targets (Shopify, Klarna, Stripe, etc.) are mostly large incumbents where Sardis is unlikely to be an immediate priority. These are better approached after traction with agent-native and workflow companies validates the thesis. Revisit in wave 2.

---

## WHAT IS DIFFERENT IN THESE EMAILS

**v1 pattern (too thesis-heavy):**
> "You probably have this problem. AI must be creating this governance gap. Sardis solves it with X, Y, Z. Here are our traction bullets."

**v2 pattern (diagnostic):**
> "Here is what I see about your workflow. Does this specific thing actually happen? Curious if it is a real problem or not."

Specific changes:

1. **No proof-stack bullets** unless the proof is directly about their workflow (e.g., "we already have an n8n node" is relevant to n8n; "25k SDK installs" is not).
2. **Questions ask about their reality**, not about whether they want Sardis. "Do you see traces where agents hit a payment wall?" is diagnostic. "Would you like deterministic policy enforcement?" is pitchy.
3. **Under 80 words in most cases.** The shorter the email, the higher the reply rate for cold outreach.
4. **No discovery disguised as assertion.** If we do not know whether they have the pain, we ask. We do not say "you probably deal with X."
5. **Demo offer is casual.** "Happy to show you a 2-minute demo if relevant" not "Let me walk you through our platform."

---

*This is the send-ready first wave. The remaining 74 leads from the v1 list form the wave 2 pipeline, to be refined after first-wave response data comes in.*
