# Execution Guide: Week of March 8, 2026
## Copy-paste ready. Work top to bottom.

---

## PRIORITY 1: Send 2 Warm Follow-ups (TODAY)

### 1A. AutoGPT -- Nicholas Tindle
**To:** nicholas.tindle@agpt.co
**Subject:** One wallet per AutoGPT agent

> Hi Nicholas,
>
> Wanted to follow up on something we've been building that fits directly into AutoGPT's roadmap.
>
> As your agents scale, each one needs a way to transact autonomously. Sardis gives each agent its own non-custodial wallet with a spending policy you write in plain English. No per-transaction approvals, no shared keys.
>
> Would love to show you how it works. 15 minutes this week?
>
> Efe
> Sardis

**Pre-send:** Delete the older duplicate draft ("Sardis x AutoGPT -- checking in").
**Post-send:** When he responds, submit PR to `Significant-Gravitas/AutoGPT`. Code is ready at `prs/autogpt-blocks/sardis.py`.

### 1B. Catena Labs -- Sean
**To:** sean@catenalabs.com
**Subject:** The trust layer between Catena's agents and money

> Hi Sean,
>
> Good talking last time. Wanted to share where we've landed.
>
> Sardis is the execution layer for agent payments: each agent gets a non-custodial wallet with a spending policy in plain English. It transacts when the policy allows, stops when it doesn't, and everything is auditable.
>
> Happy to walk you through a live demo if useful.
>
> Efe
> Sardis

---

## PRIORITY 2: Post on 3 Community Forums (TODAY, ~10 min each)

### 2A. CrewAI Discord (#community-tools)

Copy-paste:

> **Sardis: Payment tool for CrewAI agents**
>
> Built sardis-crewai, a payment tool for CrewAI agents. Each agent gets a non-custodial wallet with spending policies you define in plain English. The agent executes within the policy, stops when it doesn't match.
>
> `pip install sardis-crewai`
>
> GitHub: github.com/EfeDurmaz16/sardis
> Docs: sardis.sh/docs
>
> Supports USDC/USDT on Base, Polygon, Ethereum, Arbitrum, Optimism. Happy to answer questions.

### 2B. n8n Community (Community Nodes category)

**Title:** Sardis: Policy-controlled payments for n8n workflows
Copy-paste for body:

> Published **n8n-nodes-sardis**: a community node that adds policy-controlled payment execution to n8n workflows.
>
> **What it does:**
> - Execute stablecoin payments (USDC, USDT) from non-custodial wallets
> - Check wallet balances
> - Verify spending policies before execution
> - Full audit trail for every transaction
>
> **Supported chains:** Base, Polygon, Ethereum, Arbitrum, Optimism
>
> **Install:** `npm install n8n-nodes-sardis` in your n8n instance
>
> Each wallet has spending policies in plain English (e.g. "max $500/day, approved vendors only"). The node checks policy before every payment.
>
> npm: https://www.npmjs.com/package/n8n-nodes-sardis
> GitHub: https://github.com/EfeDurmaz16/sardis
> Docs: https://sardis.sh/docs
>
> Feedback welcome!

### 2C. LangChain Forum (Integrations category)

**Title:** sardis-langchain: Payment tools for LangChain agents
Copy-paste for body:

> Published **sardis-langchain** on PyPI: payment tools for LangChain agents.
>
> **Tools included:**
> - `SardisPaymentTool` -- Execute policy-controlled payments
> - `SardisBalanceTool` -- Check wallet balances
> - `SardisPolicyCheckTool` -- Verify if a payment would pass policy before executing
>
> **How it works:**
> Each agent gets a non-custodial MPC wallet with spending policy guardrails you define in plain English. The agent proposes a payment, deterministic policy decides, full audit trail.
>
> **Supported:** USDC/USDT on Base, Polygon, Ethereum, Arbitrum, Optimism.
>
> ```
> pip install sardis-langchain
> ```
>
> PyPI: https://pypi.org/project/sardis-langchain/
> GitHub: https://github.com/EfeDurmaz16/sardis
> Docs: https://sardis.sh/docs
>
> Happy to answer questions or take feedback.

---

## PRIORITY 3: Submit Composio Dashboard Integration (TODAY)

**Steps:**
1. Go to composio.dev, log in
2. Navigate to integration submission / developer dashboard
3. Fill in using values from `prs/composio/integrations.yaml`:
   - Name: `sardis`
   - Display name: `Sardis`
   - Description: "Policy-controlled payments for AI agents. Execute stablecoin payments through non-custodial MPC wallets with spending guardrails."
   - Categories: finance, payments, crypto
   - Auth type: API key, header `X-API-Key`
   - Base URL: `https://api.sardis.sh`
   - Docs URL: `https://sardis.sh/docs`
   - OpenAPI spec: `https://api.sardis.sh/api/v2/openapi.json`
4. Submit

**Then** proceed to send Composio email (Wave 1A #3 to Karan Vaidya).

---

## PRIORITY 4: Wave 1A Emails (TUESDAY-THURSDAY, 9-11am recipient local time)

Send in numbered order. All emails are in `docs/marketing/first-wave-campaign-v2.md`.

| Day | # | Company | Person | Channel | Subject |
|-----|---|---------|--------|---------|---------|
| Tue | 1 | CrewAI | Joao Moura | Email + X DM | Sardis // CrewAI agent payments |
| Tue | 2 | LangChain | Harrison Chase | Email + LinkedIn | Sardis // LangChain agents and payment execution |
| Tue | 3 | Composio | Karan Vaidya | Email + X DM | Sardis // payments as a Composio tool |
| Wed | 4 | n8n | Jan Oberhauser | Email + LinkedIn | Sardis // payment node for n8n workflows |
| Wed | 5 | E2B | Vasek Mlejnsky | Email + X DM | Sardis // financial capabilities inside E2B sandboxes |
| Wed | 6 | Helicone | Scott Nguyen | Email + Direct | Sardis // Helicone next steps |
| Thu | 7 | AgentOps | Alex Reibman | Email + X DM | Sardis // payment failures in agent traces |
| Thu | 8 | Activepieces | Ashraf Samhouri | Email + LinkedIn | Sardis // payment piece for Activepieces |
| Thu | 9 | Humanloop | Raza Habib | Email + LinkedIn | Sardis // cost governance for multi-model teams |
| Thu | 10 | Lindy AI | Flo Crivello | Email + X DM | Sardis // Lindy agents and real transactions |

**Follow-up cadence:** Day 3, Day 7, Day 14 (templates in `customer-outreach-playbook.md` section 5).

---

## PRIORITY 5: Gmail Draft Cold Outreach (SAME WEEK, after Wave 1A starts)

### Dedup Decisions (4 overlapping accounts)

| Company | Action | Reason |
|---------|--------|--------|
| CrewAI (Joao) | **DELETE Gmail draft** | Wave 1A version is better. Same person. |
| Composio (Karan) | **DELETE Gmail draft** | Wave 1A version is better. Same person. |
| E2B (Vasek) | **DELETE Gmail draft** | Wave 1A version is better. Same person. |
| Lindy (Flo) | **DELETE Gmail draft** | Wave 1A version is better. Same person. |

### LangChain Special Case
- **Wave 1A** goes to Harrison Chase (CEO) -- send this one
- **Gmail draft** goes to Karan (different person, likely DevRel/partnerships) -- also send, but stagger 3-5 days after Harrison's email to avoid looking uncoordinated

### Remaining 17 Unique Gmail Drafts to Send

| # | Company | Contact | Temp |
|---|---------|---------|------|
| 1 | AutoGPT | Nicholas Tindle | WARM (already sent in Priority 1) |
| 2 | Catena Labs | Sean | WARM (already sent in Priority 1) |
| 3 | Stampli | Eyal | COLD |
| 4 | Ramp | Jonathan Avraham | COLD |
| 5 | Xelix | Fred | COLD |
| 6 | Airbase | Thejo | COLD |
| 7 | Lio | Temoc | COLD |
| 8 | Stacks | Albert | COLD |
| 9 | Skyvern | Suchintan | COLD |
| 10 | Procure.ai | Konstantin | COLD |
| 11 | Relevance AI | Daniel | COLD |
| 12 | Dust | Thibault | COLD |
| 13 | Sierra | Rosie | COLD |
| 14 | Decagon | Kelsey | COLD |
| 15 | Lava Network | Shehzan | COLD |
| 16 | MultiOn | Div | COLD |
| 17 | Parallel | Parag | COLD |

### Pre-send Checklist for Gmail Drafts
- [ ] Update FROM address on all drafts to `contact@sardis.sh`
- [ ] Delete duplicate AutoGPT draft ("Sardis x AutoGPT -- checking in")
- [ ] Delete 4 overlapping drafts (CrewAI, Composio, E2B, Lindy)
- [ ] Verify Clay enriched emails for the 20 cold addresses
- [ ] Resolve 3 open flags: inflow.finance, natural.tech, Locus Finance

---

## PRIORITY 6: n8n Creator Portal Submission (THIS WEEK)

**URL:** https://docs.n8n.io/integrations/creating-nodes/deploy/submit-community-nodes/

**Requires:** A 1-2 min screen recording showing:
1. Install `n8n-nodes-sardis` from npm in an n8n instance
2. Add the Sardis node to a workflow
3. Configure credentials
4. Execute a payment

**Tips for recording:**
- Use QuickTime or OBS
- 1280x720 minimum
- No audio required (but recommended)
- Keep it under 2 minutes
- Show the node working, not just the config

---

## PRIORITY 7: Wave 1B (IN 1-2 WEEKS, after Wave 1A responses)

8 accounts. Emails ready in `first-wave-campaign-v2.md`. Wait for Wave 1A data before sending.

For larger companies (Ramp, Zip, Mercury, Airwallex, Fireblocks): lead with secondary buyer, not CEO.

---

## TRACKING

Log all sends and responses in `docs/marketing/first-wave-ops.xlsx`.

| Metric | Target |
|--------|--------|
| Wave 1A sent | 10 emails + 10 DMs |
| Gmail drafts sent | 15 cold + LangChain Karan |
| Forum posts | 3 |
| Composio submission | 1 |
| n8n Creator Portal | 1 |
| Follow-up Day 3 | All non-responders |
| Follow-up Day 7 | All non-responders |
| Follow-up Day 14 | Final touch |

---

## PR MONITORING (ONGOING)

| PR | Repo | Status | Action |
|----|------|--------|--------|
| #2990 | langchain-ai/docs | Submitted | Check for review comments |
| Vercel AI SDK | vercel/ai | Submitted | Check for review comments |
| Google ADK | google/adk-python-community | Submitted, CLA signed | Check for merge |
| #992 | coinbase/agentkit | Submitted | Check for review comments |

Check each PR every 2-3 days. Respond to review comments within 24 hours.
