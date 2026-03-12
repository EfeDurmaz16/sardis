# Sardis Investor Diligence Report

Date: 2026-03-10
Prepared as: independent investor-grade diligence, market map, and fundraising strategy memo

## A. Executive Summary

### Bottom line
- Sardis is building a real product, not a mock pitch category. The core is a deterministic trust and control plane for AI-agent payments, not merely a wallet SDK or x402 wrapper.
- The technical surface is unusually deep for the age of the company, but the commercial surface is still early. This looks like design-partner stage, not repeatable sales stage.
- A serious investor will like the architecture depth, fail-closed posture, and control-plane framing. The same investor will worry about scope breadth, partner dependency, solo-founder concentration, and lack of hard commercial proof.
- This company is fundable now for specialist angels, operator angels, strategic investors, and a narrower set of seed/pre-seed funds. It is not yet obviously ready for a broad competitive institutional seed process.
- The most rational strategy is a hybrid raise: enough money now to harden GTM and land paid pilots, then a stronger institutional round once proof points are real.

### Core recommendation
- Raise now, but selectively.
- Best instrument: SAFE or small pre-seed style round.
- Target: $1.5M to $3.0M now.
- Use of funds: convert 3 to 5 design partners into paid pilots, tighten one flagship ICP, land at least one category-defining rail or card partnership, and publish reliability / control-plane proof.
- Re-open a larger seed only after commercial evidence is materially stronger.

## B. Company Diligence Report

### B1. High-priority findings

| Finding | Direct evidence | Inference | Confidence |
|---|---|---|---|
| Sardis is fundamentally a control plane, not a payment rail | README describes natural-language policy firewall, KYA, append-only ledger, AP2 verification, A2A escrow, and multi-rail support; investor docs repeat “trust and control plane” framing | Best framing is governed agent finance, not “agent payments API” | High |
| Product breadth is real, but maturity is uneven | README marks policy engine, AP2, policy attestation, and pre-execution pipeline as production; checkout, x402, virtual cards are pilot; multi-chain and FIDES are experimental | Investor diligence will separate what is load-bearing today from roadmap breadth | High |
| Technical depth is strong for stage | 1,161 commits in repo history, 41 package directories, 63 migration files, policy-first orchestration and fail-closed control logic in code paths | Technical credibility is seed-investable even before large revenue | High |
| The stack has meaningful operational burden | Production boot expects Postgres, Redis, live signer posture, KYC provider, sanctions provider, and multiple rail integrations | This is not a lightweight self-serve dev tool; enterprise motion will be heavier and implementation-led | High |
| Security posture is a positive outlier | Recent commits center on approval binding, origin allowlists, prompt injection scanning, policy attestation, durable dedup, reconciliation, and PaymentOrchestrator unification | Security and controls are not bolt-ons; they are near the center of the product | High |
| Commercial maturity is still early | Local traction and GTM docs show outreach, drafts, and warm leads, but not repeatable ARR or multiple public paid pilot case studies | Investors will see design-partner promise, not repeatable GTM | High |
| Moat today is workflow governance, not rails | Internal planning docs explicitly say Coinbase/Circle build primitives while Sardis’ defensibility is policy enforcement, compliance orchestration, and multi-rail OS on top | Strongest moat argument is control consistency above commoditizing rails | High |
| Partner assembly risk is real | Wallets, onramps, KYC, AML, cards, and payouts depend on several external providers, with proposed future stack adding Lightspark, Striga, Plaid, etc. | Investors may worry the product is orchestration plus wrappers unless the control plane is made unmistakably proprietary | High |
| Team quality may be strong, but concentration risk is high | Local investor docs describe a solo technical founder and high velocity since Nov 2025 | Key-man risk and execution concentration will come up immediately in diligence | High |
| Fundability exists, but only for the right buyer of the story | Category is warm, comparable rounds exist, and incumbents validate the space; however direct proof of commercial pull remains limited | Best fit today is specialist capital, not broad seed-tourist capital | High |

### B2. Product and technical substance

#### What the product really is
Sardis is a payment governance layer that sits between model intent and money movement. In code and docs, the important product is not “agents have wallets.” The important product is that every transaction passes through deterministic policy validation, trust / identity checks, compliance gates, execution controls, and audit evidence generation before money moves.

Evidence:
- README positioning and maturity table: `README.md`
- Orchestrator phase ordering in `packages/sardis-core/src/sardis_v2_core/orchestrator.py`
- Competitive moat doc emphasizing risk scoring, plain-English policy, escrow, compliance, and emergency brakes

What it is not:
- Not merely x402 middleware
- Not merely embedded wallets
- Not merely card issuing
- Not yet a complete “modern bank for agents” in production reality

#### Maturity
Most credible now:
- Policy engine and fail-closed orchestration
- AP2 / mandate verification and attestation
- Audit / receipt / reconciliation posture
- Security hardening around browser-use and origin binding

Real but still pilot / partial:
- Hosted checkout
- x402 as go-to-market surface
- Virtual cards / card issuing
- Some multi-chain lanes

Aspirational / still narrative-heavy:
- Full fiat rail coverage
- “anyone, anywhere, any currency” settlement
- True global payout stack
- Broad consumer internet commerce adoption

#### Proprietary versus assembly
The hard part appears to be proprietary where it matters most:
- deterministic policy semantics
- approval logic and confidence routing
- audit evidence / attestation / receipts
- cross-rail governance consistency
- protocol verification and trust controls

The non-proprietary layer is large:
- custody / wallets
- onramp / offramp
- sanctions / KYC vendors
- card issuance vendors
- some payout infrastructure

Investor judgment:
- This is not “just assembly,” but it is also not defensible because of custody or raw rails.
- Sardis must win because its control layer becomes the place where customers encode trust, approvals, and operational policy.

### B3. Customer problem and urgency

#### Core pain
The real pain is not “agents need to pay.” The real pain is: teams want agents to execute financially meaningful actions, but they do not trust them to do so without hard controls, human approvals, and auditability.

This pain is strongest in:
- procurement and spend workflows
- travel and expense automation
- agent-to-agent task fulfillment with escrow
- API and usage-based agent transactions for B2B systems
- high-risk browser or checkout workflows

Painkiller or vitamin:
- Painkiller for teams already trying to let agents spend or transact
- Vitamin for teams still experimenting with chat UX or internal copilots

Budget reality:
- Budget is likely to come from platform, AI, payments, RevOps, FinOps, or procurement transformation teams, not generic developer budgets
- Near-term willingness to pay will be highest when Sardis removes a specific blocked workflow, not when pitched as future TAM infrastructure

### B4. Market and category

#### Actual market
Sardis sits at the intersection of:
- AI agent infrastructure
- fintech infrastructure
- payment orchestration
- compliance / control software
- developer platforms

That intersection is attractive but dangerous.
- Attractive because it rides strong macro interest in AI agents and stablecoin-enabled infrastructure.
- Dangerous because investors and buyers can bucket it as a feature of larger platforms unless the wedge is crisp.

#### Category temperature
The category is warm, not manic.
- Direct players are getting funded.
- Adjacent infrastructure is getting funded aggressively.
- Incumbents are moving in fast.
- Consumer agentic checkout still looks unsettled, while B2B workflow automation is more credible.

### B5. Commercial posture

What Sardis looks like today:
- developer-first entry
- enterprise or strategic buyer close
- design-partner stage
- sales-assisted rather than self-serve revenue today
- platform wedge rather than finished platform company

Likely commercial dynamics:
- ACV can be attractive if Sardis becomes a control and compliance layer for enterprise workflows
- Sales cycles will be longer than a typical SDK because compliance, finance, and risk teams will matter
- Gross margin should be software-like at the control-plane layer, but blended margin gets muddier if Sardis bundles or passes through rail economics
- Pricing likely needs a mix of platform fee + usage fee + enterprise controls, not only bps

### B6. Moat and defensibility

#### What is actually hard
- Creating deterministic control semantics over non-deterministic agents
- Getting enterprises to trust agent execution at all
- Keeping one policy / approval / audit boundary across multiple rail types
- Building governance that survives rail/provider swaps

#### What is easy to copy
- SDK wrappers
- basic wallet abstractions
- x402 connectivity
- basic card controls
- checkout flows without governance depth

#### What incumbents can absorb quickly
- simple “agent checkout” features
- wallet creation and balance primitives
- some spend limits and merchant locks

#### What incumbents cannot absorb as quickly if Sardis executes
- cross-rail policy consistency
- auditable agent-specific approval workflows
- trust-scored agent identities + action governance
- workflow embedding into real operational use cases

Net moat assessment today:
- Moderate in theory, early in practice.
- Real moat exists only if Sardis becomes embedded in sensitive workflows before larger infra players extend upward.

### B7. Founder and team risk

Positive signals:
- High technical output velocity
- Product intuition around trust and controls seems coherent
- Willingness to pivot narrative from “rails” to “control plane” is a good sign

Risks investors will see:
- solo-founder concentration
- possible over-breadth in surface area
- enterprise GTM learning curve
- regulatory overhang if narrative drifts into “bank-like” claims

Most important next hires:
- implementation / solutions engineer
- security / compliance lead or fractional operator
- focused GTM operator for design-partner conversion

### B8. Investor attractiveness today

What gets investors interested:
- unusual technical depth for stage
- category timing and incumbents validating the space
- clear control-plane wedge above x402 / wallets / cards
- ability to tell a bigger platform story if early pilots work

What makes them hesitate:
- too many surfaces, unclear first wedge
- no strong public paid-customer proof yet
- heavy partner dependency
- solo founder risk
- risk of being a feature, not a company

What kills the deal:
- overclaiming maturity on cards / fiat / global rails
- fuzzy or inflated traction metrics
- inability to explain why Stripe / Coinbase / Circle cannot just build enough of this
- telling a consumer-commerce story before B2B trust use cases are proven

## C. Comparable Company Map

| Company | Website | Similarity type | Why relevant | Stronger than Sardis | Weaker than Sardis | True comp? |
|---|---|---|---|---|---|---|
| Skyfire | https://skyfire.xyz | Direct | Agent payment network and identity for AI agents | More singular payment-network story, market visibility | Less visible control-plane depth and cross-rail governance | True direct comp |
| Locus | https://paywithlocus.com | Direct | Payment infrastructure for agents with policy and escrow messaging | Cleaner narrow wedge, YC signal | Much earlier, less breadth, no visible broad stack | True direct comp but earlier |
| Payman | https://paymanai.com | Direct / functional | AI-to-human payments with policies and approvals | Simpler use case, easier to explain | Narrower scope, weaker platform breadth | Partial direct comp |
| Natural | https://www.natural.co | Direct | Agentic payments infrastructure, raised seed recently | Stronger current market momentum | Less visible trust/control-plane substance from public material | True direct comp |
| TODAQ | https://todaq.substack.com | Direct / narrative | Internet-native API settlement for AI agents | Sharper micropayment story | Appears narrower, more settlement-focused, less obvious governance layer | Loose direct comp |
| Paid | https://www.paid.ai | Functional / fundraising | Monetization and billing infrastructure for AI agents | Stronger revenue / monetization story, clearer ROI | Not a trust/control layer, less relevant to payment governance | Functional comp |
| Rain | https://rain.xyz | Infrastructure / fundraising | Stablecoin-powered card issuing and enterprise payment infra | Much stronger regulated rail and card posture | Not a cross-rail agent governance layer | Infrastructure comp |
| Crossmint | https://crossmint.com | Infrastructure / fundraising | Wallets, onchain infra, payments for businesses and AI agents | Stronger horizontal infra traction and revenue story | Less focused on agent payment controls as the core product | Infrastructure comp |
| Turnkey | https://turnkey.com | Infrastructure / fundraising | Wallet and signing infra used by many products | Strong infra focus, enterprise-grade primitive | Not the policy / trust layer | Infrastructure comp |
| Privy | https://privy.io | Infrastructure / narrative | Embedded wallet and crypto onboarding infra, acquired by Stripe | Strong developer adoption and strategic value proven by M&A | Not a payment control layer | Narrative / infrastructure comp |
| Bridge | https://bridge.xyz | Narrative / fundraising | Stablecoin financial rails, acquired by Stripe | Deeper rail-level strategic value | Not an agent governance platform | Narrative comp |
| Stripe | https://stripe.com | Narrative / incumbent | Investor mental model and future feature threat | Distribution, merchant footprint, card and payment scale | Not built around agent-specific control-plane logic today | Narrative comp, not startup comp |

## D. Recent Funding Analysis

| Company | Date | Amount / round | Source | What investors likely bought | What it implies for Sardis |
|---|---|---|---|---|---|
| Skyfire | Aug 2024 | $8.5M seed | The SaaS News / SiliconANGLE | Category validation, founder pedigree, machine-economy narrative, agent payments novelty | Investors will fund this category early, but that does not prove Sardis’ control-plane wedge yet |
| Payman | Aug 2024 | $3M pre-seed | LinkedIn founder post / secondary databases | Novel AI-to-human payment use case plus brand-name fintech investors | Small round size suggests category interest exists, but commercial proof bar remains low and early |
| Natural | Oct 2025 | $9.8M seed | Natural blog / Business Wire | Strong “payments for agents” narrative plus credible investor set and timing | Direct comp that raised on category + team + thesis, not necessarily on strong public traction |
| Paid | Sep 2025 | $21.6M seed, $33.3M total | PR Newswire | Clear monetization pain, early customer ROI, founder quality | Shows investors pay up when AI-agent infrastructure has measurable economic impact. Sardis does not yet have equivalent ROI evidence |
| Rain | Mar 2025 and Aug 2025 | $24.5M funding, then $58M Series B | Rain site / PR Newswire | Enterprise stablecoin payments and card issuing, then strong growth and distribution | Capital is flowing aggressively to rail providers with enterprise proof. Sardis is not there yet and should not benchmark off these rounds directly |
| Crossmint | Mar 2025 | $23.6M funding | Crossmint blog | Strong horizontal infra simplification, onchain business adoption, and growth | Investors reward picks-and-shovels with broad adoption. Sardis needs comparable proof or narrower wedge dominance |
| Turnkey | Jun 2025 | $30M Series B | Turnkey blog | Wallet infrastructure as foundational primitive | Confirms primitives can raise big rounds, but also shows where Sardis can be undercut if it looks too close to wallet infra |
| Privy | Mar 2025 fundraise; Jun 2025 acquired by Stripe | $15M round, then acquisition | Privy blog | Wallet onboarding as strategic infrastructure | Strategic M&A risk is real: incumbents are buying primitives. That can be upside or compression depending on Sardis’ wedge |
| Bridge | Oct 2024 announced, Feb 2025 closed | acquired by Stripe for $1.1B | CNBC / Architect Partners | Stablecoin rails became strategically important to a major incumbent | Huge validation for rails, but also a warning that rail value can be captured by platforms with distribution |

### Negative calibration
- Locus appears to have YC backing but no disclosed major institutional round yet. That suggests the market is still early enough that not every direct player is getting aggressively funded.
- TODAQ has thought-through narrative material, but there is no obvious public large institutional financing visible from the sources reviewed. That matters because good narrative alone is not clearing rounds.
- Consumer-facing agentic checkout appears less settled than B2B workflow automation. Public reporting in March 2026 suggests OpenAI is changing course on direct checkout strategy, which is a warning against over-indexing on consumer commerce too early.

## E. Investor Market Read

### How investors are likely to bucket Sardis
Most likely:
- AI infrastructure with fintech and compliance overlays

Second-order buckets:
- agent trust layer
- payment operating system for AI agents
- control/compliance layer for agentic commerce

Weak buckets to avoid:
- “crypto startup”
- “another wallet company”
- “just x402 middleware”
- “consumer shopping agent payments”

### Category temperature
- Hot: no
- Warm: yes
- Easy to fund: no
- Specialist-interesting: yes

Why:
- Incumbents have validated the problem space.
- Recent direct startup rounds show real appetite.
- But investor scrutiny is already moving toward who owns the durable control layer, not who can merely move stablecoins.

### Who cares most
- AI infra seed funds that understand developer platforms
- fintech infra seed funds that understand payments and compliance
- crypto-adjacent funds that like real payment utility, not token games
- operator angels from Stripe, Coinbase, Bridge, Rain, Ramp, Navan, Zip, Modern Treasury, LangChain, Browserbase
- strategic investors that can open rails, cards, or distribution

### Who passes quickly
- late-stage tourists
- generalist AI funds looking for faster-consumption or app-layer growth
- traditional fintech funds expecting mature regulated revenue or bank partnerships already live
- crypto-only funds looking for token upside or chain-native speculation

### First objections
1. Why is this not a feature inside Stripe, Coinbase, Circle, Rain, or Shopify?
2. What exact workflow is the wedge?
3. Is this too broad for a solo founder and early company?
4. Are the customer budgets real now, or is this founder push into a future category?
5. How much of the stack is proprietary versus assembled from third-party providers?

### What proof points matter most
- 3 to 5 paid pilots with clear success criteria
- 1 flagship rail or card partnership actually operationalized
- latency, reliability, and control-plane metrics in production
- at least one public case study showing the workflow Sardis unlocks
- pricing acceptance and renewal signals

## F. Round Recommendation

### Should the company raise now?
Yes, but selectively.

This is not a “go run a broad 80-fund seed process” company today.
This is a “raise from specialists, operators, and strategic investors who understand the control-plane thesis” company.

### Best round type
- Primary recommendation: SAFE or small pre-seed style round
- Acceptable alternative: small priced seed only if a true specialist lead appears
- Not recommended now: large priced seed built mostly on category heat

### Recommended amount now
- Base case: $1.5M to $3.0M
- Stretch case if strong investor competition emerges: $3.0M to $4.0M

### What the money should buy
- 3 to 5 structured design partners converted into paid pilots
- one narrow ICP with repeatable message and onboarding motion
- production-grade proof on one or two highest-value rails, not ten surfaces at once
- one flagship partner or integration that materially expands trust or distribution
- an implementation / GTM layer around the founder

### Recommended use of funds
- 40% product hardening and control-plane observability
- 25% implementation / solutions engineering and pilot onboarding
- 20% security / compliance / diligence readiness
- 15% GTM experiments focused on one ICP and one wedge message

### Milestones before or during raise
- publish canonical maturity and metrics dashboard
- close at least 2 design partners with named internal champions and scoped success criteria
- show one high-value workflow in production with policy + approval + audit proof
- land one written provider / partner commitment on cards, fiat, or payouts

### Best investor profile
- seed or pre-seed funds with AI infra + fintech infra overlap
- operator angels with payments, cards, wallets, and agent-platform credibility
- strategic investors that expand rails, cards, or enterprise access without demanding exclusivity

### Wrong investor profile
- fintech funds requiring mature ARR and compliance stack already fully institutionalized
- crypto funds expecting token narratives or consumer speculation
- generalist AI funds who want obvious PLG or model-layer defensibility

### What justifies a stronger next round
- 3 to 5 paid pilots
- one lighthouse customer or partner with public credibility
- clean wedge dominance in procurement, travel/expense, or agent payments for APIs
- strong reliability evidence and tighter partner architecture

## G. Capital Strategy Scenarios

### Scenario A: Raise now
- Size: $3M to $4M
- Instrument: SAFE or small seed
- Pros: buys speed, lets founder stay aggressive, captures category warmth
- Risks: weaker pricing, more dilution, narrative may outrun proof
- Required narrative: “The agent-payment control plane is inevitable, and we are the best technical team to build it”

### Scenario B: Delay and de-risk first
- Delay until: 2 to 3 paid pilots, one flagship partner, clear reliability metrics
- Pros: stronger pricing, broader investor pool, cleaner story
- Risks: runway and category-speed risk, incumbents keep moving
- What becomes stronger: conversion story, customer proof, moat credibility

### Scenario C: Hybrid strategy
- Raise now: $1.5M to $2.5M from angels / strategics / a few specialists
- Raise later: institutional seed after proof points
- Pros: minimizes dilution while buying time to prove the wedge; best match for current maturity
- Risks: two fundraising motions instead of one
- Required narrative: “We are raising enough to turn technical credibility into commercial proof”

### Recommended scenario
Scenario C is the most rational.

## H. Investor Narrative Recommendations

### Most fundable framing
**Sardis is the trust and control layer for AI-agent payments.**

Why this wins:
- It avoids getting trapped as a rail or wallet feature.
- It leverages the strongest real product surface in the repo.
- It speaks directly to enterprise adoption blockers.

### Top 3 narrative variants

1. **Governed AI payments / control plane**
- Best for: fintech infra and enterprise seed investors
- Strength: closest to product truth
- Objection: “Is this too niche?”
- Defense: trust and control is what determines whether agentic payments happen at all

2. **Payment operating system for the agent economy**
- Best for: broader seed funds and strategic investors
- Strength: bigger outcome and platform ambition
- Objection: “Sounds too broad and early”
- Defense: start with one wedge workflow, expand across rails under the same control boundary

3. **Compliance and observability layer for agentic commerce**
- Best for: enterprise software and compliance-aware investors
- Strength: sharp B2B value proposition
- Objection: “Is that a feature inside existing payment stacks?”
- Defense: existing stacks optimize payment movement, not deterministic AI governance across rails

### Weak narrative to avoid
- “We are a modern bank for agents”
- “We do everything across all rails, globally, today”
- “We are just x402 plus cards plus onramp”

## I. Valuation and Dilution Reasoning

### If Sardis raised now
Realistic band:
- $12M to $18M post-money base case
- $18M to $22M post only if a few strong specialists compete

Why not higher:
- pre-repeatable revenue
- broad surface, early wedge
- solo founder risk
- category still being defined

### After stronger proof points
Realistic band:
- $25M to $40M post-money for a seed
- upside beyond that only if there is real investor competition plus convincing paid pilot evidence

### What moves valuation up
- named or publicly referenceable customers / pilots
- one flagship partner that materially expands rail reach
- production reliability metrics and clear pricing acceptance
- tighter story focused on one ICP and one wedge

### What moves valuation down
- continued category breadth without conversion proof
- inconsistent traction definitions
- unclear live production usage
- investor concern that incumbents will absorb the product surface

### Rational dilution logic
- Taking a slightly smaller round now at lower dilution is rational if it materially improves the chance of a stronger institutional seed later.
- Chasing a vanity seed today risks both pricing disappointment and a weak syndicate.

## J. Risk Matrix

| Risk | Severity | Why it matters | Fixable? | Milestone that reduces it |
|---|---|---|---|---|
| Product breadth risk | High | Too many rails and surfaces can blur the wedge | Yes | freeze one flagship workflow and one ICP |
| GTM risk | High | No repeatable commercial motion yet | Yes | 3 to 5 paid pilots and one public case study |
| Competitive / incumbent risk | High | Stripe, Coinbase, Rain, Shopify, Visa, Mastercard can all move into adjacent surfaces | Partly | become workflow-embedded before primitives commoditize |
| Narrative risk | High | Can be bucketed as feature / wrapper / crypto startup | Yes | tighten framing around governed, observable AI payments |
| Team concentration risk | High | Solo founder concentration affects reliability and enterprise confidence | Yes | hire implementation and security/compliance support |
| Regulatory / compliance risk | Medium-High | Bigger claims trigger heavier diligence and slow sales | Yes | precise claims, external audits, partner RACI clarity |
| Financing risk | Medium-High | Wrong round now can create a weak cap table and low-signal process | Yes | run a selective specialist process only |
| Market timing risk | Medium | Category is early and noisy; consumer commerce story may be premature | Yes | stay B2B and workflow-specific |

## K. Final Recommendation

### Is this company fundable now?
Yes, selectively.

### For whom is it fundable now?
- specialist AI infra seed investors
- fintech infra seed investors
- strategic investors in payments / wallets / cards / stablecoins
- operator angels with direct distribution or domain leverage

### What money should it raise?
- A selective $1.5M to $3.0M SAFE or small pre-seed style round now
- Then a larger institutional seed after proof points are materially stronger

### Strongest investor story
Sardis is not another payment rail for AI agents. It is the control plane that makes AI-agent money movement trustworthy, observable, and deployable inside real businesses.

### Milestones that most increase fundraising power
- 3 to 5 paid pilots
- one flagship provider or distribution partnership
- publicly referenceable case study
- production reliability and control metrics
- one crisp ICP wedge

## L. 30 / 60 / 90 Day Fundraising Action Plan

### 30 days
- Freeze investor narrative around one wedge: governed AI payments for B2B workflows
- Publish one source-of-truth metrics artifact with strict labels: verified, founder-reported, planned
- Remove or downgrade maturity claims that conflict with README status
- Pick one ICP for proof: procurement, travel/expense, or API-native agent payments
- Start targeted relationship-building with 20 to 30 specialist investors and operator angels, not a mass process

### 60 days
- Close 2 to 3 structured design partners with written success criteria
- Produce one live workflow demo with policy, approval, audit, and exception handling visible
- Finalize diligence packets for Stripe / Rain / Lightspark / other key partners
- Show the first signs of pricing acceptance, even if pilots are small

### 90 days
- Convert at least 1 to 2 pilots into paid engagements or signed commercial paths
- Publish reliability and operational metrics from live deployments
- Decide whether proof is strong enough for a broader seed process
- If yes, run a focused institutional seed. If not, extend the hybrid strategy with more strategic/operator capital only.

## Sources Reviewed

### Local / internal
- README and architecture notes in repo
- `docs/investor/traction-snapshot-2026-03.md`
- `docs/investor/sardis-competitive-positioning-q1-2026.md`
- `docs/investor/internal/a16z_ic_memo_2026-03.md`
- `docs/investor/sardis-competitive-moat.html`
- GTM and partner diligence notes under `docs/marketing/`
- Recent local git history and orchestration code paths

### Public market and funding sources
- a16z: https://a16z.com/newsletter/agent-payments-stack/
- Skyfire launch / beta: https://skyfire.xyz/skyfire-launches-identity-and-payments-for-autonomous-ai-agents/ and https://www.businesswire.com/news/home/20250306938250/en/Skyfire-Exits-Beta-with-Enterprise-Ready-Payment-Network-for-AI-Agents
- Skyfire funding (secondary): https://www.thesaasnews.com/news/skyfire-raises-8-5-million-in-seed-round
- Payman funding (secondary): https://www.linkedin.com/posts/tyllenbicakcic_payman-ai-that-pays-humans-activity-7226698798197002240-ZwtY and https://www.examinecrypto.com/post/payman-ai-an-ai-to-human-payments-platform-secures-3m-in-pre-seed-funding-round
- Natural funding: https://www.natural.co/blog/natural-seed-round and https://www.businesswire.com/news/home/20251023151615/en/Fintech-Natural-Launches-With-%249.8M-Seed-Round-to-Power-Agentic-Payments
- Paid funding: https://www.prnewswire.com/news-releases/paid-raises-21-million-seed-to-build-infrastructure-for-the-ai-agent-economy-302569185.html
- Rain funding: https://rain.xyz/resources/rain-announces-24-5-million-in-funding-led-by-norwest-to-expand-stablecoin-powered-card-issuing-globally and https://www.prnewswire.com/news-releases/rain-raises-58m-series-b-led-by-sapphire-ventures-to-become-the-enterprise-stablecoin-platform-of-record-302540587.html
- Crossmint funding: https://blog.crossmint.com/crossmint-raises-23-6m-led-by-ribbit-capital/
- Turnkey Series B: https://turnkey.com/blog/30m-series-b-to-secure-the-next-era-of-crypto
- Privy fundraise and acquisition: https://privy.io/blog/announcing-our-fundraise-led-by-ribbit-capital and https://privy.io/blog/announcing-our-acquisition-by-stripe
- Bridge / Stripe acquisition context: https://www.cnbc.com/2025/02/04/stripe-closes-1point1-billion-bridge-deal-prepares-for-stablecoin-push-.html
- Locus YC profile: https://www.ycombinator.com/companies/locus
- OpenAI / agentic commerce caution: https://www.digitalcommerce360.com/2026/03/06/openai-shifts-checkout-plans-agentic-commerce-strategy/
