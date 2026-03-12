# Sardis Investor Diligence Report

Date: 2026-03-10
Prepared as: investor-grade diligence, comparable mapping, and fundraising strategy memo

## A. Executive Summary

### Bottom line
- Sardis is building a real product with real technical substance. The strongest description is not "agent payments API" and not "modern bank for agents." It is a trust and control plane for AI-agent money movement.
- The repo supports that thesis. The highest-signal code is in policy enforcement, approval logic, orchestration, attestation, evidence, auditability, and fail-closed execution. The rail layer matters, but it is not the moat.
- The company is more fundable than a raw concept because the product is unusually deep for stage and the market is being validated by incumbents and adjacent raises.
- The company is less fundable than the category hype implies because commercial proof is still thin, partner dependency is high, and the diligence story is internally inconsistent today.
- Best answer: fundable now, but selectively. This is specialist pre-seed / seed crossover territory, not a broad generalist frenzy round.

### My direct recommendation
- Raise now, selectively.
- Best structure: SAFE or small priced seed.
- Recommended target: $2.0M to $3.5M.
- Best investor set: AI infra specialists, fintech infra specialists, operator angels, and selective strategics.
- Best use of funds: convert design-partner interest into paid pilots, reconcile product truth vs marketing claims, harden one flagship workflow, and convert ecosystem conversations into signed integrations or distribution.

### Most important diligence insight
The biggest near-term fundraising risk is not the product. It is diligence coherence.

Three important truth mismatches show up immediately:
- Product maturity: `README.md` calls several surfaces "Production," while internal docs still say `pre-revenue, zero transaction volume, zero mainnet deployments`.
- Traction: internal materials say `25,000+ SDK installs`, founder update says `50k+`, but the public SDK metrics service currently resolves to roughly `1.8k` trailing-30-day npm installs and `0` PyPI installs because the tracked package set or package mapping is incomplete.
- Team: founder narrative provided in conversation says long-standing founding team with prior exits, while internal docs and ops materials still present as `solo founder / single engineer`.

An investor can tolerate early-stage uncertainty. They will not tolerate inconsistent diligence surfaces.

## B. Company Diligence Report

### B1. Core conclusions with evidence, inference, and confidence

| Conclusion | Evidence | Inference | Confidence |
|---|---|---|---|
| Sardis is fundamentally a control plane, not a rail company | `README.md` centers NL policies, KYA, append-only ledger, attestation, orchestration, A2A escrow, fail-closed execution; `docs/engineering/infrastructure-replacement-plan.md` explicitly says Coinbase/Circle are primitives and Sardis must own policy/compliance orchestration | Best investor framing is governed agent finance, not payment transport | High |
| Technical substance is real and above average for stage | 1,228 commits in repo history, strong last-200-commit hardening streak, large package surface, security-first orchestration, evidence/export/approval/control-center work, recent issue-completion commits on product truth | This is not a wrapper deck. Technical quality alone is seed-interesting | High |
| Product maturity is uneven | `README.md` marks policy engine, attestation, pre-execution pipeline as production, but cards/x402/checkout are pilot and multi-chain/FIDES are experimental; internal docs still call stage pre-revenue and pre-mainnet | Investors will separate credible core from aspirational surface quickly | High |
| Operational burden is high | On-call doc still says pre-GA/single-engineer; infra replacement plan lists wallet, KYC, AML, cards, on/off-ramp, and gas abstractions across multiple vendors | This will not behave like a lightweight self-serve dev tool business in the near term | High |
| Commercial proof exists as signals, not proof points | Founder-reported: 50k+ installs, Helicone and AutoGPT verbal customer intent, ongoing Base/Catena/Stripe/Coinbase/Bridge/Striga talks; internal docs show 25k+ install claim and "in conversation" design partners | There is clear directional pull, but much of it is not yet investor-grade proof | Medium |
| Traction instrumentation is not yet investor-safe | Repo metrics endpoint currently returns ~1.8k trailing-30-day npm installs and 0 PyPI installs from tracked packages; one-pager still says 25k+, founder says 50k+ | The number may still be real on a cumulative basis, but the methodology is not reconciled | High |
| Moat today is trust and workflow governance, not custody or raw rails | Internal infra plan explicitly says use Coinbase/Circle/Stripe primitives and keep policy/compliance/multi-rail OS custom | Defensibility is strongest if Sardis becomes the approval boundary and evidence layer for money-moving agents | High |
| Investor appetite exists, but it is niche not universal | Direct and adjacent players have raised, large incumbents are validating the space, but many direct agent-payment startups still have small or undisclosed financings | Right buyer exists, wrong buyer will pass fast | High |

### B2. Product and technical substance

#### What the product really is
Sardis is software that decides whether an AI agent should be allowed to move money, under what rules, with what approvals, on which rail, and with what audit evidence.

What it is:
- Policy-controlled agent payment orchestration
- Trust and approval layer for AI-agent execution
- Evidence and audit boundary between AI intent and financial action
- Multi-rail governance layer over wallets, stablecoin rails, cards, checkout, and protocol-native payments

What it is not:
- Not just x402
- Not just embedded wallets
- Not just Stripe Issuing for agents
- Not yet a fully realized global banking stack for agents

#### What is real vs aspirational
Most real:
- Natural language policy engine and fail-closed execution pipeline
- Approval logic, policy lifecycle, simulation, and evidence surfaces
- Attestation and audit posture
- Security-oriented browser-use / approval-context work
- SDK and framework breadth

Real but partner- or pilot-dependent:
- Hosted checkout
- Virtual cards
- x402 and broader protocol monetization
- Multi-rail fiat expansion

Still aspirational in commercial terms:
- Full "pay anyone anywhere any currency" narrative
- Broad consumer-commerce adoption
- Bank-like settlement breadth
- Deep global payout footprint

#### Technical differentiation
The differentiating layer appears to be:
- deterministic policy semantics
- pre-execution orchestration
- trust scoring / KYA
- approval routing
- evidence and audit bundles
- cross-rail consistency

The commodity layer is large:
- custody and wallets
- card issuance
- KYC and AML providers
- on/off-ramps
- chain and payment primitives

Investor judgment:
Sardis is not "just assembled middleware," but it is also not defensible because of wallet custody, raw stablecoin movement, or onramp access. It wins only if customers come to treat the control plane as the system of record for AI-agent spending rules.

### B3. Customer problem and urgency

#### Real pain
The core pain is not "agents need a wallet." The pain is:

> teams want agents to act in financially meaningful workflows, but they do not trust them enough to let money move without hard controls.

That is acute in:
- procurement
- travel and expense
- vendor/API purchasing
- browser-executed checkout
- agent-to-agent job fulfillment and escrow

Painkiller or vitamin:
- Painkiller for companies already trying to automate spend or commerce with agents
- Vitamin for companies still experimenting with chat UI and generic copilots

Who feels it:
- Head of AI / applied AI teams
- platform engineering
- payments/product teams
- finance systems / spend owners
- risk / compliance aware operators in later-stage software companies

Budget likelihood:
- Medium in the abstract
- High when attached to a blocked workflow with real dollars attached

Timing:
- Favorable now because incumbents are legitimizing agentic commerce, machine payments, and stablecoin-based infrastructure
- Still early enough that customer pull is not yet fully standardized

### B4. Market and category

#### Market Sardis is actually in
Sardis sits at the overlap of:
- AI infrastructure
- fintech infrastructure
- payment orchestration
- compliance / control software
- workflow software for enterprise automation

#### Category maturity
- Warm, not euphoric
- Fast-moving
- Narrative-rich
- Still early enough that category boundaries are sloppy

This matters because investors will bucket Sardis differently:
- best bucket: AI infra with fintech/compliance wedge
- weaker bucket: crypto payments startup
- dangerous bucket: feature of Stripe/Coinbase/Shopify

#### Market pull vs founder push
Current state looks like a mix:
- Founder push is still doing real work
- Early market pull exists, but a lot of it is conversational and ecosystem-level rather than contracted

My judgment:
- The market is venture-scale if AI agents become real transaction actors in enterprise workflows
- Sardis is not yet proving that its exact wedge will capture that scale

### B5. Commercial posture

Current posture:
- Developer-first top of funnel
- Enterprise or strategic close
- Design-partner stage, not repeatable sales stage
- Self-serve adoption signals, sales-assisted monetization

Likely business shape if it works:
- Mid-five to low-six figure ACVs for enterprise control-plane deals
- Longer implementation-led cycles than generic SDK businesses
- Expansion from one workflow into broader governance / policy / audit usage
- Gross margins can be software-like if Sardis avoids becoming a low-margin pass-through rail reseller

Pricing logic that fits:
- Platform fee
- Usage-based fee
- Enterprise controls / support tier

Pricing logic that does not fit:
- Pure take rate only
- Pure seat-based dev tool pricing

### B6. Moat and defensibility

#### What is genuinely hard
- Making agent execution trustworthy enough for real businesses
- Keeping one control boundary across many rails and protocols
- Encoding approvals and evidence in a way buyers can defend internally
- Owning the place where policy, risk, and execution meet

#### What is easy to copy
- thin SDKs
- wallet wrappers
- x402 connectors
- simple card controls
- demo checkout

#### What incumbents can absorb quickly
- "agents can pay" feature slices
- simple wallet + spend-limit features
- merchant-side agent checkout experiments

#### What incumbents may not absorb quickly
- cross-rail governance consistency
- agent-specific approval workflows
- evidence / attestation / exception handling as a unified operational system
- workflow embedding into procurement/travel/API purchasing processes

#### Moat judgment
Today:
- moderate in concept
- early in practice

Potential later:
- strong if Sardis becomes the default control system for sensitive AI spending workflows before the rail providers move higher in the stack

### B7. Founder and team risk

#### Strengths
- High product and shipping velocity
- Good instincts around where the real trust boundary is
- Willingness to use third-party primitives instead of rebuilding everything forever

#### Risks
- Current repo and ops posture still look single-founder / single-engineer
- Team story is inconsistent across materials
- Enterprise GTM learning curve is steep
- Surface area can sprawl faster than proof points

#### Investor concern
If there is in fact a broader founding team, the data room must show it cleanly. Right now the operating evidence still reads as highly concentrated execution risk.

### B8. Investor attractiveness today

#### What gets investors interested
- Deep product for stage
- Category timing and incumbent validation
- Strong framing if pitched as trust/control layer rather than rail
- Potentially large market if AI becomes a real transaction actor

#### What makes them hesitate
- inconsistent traction and stage claims
- no strong public paid-revenue proof yet
- partner dependency
- scope breadth
- founder concentration

#### What kills the deal
- claiming "modern bank for agents" too early
- not reconciling installs / team / deployment truth
- pitching broad consumer commerce before winning a narrow B2B workflow
- inability to answer "why is this not a Stripe/Coinbase feature?"

## C. Comparable Company Map

### C1. Direct comparables

| Company | Website | One-line description | Why relevant | Stronger than Sardis | Weaker than Sardis | True comp? |
|---|---|---|---|---|---|---|
| Skyfire | https://skyfire.xyz | Payment and identity network for AI agents | Closest direct "agents need to pay" company in market narrative | Cleaner singular story, earlier category mindshare | Less visible control-plane depth | Yes |
| Natural | https://www.natural.ai | Financial rails for autonomous AI agents | Very close fundraising and narrative comp | Cleaner investor-ready category pitch | Less visible depth in governance layer from public materials | Yes |
| Payman | https://paymanai.com | Payment workflows for AI and human recipients | Similar pain around controlled AI payments | Simpler and easier to grasp use case | Narrower platform ambition | Partial |
| TODAQ | private / PDF-led narrative | Internet-native API settlement for AI agents | Same machine-to-machine payments narrative | Sharper embedded-settlement framing | Appears narrower, more transport-focused, less trust/control depth | Loose |

### C2. Functional comparables

| Company | Website | Why relevant | Stronger than Sardis | Weaker than Sardis | True comp? |
|---|---|---|---|---|---|
| Paid | https://www.paid.ai | AI-agent monetization infrastructure with clearer immediate ROI | Monetization pain is more explicit and easier to buy | Not a trust/control layer | Functional |
| Zip | https://ziphq.com | Spend control, approval routing, procurement workflows | Proven buyer pain and enterprise willingness to pay | Not agent-native | Functional |
| Ramp | https://ramp.com | Spend controls, approvals, finance workflow | Strong buyer education and budget line | Not agent-native, not multi-rail | Functional |

### C3. Infrastructure comparables

| Company | Website | Why relevant | Stronger than Sardis | Weaker than Sardis | True comp? |
|---|---|---|---|---|---|
| Turnkey | https://www.turnkey.com | Wallet/signing primitive for developer-facing finance apps | Enterprise wallet credibility and capital access | Not the control plane | Infrastructure |
| Crossmint | https://crossmint.com | Developer infra for wallets, payments, and onchain apps | Horizontal infra traction and distribution | Less focused on agent governance as the wedge | Infrastructure |
| Bridge | https://bridge.xyz | Stablecoin financial rails | Distribution and strategic rail value | Not a trust layer | Infrastructure |
| Privy | https://privy.io | Embedded wallets and user onboarding | Massive simplification of wallet adoption and strategic M&A interest | Not agent payment governance | Infrastructure |

### C4. Narrative comparables

| Company | Website | Why investors mentally compare it | Why comparison is imperfect |
|---|---|---|---|
| Stripe | https://stripe.com | Best-known "payments operating system" mental model | Sardis is far earlier and not a raw PSP |
| Coinbase x402 / AgentKit | https://docs.cdp.coinbase.com/x402/welcome | Direct validation of machine payments and agent wallets | Coinbase owns primitives, not Sardis's cross-rail governance wedge |
| Visa / Mastercard agent commerce efforts | https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.20701.html and https://www.mastercard.com/news/perspectives/2025/mastercard-agent-pay/ | Proves incumbents take the category seriously | Also increases feature / platform-risk pressure |
| Catena Labs | https://catena.xyz | AI + financial trust and compliance narrative | More trust/compliance narrative than direct payment-control product overlap |

### C5. Fundraising comparables

Most useful for round strategy:
- Skyfire
- Natural
- Paid
- Turnkey
- Crossmint
- Bridge

Least useful for round strategy:
- Stripe, Visa, Mastercard
- Shopify
- Coinbase

Those validate the macro, but they do not tell you what a small startup can raise today.

## D. Recent Funding Analysis

### D1. Relevant financings and strategic events

| Company | Date | Amount / type | Source quality | What investors likely bought | What it does and does not imply for Sardis |
|---|---|---|---|---|---|
| Skyfire | 2024-08 | $8.5M seed | Medium, public reporting | Category validation plus team and novelty around agent payments | Shows category fundability, not proof that Sardis can raise broadly |
| Natural | 2025-10 | $9.8M seed | Medium, public reporting / company source | Direct bet on autonomous AI financial rails | Strong direct comp. Investors will ask why Natural got funded and Sardis is different |
| Paid | 2025-09 | $21.6M seed | Medium, public reporting / company | Clear ROI story around monetization of AI work | Investors pay up when AI infra ties directly to revenue. Sardis needs similarly concrete ROI proof |
| Crossmint | 2025-03 | $23.6M funding led by Ribbit | High, official company announcement | Horizontal infra adoption and strategic importance of wallets/payments for businesses | Shows infra funding appetite is real, but also raises the bar on traction and breadth |
| Turnkey | 2025-06 | $30M Series B led by Bain Capital Crypto | High, official company announcement | Developer wallet/signing infra as foundational primitive | Positive for the space, but later-stage and far stronger proof than Sardis has today |
| Bridge | 2024-10 announced, 2025 strategic outcome | $1.1B acquisition by Stripe | High, CNBC/public reporting | Stablecoin rails became strategically valuable to incumbents | Massive validation of rails, but it also proves the heat may be captured by platforms with distribution |
| Catena Labs | 2025, reported | $18M seed | Medium, media reporting | Trust/compliance/financial control narrative around AI | Good narrative comp. Also raises the pressure to tell a differentiated trust story |

### D2. How to interpret these rounds

#### Hype round vs proof-driven round
- Skyfire and Natural look more category-validation / founder-thesis rounds than deep proof-driven rounds.
- Turnkey and Crossmint look proof-driven.
- Bridge was strategic and distribution-driven, not a startup-stage comparable financing.
- Paid is useful because it ties AI infrastructure to measurable money movement and monetization pain.

#### Earlier or later than Sardis
- Earlier or similar: Skyfire, Natural, some Payman-like companies
- Later and stronger: Turnkey, Crossmint, Bridge
- Narrative adjacent but not directly comparable: Catena Labs, Privy

#### What the market is buying
The investor market is funding:
- primitives with proven developer pull
- AI infrastructure tied to economic outcomes
- picks-and-shovels that can become platform layers

The investor market is not automatically funding:
- vague "agent economy" decks
- broad multi-rail visions without traction
- crypto-native payment narratives with no clear B2B buyer

### D3. Negative calibration

Important negative signals:
- Direct agent-payment startups are still generally raising small or mid-sized early rounds, not mega-seed rounds, unless they have stronger narrative, brand, or traction advantages.
- I did not find strong public evidence that all nearby startups in this space are raising aggressively. Some appear to have small rounds, soft launches, or no major disclosed financings.
- This is evidence that the category is real but still proving itself.

## E. Investor Market Read

### Category temperature
- AI infrastructure: hot
- fintech infrastructure: warm to hot
- direct "agent payments" startups: warm, but noisy
- crypto-native payment infra without enterprise trust story: harder

### How investors will bucket Sardis
Most likely:
- AI infrastructure with fintech/compliance wedge

Secondary:
- payment infrastructure for AI agents
- enterprise trust/control layer

Dangerous mis-buckets:
- crypto startup
- wallet startup
- feature of Stripe/Coinbase

### Which investors care

#### Top-tier VC
- Reaction: intrigued, but likely to wait
- Why they pass: proof too early, solo-founder risk, inconsistent diligence surfaces

#### Specialist seed fund
- Reaction: this is the best fit
- Why they care: can underwrite technical depth plus early category formation

#### Operator angels
- Reaction: very attractive
- Why they care: can back founder quality and help shape GTM / partnerships / team

#### Strategic investors
- Reaction: potentially high interest if workflow fit is real
- Why they care: Sardis can be a distribution layer for their primitives

### What objections come first
- Why is this not a Stripe / Coinbase / Circle feature?
- How much of the product is truly proprietary?
- What customer is paying today?
- Are install metrics real and what do they mean?
- Is this solo-founder execution risk disguised as team strength?
- Is the company too broad?

### Proof points that matter most next
- Signed or paid pilot with one named customer
- Reconciled traction instrumentation
- One referenceable use case with real workflow ROI
- One strategic integration moving from conversation to concrete timeline
- Reliability metrics on live transactions

## F. Round Recommendation

### F1. Should the company raise now?
Yes, selectively.

Not aggressively. Not from everyone. Not with a broad "hot category" pitch.

### F2. Best round type
- Preferred: SAFE with disciplined cap expectations
- Acceptable: small priced seed if specialist lead interest appears

### F3. How much to raise
Recommended now:
- $2.0M to $3.5M

Why not more:
- Too much money before proof will force a narrative-led round and invite the wrong investors
- This company still needs to prove one commercial wedge and one clean data room truth

### F4. Use of funds
- product hardening for one flagship workflow
- two key hires: implementation engineer and GTM / founder-assist operator
- convert 3 to 5 design partners into paid pilots
- security/compliance credibility work
- partnership and integration conversion work
- traction instrumentation and investor-grade reporting

### F5. Proof points to reach during or before the raise
- 2 to 3 written pilot agreements or LOIs, at least 1 paid
- 1 named ecosystem integration or partner agreement with defined scope
- 1 narrow wedge with real pull, such as procurement/API commerce/travel-expense
- investor-safe install / activation / active-org metrics
- live control-plane metrics: approvals, blocked spend, evidence exports, recovery outcomes

### F6. Best investor profile
- AI infra seed funds
- fintech infra seed funds
- crypto-adjacent but product-first funds, not token-first funds
- operator angels from Stripe, Coinbase, Ramp, Shopify, Visa, Mastercard, or agent-platform founders
- selective strategics

### F7. Wrong investor profile
- generalist hype tourists
- late-stage fintech funds expecting mature revenue
- crypto-only funds expecting token economics
- pure dev-tool investors who do not understand financial workflows

### F8. Milestones for a stronger next round
- 3 to 5 paid pilots
- $10k to $30k MRR quality proof, or equivalent annualized committed revenue
- one flagship case study
- signed category-defining partnership
- reconciled and credible adoption metrics
- cleaner team story with at least one key hire

## G. Capital Strategy Scenarios

### Scenario A: Raise now
- Round: $2.5M to $3.5M
- Why: category timing is favorable, technical product is real, and the current window rewards high-quality infra with credible founder velocity
- Pros: captures momentum, allows faster pilot conversion, gives partnership discussions more weight
- Risks: if story is not cleaned up first, investors will focus on inconsistencies and the raise will feel weaker than the product deserves
- Required narrative: trust and control layer for AI-agent money movement

### Scenario B: Delay and de-risk first
- Wait for: 1 paid pilot, 1 signed integration path, reconciled install data, 1 mainnet proof point
- Benefit: materially stronger institutional seed case and better valuation
- Risk: category may get noisier while incumbents keep moving, and the founder bears more execution load without help

### Scenario C: Hybrid strategy
- Raise: $1M to $2M from angels / strategics / small specialist funds now
- Then: run larger institutional seed after milestone conversion
- Why it may be optimal: preserves optionality, reduces story risk, lets founder prove the right wedge before scaling the narrative

### Best scenario
Scenario C is the most rational.

Why:
- Sardis is strong enough to deserve capital now
- Not strong enough to maximize price and process with broad institutional demand
- A smaller selective round can convert soft signals into hard evidence

## H. Investor Narrative Recommendations

### Most fundable framing
Sardis is the trust and control layer that makes AI-agent payments deployable inside real businesses.

Why this is best:
- highlights the real pain
- distinguishes Sardis from rail providers
- fits the product truth in the repo
- maps to enterprise budget holders

### Weak narrative to avoid
"We are a modern bank for agents."

Why to avoid it:
- too broad
- too regulated-sounding
- easy to attack on maturity
- invites diligence on rails and licenses instead of control-plane value

### Top 3 narrative variants

1. Trust and control layer for AI-agent payments
- Best for: AI infra and fintech infra specialists
- Objection: sounds like a feature
- Defense: cross-rail policy, approvals, evidence, and audit form a system of record, not a button

2. Financial control plane for enterprise agent workflows
- Best for: enterprise software investors and strategic partners
- Objection: is the buyer budget real?
- Defense: wedge into procurement, travel, API commerce, and finance-adjacent automation

3. Payment OS for the agent economy
- Best for: broader seed narrative and strategic vision
- Objection: too broad and too early
- Defense: use only after anchoring the wedge and showing one workflow that actually pulls

## I. Valuation and Dilution Reasoning

### Realistic valuation band now
Today:
- $15M to $22M post-money is the rational band

Possible upside band:
- $22M to $28M post-money only if the founder reconciles the story, signs real pilots, and gets competitive specialist interest

Why not higher:
- no clear revenue proof
- inconsistent traction instrumentation
- solo-founder / small-team risk
- partner dependency
- product breadth still ahead of commercial proof

### Stronger valuation band later
After proof points:
- $25M to $40M post-money becomes much more plausible

Needed to get there:
- paid pilots
- signed partnership
- credible adoption metrics
- cleaner data room
- stronger team surface

### Dilution guidance
- Raising $2.0M to $3.5M at $15M to $22M post implies roughly 9% to 18% dilution
- That is acceptable if it buys:
  - one key hire
  - 3 to 5 pilots
  - one signed integration / distribution win
- Founders are most likely to overestimate value if they price off Stripe/Bridge/Crossmint-style narratives without comparable proof

## J. Risk Matrix

| Risk | Severity | Why it matters | Fixable? | Milestone that reduces it |
|---|---|---|---|---|
| Product truth mismatch across materials | High | Investors lose trust fast when story surfaces disagree | Yes | single reconciled fundraising data room |
| Traction metric inconsistency | High | Install claims can become credibility sink | Yes | investor-grade metrics methodology and active-usage reporting |
| GTM proof still thin | High | Category story without paying users weakens process | Yes | 1 to 3 paid pilots |
| Partner dependency | High | Rail and card roadmap depends on third parties | Partly | signed scope with at least one major partner |
| Feature-not-company risk | High | Incumbents can add simple agent-payment features | Partly | wedge dominance in approvals/evidence/trust workflow |
| Team concentration | High | Single-founder execution limits scale and raises bus-factor concern | Yes | first senior hire + clearer founding team evidence |
| Regulatory / compliance over-claiming | Medium | "Bank for agents" style narrative triggers extra diligence | Yes | disciplined positioning and scoped claims |
| Market timing risk | Medium | Category could get crowded before Sardis proves wedge | Partly | faster pilot conversion and sharper ICP focus |
| Narrative sprawl | Medium | Too many surfaces reduce investor comprehension | Yes | one narrow fundraising story |

### What causes sophisticated investors to pass
- story incoherence
- no signed customers
- too much breadth
- weak response to incumbent-threat question

### What still attracts the right specialists
- unusually deep product
- credible control-plane framing
- timing tailwinds from agentic commerce
- strong founder velocity

## K. Final Recommendation

### Direct answers

Is this company fundable now?
- Yes, selectively.

For whom is it fundable now?
- Specialist seed funds, operator angels, selective strategics, and a subset of fintech/AI infra investors.

What kind of money should it raise?
- $2.0M to $3.5M, ideally in a selective hybrid round.

What is the strongest investor story?
- Sardis is the trust and control layer that makes AI-agent money movement safe enough for real business workflows.

What milestones most increase fundraising power?
- signed pilots
- reconciled metrics
- one flagship workflow
- one strategic integration or partner agreement

## L. 30 / 60 / 90 Day Fundraising Action Plan

### Next 30 days
- Reconcile all diligence surfaces:
  - installs
  - team
  - deployment / mainnet status
  - production vs pilot language
- Build one investor-grade traction dashboard:
  - cumulative installs
  - 30-day installs
  - activated orgs
  - active orgs
  - design partners
  - pilot pipeline
- Convert Helicone / AutoGPT verbal intent into written pilot structure or LOI
- Build target investor list of 30 to 40 names, mostly specialists and operators

### Next 60 days
- Close at least 1 paid pilot and 1 additional signed design partner
- Push one partnership discussion into explicit technical/commercial next step
- Publish one evidence-heavy case study or design-partner memo
- Add one senior hire or formal advisor with category credibility

### Next 90 days
- Run focused selective fundraising process
- Use milestone-based deck, not category deck
- Target a tight set of investors who understand AI infra and fintech infra
- If paid pilot conversion is weak, pivot to smaller strategic/angel extension and continue customer-funded learning

## Source Notes

### Local evidence
- `README.md`
- `docs/investor-one-pager.md`
- `docs/engineering/infrastructure-replacement-plan.md`
- `docs/on-call.md`
- `research/investor-diligence-2026-03-10.md`
- `git log --oneline -200`
- `git shortlog -sn HEAD`
- `packages/sardis-api/src/sardis_api/services/sdk_metrics.py`
- live metrics fetch from the repo's own SDK metrics service on 2026-03-10

### Public market sources
- Turnkey Series B: https://www.turnkey.com/blog/30m-series-b-to-secure-the-next-era-of-crypto
- Crossmint financing announcement: https://crossmint.com/announcement/crossmint-raises-23-6m-led-by-ribbit-capital
- Privy funding context: https://privy.io/blog/privy-series-a and https://privy.io/blog/privy-series-b
- Coinbase x402 docs: https://docs.cdp.coinbase.com/x402/welcome
- Stripe / OpenAI instant checkout announcement: https://stripe.com/newsroom/news/stripe-openai-instant-checkout
- Visa intelligent commerce announcement: https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.20701.html
- Mastercard Agent Pay: https://www.mastercard.com/news/perspectives/2025/mastercard-agent-pay/
- Skyfire funding and market reporting: public press coverage and company materials reviewed on 2026-03-10
- Natural funding and market reporting: public company / press coverage reviewed on 2026-03-10
- Paid funding and market reporting: public company / press coverage reviewed on 2026-03-10
- Bridge strategic outcome: CNBC public reporting reviewed on 2026-03-10

### Confidence note
Where a source is not an official company financing post, I have treated it as medium-confidence market evidence rather than hard diligence proof.
