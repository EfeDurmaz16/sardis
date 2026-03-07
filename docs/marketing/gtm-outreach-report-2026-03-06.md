# Sardis GTM Outreach Report
**Date:** March 6, 2026
**Prepared for:** Efe (Founder, Sardis)
**Scope:** Full outreach cycle — enrichment, CRM setup, email drafts

---

## Executive Summary

| Metric | Count |
|---|---|
| Companies in Attio (total) | 30 |
| Warm leads (active) | 4 |
| Cold targets outreached | 20 |
| Rejected / DNC | 6 |
| Gmail drafts created | 22 |
| — Warm follow-ups | 2 |
| — Cold outreach | 20 |
| Clay enrichment jobs launched | 23 |
| Apollo emails retrieved | 0 (blocked — see flags) |
| Flags requiring attention | 3 |

---

## Step 1: Clay Enrichment

Clay enrichment was launched for all 22 cold targets + Catena Labs (23 total). Enrichment is **asynchronous** — emails and contact data will populate in the Clay widget over the coming minutes/hours.

**Targets enriched:** stampli.com, lindy.ai, ramp.com, xelix.com, airbase.com, e2b.dev, lio.ai, inflow.finance, stacks.ai, skyvern.com, crewai.com, procure.ai, relevanceai.com, dust.tt, langchain.com, sierra.ai, decagon.ai, natural.tech, lava.xyz, multion.ai, composio.dev, parallel.ai, catenalabs.com

**Job parameters:** Title targets — CTO, VP Engineering, Head of AI, Head of Platform, VP Product, Founder, Head of Partnerships. Waterfall email enrichment enabled.

---

## Step 2: Apollo Email Backup

**Status: Blocked — API_INACCESSIBLE**

All Apollo endpoints (`mixed_people_api_search`, `people_bulk_match`, `people_match`) returned `API_INACCESSIBLE` on the free plan. No emails were retrieved via Apollo.

**Workaround applied:** All cold email drafts use guessed email patterns:
- Founders: `firstname@domain.com`
- Other roles: `firstname.lastname@domain.com`

**Action required:** Upgrade Apollo plan to unlock bulk enrichment, then re-verify all 20 cold email addresses before sending.

---

## Step 3: Attio GTM Pipeline

**30 companies upserted across 3 categories.**

> **Note:** The Attio MCP does not expose a `create-list` endpoint. The "GTM Pipeline" list must be created manually in the Attio UI. GTM stage has been encoded in each company's `description` field as a workaround. Once the list is created, companies can be added manually using the stage data below.

### Warm Leads (4) — Do Not Cold Email

| Company | Domain | Contact | Stage | Notes |
|---|---|---|---|---|
| Base Protocol | base.org | Jesse (jesse@base.org) | Awaiting Reply | Do not contact — waiting on Jesse's response |
| Helicone | helicone.ai | (enrichment pending) | Hold | Wait for Series A close |
| AutoGPT | agpt.co | Nicholas Tindle (nicholas.tindle@agpt.co) | Follow-up Sent | Warm follow-up drafted ✅ |
| Catena Labs | catenalabs.com | Sean (sean@catenalabs.com) | Follow-up Sent | Warm follow-up drafted ✅ |

### Cold Targets (20) — Email Drafted

| Company | Domain | ICP Score | Contact | Email |
|---|---|---|---|---|
| Stampli | stampli.com | 76 | Eyal | eyal@stampli.com |
| Lindy | lindy.ai | 74 | Flo | flo@lindy.ai |
| Ramp | ramp.com | 73 | Jonathan Avraham | jonathan.avraham@ramp.com |
| Xelix | xelix.com | 72 | Fred | fred@xelix.com |
| Airbase | airbase.com | 71 | Thejo | thejo@airbase.com |
| E2B | e2b.dev | 68 | Vasek | vasek@e2b.dev |
| Lio | lio.ai | 68 | Temoc | temoc@lio.ai |
| Stacks.ai | stacks.ai | 65 | Albert | albert@stacks.ai |
| Skyvern | skyvern.com | 64 | Suchintan | suchintan@skyvern.com |
| CrewAI | crewai.com | 62 | Joao | joao@crewai.com |
| Procure.ai | procure.ai | 62 | Konstantin | konstantin@procure.ai |
| Relevance AI | relevanceai.com | 62 | Daniel | daniel@relevanceai.com |
| Dust | dust.tt | 62 | Thibault | thibault@dust.tt |
| LangChain | langchain.com | 61 | Karan | karan@langchain.com |
| Sierra.ai | sierra.ai | 59 | Rosie | rosie@sierra.ai |
| Decagon | decagon.ai | 59 | Kelsey | kelsey@decagon.ai |
| Lava Network | lava.xyz | 58 | Shehzan | shehzan@lava.xyz |
| MultiOn | multion.ai | 57 | Div | div@multion.ai |
| Composio | composio.dev | 56 | Karan | karan@composio.dev |
| Parallel.ai | parallel.ai | 55 | Parag | parag@parallel.ai |

### Rejected / DNC (6)

| Company | Domain | Reason |
|---|---|---|
| Marqeta | marqeta.com | Rejected |
| Bridge | bridge.xyz | Rejected (acquired by Stripe) |
| Stripe | stripe.com | Rejected (competitor/acquirer) |
| Rain | rain.com | Rejected |
| Lithic | lithic.com | Current vendor — not a GTM target |
| Lightspark | lightspark.com | Rejected |

---

## Step 4: Gmail Drafts

**22 total drafts created.** All are in Gmail drafts folder.
⚠️ **Before sending:** Update the FROM address to `contact@sardis.sh` (Gmail API does not allow setting sender programmatically).

### Warm Follow-ups (2)

#### 1. AutoGPT — Nicholas Tindle
**To:** nicholas.tindle@agpt.co
**Draft ID:** r-1256647487528069597
**Subject:** AutoGPT + Sardis — one wallet per agent

---

#### 2. Catena Labs — Sean
**To:** sean@catenalabs.com
**Draft ID:** r5575990574239193366
**Subject:** Sardis x Catena Labs — building the trust layer together

---

### Cold Outreach (20)

#### 1. Stampli — Eyal
**To:** eyal@stampli.com | **Draft ID:** r8378314541507558259
**Subject:** Sardis + Stampli — completing the last mile of AP automation

#### 2. Lindy — Flo
**To:** flo@lindy.ai | **Draft ID:** r-7174077703790766674
**Subject:** Lindy + Sardis — safe spending for your AI agents

#### 3. Ramp — Jonathan Avraham *(avoiding Carolyn Zhao)*
**To:** jonathan.avraham@ramp.com | **Draft ID:** r-8406418179836854959
**Subject:** Sardis + Ramp — payment infrastructure for Ramp-powered AI agents

#### 4. Xelix — Fred
**To:** fred@xelix.com | **Draft ID:** r-6657638857837558642
**Subject:** Sardis + Xelix — closing the loop on AI-driven spend control

#### 5. E2B — Vasek
**To:** vasek@e2b.dev | **Draft ID:** r-5957362585853382968
**Subject:** E2B + Sardis — safe payment execution for your sandbox agents

#### 6. Lio — Temoc
**To:** temoc@lio.ai | **Draft ID:** r8246758593797772571
**Subject:** Lio + Sardis — financial execution layer for your AI agents

#### 7. Airbase — Thejo
**To:** thejo@airbase.com | **Draft ID:** r6018978292875988875
**Subject:** Sardis + Airbase — safe spending for AI-native finance teams

#### 8. Stacks.ai — Albert
**To:** albert@stacks.ai | **Draft ID:** r-5533155060881924184
**Subject:** Stacks + Sardis — payment rails for your AI agents

#### 9. Skyvern — Suchintan
**To:** suchintan@skyvern.com | **Draft ID:** r-6046571055624785465
**Subject:** Skyvern + Sardis — when your browser agent needs to pay

#### 10. CrewAI — Joao
**To:** joao@crewai.com | **Draft ID:** r-6921209496421069946
**Subject:** CrewAI + Sardis — giving your agents a safe wallet

#### 11. Procure.ai — Konstantin
**To:** konstantin@procure.ai | **Draft ID:** r-6974961253796373221
**Subject:** Procure.ai + Sardis — closing the loop on autonomous procurement

#### 12. Relevance AI — Daniel
**To:** daniel@relevanceai.com | **Draft ID:** r-4509464083076906133
**Subject:** Relevance AI + Sardis — the payment primitive your agents are missing

#### 13. Dust — Thibault
**To:** thibault@dust.tt | **Draft ID:** r-7176223760747594609
**Subject:** Dust agents + Sardis — safe spending for enterprise AI

#### 14. LangChain — Karan
**To:** karan@langchain.com | **Draft ID:** r-4156500550574979147
**Subject:** LangChain agents + Sardis — payments as a first-class primitive

#### 15. Sierra.ai — Rosie
**To:** rosie@sierra.ai | **Draft ID:** r3182145722568284525
**Subject:** Sierra agents + Sardis — closing the loop on financial resolution

#### 16. Decagon — Kelsey
**To:** kelsey@decagon.ai | **Draft ID:** r4893556846977499750
**Subject:** Decagon + Sardis — autonomous financial resolution for support AI

#### 17. Lava Network — Shehzan
**To:** shehzan@lava.xyz | **Draft ID:** r-5667187786252694290
**Subject:** Sardis + Lava — payment rails for AI agents on-chain

#### 18. MultiOn — Div
**To:** div@multion.ai | **Draft ID:** r6893215790484118628
**Subject:** MultiOn + Sardis — safe payments when your agent hits checkout

#### 19. Composio — Karan
**To:** karan@composio.dev | **Draft ID:** r-311647990105469012
**Subject:** Composio + Sardis — the missing payment tool for your agent stack

#### 20. Parallel.ai — Parag
**To:** parag@parallel.ai | **Draft ID:** r5673531148304294024
**Subject:** Sardis + Parallel — financial infrastructure for your agents

---

## Key Enrichment Signals

**Decagon** — $100-250M raised (a16z, Accel, Bain Capital). One of the best-funded AI support agent plays. If they're building autonomous resolution, Sardis is the missing financial layer. High priority.

**Sierra.ai** — Founded by Bret Taylor (ex-Salesforce CEO, ex-Twitter Chairman) + Pat Grady (Sequoia). Enterprise pedigree is very high. Customer agents issuing refunds/credits are a clear wedge. High priority.

**Parallel.ai** — Founded by Parag Agrawal (ex-Twitter/X CEO). Stealth profile, sophisticated AI team. Worth a carefully crafted note — Parag will have seen a lot of pitches.

**Xelix** — Processes $750B+ in annual enterprise spend. Their AI is already touching massive financial decisions. The pitch almost writes itself.

**Ramp** — One of the fastest-growing fintechs in the US. They're building AI into their own product. Partnership angle is strong — Sardis as the policy layer for Ramp-native AI agents. Targeted Jonathan Avraham (Head of Partnerships - Financial Products) specifically to avoid Carolyn Zhao (already in contact).

**CrewAI / LangChain / Composio** — Framework and tooling players. The integration/partnership angle is stronger than pure sales here. A native payment tool integration could drive developer adoption for Sardis.

**MultiOn** — Web browsing agent. The checkout problem is the most visceral demonstration of why Sardis exists. Demo potential is very high.

---

## Flags Requiring Attention

### 🚩 Flag 1: inflow.finance — Wrong Company
Clay returned a Nigerian personal finance consumer app (Lagos) instead of the intended B2B target. **No email was drafted for inflow.finance.** Verify the correct company/domain before pursuing.

### 🚩 Flag 2: natural.tech — No Results
Clay returned empty for natural.tech. Company may be too small, defunct, or using a different domain. **No email was drafted.** Investigate before pursuing.

### 🚩 Flag 3: Locus Finance — Unknown Domain
Locus Finance was listed as "monitor only" with no known domain. **Not added to Attio, no email drafted.** Identify the correct domain/website before proceeding.

---

## Action Items Before Sending

1. **Update sender address** on all 22 drafts to `contact@sardis.sh` (required — Gmail API cannot set FROM address)
2. **Verify Clay results** — check Clay widget for enriched emails; update any drafts where guessed patterns were wrong
3. **Apollo upgrade** — consider upgrading to unlock bulk email verification for the 20 cold addresses
4. **Create GTM Pipeline list in Attio** — go to Attio UI → Lists → New List → add all 30 companies with stage data from the `description` field
5. **Resolve 3 flags** — inflow.finance (wrong company), natural.tech (no results), Locus Finance (unknown domain)
6. **Ramp — confirm Jonathan Avraham** is the right contact before sending; avoid Carolyn Zhao

---

## Attio Record IDs Reference

| Company | Domain | Record ID |
|---|---|---|
| Marqeta | marqeta.com | 4308abb5-... |
| Stampli | stampli.com | bccfb54f-... |
| Lindy | lindy.ai | d5bc7f38-... |
| Ramp | ramp.com | 194dd726-... |
| Xelix | xelix.com | 97c397b6-... |
| E2B | e2b.dev | 38f18a83-... |
| Lio | lio.ai | 391d37d6-... |
| Base Protocol | base.org | c4cac8c5-... |
| Helicone | helicone.ai | 80f4382d-... |
| AutoGPT | agpt.co | a89afa20-... |
| Catena Labs | catenalabs.com | 83a32cc1-... |
| Bridge | bridge.xyz | a7d2a1cb-... |
| Stripe | stripe.com | 573138ca-... |
| Rain | rain.com | 680c437e-... |
| Lithic | lithic.com | c0603e0c-... |
| Lightspark | lightspark.com | 1314d490-... |
| Airbase | airbase.com | 33084725-... |
| Stacks.ai | stacks.ai | d7b3bb15-... |
| Skyvern | skyvern.com | 7ef0812a-... |
| CrewAI | crewai.com | 498110fb-... |
| Procure.ai | procure.ai | bbdd6352-... |
| Relevance AI | relevanceai.com | c5290700-... |
| Dust | dust.tt | 63790fa4-... |
| LangChain | langchain.com | 98941c7c-... |
| Sierra.ai | sierra.ai | 87538856-... |
| Decagon | decagon.ai | 30049891-... |
| Lava Network | lava.xyz | 19193c33-... |
| MultiOn | multion.ai | 35a72ef8-... |
| Composio | composio.dev | 4d2e892e-... |
| Parallel.ai | parallel.ai | 4059b800-... |
