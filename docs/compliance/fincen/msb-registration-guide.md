# FinCEN MSB Registration Guide -- Sardis

**Document ID:** SARDIS-FINCEN-MSB-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Legal
**Classification:** Internal

---

## 1. Overview

Sardis must register as a Money Services Business (MSB) with the Financial Crimes Enforcement Network (FinCEN) under the Bank Secrecy Act (BSA). Registration is accomplished via FinCEN Form 107 ("Registration of Money Services Business"), which is filed electronically at no cost through the BSA E-Filing System.

**Key regulatory citation:** 31 CFR Section 1022.380 -- Registration of money services businesses.

**Processing time:** Approximately 30 calendar days from submission.

**Renewal cadence:** Every 2 years from the date of initial registration, or within 180 days of any material change in ownership, control, or organizational structure.

### 1.1 Why Register Proactively

Sardis operates a non-custodial MPC wallet infrastructure (via Turnkey) where neither Sardis nor the user holds the complete private key. Under FinCEN's 2019 CVC Guidance, non-custodial wallet providers are generally **not** classified as money transmitters. FinCEN further withdrew its 2020 proposal to impose KYC requirements on non-custodial wallets in August 2024.

Despite this favorable regulatory posture, Sardis registers proactively for the following reasons:

1. **Investor confidence:** Registered MSB status signals regulatory seriousness to institutional investors and partners.
2. **Conservatism on classification:** Sardis orchestrates payments between parties and issues virtual cards via Stripe Issuing. The "payment processor" and "agent of payee" exemptions are fact-specific, and registering eliminates ambiguity.
3. **Banking relationships:** Banks and payment partners (Stripe, Circle, stablecoin on/off-ramp providers) increasingly require MSB registration as a precondition for business relationships.
4. **Zero cost:** Federal MSB registration is free. The only cost is legal review time.
5. **Preemptive defense:** If FinCEN or a state regulator later challenges Sardis's non-custodial classification, having voluntarily registered demonstrates good faith and cooperation.

---

## 2. Registration Requirements

### 2.1 Entity Information

The following information must be provided on Form 107:

| Field | Description | Sardis Value |
|---|---|---|
| Legal name of MSB | Entity as registered with state | [Legal entity name] |
| DBA (if any) | Doing business as | Sardis |
| EIN / TIN | Employer Identification Number | [To be provided] |
| Address | Principal place of business | [Registered address] |
| State of incorporation | Where the entity is legally formed | [State] |
| Date of incorporation | Entity formation date | [Date] |
| Fiscal year end | For reporting purposes | December 31 |

### 2.2 Principal Owner / Officer Designation

FinCEN requires disclosure of each individual who directly or indirectly owns or controls 25% or more of the MSB, as well as any individual who exercises significant responsibility for the MSB's compliance program.

**Required information per individual:**

- Full legal name
- Title / position
- Date of birth
- Social Security Number (SSN) or Individual Taxpayer Identification Number (ITIN)
- Residential address
- Percentage of ownership (if applicable)

### 2.3 Services Provided

Form 107 requires the MSB to indicate which money services it provides. The following checkboxes are available:

| Service | Check? | Rationale |
|---|---|---|
| Dealer in foreign exchange | No | Sardis does not exchange fiat currencies |
| Check casher | No | Not applicable |
| Issuer / seller of traveler's checks or money orders | No | Not applicable |
| Provider of prepaid access | Potentially | Virtual cards via Stripe Issuing could qualify depending on structure |
| Money transmitter | Yes (conservative) | Sardis facilitates stablecoin transfers between parties |
| U.S. Postal Service | No | Not applicable |

**Note:** Checking "money transmitter" is the conservative approach. Even though Sardis's non-custodial architecture may exempt it from money transmitter classification, registering under this category ensures full BSA compliance obligations are met and eliminates any enforcement ambiguity.

### 2.4 Geographic Coverage

Form 107 requires listing all states and territories where the MSB conducts business or has agents. For a digital-first platform like Sardis, this typically means all states where users/merchants are located.

**Recommendation:** List all 50 states, the District of Columbia, and U.S. territories where Sardis accepts users. This can be amended as the geographic footprint changes.

---

## 3. Step-by-Step Registration Process

### Step 1: Prepare Required Information

Before beginning the electronic filing, gather:

- [ ] Legal entity formation documents (Articles of Incorporation / Organization)
- [ ] EIN confirmation letter (IRS Form CP 575 or equivalent)
- [ ] Principal owner(s) personal information (name, DOB, SSN, address)
- [ ] Registered agent information (name, address, state)
- [ ] List of states where Sardis operates or intends to operate
- [ ] Designated compliance officer information

### Step 2: Create BSA E-Filing Account

1. Navigate to the BSA E-Filing System: https://bsaefiling.fincen.treas.gov
2. Click "Register" to create a new organizational account.
3. Complete the organizational registration form with Sardis's entity information.
4. Designate a Supervisory User who will manage the BSA E-Filing account. This should be the compliance officer or a senior executive.
5. The Supervisory User will receive a confirmation email with login credentials.
6. Log in and set up any additional users who will need access for ongoing BSA filings (SARs, etc.).

### Step 3: Complete FinCEN Form 107

1. Log in to the BSA E-Filing System.
2. Select "File" and then "FinCEN Registration of Money Services Business (RMSB)" or "Form 107."
3. Complete all required sections:
   - **Part I:** Filing information (initial registration vs. re-registration)
   - **Part II:** MSB information (legal name, address, EIN, state of formation)
   - **Part III:** Owner/officer information (for each individual meeting the 25% threshold or compliance designation)
   - **Part IV:** MSB activities (check applicable money services categories)
   - **Part V:** States and territories where MSB is authorized to do business
   - **Part VI:** Agent information (if Sardis uses agents to provide money services -- likely N/A for initial filing)
4. Review all entries for accuracy. Incorrect information may delay processing or trigger follow-up inquiries.

### Step 4: Designate Compliance Officer

Under BSA regulations, every registered MSB must designate a person responsible for the day-to-day management of the AML compliance program. This designation should be made before or concurrent with registration.

**Compliance Officer responsibilities:**

- Oversee the BSA/AML compliance program (see `bsa-aml-program.md`)
- Authorize and file Suspicious Activity Reports (SARs) via BSA E-Filing
- Respond to FinCEN inquiries and regulatory examinations
- Coordinate annual AML training for all employees
- Report to CEO / Board on compliance matters at least quarterly
- Maintain awareness of evolving regulations (GENIUS Act, MiCA, state laws)

### Step 5: Submit and Await Confirmation

1. After final review, submit Form 107 electronically.
2. The system will provide an immediate confirmation number -- record this.
3. FinCEN will process the registration and issue a formal acknowledgment within approximately 30 calendar days.
4. The acknowledgment will include an MSB Registration Number (also called the "FinCEN Registration Number"), which must be retained and provided upon request by law enforcement or regulators.

### Step 6: Post-Registration Obligations

Upon successful registration, Sardis must immediately comply with all BSA obligations applicable to registered MSBs. See the following companion documents:

- `bsa-aml-program.md` -- Full BSA/AML compliance program
- `regulatory-reporting-checklist.md` -- Reporting obligations and calendar
- `state-licensing-analysis.md` -- State-level licensing requirements

---

## 4. Renewal and Amendment Requirements

### 4.1 Biennial Renewal

MSB registration must be renewed every 2 years. The renewal is filed via the same BSA E-Filing System using a re-registration Form 107.

**Renewal timeline:**

| Event | Deadline |
|---|---|
| Initial registration | Within 180 days of commencing operations as an MSB |
| First renewal | 2 years from initial registration date |
| Subsequent renewals | Every 2 years thereafter |

**Important:** Failure to renew on time does not automatically terminate registration, but it does expose the MSB to enforcement action and may impair banking relationships.

### 4.2 Material Change Amendments

Sardis must file an amended Form 107 within 180 days of any of the following material changes:

- Change in legal name or DBA
- Change in principal place of business address
- Change in ownership or control (any individual crossing the 25% threshold)
- Addition or removal of money services categories
- Change in states or territories of operation
- Change in designated compliance officer (recommended, though not strictly required by regulation)

---

## 5. Non-Custodial Exemption Analysis

### 5.1 FinCEN 2019 CVC Guidance

FinCEN's May 2019 "Application of FinCEN's Regulations to Certain Business Models Involving Convertible Virtual Currencies" established the following framework:

**Four factors for money transmitter classification:**

1. **Who owns the value?** -- The user owns the USDC/EURC in their Sardis wallet. Sardis does not hold or own user funds.
2. **Where is the value stored?** -- On-chain in smart contract wallets (Safe Smart Accounts v1.4.1) controlled by MPC key shares. Value is never stored in Sardis's systems.
3. **Does the owner interact directly with the payment system?** -- Yes. Users (or their AI agents) initiate transactions directly. Sardis provides the orchestration layer but does not unilaterally move funds.
4. **Does the intermediary have total independent control over the value?** -- No. Turnkey MPC architecture means neither Sardis nor Turnkey holds the complete private key. Sardis cannot unilaterally access, move, or seize user funds.

**FinCEN's conclusion for this pattern:** "A person that provides and sells software designed to facilitate the creation of a CVC wallet...is not a money transmitter."

### 5.2 Turnkey MPC Architecture

Sardis uses Turnkey for MPC (Multi-Party Computation) wallet infrastructure:

- Private keys are split into multiple shares across secure enclaves (TEEs)
- Neither Sardis, Turnkey, nor the user holds the complete private key
- Transaction signing requires cooperation of multiple parties
- Turnkey is explicitly non-custodial -- they never have the ability to unilaterally access or move user funds
- This architecture is analogous to the "multi-sig provider without unilateral control" scenario that FinCEN explicitly excluded from money transmitter classification

### 5.3 FinCEN Non-Custodial Wallet KYC Proposal (Withdrawn)

In December 2020, FinCEN proposed a rule that would have imposed KYC requirements on transactions involving non-custodial (self-hosted) wallets. This proposal was formally **withdrawn in August 2024** after receiving over 7,700 public comments, the majority opposing the rule.

**Implication for Sardis:** The withdrawal confirms FinCEN's current position that non-custodial wallet providers do not face the same regulatory burden as custodial services. This reinforces Sardis's exemption argument.

### 5.4 Residual Regulatory Risk

Despite the favorable analysis above, the following risk factors remain:

| Risk Factor | Assessment | Mitigation |
|---|---|---|
| Payment orchestration | Sardis routes payments between parties, which could be viewed as "facilitating value transfer" | Non-custodial: Sardis never holds or controls funds in transit |
| Virtual card issuance | Stripe Issuing creates cards funded by user wallets | Stripe is the card program manager and money transmitter for card transactions |
| AI agent transactions | Novel use case with no direct regulatory precedent | Comprehensive AML monitoring, spending policies, audit trail |
| Stablecoin regulation | GENIUS Act may impose new requirements on non-issuers after July 2028 | USDC/EURC are GENIUS-compliant; Sardis uses only compliant stablecoins |
| State-level variation | States may classify MPC wallets differently | See `state-licensing-analysis.md` for per-state analysis |

### 5.5 Legal Recommendation

**Register as MSB despite likely exemption.** The cost is zero, the processing time is minimal, and the benefits (investor confidence, banking relationships, regulatory good faith) far outweigh the negligible compliance burden of registration itself. The substantive compliance obligations (AML program, SAR filing, recordkeeping) are already implemented in Sardis's codebase:

- SAR filing: `packages/sardis-compliance/src/sardis_compliance/sar.py`
- KYC verification: `packages/sardis-compliance/src/sardis_compliance/kyc.py`
- Sanctions screening: `packages/sardis-compliance/src/sardis_compliance/sanctions.py`
- Travel Rule: `packages/sardis-compliance/src/sardis_compliance/travel_rule.py`
- Risk scoring: `packages/sardis-compliance/src/sardis_compliance/risk_scoring.py`
- PEP screening: `packages/sardis-compliance/src/sardis_compliance/pep.py`
- Adverse media: `packages/sardis-compliance/src/sardis_compliance/adverse_media.py`

---

## 6. Timeline and Cost Summary

### 6.1 Registration Timeline

| Phase | Duration | Description |
|---|---|---|
| Preparation | 1-2 weeks | Gather entity docs, EIN, owner info, designate compliance officer |
| BSA E-Filing account setup | 1-2 days | Create account, confirm email, set up users |
| Form 107 completion | 1-2 hours | Fill out the electronic form |
| FinCEN processing | ~30 calendar days | Await confirmation and MSB registration number |
| **Total** | **~6-8 weeks** | From decision to registered status |

### 6.2 Cost Breakdown

| Item | Cost | Notes |
|---|---|---|
| FinCEN Form 107 filing | $0 | Free federal registration |
| BSA E-Filing account | $0 | Free |
| Legal review of Form 107 | $5,000 - $10,000 | Recommended but not required |
| Outside counsel AML program review | $5,000 - $15,000 | Recommended for program documentation |
| Biennial renewal filing | $0 | Free |
| **Total (without legal)** | **$0** | |
| **Total (with legal review)** | **$10,000 - $25,000** | One-time; renewal is free |

### 6.3 Ongoing Compliance Costs

| Obligation | Annual Cost | Notes |
|---|---|---|
| Compliance officer time | Included in salary | Part-time initially, full-time as scale increases |
| SAR filing | $0 (BSA E-Filing is free) | Already automated via `sardis_compliance/sar.py` |
| AML training | $1,000 - $5,000 | Annual training for all employees |
| Independent AML testing | $5,000 - $15,000 | Annual audit or third-party review |
| Sanctions screening vendor | Varies | Elliptic/Circle Compliance Engine; already integrated |
| KYC verification | $0.55/verification (iDenfy) | Already integrated |
| **Total annual ongoing** | **$6,000 - $20,000** | Excluding salary costs |

---

## 7. Key Contacts and Resources

### 7.1 FinCEN Resources

| Resource | URL |
|---|---|
| BSA E-Filing System | https://bsaefiling.fincen.treas.gov |
| FinCEN Form 107 Instructions | https://www.fincen.gov/sites/default/files/shared/FinCEN_Form107_Instructions.pdf |
| FinCEN Regulatory Helpline | 1-800-949-2732 |
| FinCEN 2019 CVC Guidance | https://www.fincen.gov/sites/default/files/2019-05/FinCEN%20CVC%20Guidance%20FINAL.pdf |
| BSA/AML Examination Manual | https://bsaaml.ffiec.gov/manual |

### 7.2 Internal References

| Document | Path |
|---|---|
| BSA/AML Compliance Program | `docs/compliance/fincen/bsa-aml-program.md` |
| State Licensing Analysis | `docs/compliance/fincen/state-licensing-analysis.md` |
| Regulatory Reporting Checklist | `docs/compliance/fincen/regulatory-reporting-checklist.md` |
| Regulatory Research (comprehensive) | `docs/compliance/regulatory-compliance-research.md` |
| Data Retention Policy | `docs/compliance/soc2/data-retention-policy.md` |
| SAR Module | `packages/sardis-compliance/src/sardis_compliance/sar.py` |
| KYC Module | `packages/sardis-compliance/src/sardis_compliance/kyc.py` |
| Sanctions Module | `packages/sardis-compliance/src/sardis_compliance/sanctions.py` |
| Travel Rule Module | `packages/sardis-compliance/src/sardis_compliance/travel_rule.py` |

---

## 8. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-11 | Sardis Compliance | Initial document |
