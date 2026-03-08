# 30-Day Ops, Outreach & Revenue Activation Plan

**Date:** 2026-03-09
**Scope:** March 9 – April 8, 2026
**Approach:** Parallel Tracks (4 concurrent workstreams)

---

## Context

Sardis has closed all technical hardening gaps. 1095 commits, 39 packages, 272 test files, 63 API routers, 52 DB migrations, 4 smart contracts, 9 AI framework SDKs, 5 protocol compliances (AP2, TAP, x402, UCP, A2A). CI green with 1600+ tests.

The platform needs to transition from "built" to "operating and selling."

**Key facts:**
- Revenue flow is fully implemented but disabled (missing `SARDIS_TREASURY_ADDRESS` env var)
- Mainnet deploy scripts ready, 2 contracts to deploy (SardisLedgerAnchor + RefundProtocol)
- 30+ companies in Attio CRM, 22 Gmail drafts ready, Wave 1A/1B campaigns designed
- Stripe/Visa/Mastercard all have active agent payment programs with open applications
- Target raise: $9M seed @ $36M pre-money (drafts only, not sending this month)
- Tempo x Stripe hackathon application submitted
- Warm leads: AutoGPT (Nicholas Tindle), Catena Labs (Sean), Base (Jesse Pollak)

---

## Track 1 — OPS & Revenue Activation (Weeks 1-2)

**Goal:** Mainnet live, fees collecting, first GMV proven.

### Week 1 (March 9-14)

| # | Task | Detail | Output |
|---|------|--------|--------|
| 1.1 | Create Treasury Safe | Base mainnet Safe multisig, founder as owner | Safe address |
| 1.2 | Mainnet deploy | `./scripts/deploy-mainnet.sh base` — SardisLedgerAnchor + RefundProtocol | 2 contract addresses |
| 1.3 | Set env vars | Cloud Run: `SARDIS_TREASURY_ADDRESS`, `SARDIS_PLATFORM_FEE_BPS=50`, contract addresses | Revenue flow active |
| 1.4 | Fee flow smoke test | Small tx verifying fee reaches treasury | Screenshot proof |
| 1.5 | Update deployment manifest | `contracts/deployments/base.json` + `MANIFEST.md` | Git commit |

### Week 2 (March 15-21)

| # | Task | Detail | Output |
|---|------|--------|--------|
| 1.6 | First merchant checkout | Self-hosted or test merchant with Pay-with-Sardis embed → first real GMV | Live GMV proof |
| 1.7 | Fee reporting | Treasury balance + fee history viewable (API or dashboard) | Endpoint live |
| 1.8 | Monitoring setup | Treasury balance alerts, fee dispatch failure alerts | Operational |

**Week 2 exit criteria:** Mainnet live, fees collecting to treasury, at least 1 proven transaction.

---

## Track 2 — OUTREACH & Pipeline Execute (Weeks 1-4)

**Goal:** Execute all existing outreach. Convert warm leads. Activate community channels.

### Week 1 (March 9-14)

| # | Task | Detail |
|---|------|--------|
| 2.1 | Send warm follow-ups | AutoGPT (Nicholas Tindle) + Catena Labs (Sean) — TODAY |
| 2.2 | AutoGPT PR submit | On reply → submit PR to `Significant-Gravitas/AutoGPT` |
| 2.3 | Forum posts (3) | CrewAI Discord (#community-tools) + n8n Community + LangChain Forum |
| 2.4 | Composio dashboard submit | Submit integration to composio.dev |
| 2.5 | Gmail draft cleanup | Update FROM to `contact@sardis.sh`, delete 4 duplicates, verify Clay emails |

### Week 2 (March 15-21)

| # | Task | Detail |
|---|------|--------|
| 2.6 | Wave 1A send (10 emails) | CrewAI, LangChain, Composio, n8n, E2B, Helicone, AgentOps, Activepieces, Humanloop, Lindy |
| 2.7 | n8n Creator Portal | Record 1-2 min demo video + submit |
| 2.8 | PR monitoring | langchain-ai/docs, vercel/ai, google/adk-python-community, coinbase/agentkit |

### Week 3 (March 22-28)

| # | Task | Detail |
|---|------|--------|
| 2.9 | Wave 1A Day 7 follow-up | Second touch to non-responders |
| 2.10 | Gmail cold batch send | 17 unique cold emails (Stampli, Ramp, Xelix, Airbase, Lio, Stacks, Skyvern, Procure.ai, Relevance AI, Dust, Sierra, Decagon, Lava Network, MultiOn, Parallel + LangChain Karan) |
| 2.11 | Wave 1B start (8 emails) | Dust, Lithic, Ramp, Zip, Mercury, Airwallex, Bridge, Fireblocks |

### Week 4 (March 29 – April 4)

| # | Task | Detail |
|---|------|--------|
| 2.12 | Wave 1A Day 14 final follow-up | Last chance email |
| 2.13 | Wave 1B Day 7 follow-up | |
| 2.14 | Pipeline review | Evaluate all replies, schedule demos/meetings |

**Week 4 exit criteria:** 35+ outreach emails sent, 3+ community posts live, 4 PRs monitored, all warm leads contacted.

---

## Track 3 — EXPANSION: New Segments + Card Networks (Weeks 2-4)

**Goal:** Open new distribution channels. Apply to Stripe/Visa/MC programs. Expand prospect base via Apollo.io.

### Week 2 (March 15-21)

| # | Task | Detail |
|---|------|--------|
| 3.1 | Apollo.io new target research | Find 50+ new leads: agent-payment, AI procurement, autonomous commerce companies |
| 3.2 | Stripe Partner Intake form | Fill https://stripe.events/LPMpartnerintake |
| 3.3 | Mastercard Start Path application | Agentic commerce track |
| 3.4 | Visa Developer account | Open sandbox at developer.visa.com |
| 3.5 | Stripe personal outreach | Jeff Weinstein (Product Lead, Payments Infra) + Jacob Petrie (Head of DevRel) — LinkedIn + email |

### Week 3 (March 22-28)

| # | Task | Detail |
|---|------|--------|
| 3.6 | Visa personal outreach | Rubail Birwadker (SVP Growth & Partnerships) — LinkedIn + email |
| 3.7 | Mastercard personal outreach | Jorn Lambert (CPO), Pablo Fourez (CDO) — LinkedIn + email |
| 3.8 | New segment email drafts | Segment-based templates for 50+ Apollo.io leads |
| 3.9 | New segment send (batch 1) | First 20 emails |
| 3.10 | Tempo x Stripe hackathon | Build + demo |

### Week 4 (March 29 – April 4)

| # | Task | Detail |
|---|------|--------|
| 3.11 | New segment send (batch 2) | Remaining 30 emails |
| 3.12 | Card network follow-up | Check Stripe/Visa/MC application status |
| 3.13 | Vendor partnerships | Send Lithic, Persona, Elliptic, Bridge.xyz outreach emails |

**Week 4 exit criteria:** 3 formal partnership applications submitted (Stripe/Visa/MC), 50+ new leads contacted, vendor partnerships initiated.

---

## Track 4 — INVESTOR PREP (Weeks 3-4)

**Goal:** Draft-ready investor materials at $9M/$36M pre. DO NOT SEND — hold for hackathon results and early traction signals.

### Week 3 (March 22-28)

| # | Task | Detail |
|---|------|--------|
| 4.1 | Traction snapshot | 1095 commits, 39 packages, 272 test files, 63 API routers, 52 migrations, 4 contracts, 9 SDKs, 5 protocols, mainnet live, revenue active |
| 4.2 | Pitch update | $9M / $36M pre narrative. Comp: Skyfire $9.5M, Payman $13.7M, Paid $33.3M@$100M, Natural $9.8M |
| 4.3 | Investor email template update | 28 investor pitches from $3M → $9M/$36M pre |
| 4.4 | Commit/PR traction doc | Last 200-300 commits: hardening, trust surface, evidence platform, control plane evolution |

### Week 4 (March 29 – April 4)

| # | Task | Detail |
|---|------|--------|
| 4.5 | 28 investor email drafts | Ready in Gmail, NOT SENT |
| 4.6 | Add hackathon results | Stripe hackathon outcome → investor narrative |
| 4.7 | Warm intro strategy | Map investor intro paths via Coinbase/Base network (Jesse Pollak, Luca Curran) |

**Week 4 exit criteria:** 28 investor drafts ready, pitch deck updated, traction doc written. Nothing sent.

---

## Traction Snapshot (as of March 9, 2026)

| Metric | Value |
|--------|-------|
| Total commits | 1,095 |
| Monorepo packages | 39 |
| Test files | 272 |
| API routers | 63 |
| DB migrations | 52 |
| Smart contracts | 4 |
| AI framework SDKs | 9 (LangChain, CrewAI, OpenAI Agents, Claude Agent SDK, Vercel AI SDK, Google ADK, Composio, Browser Use, AutoGPT) |
| Protocol compliance | 5 (AP2, TAP, x402, UCP, A2A) |
| Platform PRs submitted | 4 (langchain-ai, vercel/ai, google/adk, coinbase/agentkit) |
| CRM companies | 30+ in Attio |
| Email drafts ready | 22 Gmail + 10 Wave 1A + 8 Wave 1B |
| Warm leads | 4 (AutoGPT, Catena Labs, Base Protocol, Helicone) |

## Competitive Landscape

| Company | Funding | Valuation | Sardis Advantage |
|---------|---------|-----------|------------------|
| Skyfire | $9.5M seed | Undisclosed | Point solution (routing only). No policy engine, no cards, no compliance |
| Locus | YC F25 | Undisclosed | Base-only, basic payments. No multi-chain, no approval workflows |
| Payman | $13.7M seed+ | Undisclosed | Compliance focus but no crypto, no escrow, no anomaly detection |
| Paid | $33.3M | ~$100M | Results-based billing, different category. No agent wallets |
| Natural | $9.8M seed | Undisclosed | Early stage, limited public info |

**Sardis moat:** Only platform combining spending rules + risk scoring + goal drift detection + MPC custody + 5-chain support + virtual cards + KYC/AML + agent-to-agent escrow + team wallets + approval workflows + audit trail + kill switches + 9 framework SDKs.

---

## Card Network Outreach Targets

### Stripe
- **Programs:** Agentic Commerce Suite, Shared Payment Tokens (SPT), x402 Protocol, ACP
- **Apply:** https://stripe.events/LPMpartnerintake
- **Contacts:** Jeff Weinstein (Product Lead), Jacob Petrie (Head of DevRel)

### Visa
- **Programs:** Visa Intelligent Commerce (VIC), Trusted Agent Protocol (TAP), MCP Server
- **Apply:** https://developer.visa.com/
- **Contacts:** Rubail Birwadker (SVP Growth & Partnerships), Jack Forestell (Chief Product Officer)

### Mastercard
- **Programs:** Agent Pay, Agentic Tokens, Start Path (applications open)
- **Apply:** https://mastercard.com/us/en/innovation/partner-with-us/start-path.html
- **Contacts:** Jorn Lambert (CPO), Pablo Fourez (CDO)

---

## Revenue Model (Active)

- **Platform fee:** 50 BPS (0.50%) per transaction
- **Implementation:** `packages/sardis-core/src/sardis_v2_core/platform_fee.py`
- **Flow:** Merchant receives `net_amount`, treasury receives `fee_amount` as separate tx
- **Activation requires:** `SARDIS_TREASURY_ADDRESS` + `SARDIS_PLATFORM_FEE_BPS` env vars
- **Tracking:** `platform_fee_amount` + `net_amount` columns in `merchant_checkout_sessions`

---

## Success Metrics (30-day)

| Metric | Target |
|--------|--------|
| Mainnet contracts deployed | 2 (LedgerAnchor + RefundProtocol) |
| Revenue flow active | Yes (fee collecting to treasury) |
| First GMV | At least 1 live transaction with fee |
| Outreach emails sent | 75+ (10 Wave 1A + 8 Wave 1B + 17 cold + 50 new segment) |
| Community posts | 3+ (CrewAI, n8n, LangChain) |
| Platform submissions | 2 (Composio + n8n Creator Portal) |
| Card network applications | 3 (Stripe + Visa + MC) |
| Card network personal outreach | 5+ contacts |
| Investor drafts ready | 28 (not sent) |
| Design partner meetings | 3+ scheduled |
| Vendor partnerships initiated | 4 (Lithic, Persona, Elliptic, Bridge) |
