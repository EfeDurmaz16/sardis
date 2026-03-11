# State Money Transmitter Licensing Analysis -- Sardis

**Document ID:** SARDIS-FINCEN-STATE-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Legal
**Classification:** Internal

---

## 1. Overview

Federal MSB registration with FinCEN does **not** preempt state-level money transmitter licensing (MTL) requirements. Each state independently regulates money transmission under its own statutes, and operating as an MSB in a state without the required state license is a separate violation from federal registration failures.

Sardis's non-custodial MPC wallet architecture (Turnkey) provides a strong basis for exemption from money transmitter classification in most states, but the analysis is state-specific and depends on each state's definition of "money transmission," "control," and available exemptions.

This document provides a comprehensive state-by-state analysis to guide Sardis's licensing strategy.

---

## 2. Non-Custodial Exemption Framework

### 2.1 Core Argument

Sardis's exemption argument rests on three pillars:

1. **No custody of funds:** Sardis never holds, controls, or has unilateral access to user funds. Private keys are managed via Turnkey's MPC architecture with key shares distributed across secure enclaves (TEEs). Neither Sardis nor Turnkey can independently sign transactions.

2. **No momentary possession:** During a payment flow, stablecoins move directly from the user's on-chain wallet (Safe Smart Account) to the recipient's address. Funds never transit through a Sardis-controlled address or escrow (except in the optional RefundProtocol escrow for dispute resolution, which is a smart contract, not Sardis custody).

3. **Software provider classification:** Under FinCEN's 2019 guidance and most state analogs, providers of wallet software that do not have independent control over user funds are classified as software providers, not money transmitters.

### 2.2 Limiting Factors

The exemption argument is weakened in states that:

- Define "money transmission" broadly to include "facilitating" or "arranging" transfers (regardless of custody)
- Have not adopted modern definitions that account for non-custodial crypto architectures
- Require separate analysis for "prepaid access" (relevant to Sardis's virtual card issuance via Stripe Issuing)
- Apply a "substance over form" test that could look past the non-custodial architecture to Sardis's role in initiating and orchestrating payments

### 2.3 Agent-of-Payee Exemption

An alternative or supplementary exemption available in many states is the "agent of the payee" exemption. Under this exemption, a payment processor acting as the agent of the merchant (payee) is not considered a money transmitter because the payment is deemed received by the merchant at the moment it is received by the agent.

**Relevance to Sardis:** For the "Pay with Sardis" merchant checkout flow, Sardis acts as the merchant's payment processor. In states recognizing the agent-of-payee exemption, this flow may be exempt from MTL requirements.

**CSBS Agent-of-Payee Exemption Map (as of 2026):**

| Status | States |
|---|---|
| Exemption available by statute | AL, AZ, CA, CO, CT, DC, GA, HI, IN, IA, KS, KY, MA, MD, ME, MN, MT, ND, NE, NH, NJ, NM, NV, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VA, VT, WA, WI, WV, WY (22+ states) |
| Case-by-case determination | AR, DE, MO |
| No exemption | FL, IL, LA, MI, MS, NC |

### 2.4 Payment Processor Exemption

Some states exempt "payment processors" from MTL requirements if:

- Payment processing is the entity's primary business activity
- The entity uses regulated payment networks (ACH, card networks)
- A formal written agreement exists between the processor and the merchant

**Relevance to Sardis:** Sardis's checkout flow processes payments via on-chain stablecoin transfers (not ACH/card networks), so the traditional "payment processor" exemption may not apply directly. However, Sardis's virtual card issuance via Stripe Issuing uses the card network, which may qualify for this exemption in certain states.

---

## 3. State-by-State Analysis

### 3.1 Tier 1: Registration/License Required (Even with Exemption Argument)

These states either have the most stringent requirements, the broadest definitions of money transmission, or specific virtual currency licensing regimes that likely capture Sardis's activities regardless of non-custodial architecture.

#### New York -- BitLicense

| Attribute | Details |
|---|---|
| **Regulator** | New York Department of Financial Services (NYDFS) |
| **License** | BitLicense (23 NYCRR Part 200) |
| **Filing fee** | $5,000 |
| **Surety bond** | Determined by NYDFS based on risk assessment |
| **Timeline** | 12-18 months (historically; improving) |
| **Capital requirement** | Determined by NYDFS; typically $100,000+ |
| **Non-custodial exemption** | Unclear. NYDFS defines "virtual currency business activity" broadly to include "storing, holding, or maintaining custody or control of virtual currency on behalf of others" AND "controlling, administering, or issuing a virtual currency." The "control" prong may capture MPC wallet orchestration. |
| **Agent-of-payee** | Available but narrowly interpreted |
| **Recommendation** | **Engage NY-licensed counsel immediately.** Consider: (a) applying for BitLicense ($5K + substantial legal costs), (b) partnering with a BitLicense holder, or (c) geo-blocking NY users until license is obtained. |
| **Estimated cost** | $50,000-$200,000 (legal + application + ongoing compliance) |

#### California -- DFPI Digital Financial Assets Law

| Attribute | Details |
|---|---|
| **Regulator** | California Department of Financial Protection and Innovation (DFPI) |
| **License** | Digital Financial Assets Law (DFAL) license (effective July 1, 2025; applications opening Q1 2026) |
| **Filing fee** | $5,000 |
| **Surety bond** | $250,000 minimum (may be higher based on volume) |
| **Timeline** | 3-6 months (estimated for new regime) |
| **Capital requirement** | $500,000 net worth (proposed) |
| **Non-custodial exemption** | The DFAL includes an exemption for persons who "provide only connectivity software or computing hardware" used for virtual currency activities. Sardis's MPC wallet orchestration may qualify, but the exemption is narrow. |
| **Agent-of-payee** | Available under California money transmission law |
| **Recommendation** | **Apply for DFAL license.** California is Sardis's likely largest market. The new regime is purpose-built for crypto businesses and more achievable than NY BitLicense. |
| **Estimated cost** | $30,000-$80,000 (legal + application + bond) |

### 3.2 Tier 2: Likely Exempt (Non-Custodial Architecture)

These states have explicit non-custodial exemptions, crypto-friendly regulatory frameworks, or definitions of money transmission that clearly exclude Sardis's architecture.

#### Wyoming

| Attribute | Details |
|---|---|
| **Regulator** | Wyoming Division of Banking |
| **Exemption basis** | Wyoming Digital Asset Act (W.S. 34-29-101 et seq.) -- most crypto-friendly state. Explicit exemption for non-custodial virtual currency activities. Wyoming also offers DAO LLC and Special Purpose Depository Institution (SPDI) options. |
| **Non-custodial exempt?** | **Yes.** Wyoming explicitly excludes non-custodial wallet providers from money transmitter definition. |
| **Action required** | Document exemption basis; retain Wyoming counsel opinion. No license application needed. |
| **Cost** | $3,000-$5,000 (legal opinion) |

#### Texas

| Attribute | Details |
|---|---|
| **Regulator** | Texas Department of Banking |
| **Exemption basis** | Texas Money Services Act (Tex. Fin. Code Ch. 151). Texas Department of Banking issued guidance that "non-custodial wallet software providers do not engage in money transmission." Also adopted MMTMA with agent-of-payee provisions. |
| **Non-custodial exempt?** | **Very likely yes.** Clear regulatory guidance favoring non-custodial exemption. |
| **Action required** | Document exemption basis; retain Texas counsel opinion. |
| **Cost** | $3,000-$5,000 (legal opinion) |

#### Florida

| Attribute | Details |
|---|---|
| **Regulator** | Florida Office of Financial Regulation (OFR) |
| **Exemption basis** | Florida's money transmitter statute (Fla. Stat. Chapter 560) does not have an explicit non-custodial exemption, but OFR has indicated in guidance that entities not holding customer funds may not need a license. |
| **Non-custodial exempt?** | **Likely yes**, but less certain than WY/TX. Florida does NOT recognize agent-of-payee exemption. |
| **Action required** | Obtain Florida counsel opinion. Consider no-action letter from OFR. |
| **Cost** | $5,000-$10,000 (legal opinion + potential OFR consultation) |

#### Colorado

| Attribute | Details |
|---|---|
| **Regulator** | Colorado Division of Banking |
| **Exemption basis** | Colorado Digital Token Act (C.R.S. 11-110-101 et seq.) provides exemption for certain digital token activities. Colorado also has relatively narrow money transmitter definitions. |
| **Non-custodial exempt?** | **Likely yes.** The Digital Token Act provides a pathway for exemption, and non-custodial providers generally fall outside Colorado's money transmitter definition. |
| **Action required** | Document exemption basis. |
| **Cost** | $3,000-$5,000 (legal opinion) |

#### Indiana

| Attribute | Details |
|---|---|
| **Regulator** | Indiana Department of Financial Institutions |
| **Exemption basis** | MMTMA adopted state. Agent-of-payee exemption available. Non-custodial architecture likely exempt under narrow money transmission definition. |
| **Non-custodial exempt?** | **Yes.** |
| **Action required** | Document exemption basis. |
| **Cost** | $2,000-$4,000 (legal opinion) |

#### Iowa

| Attribute | Details |
|---|---|
| **Regulator** | Iowa Division of Banking |
| **Exemption basis** | MMTMA adopted state. |
| **Non-custodial exempt?** | **Yes.** |
| **Action required** | Document exemption basis. |
| **Cost** | $2,000-$4,000 (legal opinion) |

#### Minnesota

| Attribute | Details |
|---|---|
| **Regulator** | Minnesota Department of Commerce |
| **Exemption basis** | MMTMA adopted state. |
| **Non-custodial exempt?** | **Yes.** |
| **Action required** | Document exemption basis. |
| **Cost** | $2,000-$4,000 (legal opinion) |

#### Arizona

| Attribute | Details |
|---|---|
| **Regulator** | Arizona Department of Insurance and Financial Institutions |
| **Exemption basis** | FinTech Sandbox program + MMTMA adoption. Arizona is generally favorable to crypto businesses. |
| **Non-custodial exempt?** | **Yes.** |
| **Action required** | Document exemption basis. Consider FinTech Sandbox participation for additional regulatory clarity. |
| **Cost** | $2,000-$4,000 (legal opinion) |

#### Tennessee, North Dakota

| Attribute | Details |
|---|---|
| **Regulator** | State banking departments |
| **Exemption basis** | MMTMA adopted states with agent-of-payee exemptions. |
| **Non-custodial exempt?** | **Yes.** |
| **Action required** | Document exemption basis. |
| **Cost** | $2,000-$4,000 each (legal opinion) |

### 3.3 Tier 3: Requires Analysis (Ambiguous)

These states have statutes that could go either way on non-custodial exemption. A legal opinion is recommended but licensing may not be required.

#### Illinois

| Attribute | Details |
|---|---|
| **Regulator** | Illinois Department of Financial and Professional Regulation (IDFPR) |
| **Notes** | Illinois Transmitters of Money Act has a broad definition. No explicit crypto exemption. No agent-of-payee exemption. However, IDFPR has not actively enforced against non-custodial wallet providers. |
| **Recommendation** | Obtain legal opinion. May need to apply for license if opinion is unfavorable. |
| **Cost** | $5,000-$15,000 (legal opinion); $10,000-$50,000 (if licensing required) |

#### Georgia

| Attribute | Details |
|---|---|
| **Regulator** | Georgia Department of Banking and Finance |
| **Notes** | Georgia's money transmitter law covers "receiving money or monetary value for transmission." The definition of "receiving" in a non-custodial context is unclear. Agent-of-payee exemption available. |
| **Recommendation** | Obtain legal opinion. Agent-of-payee may cover checkout flow. |
| **Cost** | $3,000-$8,000 (legal opinion) |

#### Massachusetts

| Attribute | Details |
|---|---|
| **Regulator** | Massachusetts Division of Banks |
| **Notes** | Massachusetts has been moderately active on crypto regulation. Money transmitter statute is traditional and does not address non-custodial architectures directly. Agent-of-payee exemption available. |
| **Recommendation** | Obtain legal opinion. |
| **Cost** | $3,000-$8,000 (legal opinion) |

#### Washington

| Attribute | Details |
|---|---|
| **Regulator** | Washington Department of Financial Institutions |
| **Notes** | Washington's Uniform Money Services Act includes "virtual currency" in the definition of money transmission. However, the state has indicated that non-custodial providers may be exempt. Agent-of-payee exemption available. |
| **Recommendation** | Obtain legal opinion. |
| **Cost** | $5,000-$10,000 (legal opinion) |

#### Louisiana, Mississippi, Michigan, North Carolina

| Attribute | Details |
|---|---|
| **Notes** | These states do not offer agent-of-payee exemptions and have relatively broad money transmitter definitions. Non-custodial exemption status is unclear. |
| **Recommendation** | Obtain legal opinions. Consider geo-blocking if opinions are unfavorable and licensing cost is prohibitive. |
| **Cost** | $3,000-$8,000 each (legal opinion) |

### 3.4 Tier 4: Low Priority (Small Market or Clear Exemption)

Remaining states generally fall into one of two categories:

1. **Small market states** with standard money transmitter laws where Sardis has minimal user presence. Address licensing as user base grows in these states.
2. **States with clear exemptions** for non-custodial providers or broad agent-of-payee exemptions.

These states should be addressed in Phase 3 of the licensing strategy (see Section 5).

---

## 4. Multi-State Licensing Options

### 4.1 NMLS (Nationwide Multistate Licensing System)

Most state money transmitter license applications are filed through the NMLS platform (https://mortgage.nationwidelicensingsystem.org). This provides a centralized application process, though each state reviews and approves independently.

**Benefits:**
- Single platform for managing multiple state applications
- Centralized document repository
- Standardized reporting

**Limitations:**
- Each state still requires individual application, separate fees, and independent review
- Processing times vary dramatically by state
- Not all states participate (though most do)

### 4.2 State Compacts and Reciprocity

The Money Transmitter Modernization Act (MMTMA), model legislation from the Conference of State Bank Supervisors (CSBS), has been adopted by 7 states (AZ, IN, IA, MN, TX, TN, ND). Adoption is expected to continue growing.

MMTMA states generally have:
- Standardized definitions of money transmission
- Agent-of-payee exemption provisions
- More modern treatment of virtual currency
- Reciprocal examination arrangements

### 4.3 Partnership Strategy

As an alternative to direct licensing, Sardis could partner with a fully licensed money transmitter to operate under their license umbrella. This is common in fintech (e.g., operating as an "authorized delegate" or "agent" of a licensed entity).

**Potential partners:**
- **Circle:** Already licensed as an MSB and holds state licenses; Sardis uses USDC.
- **Stripe:** Holds money transmitter licenses nationwide; Sardis already uses Stripe Issuing.
- **Bridge (Stripe):** OCC conditional approval for national trust bank charter.
- **Licensed banking-as-a-service providers:** Various BaaS platforms that provide license coverage.

**Tradeoffs:**
- Pro: Immediate nationwide coverage without per-state licensing
- Pro: Significantly lower cost ($0-$50K/year vs. $500K+ for multi-state licensing)
- Con: Dependency on partner's license and compliance program
- Con: Revenue sharing or platform fees
- Con: Less control over compliance decisions

---

## 5. Recommended Licensing Strategy

### Phase 1: Immediate (Q1-Q2 2026) -- Cost: $0-$30K

1. **Complete federal MSB registration** with FinCEN (see `msb-registration-guide.md`). Cost: $0. Timeline: 30 days.
2. **Obtain legal opinions for priority states:** New York, California, Texas, Florida. Cost: $15,000-$30,000 for four opinions. Timeline: 4-8 weeks.
3. **Document exemption basis** for all Tier 2 states (Wyoming, Colorado, Indiana, Iowa, Minnesota, Arizona, Tennessee, North Dakota). Create a formal legal memorandum detailing the non-custodial architecture and its implications under each state's law.
4. **Decision point:** Based on legal opinions, determine whether to apply for NY BitLicense and CA DFAL license, or pursue alternative strategies (partnership, geo-blocking).

### Phase 2: Strategic (Q2-Q4 2026) -- Cost: $30K-$100K

5. **Apply for California DFAL license** if legal opinion recommends it. Cost: $30,000-$80,000 (legal + application + bond). Timeline: 3-6 months.
6. **Begin New York BitLicense process** if pursuing (or formalize partnership with licensed entity for NY coverage). Cost: $50,000-$200,000. Timeline: 12-18 months.
7. **Obtain legal opinions for Tier 3 states** (IL, GA, MA, WA, LA, MS, MI, NC) as user base grows in these states. Cost: $3,000-$8,000 per state.
8. **Evaluate partnership strategy** as alternative to multi-state licensing.

### Phase 3: Expansion (2027+) -- Cost: Variable

9. **Address remaining states** as user base and revenue justify the licensing cost.
10. **Monitor regulatory changes:** Several states are expected to adopt MMTMA or pass crypto-specific legislation that may simplify licensing or provide clearer exemptions.
11. **Consider national trust bank charter** only if Sardis's business model evolves to include custody or stablecoin issuance (unlikely per current strategy).

---

## 6. Cost Summary

### 6.1 Licensing Costs by Phase

| Phase | Items | Low Estimate | High Estimate |
|---|---|---|---|
| Phase 1 | Federal MSB + 4 state legal opinions | $15,000 | $30,000 |
| Phase 2 | CA DFAL license | $30,000 | $80,000 |
| Phase 2 | NY BitLicense (if pursuing) | $50,000 | $200,000 |
| Phase 2 | Tier 3 legal opinions (8 states) | $24,000 | $64,000 |
| Phase 3 | Additional state licenses (as needed) | $50,000 | $500,000 |

### 6.2 Ongoing Annual Costs

| Item | Annual Cost | Notes |
|---|---|---|
| State license renewals | $5,000-$20,000 | Varies by state; some have annual renewal fees |
| Surety bond premiums | $2,500-$25,000 | 1-10% of bond face value; varies by creditworthiness |
| State examination costs | $5,000-$50,000 | States may charge for examinations |
| Legal counsel (regulatory) | $10,000-$50,000 | Ongoing counsel for multi-state compliance |
| NMLS fees | $1,000-$5,000 | Annual platform and reporting fees |
| **Total annual** | **$23,500-$150,000** | Depends on number of state licenses held |

### 6.3 Alternative: Partnership Model

| Item | Cost | Notes |
|---|---|---|
| Partnership setup | $10,000-$50,000 | Legal review of partnership agreement |
| Annual partnership fees | $20,000-$100,000 | Revenue share or flat fee to licensed partner |
| Compliance oversight | $5,000-$20,000 | Ongoing compliance coordination |
| **Total Year 1** | **$35,000-$170,000** | |
| **Total ongoing annual** | **$25,000-$120,000** | |

---

## 7. State Regulatory Contact Information

| State | Regulator | Website |
|---|---|---|
| New York | NYDFS | https://www.dfs.ny.gov |
| California | DFPI | https://dfpi.ca.gov |
| Texas | Dept. of Banking | https://www.dob.texas.gov |
| Florida | OFR | https://www.flofr.gov |
| Wyoming | Division of Banking | https://wyomingbankingdivision.wyo.gov |
| Illinois | IDFPR | https://idfpr.illinois.gov |
| Washington | DFI | https://dfi.wa.gov |
| NMLS (multi-state) | CSBS | https://mortgage.nationwidelicensingsystem.org |

---

## 8. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-11 | Sardis Compliance | Initial document |
