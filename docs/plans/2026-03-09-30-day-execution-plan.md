# 30-Day Ops, Outreach & Revenue Activation — Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Take Sardis from "built" to "operating and selling" in 30 days — mainnet live, fees collecting, 75+ outreach emails sent, 3 card network applications submitted, 28 investor drafts ready.

**Architecture:** 4 parallel tracks executed concurrently. Track 1 (ops) provides the "live on mainnet" proof that Track 2-3 (outreach) references. Track 4 (investor) consumes traction from all other tracks.

**Tools:** Gmail API (via MCP), Apollo.io (via MCP), Attio CRM (via MCP), gh CLI, gcloud CLI, Foundry/forge, Safe UI, Playwright (for form submissions).

---

## Task 1: Treasury Safe Creation (Track 1 — Manual)

**Context:** Revenue flow needs a `SARDIS_TREASURY_ADDRESS`. This is a Base mainnet Safe multisig.

**Step 1:** Go to https://app.safe.global/new-safe/create?chain=base
- Network: Base
- Name: "Sardis Treasury"
- Owner 1: Your deployer wallet address
- Threshold: 1/1 (can add signers later)

**Step 2:** Record the Safe address

**Step 3:** Verify on BaseScan that the Safe is deployed

**Verification:** Safe address exists on Base mainnet and is controlled by your wallet.

---

## Task 2: Mainnet Contract Deployment (Track 1)

**Files:**
- Run: `scripts/deploy-mainnet.sh`
- Reference: `contracts/script/DeploySafeModules.s.sol`
- Update: `contracts/deployments/base.json`, `contracts/deployments/MANIFEST.md`

**Step 1:** Create `.env` file from template

```bash
cp .env.mainnet .env
```

Fill in:
```
PRIVATE_KEY=<your-deployer-private-key>
SARDIS_ADDRESS=<your-sardis-treasury-safe-from-task-1>
USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<your-alchemy-key>
BASESCAN_API_KEY=<your-basescan-key>
```

**Step 2:** Run deployment

```bash
cd contracts
forge script script/DeploySafeModules.s.sol:DeploySafeModules \
  --rpc-url base --broadcast --verify
```

**Step 3:** Record deployed addresses from output

**Step 4:** Update deployment manifest

Edit `contracts/deployments/base.json`:
```json
{
  "chain": "base",
  "chain_id": 8453,
  "status": "deployed",
  "deployed_at": "2026-03-XX",
  "deployer": "<deployer-address>",
  "contracts": {
    "ledger_anchor": "<deployed-address>",
    "refund_protocol": "<deployed-address>"
  }
}
```

**Step 5:** Commit

```bash
git add contracts/deployments/base.json contracts/deployments/MANIFEST.md
git commit -m "deploy(base): SardisLedgerAnchor + RefundProtocol on Base mainnet"
```

**Verification:** Both contracts verified on BaseScan. `forge verify-contract` returns success.

---

## Task 3: Activate Revenue Flow (Track 1)

**Context:** Platform fee is implemented in `packages/sardis-core/src/sardis_v2_core/platform_fee.py` but disabled because `SARDIS_TREASURY_ADDRESS` is not set.

**Step 1:** Set env vars on Cloud Run

```bash
gcloud run services update sardis-api-staging \
  --update-env-vars \
  SARDIS_TREASURY_ADDRESS=<safe-address-from-task-1>,\
  SARDIS_PLATFORM_FEE_BPS=50,\
  SARDIS_BASE_LEDGER_ANCHOR_ADDRESS=<from-task-2>,\
  SARDIS_BASE_REFUND_PROTOCOL_ADDRESS=<from-task-2>
```

**Step 2:** Verify API is running

```bash
curl https://api.sardis.sh/health
```

**Step 3:** Smoke test fee flow

Create a small checkout session and complete payment. Verify:
- `platform_fee_amount` is set in session record
- Fee tx is dispatched to treasury address
- Treasury Safe balance increases

**Verification:** Treasury Safe on BaseScan shows incoming USDC from fee dispatch.

---

## Task 4: Send Warm Follow-ups — TODAY (Track 2)

**Context:** 2 warm leads need follow-up today. Email templates exist.

**Step 1:** Send AutoGPT follow-up to Nicholas Tindle

Using Gmail MCP tool `gmail_create_draft` or update existing draft `r-1256647487528069597`:
- **To:** nicholas.tindle@agpt.co
- **From:** contact@sardis.sh (UPDATE before sending)
- **Subject:** One wallet per AutoGPT agent
- **Body:**
```
Hi Nicholas,

Wanted to follow up on something we've been building that fits directly
into AutoGPT's roadmap.

As your agents scale, each one needs a way to transact autonomously.
Sardis gives each agent its own non-custodial wallet with a spending
policy you write in plain English. No per-transaction approvals,
no shared keys.

We've also built 3 production-ready AutoGPT blocks (Pay, Balance,
Policy Check) — ready to PR when you'd like to take a look.

Would love to show you how it works. 15 minutes this week?

Efe
Sardis
```

**Step 2:** Send Catena Labs follow-up to Sean

- **To:** sean@catenalabs.com
- **Subject:** The trust layer between Catena's agents and money
- **Body:**
```
Hi Sean,

Good talking last time. Wanted to share where we've landed.

Sardis is the execution layer for agent payments: each agent gets a
non-custodial wallet with a spending policy in plain English. It
transacts when the policy allows, stops when it doesn't, and
everything is auditable.

We're now live on Base mainnet with fee-collecting checkout.
Happy to walk you through a live demo if useful.

Efe
Sardis
```

**Verification:** Both emails show as "sent" in Gmail.

---

## Task 5: Gmail Draft Cleanup (Track 2)

**Context:** 22 Gmail drafts exist but need cleanup before sending.

**Step 1:** Delete 4 duplicate drafts (keep Wave 1A versions)
- CrewAI (Joao) duplicate
- Composio (Karan) duplicate
- E2B (Vasek) duplicate
- Lindy (Flo) duplicate

**Step 2:** Update FROM address on remaining 18 drafts to `contact@sardis.sh`

**Step 3:** Verify Clay-enriched email addresses — cross-check with Apollo.io

Using Apollo MCP tools:
```
apollo_people_match for each contact → verify email
```

**Step 4:** Flag and resolve 3 data issues:
- inflow.finance → verify correct company
- natural.tech → verify domain
- Locus Finance → identify correct domain

**Verification:** 17 unique cold drafts ready with verified emails, correct FROM address.

---

## Task 6: Community Forum Posts (Track 2)

**Context:** Copy-paste templates exist in `docs/marketing/execution-guide-week-of-march-8.md`.

**Step 1:** Post to CrewAI Discord (#community-tools)
```
**Sardis: Payment tool for CrewAI agents**

Built sardis-crewai, a payment tool for CrewAI agents. Each agent
gets a non-custodial wallet with spending policies you define in
plain English. The agent executes within the policy, stops when
it doesn't match.

pip install sardis-crewai

GitHub: github.com/EfeDurmaz16/sardis
Docs: sardis.sh/docs

Supports USDC/USDT on Base, Polygon, Ethereum, Arbitrum, Optimism.
Happy to answer questions.
```

**Step 2:** Post to n8n Community (Community Nodes category)
```
Title: Sardis: Policy-controlled payments for n8n workflows
Body: Published n8n-nodes-sardis community node with payment execution,
balance checks, policy verification, audit trails.
npm: https://www.npmjs.com/package/n8n-nodes-sardis
```

**Step 3:** Post to LangChain Forum (Integrations category)
```
Title: sardis-langchain: Payment tools for LangChain agents
Body: Published on PyPI with SardisPaymentTool, SardisBalanceTool,
SardisPolicyCheckTool. Non-custodial MPC wallets with spending policies.
PyPI: https://pypi.org/project/sardis-langchain/
```

**Verification:** 3 posts live with working links.

---

## Task 7: Composio Dashboard Submission (Track 2)

**Context:** Integration config at `prs/composio/integrations.yaml`.

**Step 1:** Log into composio.dev developer dashboard

**Step 2:** Fill submission:
- Name: `sardis`
- Display name: `Sardis`
- Auth: API key, header `X-API-Key`
- Base URL: `https://api.sardis.sh`
- OpenAPI spec: `https://api.sardis.sh/api/v2/openapi.json`

**Step 3:** Submit for review

**Verification:** Composio shows submission as "pending review."

---

## Task 8: Wave 1A Email Send — 10 Emails (Track 2, Week 2)

**Context:** Templates in `docs/marketing/first-wave-campaign-v2.md`. Send Tue-Thu 9-11am recipient local time.

**Step 1:** Day 1 (Tuesday) — Send 2:
- CrewAI → João Moura (joao@crewai.com) — Subject: "Sardis // CrewAI agent payments"
- LangChain → Harrison Chase — Subject: "Sardis // LangChain agents and payment execution"

**Step 2:** Day 2 (Wednesday) — Send 3:
- n8n → Jan Oberhauser — Subject: "Sardis // payment node for n8n workflows"
- E2B → Vasek Mlejnsky (vasek@e2b.dev) — Subject: "Sardis // financial capabilities inside E2B sandboxes"
- Helicone → Scott Nguyen (scott@helicone.ai) — Subject: "Sardis // Helicone next steps"

**Step 3:** Day 3 (Thursday) — Send 5:
- AgentOps → Alex Reibman (alex@agentops.ai)
- Activepieces → Ashraf Samhouri (ashraf@activepieces.com)
- Humanloop → Raza Habib (raza@humanloop.com)
- Lindy AI → Flo Crivello (flo@lindy.ai)
- Composio → Karan Vaidya (karan@composio.dev)

**Step 4:** Log all sends in tracking doc / Attio CRM

**Verification:** 10 emails sent, all tracked in CRM with sent date.

---

## Task 9: PR Monitoring (Track 2, Weekly)

**Step 1:** Check PR status every 2-3 days:

```bash
gh pr view --repo langchain-ai/docs 2990
gh pr list --repo vercel/ai --author EfeDurmaz16
gh pr list --repo google/adk-python-community --author EfeDurmaz16
gh pr view --repo coinbase/agentkit 992
```

**Step 2:** Respond to review comments within 24 hours

**Verification:** All PRs either merged or actively in review with no stale comments.

---

## Task 10: Apollo.io New Segment Research (Track 3, Week 2)

**Context:** Need 50+ new leads beyond existing pipeline.

**Step 1:** Search Apollo.io for companies in these segments:

Using `apollo_mixed_companies_search`:
- Keywords: "AI agent payments", "autonomous procurement", "agent commerce"
- Keywords: "AI spending", "AI financial", "agent wallet"
- Industry: fintech, AI/ML, developer tools
- Employee count: 10-500
- Funding: Seed to Series B

**Step 2:** For top 50 results, enrich contacts:

Using `apollo_mixed_people_api_search`:
- Titles: CTO, VP Engineering, Head of AI, Head of Product, Founder, CEO
- Get verified emails

**Step 3:** Segment results into 6 categories (from customer-outreach-playbook.md):
- S1: Multi-Vendor AI Spend
- S2: Agent-Enabled Spend
- S3: Recurring Payouts & Disbursements
- S4: B2B AP/AR & Invoice Automation
- S5: Platform & Ecosystem Enabler
- S6: Commerce & Merchant Operations

**Step 4:** Draft emails using segment-specific templates from `docs/marketing/customer-outreach-playbook.md`

**Step 5:** Add all new companies to Attio CRM

**Verification:** 50+ new leads with verified emails, segmented and drafted, in Attio.

---

## Task 11: Stripe Partner Application (Track 3, Week 2)

**Step 1:** Fill Stripe Partner Intake form at https://stripe.events/LPMpartnerintake

Key fields:
- Company: Sardis
- Website: sardis.sh
- Description: Trust and control plane for AI agent payments. Policy-enforced, approval-aware, auditable payments across stablecoins and fiat rails.
- Integration type: Technology partner — agent payment infrastructure
- Relevant products: Agentic Commerce Suite, Shared Payment Tokens, x402 Protocol
- Current stack: USDC on Base (x402 compatible), Stripe Issuing for virtual cards

**Step 2:** Follow up with confirmation email

**Verification:** Confirmation email received from Stripe.

---

## Task 12: Mastercard Start Path Application (Track 3, Week 2)

**Step 1:** Apply at https://mastercard.com/us/en/innovation/partner-with-us/start-path.html

Key fields:
- Track: Agentic Commerce
- Company: Sardis
- Stage: Seed (pre-revenue, mainnet)
- Description: Financial operating system for AI agents — spending policies, risk scoring, compliance, multi-chain payments, virtual cards, audit trails
- Competitive advantage: Only platform combining policy engine + risk scoring + MPC custody + 5-chain support + 9 framework SDKs
- Mastercard integration: Agent Pay tokenized payments, Agentic Tokens for agent-initiated commerce

**Verification:** Application submitted, confirmation received.

---

## Task 13: Visa Developer Account (Track 3, Week 2)

**Step 1:** Register at https://developer.visa.com/

**Step 2:** Request sandbox access for:
- Visa Intelligent Commerce (VIC)
- Visa Direct
- Trusted Agent Protocol

**Verification:** Developer account active, sandbox credentials received.

---

## Task 14: Card Network Personal Outreach (Track 3, Weeks 2-3)

**Step 1:** Draft and send LinkedIn messages + emails to:

**Stripe (Week 2):**
- Jeff Weinstein (Product Lead, Payments Infrastructure)
  - Message angle: x402 + USDC/Base alignment, SPT integration opportunity
- Jacob Petrie (Head of Developer Relations)
  - Message angle: 9 AI framework SDK integrations, developer ecosystem overlap

**Visa (Week 3):**
- Rubail Birwadker (SVP, Head of Growth, Products & Partnerships)
  - Message angle: TAP protocol alignment (Sardis implements TAP), VIC integration

**Mastercard (Week 3):**
- Jorn Lambert (Chief Product Officer)
  - Message angle: Agent Pay + Sardis policy engine = production-safe agentic commerce
- Pablo Fourez (Chief Digital Officer)
  - Message angle: Start Path application, pilot proposal

**Email template for all:**
```
Subject: Sardis — agent payment trust layer + [Company] integration

Hi [Name],

I'm building Sardis — the trust and control plane for AI agent payments.
We give each agent a non-custodial wallet with deterministic spending
policies, risk scoring, approval workflows, and tamper-evident audit
trails. Currently live on Base mainnet with 9 AI framework SDK
integrations (LangChain, CrewAI, OpenAI Agents, etc.).

[Company-specific hook]:
- Stripe: We're aligned with x402 (USDC on Base) and interested in
  SPT integration for agentic commerce.
- Visa: We implement the Trusted Agent Protocol and would like to
  explore VIC integration.
- Mastercard: We've applied to Start Path (agentic commerce track)
  and see strong alignment with Agent Pay.

Would love 15 minutes to explore how we might work together.

Efe Baran Durmaz
Founder, Sardis
sardis.sh
```

**Verification:** 5 messages sent (2 Stripe, 1 Visa, 2 Mastercard). Tracked in Attio.

---

## Task 15: Wave 1A Follow-ups + Cold Batch (Track 2, Week 3)

**Step 1:** Wave 1A Day 7 follow-up — resend to non-responders with shorter message:
```
Subject: Re: [original subject]

Hi [Name],

Following up on my note last week. Happy to jump on a quick 15-min
call if useful — or just reply here with any questions.

Efe
```

**Step 2:** Send 17 Gmail cold emails (already drafted, cleaned in Task 5)

**Step 3:** Start Wave 1B — 8 harder-reach emails (templates in `first-wave-campaign-v2.md`)

**Step 4:** Log all sends in Attio CRM

**Verification:** 25+ additional emails sent this week. All tracked.

---

## Task 16: New Segment Email Send (Track 3, Weeks 3-4)

**Step 1:** Week 3 — Send batch 1 (20 emails) from Apollo.io research (Task 10)

**Step 2:** Week 4 — Send batch 2 (remaining 30 emails)

**Step 3:** Track all in Attio CRM with segment tag

**Verification:** 50 new-segment emails sent over 2 weeks.

---

## Task 17: Vendor Partnership Outreach (Track 3, Week 4)

**Context:** Templates in `docs/design-partner/partner-outreach-emails.md`.

**Step 1:** Send to Lithic — production card issuing partnership
**Step 2:** Send to Persona — KYC/KYB production rollout
**Step 3:** Send to Elliptic — AML/sanctions integration
**Step 4:** Send to Bridge.xyz — fiat on/off-ramp partnership

**Verification:** 4 vendor emails sent, tracked in Attio.

---

## Task 18: Traction Snapshot Document (Track 4, Week 3)

**Files:**
- Create: `docs/investor/traction-snapshot-2026-03.md`

**Step 1:** Generate traction stats from repo:

```bash
git log --oneline | wc -l                    # total commits
ls packages/ | wc -l                         # packages
find tests/ packages/*/tests/ -name "test_*.py" | wc -l  # test files
ls packages/sardis-api/src/sardis_api/routers/*.py | wc -l  # API routers
ls packages/sardis-api/migrations/*.sql | wc -l  # migrations
```

**Step 2:** Write traction snapshot document including:
- Repo stats (commits, packages, tests, routers, migrations, contracts)
- Framework integrations (9 SDKs with links)
- Protocol compliance (5 protocols)
- Platform PRs submitted (4 with status)
- Competitive positioning table
- Moat analysis (6 unique capabilities)
- Recent commit highlights (last 50 feature commits)

**Step 3:** Commit

```bash
git add -f docs/investor/traction-snapshot-2026-03.md
git commit -m "docs(investor): add March 2026 traction snapshot for seed raise"
```

**Verification:** Document committed with accurate, current stats.

---

## Task 19: Investor Email Template Update (Track 4, Week 3-4)

**Context:** 28 investor pitches exist but reference $3M seed. Update to $9M/$36M pre.

**Step 1:** Read existing investor email templates:
- File: `docs/marketing/investor-cold-emails.md` (or similar)

**Step 2:** Update all 28 templates:
- Raise: $3M → $9M seed
- Valuation: update to $36M pre-money
- Narrative: "trust layer for agent payments" + "live on mainnet" + "revenue-generating"
- Traction: reference traction snapshot from Task 18
- Comp table: Skyfire $9.5M, Payman $13.7M, Paid $33.3M@$100M
- Use case: $8-10M for audits, card programs, licenses, fiat rails, hiring

**Step 3:** Create 28 Gmail drafts (NOT SEND)

Using Gmail MCP `gmail_create_draft` for each investor, organized by tier:
- Tier 1: Better Tomorrow Ventures, Abstract Ventures, QED Investors, The Fintech Fund
- Tier 2: Draper Associates, Paradigm, Foundation Capital
- Tier 3: Revo Capital, 212, Collective Spark, Sistem Global, TechOne, Seedcamp
- Tier 4: Hustle Fund, Precursor Ventures, 500 Global
- Tier 5: Balaji, Immad Akhund, Eric Glyman, Zach Abrams, Guillermo Rauch, others
- Tier 6: Accelerators

**Step 4:** Commit template updates

**Verification:** 28 Gmail drafts created (NOT SENT). Templates updated in repo.

---

## Task 20: Hackathon Results + Warm Intro Strategy (Track 4, Week 4)

**Step 1:** After Tempo x Stripe hackathon:
- Document results (placement, demo feedback, contacts made)
- Add to investor narrative and traction snapshot

**Step 2:** Map warm intro paths through existing network:
- Jesse Pollak (Base) → which investors does he know?
- Luca Curran (Coinbase) → Coinbase Ventures, a16z crypto
- Hackathon contacts → Stripe Ventures, any judges

**Step 3:** Document intro strategy in `docs/investor/warm-intro-map.md`

**Verification:** Intro map documented with specific ask per connection.

---

## Task 21: Final Follow-ups + Pipeline Review (Track 2, Week 4)

**Step 1:** Wave 1A Day 14 final follow-up to remaining non-responders:
```
Subject: Re: [original]

Hi [Name], closing the loop on this. If timing isn't right, no worries
at all. Happy to reconnect whenever agent payments becomes relevant
for [Company].

Efe
```

**Step 2:** Wave 1B Day 7 follow-up

**Step 3:** Pipeline review meeting prep:
- Count total emails sent (target: 75+)
- Count replies received
- Count meetings scheduled
- Classify: interested / not now / no response
- Update Attio CRM with latest status

**Step 4:** Commit final tracking update

**Verification:** All follow-ups sent. Pipeline status clear in Attio. 75+ total outreach completed.

---

## Weekly Cadence Summary

| Day | Track 1 (Ops) | Track 2 (Outreach) | Track 3 (Expansion) | Track 4 (Investor) |
|-----|---------------|--------------------|--------------------|-------------------|
| W1 Mon | Treasury Safe | Warm follow-ups (2) | — | — |
| W1 Tue | Mainnet deploy | Forum posts (3) | — | — |
| W1 Wed | Env vars + smoke test | Composio submit | — | — |
| W1 Thu | Deploy manifest commit | Gmail cleanup | — | — |
| W1 Fri | — | — | — | — |
| W2 Mon | First merchant setup | Wave 1A Day 1 (2) | Apollo.io research | — |
| W2 Tue | Fee reporting | Wave 1A Day 2 (3) | Stripe partner form | — |
| W2 Wed | Monitoring | Wave 1A Day 3 (5) | MC Start Path app | — |
| W2 Thu | — | n8n Creator Portal | Visa Dev account | — |
| W2 Fri | — | PR monitoring | Stripe personal outreach | — |
| W3 Mon | — | Wave 1A Day 7 f/u | New segment drafts | Traction snapshot |
| W3 Tue | — | Gmail cold batch (17) | Visa outreach | Pitch update |
| W3 Wed | — | Wave 1B start (8) | MC outreach | Investor templates |
| W3 Thu | — | — | New segment batch 1 (20) | Commit/PR traction doc |
| W3 Fri | — | — | Hackathon prep | — |
| W4 Mon | — | Wave 1A Day 14 f/u | New segment batch 2 (30) | Investor drafts |
| W4 Tue | — | Wave 1B Day 7 f/u | Card network follow-up | Investor drafts |
| W4 Wed | — | — | Vendor partnerships (4) | Hackathon results |
| W4 Thu | — | Pipeline review | — | Warm intro strategy |
| W4 Fri | — | — | — | Final review |

---

## Exit Criteria (April 8)

- [ ] Mainnet: 2 contracts deployed on Base, verified on BaseScan
- [ ] Revenue: Fee flow active, at least 1 transaction with fee collected
- [ ] Outreach: 75+ emails sent across all waves and segments
- [ ] Community: 3+ forum posts live
- [ ] Submissions: Composio + n8n Creator Portal submitted
- [ ] Card networks: 3 formal applications (Stripe/Visa/MC) + 5 personal contacts
- [ ] Investors: 28 drafts ready in Gmail (NOT sent), traction doc committed
- [ ] CRM: All contacts tracked in Attio with current status
- [ ] Meetings: 3+ design partner meetings scheduled
