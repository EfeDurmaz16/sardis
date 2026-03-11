# BSA/AML Compliance Program -- Sardis

**Document ID:** SARDIS-FINCEN-AML-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Legal
**Classification:** Internal -- Confidential

---

## 1. Program Overview

This document establishes Sardis's formal Anti-Money Laundering (AML) compliance program as required under the Bank Secrecy Act (BSA) for registered Money Services Businesses (MSBs). The program is designed to prevent Sardis's infrastructure from being used for money laundering, terrorist financing, sanctions evasion, or other financial crimes.

### 1.1 Regulatory Basis

- **Bank Secrecy Act (BSA):** 31 U.S.C. Sections 5311-5332
- **FinCEN MSB Regulations:** 31 CFR Part 1022
- **USA PATRIOT Act:** Sections 311-326
- **GENIUS Act (2025):** Stablecoin-specific compliance obligations for non-issuers (effective by July 2028 for Sardis)
- **FATF Recommendations:** Recommendations 1, 10-11, 15-16, 20, 26

### 1.2 Five Pillars of Compliance

FinCEN requires every MSB to maintain an AML program with five core pillars:

| Pillar | Description | Sardis Implementation |
|---|---|---|
| 1. Internal Controls | Policies, procedures, and systems to detect and prevent money laundering | This document + automated monitoring in `sardis_compliance` and `sardis_guardrails` |
| 2. Independent Testing | Periodic review of AML controls by internal audit or third party | Annual AML audit (Section 6) |
| 3. Compliance Officer | Designated individual responsible for AML program | Appointed officer (Section 2) |
| 4. Training | Ongoing AML training for all relevant personnel | Annual program (Section 7) |
| 5. Customer Due Diligence (CDD) | Risk-based identification and verification of customers | KYC + ongoing monitoring (Section 3) |

### 1.3 Scope

This program covers all Sardis operations including:

- Stablecoin payment orchestration (USDC, EURC, USDT, PYUSD)
- Non-custodial MPC wallet creation and management (via Turnkey)
- Virtual card issuance and management (via Stripe Issuing)
- AI agent payment transactions
- Merchant checkout flows (Pay with Sardis)
- Cross-border transfers across supported chains (Base, Polygon, Ethereum, Arbitrum, Optimism, Arc)
- Fiat on-ramp / off-ramp integrations (Coinbase Onramp, Striga, Grid)

---

## 2. Compliance Officer

### 2.1 Designation

Sardis designates the following individual as its BSA/AML Compliance Officer:

- **Name:** [To be appointed]
- **Title:** Chief Compliance Officer (or designated equivalent)
- **Reporting line:** Reports directly to CEO and Board of Directors
- **Appointment date:** [To be set upon MSB registration]

Until a dedicated compliance officer is appointed, the CEO (Efe Baran Durmaz) serves as interim compliance officer.

### 2.2 Responsibilities

The Compliance Officer is responsible for:

1. **Program oversight:** Day-to-day management of the BSA/AML compliance program, including policy updates, procedure documentation, and system configuration.
2. **SAR filing decisions:** Review all system-generated SAR drafts and make filing/rejection decisions within the 30-day filing window. Implementation: `sardis_compliance/sar.py` generates SAR drafts automatically; the compliance officer reviews via the compliance dashboard.
3. **Regulatory correspondence:** Serve as the primary point of contact for FinCEN inquiries, IRS examinations, state regulatory inquiries, and law enforcement requests (e.g., National Security Letters, subpoenas, 314(a) requests).
4. **Training coordination:** Organize and document annual AML training for all employees (Section 7).
5. **Risk assessment:** Conduct or supervise annual enterprise-wide risk assessments (Section 8).
6. **Independent testing:** Coordinate annual independent testing of AML controls (Section 6).
7. **Regulatory monitoring:** Track changes in BSA/AML regulations, FinCEN guidance, FATF recommendations, GENIUS Act rulemaking, and state money transmitter laws.
8. **Board reporting:** Provide quarterly compliance reports to the CEO/Board covering SAR activity, screening statistics, risk assessment updates, training completion, and regulatory developments.

### 2.3 Authority

The Compliance Officer has the authority to:

- Halt or reverse any transaction that presents unacceptable AML risk
- Escalate suspicious activity to law enforcement (via SAR filing)
- Suspend or terminate customer accounts pending investigation
- Allocate compliance budget within approved limits
- Engage outside legal counsel for regulatory matters
- Override automated transaction approvals when manual review is warranted

### 2.4 Succession

If the Compliance Officer is unavailable (illness, termination, vacancy), the CEO assumes interim compliance responsibilities. A permanent replacement must be designated within 30 days of a vacancy.

---

## 3. Customer Identification Program (CIP) and Customer Due Diligence (CDD)

### 3.1 KYC Verification

Sardis implements a risk-based KYC program with tiered verification levels.

**Primary KYC Provider:** iDenfy ($0.55 per verification)
**Alternative:** zkPass portable KYC (zero-knowledge proof of existing verification at another institution)

#### 3.1.1 Standard Verification (All Users)

**Required information collected at onboarding:**

| Data Element | Source | Required? |
|---|---|---|
| Full legal name | Government-issued ID | Yes |
| Date of birth | Government-issued ID | Yes |
| Residential address | Utility bill or bank statement | Yes |
| Government-issued photo ID | Passport, driver's license, or national ID card | Yes |
| Selfie / liveness check | Real-time biometric | Yes |
| Email address | User-provided | Yes |
| Phone number | User-provided, SMS-verified | Yes |

**Implementation:** `packages/sardis-compliance/src/sardis_compliance/kyc.py`

#### 3.1.2 Enhanced Due Diligence (EDD)

EDD is triggered automatically for any of the following conditions:

| Trigger | Threshold | Action |
|---|---|---|
| High-risk jurisdiction | User country in FATF grey/blacklist or sanctioned country list | Additional documentation, source of funds declaration |
| PEP status | User identified as Politically Exposed Person | Source of wealth documentation, senior management approval |
| High transaction volume | Cumulative monthly volume exceeding $50,000 | Source of funds verification, business purpose documentation |
| Adverse media hit | Negative media screening match | Manual compliance review |
| Sanctions near-match | Partial match on OFAC SDN or other sanctions lists | Manual compliance review, additional identity verification |
| AI agent operator | Entity deploying AI agents for financial transactions | Operator KYC, agent use case documentation, spending policy review |

**Implementation:** Risk-based EDD logic is driven by `packages/sardis-compliance/src/sardis_compliance/risk_scoring.py` (RiskScorer class, `assess_entity_risk` method).

#### 3.1.3 Ongoing Customer Due Diligence

KYC is not a one-time event. Sardis performs ongoing CDD through:

- **Periodic re-verification:** KYC records are reviewed annually for high-risk customers and every 2 years for standard-risk customers. Expired verifications trigger re-verification prompts.
- **Transaction monitoring:** Continuous monitoring of transaction patterns against established customer profiles (Section 4).
- **Sanctions re-screening:** All customer addresses and identities are re-screened against updated OFAC SDN lists daily (batch) and in real-time at transaction time.
- **PEP re-screening:** Quarterly re-screening against updated PEP databases.
- **Adverse media monitoring:** Continuous monitoring via `sardis_compliance/adverse_media.py`.

### 3.2 Beneficial Ownership

For entity accounts (businesses, DAOs, trusts), Sardis collects:

- Legal entity name and registration number
- Jurisdiction of formation
- Principal place of business
- All individuals owning 25% or more of the entity (beneficial owners)
- One individual with significant managerial control (the "control person")
- Entity formation documents (Articles of Incorporation, Operating Agreement, etc.)

### 3.3 Recordkeeping for CIP

All CIP records are retained for the lifetime of the customer relationship plus 5 years after account closure, consistent with BSA requirements and Sardis's Data Retention Policy (`docs/compliance/soc2/data-retention-policy.md`).

| Record Type | Retention Period | Storage |
|---|---|---|
| Government ID images | Account lifetime + 5 years | Encrypted at rest in S3 (AES-256), references in PostgreSQL |
| Selfie / liveness data | Account lifetime + 5 years | Encrypted at rest in S3 |
| Verification results | Account lifetime + 5 years | PostgreSQL (`kyc_verifications` table) |
| Address documentation | Account lifetime + 5 years | Encrypted at rest in S3 |
| EDD documentation | Account lifetime + 5 years | PostgreSQL + S3 |

---

## 4. Suspicious Activity Monitoring and Reporting

### 4.1 Detection Methods

Sardis employs a multi-layered approach to suspicious activity detection:

#### 4.1.1 Automated Detection

| System | Module | Detection Capability |
|---|---|---|
| ML Fraud Scoring | `sardis_guardrails/ml_fraud.py` | Machine learning models trained on transaction features to identify anomalous patterns |
| Graph Fraud Detection | `sardis_guardrails/graph_fraud.py` | Network analysis to identify clusters of related wallets engaging in coordinated suspicious behavior |
| Behavioral Anomaly Engine | `sardis_guardrails/anomaly_engine.py` | Baseline behavioral profiles per customer; deviations trigger alerts |
| Transaction Velocity Monitor | `sardis_compliance/risk_scoring.py` (TransactionVelocityMonitor) | Monitors transaction frequency and volume over configurable time windows |
| Structuring Detection | `sardis_compliance/sar.py` (SARGenerator.detect_structuring) | Identifies patterns of transactions deliberately structured to avoid reporting thresholds |
| Sanctions Screening | `sardis_compliance/sanctions.py` | Real-time OFAC/EU/UN sanctions screening via Elliptic, Circle Compliance Engine, Chainalysis Oracle, or OpenSanctions |
| PEP Screening | `sardis_compliance/pep.py` | Politically Exposed Person identification and risk scoring |

#### 4.1.2 Rule-Based Alerts

The following rules generate automatic compliance alerts:

| Rule | Threshold | Priority |
|---|---|---|
| Single transaction above $10,000 | $10,000 | MEDIUM |
| Cumulative 24-hour volume above $25,000 per wallet | $25,000 | MEDIUM |
| 3+ transactions between 50-99% of $10,000 within 24 hours | Structuring pattern | HIGH |
| Transaction to/from sanctioned address | Any amount | CRITICAL |
| Transaction to/from high-risk jurisdiction | Any amount | HIGH |
| Rapid movement across multiple wallets (layering) | 5+ hops in 1 hour | HIGH |
| Dormant wallet sudden large activity | $5,000+ after 90 days inactive | MEDIUM |
| AI agent exceeding spending policy limits | Policy-defined | HIGH |

#### 4.1.3 Manual Review

The compliance officer and designated reviewers maintain a queue of:

- Alerts from automated systems requiring human judgment
- Escalated cases from customer support
- Law enforcement inquiries (314(a) requests)
- Ad hoc investigations triggered by external information

### 4.2 SAR Filing Process

**Regulatory requirement:** FinCEN Form 111 (SAR-MSB) must be filed within 30 calendar days of the date the suspicious activity is first detected.

**Implementation:** `packages/sardis-compliance/src/sardis_compliance/sar.py`

#### 4.2.1 Filing Workflow

```
Detection (automated/manual)
    |
    v
SAR Draft Generated (SARGenerator.create_sar)
    |-- Status: DRAFT
    |-- Auto-populated: activity_type, wallet_id, description, detection_date
    |-- Filing deadline auto-set: detection_date + 30 days
    |
    v
Compliance Officer Review
    |-- Reviews narrative, transactions, subject info
    |-- Adds additional context, evidence
    |-- Status: PENDING_REVIEW
    |
    v
Decision
    |-- APPROVE -> Status: APPROVED -> Proceed to filing
    |-- REJECT  -> Status: REJECTED -> Document reason, no filing
    |
    v
Filing via BSA E-Filing System
    |-- Submit FinCEN Form 111 electronically
    |-- Record filing reference number
    |-- Status: FILED
    |
    v
Post-Filing
    |-- Retain SAR records for 5 years from filing date
    |-- Continue monitoring subject
    |-- File continuing SARs if activity persists (every 90 days)
```

#### 4.2.2 SAR Thresholds for MSBs

| Transaction Type | Reporting Threshold | Filing Deadline |
|---|---|---|
| Suspicious transaction (known subject) | $2,000 or more | 30 calendar days from detection |
| Suspicious transaction (unknown subject) | $5,000 or more | 30 calendar days from detection |
| Transactions aggregating to threshold | $2,000+ combined | 30 calendar days from detection |
| Ongoing suspicious activity | Any amount | Continuing SAR every 90 days |

#### 4.2.3 SAR Confidentiality

- SARs are confidential. Sardis must **never** disclose to the subject of a SAR that a report has been or will be filed.
- SAR information may only be shared with: FinCEN, law enforcement (upon proper legal process), and Sardis's federal functional regulator.
- SAR-related communications within Sardis are restricted to the compliance officer and authorized reviewers.
- The `sardis_compliance/sar.py` module redacts subject identification data in serialized output (`"[REDACTED]"` for identification field).

### 4.3 Record Retention for SARs

| Record | Retention Period | Storage Location |
|---|---|---|
| SAR filing (copy of submitted Form 111) | 5 years from filing date | PostgreSQL (`suspicious_activity_reports` table) + BSA E-Filing System |
| Supporting documentation | 5 years from filing date | PostgreSQL + S3 encrypted storage |
| Compliance officer review notes | 5 years from filing date | PostgreSQL |
| Transaction records underlying SAR | 5 years from filing date (or 7 years per Sardis data retention policy, whichever is longer) | PostgreSQL |

---

## 5. Travel Rule Compliance

### 5.1 Regulatory Requirements

The FATF Travel Rule (Recommendation 16) requires Virtual Asset Service Providers (VASPs) to collect, retain, and transmit originator and beneficiary information for qualifying transfers.

**Implementation:** `packages/sardis-compliance/src/sardis_compliance/travel_rule.py`

### 5.2 Applicable Thresholds

| Jurisdiction | Threshold | Sardis Implementation |
|---|---|---|
| United States (FinCEN) | $3,000 | `TRAVEL_RULE_THRESHOLD_USD = Decimal("3000")` |
| European Union (TFR) | EUR 1,000 (effectively zero for CASP-to-CASP) | `TRAVEL_RULE_THRESHOLD_EUR = Decimal("1000")` |
| FATF recommendation | $1,000 / EUR 1,000 | Covered by the lower of US/EU thresholds |

**Note on EU TFR:** The EU Transfer of Funds Regulation (2023/1113) technically requires originator/beneficiary data for **all** crypto-asset transfers between CASPs, regardless of value. The EUR 1,000 threshold applies specifically to transfers involving self-hosted wallets (where wallet ownership verification is required above that amount). If Sardis obtains CASP registration, the zero-threshold requirement applies to inter-CASP transfers.

### 5.3 Required Data Elements

For transfers above the applicable threshold, the following data must be collected and transmitted to the counterparty VASP:

**Originator information:**
- Full name
- Account number (wallet address or Sardis agent/wallet ID)
- Physical address (with country), or national identity document number, or customer identification number, or date and place of birth

**Beneficiary information:**
- Full name
- Account number (wallet address)

### 5.4 VASP Messaging Protocols

Sardis supports the following protocols for Travel Rule data exchange:

| Protocol | Status | Module |
|---|---|---|
| Notabene | Integrated (configurable via `SARDIS_TRAVEL_RULE_PROVIDER=notabene`) | `sardis_compliance/providers/notabene.py` |
| TRISA | Supported via `TravelRuleProvider` interface | `sardis_compliance/travel_rule.py` |
| OpenVASP | Supported via `TravelRuleProvider` interface | `sardis_compliance/travel_rule.py` |
| Manual (fallback) | Default -- flags transfers for compliance officer review | `ManualTravelRuleProvider` in `travel_rule.py` |

### 5.5 Self-Hosted Wallet Transfers

For transfers to or from self-hosted (non-custodial) wallets not associated with a known VASP:

- **Below threshold:** No Travel Rule data required; standard transaction monitoring applies.
- **Above threshold (US, $3,000+):** Sardis collects originator information from the Sardis user and records beneficiary wallet address. Since there is no counterparty VASP to transmit to, the data is retained internally for 5 years.
- **Above threshold (EU, EUR 1,000+):** If Sardis is a CASP, it must verify that the Sardis customer controls the self-hosted wallet (e.g., via signature challenge). Implementation: EIP-191 signature verification in checkout flow (`confirm-external-payment` endpoint).

---

## 6. Independent Testing

### 6.1 Requirements

BSA regulations require MSBs to conduct independent testing of their AML controls. "Independent" means the testing must be performed by someone not responsible for the day-to-day operation of the AML program.

### 6.2 Testing Schedule

| Test Type | Frequency | Performed By |
|---|---|---|
| Full AML program audit | Annually | Third-party auditor or qualified internal auditor |
| SAR filing process review | Annually | Third-party auditor |
| Sanctions screening effectiveness | Semi-annually | Internal (with external validation annually) |
| KYC procedures review | Annually | Third-party auditor |
| Transaction monitoring rules | Quarterly (internal), annually (external) | Internal compliance / external auditor |
| Travel Rule compliance | Annually | Third-party auditor |

### 6.3 Testing Scope

Each annual independent test must cover:

1. **AML policy and procedure adequacy:** Are written policies current, comprehensive, and consistent with regulatory requirements?
2. **SAR filing process:** Are SARs identified, reviewed, and filed within the 30-day window? Sample review of filed and unfiled SARs.
3. **KYC/CIP compliance:** Are customer identities verified per CIP requirements? Are records complete and retained per policy? Sample review of customer files.
4. **Sanctions screening:** Are all customers and transactions screened? Are screening systems functioning correctly? Test with known sanctioned addresses and names.
5. **Transaction monitoring:** Are monitoring rules appropriate for Sardis's risk profile? Are alerts investigated and resolved timely? Sample review of alerts and resolutions.
6. **Training:** Have all employees completed required AML training? Are training records maintained?
7. **Risk assessment:** Is the enterprise-wide risk assessment current and reflective of Sardis's actual operations?
8. **Travel Rule:** Are qualifying transfers identified and processed per Travel Rule requirements?

### 6.4 Reporting

Independent testing results are documented in a written report that includes:

- Scope and methodology
- Findings and observations
- Risk ratings for each finding (Critical, High, Medium, Low)
- Recommended corrective actions
- Management responses and remediation timelines

Reports are delivered to the Compliance Officer and CEO/Board. Findings rated Critical or High must have remediation plans initiated within 30 days.

---

## 7. Training Program

### 7.1 Training Requirements

All Sardis employees, contractors, and relevant third parties must complete AML training as follows:

| Audience | Initial Training | Recurring Training |
|---|---|---|
| All employees | Within 30 days of hire | Annually |
| Compliance team | Within 15 days of hire (extended program) | Annually + ad hoc on regulatory changes |
| Engineering (compliance modules) | Within 30 days of hire | Annually + when compliance code is modified |
| Customer support | Within 30 days of hire | Annually |
| Senior management / Board | Within 30 days of appointment | Annually |

### 7.2 Training Topics

#### 7.2.1 General AML Training (All Employees)

- Overview of BSA/AML requirements and Sardis's obligations as a registered MSB
- Definition of money laundering and terrorist financing
- Red flags for suspicious activity (structuring, layering, unusual patterns)
- SAR identification and internal reporting procedures (how to escalate concerns)
- Sanctions screening basics (OFAC, EU, UN lists)
- Travel Rule requirements
- Customer Due Diligence principles
- Confidentiality obligations (especially SAR non-disclosure)
- Consequences of non-compliance (personal and organizational)
- Sardis-specific scenarios: AI agent transactions, stablecoin payments, cross-chain transfers

#### 7.2.2 Compliance Team Training (Extended)

All topics in 7.2.1, plus:

- Detailed SAR narrative writing
- BSA E-Filing System usage
- FinCEN regulatory examination preparation
- Risk assessment methodology
- EDD procedures
- Travel Rule VASP messaging protocols
- Sanctions screening system administration
- 314(a) and 314(b) information sharing procedures
- GENIUS Act compliance requirements
- MiCA/TFR requirements (if EU operations)

#### 7.2.3 Engineering Training

All topics in 7.2.1, plus:

- Overview of `sardis_compliance` and `sardis_guardrails` modules
- How AML controls are implemented in code
- Testing requirements for compliance-related code changes
- Data retention and encryption requirements for PII
- Incident response procedures for compliance system failures

### 7.3 Training Records

Training completion is tracked and retained for a minimum of 5 years. Records include:

- Employee name and role
- Training date
- Training content / curriculum version
- Assessment score (if applicable)
- Trainer name or platform
- Completion certification

---

## 8. Risk Assessment

### 8.1 Enterprise-Wide Risk Assessment

Sardis conducts a comprehensive BSA/AML risk assessment at least annually, or upon material changes to the business (new products, new markets, regulatory changes).

### 8.2 Risk Assessment Methodology

Risk is evaluated across three dimensions:

**Risk = Product Risk x Customer Risk x Geographic Risk**

#### 8.2.1 Product Risk

| Product / Service | Risk Level | Rationale |
|---|---|---|
| Non-custodial MPC wallets | MEDIUM | Non-custodial reduces risk, but wallet creation for AI agents is novel |
| Stablecoin transfers (USDC/EURC) | MEDIUM | Pegged to fiat, traceable on-chain, but can be used for cross-border value transfer |
| Virtual cards (Stripe Issuing) | HIGH | Cards can be used for purchases at any merchant; spending policy mitigates but does not eliminate risk |
| Cross-border payments | HIGH | Inherent higher risk for international value transfer |
| Fiat on-ramp (Coinbase Onramp) | MEDIUM | Coinbase performs its own AML/KYC; Sardis relies on upstream compliance |
| Fiat off-ramp (Striga/Grid) | HIGH | Converting crypto to fiat is a primary money laundering vector |
| AI agent autonomous transactions | HIGH (NOVEL) | No regulatory precedent; requires enhanced monitoring and spending policy enforcement |
| Merchant checkout (Pay with Sardis) | MEDIUM | Standard merchant payment flow; merchant KYC and settlement address verification reduce risk |

#### 8.2.2 Customer Risk

| Customer Type | Risk Level | Rationale |
|---|---|---|
| Individual (verified KYC) | LOW-MEDIUM | Standard consumer risk, mitigated by KYC |
| Business entity (verified KYB) | MEDIUM | Standard business risk, mitigated by beneficial ownership verification |
| AI agent operator | HIGH (NOVEL) | Operator delegates financial authority to autonomous software; requires robust spending policies |
| AI agent (autonomous) | HIGH (NOVEL) | Agent cannot be "known" in the traditional CDD sense; risk managed via operator KYC + spending policies + transaction monitoring |
| PEP | HIGH | Politically exposed persons require enhanced due diligence |
| High-risk jurisdiction resident | HIGH | Enhanced due diligence required per FATF guidance |

#### 8.2.3 Geographic Risk

**Implementation:** `sardis_compliance/risk_scoring.py` (GeographicRiskAssessor class)

| Risk Tier | Countries | Risk Level |
|---|---|---|
| Sanctioned / OFAC | KP, IR, SY, CU (Cuba), Crimea/Donetsk/Luhansk regions | BLOCKED -- services prohibited |
| FATF Blacklist | KP, IR, MM | CRITICAL -- services prohibited |
| FATF Greylist | VE, BY, RU, AF, YE, SO, LY, SD, SS, CF, and others per current FATF listing | HIGH -- EDD required |
| Elevated risk | PK, NG, BD, KH, LA, VN, PH | MEDIUM -- enhanced monitoring |
| Standard | US, EU/EEA, UK, CA, AU, JP, SG, and other FATF-compliant jurisdictions | LOW |

### 8.3 Risk Mitigation Controls

For each identified risk, Sardis implements compensating controls:

| Risk | Control | Implementation |
|---|---|---|
| Structuring | Automated structuring detection | `sardis_compliance/sar.py` -- `detect_structuring()` |
| Layering | Graph-based transaction analysis | `sardis_guardrails/graph_fraud.py` |
| Sanctioned entity transactions | Real-time sanctions screening (fail-closed) | `sardis_compliance/sanctions.py` -- blocks on screening failure |
| High-value transactions | Transaction velocity monitoring + alerts | `sardis_compliance/risk_scoring.py` -- TransactionVelocityMonitor |
| AI agent misuse | Spending policies with per-transaction, daily, and merchant-category limits | `sardis_core/spending_policy.py` |
| Cross-border risk | Geographic risk scoring + EDD triggers | `sardis_compliance/risk_scoring.py` -- GeographicRiskAssessor |
| Identity fraud | Biometric liveness checks, document verification | `sardis_compliance/kyc.py` via iDenfy |
| PEP risk | Automated PEP screening + EDD | `sardis_compliance/pep.py` |

---

## 9. Recordkeeping Requirements

### 9.1 BSA Recordkeeping Obligations

Sardis maintains all required records per BSA regulations and its own Data Retention Policy (`docs/compliance/soc2/data-retention-policy.md`).

| Record Type | Retention Period | Regulatory Basis | Storage Location |
|---|---|---|---|
| KYC/CIP records | Account lifetime + 5 years | 31 CFR 1010.312, 1022.210 | PostgreSQL (Neon) + S3 (encrypted) |
| Transaction records | 7 years from transaction date | BSA + IRS requirements | PostgreSQL (Neon) |
| SAR filings and supporting docs | 5 years from filing date | 31 CFR 1022.320(c) | PostgreSQL + BSA E-Filing |
| CTR filings (N/A for crypto-only) | 5 years from filing date | 31 CFR 1010.306 | N/A |
| Travel Rule records | 5 years from transaction date | 31 CFR 1010.410 | PostgreSQL (`travel_rule_transfers` table) |
| Correspondence with regulators | 5 years | BSA general requirement | Internal document management |
| AML training records | 5 years | BSA best practice | Internal document management |
| Risk assessment reports | 5 years | BSA best practice | Internal document management |
| Independent testing reports | 5 years | BSA best practice | Internal document management |
| Compliance officer reports | 5 years | BSA best practice | Internal document management |

### 9.2 Record Availability

All records must be available for examination by:

- FinCEN examiners
- IRS (as delegated BSA examiner for MSBs)
- Federal and state law enforcement (with proper legal process)
- State regulators with jurisdiction over Sardis's money services activities

Records are retrievable from PostgreSQL via standard database queries. The compliance dashboard provides a UI for authorized compliance personnel to search and export records.

---

## 10. Information Sharing

### 10.1 Section 314(a) -- FinCEN Requests

FinCEN's 314(a) program allows law enforcement agencies to request account searches from financial institutions. Upon receiving a 314(a) request:

1. The Compliance Officer (or designated reviewer) receives the request via BSA E-Filing System.
2. Search Sardis's customer database for matches within 14 days.
3. Report positive matches to FinCEN via BSA E-Filing.
4. Do NOT disclose the existence of the 314(a) request to the subject.

### 10.2 Section 314(b) -- Voluntary Information Sharing

Section 314(b) permits financial institutions to share information with each other for the purpose of identifying and reporting suspected money laundering or terrorist financing.

**Status:** Sardis will evaluate 314(b) participation as its customer base grows and inter-institutional information sharing becomes relevant.

### 10.3 Law Enforcement Requests

All law enforcement requests (subpoenas, court orders, National Security Letters) must be routed immediately to the Compliance Officer and outside legal counsel. Sardis cooperates fully with lawful requests while protecting customer privacy rights.

---

## 11. Program Review and Updates

### 11.1 Annual Review

The BSA/AML compliance program is reviewed and updated at least annually by the Compliance Officer. The review covers:

- Changes in regulations (FinCEN guidance, GENIUS Act rulemaking, state laws)
- Changes in Sardis's products, services, or customer base
- Findings from independent testing
- SAR filing activity and trends
- New money laundering typologies or emerging threats
- Technology updates to compliance systems

### 11.2 Event-Driven Updates

The program is also updated upon:

- FinCEN or FATF issuance of new guidance
- Launch of new products or services
- Entry into new markets or jurisdictions
- Material compliance findings from testing or examinations
- Significant changes in transaction volume or customer demographics

---

## 12. Penalties for Non-Compliance

### 12.1 Organizational Penalties

| Violation | Potential Penalty |
|---|---|
| Failure to register as MSB | Up to $5,000 per day |
| Willful failure to file SARs | Up to $250,000 fine and/or 5 years imprisonment per violation |
| Failure to maintain AML program | Civil money penalties up to $1,000,000 |
| BSA violations (general) | Civil penalties up to $100,000 per violation; criminal penalties up to $500,000 and/or 10 years imprisonment |
| Structuring or aiding structuring | Up to $500,000 fine and/or 10 years imprisonment |

### 12.2 Individual Penalties

BSA violations can result in personal liability for the Compliance Officer and senior management, including:

- Civil money penalties
- Criminal prosecution (for willful violations)
- Industry bars

---

## 13. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-11 | Sardis Compliance | Initial document |
