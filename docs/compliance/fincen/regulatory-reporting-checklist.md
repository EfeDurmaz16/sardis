# Regulatory Reporting Checklist -- Sardis

**Document ID:** SARDIS-FINCEN-REPORT-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Legal
**Classification:** Internal

---

## 1. Overview

This document provides a comprehensive checklist of all regulatory reporting obligations applicable to Sardis as a registered Money Services Business (MSB) under the Bank Secrecy Act (BSA). It covers federal (FinCEN), state, and international (EU/MiCA) reporting requirements, along with automation status and the internal systems responsible for each report.

---

## 2. Federal Reporting (FinCEN)

### 2.1 MSB Registration (Form 107)

| Attribute | Details |
|---|---|
| **Form** | FinCEN Form 107 -- Registration of Money Services Business |
| **Trigger** | Initial registration; re-registration every 2 years; amendment upon material change |
| **Deadline** | Initial: within 180 days of commencing MSB operations |
| **Renewal** | Every 2 years from initial registration date |
| **Amendment** | Within 180 days of any material change (ownership, services, states) |
| **Filing method** | BSA E-Filing System (https://bsaefiling.fincen.treas.gov) |
| **Cost** | $0 (free) |
| **Responsible** | Compliance Officer |
| **Status** | [ ] PENDING -- Not yet filed |
| **Internal reference** | `docs/compliance/fincen/msb-registration-guide.md` |

**Checklist:**
- [ ] Create BSA E-Filing organizational account
- [ ] Gather entity information (legal name, EIN, address, state of incorporation)
- [ ] Gather principal owner information (name, DOB, SSN, address)
- [ ] Designate compliance officer
- [ ] Complete and submit Form 107
- [ ] Record confirmation number and MSB registration number
- [ ] Calendar biennial renewal date
- [ ] Calendar amendment triggers for monitoring

### 2.2 Suspicious Activity Reports (SARs)

| Attribute | Details |
|---|---|
| **Form** | FinCEN Form 111 -- SAR (Suspicious Activity Report) |
| **Trigger** | Detection of suspicious activity meeting MSB thresholds |
| **Threshold (known subject)** | $2,000 or more |
| **Threshold (unknown subject)** | $5,000 or more |
| **Deadline** | 30 calendar days from date of initial detection |
| **Continuing activity** | File continuing SAR every 90 days if activity persists |
| **Filing method** | BSA E-Filing System |
| **Cost** | $0 (free) |
| **Responsible** | Compliance Officer (review and approval); automated generation |
| **Automated?** | Yes -- draft generation via `sardis_compliance/sar.py` |
| **Status** | [x] IMPLEMENTED -- SARGenerator class with automated structuring detection, PostgreSQL persistence, and XML export for BSA E-Filing |

**Checklist:**
- [x] Automated SAR draft generation (`SARGenerator.create_sar()`)
- [x] Structuring detection (`SARGenerator.detect_structuring()`)
- [x] SAR lifecycle management (DRAFT -> PENDING_REVIEW -> APPROVED -> FILED)
- [x] Filing deadline auto-calculation (detection_date + 30 days)
- [x] Overdue SAR monitoring (`SARGenerator.get_overdue_sars()`)
- [x] PostgreSQL persistence (`suspicious_activity_reports` table)
- [x] FinCEN XML export (`SuspiciousActivityReport.to_fincen_xml()`)
- [x] SAR confidentiality (subject identification redacted in serialized output)
- [ ] BSA E-Filing integration for automated submission (currently manual filing step)
- [ ] Compliance dashboard UI for SAR review queue
- [ ] Continuing SAR automation (90-day recurring filing for ongoing activity)

### 2.3 Currency Transaction Reports (CTRs)

| Attribute | Details |
|---|---|
| **Form** | FinCEN Form 112 -- Currency Transaction Report |
| **Trigger** | Cash transactions exceeding $10,000 in a single business day |
| **Deadline** | 15 calendar days after the transaction |
| **Filing method** | BSA E-Filing System |
| **Status** | N/A -- Sardis is crypto-only; no cash handling |
| **Notes** | If Sardis introduces fiat cash handling (e.g., cash on-ramps), CTR obligations will apply. Stablecoin transactions are NOT "cash" for CTR purposes per current FinCEN guidance. Monitor for regulatory changes. |

**Checklist:**
- [x] Determination: N/A for current operations (crypto-only, no cash)
- [ ] Re-evaluate if fiat cash channels are added

### 2.4 FBAR (Foreign Bank Account Report)

| Attribute | Details |
|---|---|
| **Form** | FinCEN Form 114 -- Report of Foreign Bank and Financial Accounts |
| **Trigger** | U.S. person with financial interest in or signature authority over foreign financial accounts exceeding $10,000 aggregate at any point during the calendar year |
| **Deadline** | April 15 (automatic extension to October 15) |
| **Filing method** | BSA E-Filing System |
| **Status** | [ ] REVIEW NEEDED -- Depends on Sardis's operational accounts |
| **Notes** | If Sardis maintains any foreign financial accounts (e.g., EU bank accounts for Striga integration, foreign exchange accounts), FBAR filing may be required. Crypto exchange accounts at foreign exchanges may also trigger FBAR. |

**Checklist:**
- [ ] Inventory all foreign financial accounts held by Sardis (entity level)
- [ ] Determine if any individual with signature authority triggers personal FBAR
- [ ] If applicable, file by April 15 annually
- [ ] Consult tax counsel on crypto exchange account treatment under FBAR

### 2.5 FinCEN 314(a) Responses

| Attribute | Details |
|---|---|
| **Trigger** | Receipt of 314(a) request from FinCEN (law enforcement information sharing) |
| **Deadline** | Search and respond within 14 days of request |
| **Filing method** | BSA E-Filing System (314(a) portal) |
| **Responsible** | Compliance Officer |
| **Automated?** | No -- manual process |
| **Status** | [ ] PROCESS DEFINED -- not yet tested with live request |

**Checklist:**
- [ ] Register for 314(a) requests on BSA E-Filing System
- [ ] Establish internal procedure for searching customer database upon receipt
- [ ] Document response protocol (positive match reporting)
- [ ] Train compliance officer on 314(a) procedures
- [ ] Test search capability with sample data

---

## 3. State Reporting

State reporting obligations vary by jurisdiction and depend on which state licenses or registrations Sardis holds. The following are common state-level reporting requirements:

### 3.1 State License Renewals

| Attribute | Details |
|---|---|
| **Trigger** | Annual or biennial license renewal (varies by state) |
| **Typical deadline** | Annual, on the anniversary of license issuance |
| **Filing method** | NMLS (Nationwide Multistate Licensing System) for most states |
| **Status** | [ ] NOT YET APPLICABLE -- pending state licensing decisions |
| **Reference** | `docs/compliance/fincen/state-licensing-analysis.md` |

### 3.2 State Call Reports

Many states require licensed money transmitters to file periodic "call reports" (financial statements) through NMLS.

| Attribute | Details |
|---|---|
| **Frequency** | Quarterly or annually (varies by state) |
| **Content** | Transaction volumes, permissible investments, financial statements |
| **Filing method** | NMLS |
| **Status** | [ ] NOT YET APPLICABLE |

### 3.3 State SAR Notifications

Some states require notification when a SAR is filed involving activity in their jurisdiction. This is separate from the federal SAR filing.

| Attribute | Details |
|---|---|
| **States requiring notification** | New York (NYDFS), California (DFPI), and others |
| **Trigger** | Filing of a federal SAR involving activity in the state |
| **Status** | [ ] NOT YET APPLICABLE |

---

## 4. International Reporting (EU / MiCA)

These obligations apply only if Sardis obtains CASP (Crypto-Asset Service Provider) authorization in an EU member state.

### 4.1 EU SAR Equivalent

| Attribute | Details |
|---|---|
| **Requirement** | Report suspicious transactions to the national Financial Intelligence Unit (FIU) of the authorizing member state |
| **Deadline** | 72 hours from detection (stricter than US 30-day window) |
| **Automated?** | Yes -- `sardis_compliance/mica.py` handles EU-specific SAR timelines |
| **Status** | [x] IMPLEMENTED -- module ready; not yet filed (pending CASP authorization) |

### 4.2 Travel Rule (TFR) Reporting

| Attribute | Details |
|---|---|
| **Requirement** | Collect, verify, and transmit originator/beneficiary data for all crypto-asset transfers (zero threshold for CASP-to-CASP; EUR 1,000 threshold for self-hosted wallet verification) |
| **Automated?** | Yes -- `sardis_compliance/travel_rule.py` with Notabene integration |
| **Status** | [x] IMPLEMENTED -- Travel Rule service with configurable thresholds and VASP messaging |

### 4.3 MiCA Incident Reporting

| Attribute | Details |
|---|---|
| **Requirement** | Report significant ICT incidents to the national competent authority within 4 hours (initial), 72 hours (intermediate), and 1 month (final) per DORA |
| **Status** | [ ] NOT YET APPLICABLE -- pending CASP authorization |
| **Reference** | See incident response plan at `docs/compliance/soc2/incident-response-plan.md` |

### 4.4 Circle EMT Issuer Data Sharing

| Attribute | Details |
|---|---|
| **Requirement** | CASPs providing services related to MiCA-compliant EMTs (USDC, EURC) must share quarterly and daily data points with Circle France as the issuer |
| **Status** | [ ] NOT YET APPLICABLE -- pending CASP authorization |

---

## 5. Reporting Calendar

### 5.1 Annual Calendar

| Month | Report | Type | Frequency | Responsible |
|---|---|---|---|---|
| January | Annual BSA compliance review | Internal | Annual | Compliance Officer |
| January | AML training planning | Internal | Annual | Compliance Officer |
| January | Risk assessment initiation | Internal | Annual | Compliance Officer |
| February | State call reports (Q4 prior year) | State | Quarterly (if licensed) | Compliance Officer |
| March | Annual independent AML testing | External | Annual | Third-party auditor |
| March | Risk assessment completion | Internal | Annual | Compliance Officer |
| April | FBAR filing deadline (if applicable) | Federal | Annual | CFO / Tax counsel |
| May | State call reports (Q1) | State | Quarterly (if licensed) | Compliance Officer |
| June | Board compliance report (H1) | Internal | Semi-annual | Compliance Officer |
| July | AML training (annual refresh) | Internal | Annual | All employees |
| August | State call reports (Q2) | State | Quarterly (if licensed) | Compliance Officer |
| September | State license renewal check | State | Annual | Compliance Officer |
| October | FBAR extended deadline (if applicable) | Federal | Annual | CFO / Tax counsel |
| November | State call reports (Q3) | State | Quarterly (if licensed) | Compliance Officer |
| December | Board compliance report (H2) | Internal | Semi-annual | Compliance Officer |
| December | MSB re-registration check (biennial) | Federal | Every 2 years | Compliance Officer |

### 5.2 Ongoing / Event-Driven

| Report | Trigger | Deadline | Responsible |
|---|---|---|---|
| SAR (FinCEN Form 111) | Suspicious activity detected | 30 calendar days from detection | Compliance Officer |
| Continuing SAR | Ongoing suspicious activity | Every 90 days | Compliance Officer |
| 314(a) response | FinCEN 314(a) request received | 14 days | Compliance Officer |
| EU SAR | Suspicious activity detected (EU operations) | 72 hours from detection | Compliance Officer |
| MSB amendment (Form 107) | Material change in ownership, services, states | 180 days from change | Compliance Officer |
| State notification | SAR filed involving state-regulated activity | Per state requirements | Compliance Officer |
| DORA incident report | Significant ICT incident (EU operations) | 4 hours initial / 72 hours intermediate | CTO + Compliance Officer |

### 5.3 Quarterly Board Reporting

The Compliance Officer provides quarterly reports to the CEO/Board covering:

| Section | Content |
|---|---|
| SAR activity | Number of SARs generated, reviewed, filed, rejected; trends; overdue SARs |
| Screening statistics | Number of sanctions screenings, PEP screenings, adverse media checks; hit rates |
| KYC statistics | New verifications, approvals, declines, expired; EDD cases |
| Transaction monitoring | Alerts generated, investigated, resolved; false positive rate |
| Risk assessment | Any changes to risk profile; new risks identified |
| Training | Completion rates; upcoming training requirements |
| Regulatory updates | New regulations, guidance, or enforcement actions relevant to Sardis |
| Independent testing | Status and findings of most recent audit |
| Remediation | Status of any open findings from testing or examination |

---

## 6. Automation Status Summary

### 6.1 Fully Automated

| Report / Function | Module | Status |
|---|---|---|
| SAR draft generation | `sardis_compliance/sar.py` -- `SARGenerator.create_sar()` | Operational |
| Structuring detection | `sardis_compliance/sar.py` -- `SARGenerator.detect_structuring()` | Operational |
| SAR deadline tracking | `sardis_compliance/sar.py` -- `is_overdue()` + `filing_deadline` auto-set | Operational |
| SAR PostgreSQL persistence | `sardis_compliance/sar.py` -- `_persist_sar()` | Operational |
| SAR XML export (FinCEN format) | `sardis_compliance/sar.py` -- `to_fincen_xml()` | Operational |
| Sanctions screening (real-time) | `sardis_compliance/sanctions.py` -- Elliptic, Circle, Chainalysis, OFAC, OpenSanctions, layered | Operational |
| Sanctions failover | `sardis_compliance/sanctions.py` -- `FailoverSanctionsProvider` | Operational |
| PEP screening | `sardis_compliance/pep.py` | Operational |
| Adverse media monitoring | `sardis_compliance/adverse_media.py` | Operational |
| Travel Rule threshold check | `sardis_compliance/travel_rule.py` -- `requires_travel_rule()` | Operational |
| Travel Rule VASP messaging | `sardis_compliance/travel_rule.py` -- Notabene / Manual providers | Operational |
| Travel Rule PostgreSQL persistence | `sardis_compliance/travel_rule.py` -- `_persist_transfer()` | Operational |
| Risk scoring (multi-factor) | `sardis_compliance/risk_scoring.py` -- `RiskScorer` | Operational |
| Transaction velocity monitoring | `sardis_compliance/risk_scoring.py` -- `TransactionVelocityMonitor` | Operational |
| Geographic risk assessment | `sardis_compliance/risk_scoring.py` -- `GeographicRiskAssessor` | Operational |
| ML fraud detection | `sardis_guardrails/ml_fraud.py` | Operational |
| Graph fraud detection | `sardis_guardrails/graph_fraud.py` | Operational |
| Behavioral anomaly detection | `sardis_guardrails/anomaly_engine.py` | Operational |
| KYC verification (iDenfy) | `sardis_compliance/kyc.py` | Operational |
| EU/MiCA SAR timeline | `sardis_compliance/mica.py` | Operational (pending CASP) |

### 6.2 Partially Automated

| Report / Function | Current State | Remaining Work |
|---|---|---|
| SAR filing to FinCEN | XML export generated; manual upload to BSA E-Filing | Evaluate BSA E-Filing API for automated submission |
| Compliance dashboard | Backend data available; no dedicated UI | Build compliance officer review queue, SAR dashboard |
| Continuing SAR tracking | Initial SAR tracked; no automatic 90-day reminder | Add 90-day recurring SAR trigger for ongoing activity |
| 314(a) search | Customer database queryable; no dedicated search interface | Build dedicated 314(a) search tool with response workflow |

### 6.3 Manual

| Report / Function | Notes |
|---|---|
| MSB registration (Form 107) | One-time filing; manual BSA E-Filing submission |
| MSB re-registration | Biennial; manual BSA E-Filing submission |
| FBAR (Form 114) | Annual if applicable; manual BSA E-Filing submission |
| State license applications | Per-state; NMLS platform |
| State call reports | Quarterly if licensed; NMLS platform |
| AML training delivery | Annual; manual coordination |
| Independent AML testing | Annual; third-party engagement |
| Board compliance reports | Quarterly; Compliance Officer prepares |
| Risk assessment | Annual; Compliance Officer leads |

---

## 7. Key Contacts

| Role | Responsibility | Contact |
|---|---|---|
| Compliance Officer | All BSA/AML reporting; SAR filing authority | [To be appointed] |
| CEO (interim) | Backup compliance authority | Efe Baran Durmaz |
| Outside legal counsel | Regulatory guidance, examination support | [To be engaged] |
| BSA E-Filing Support | FinCEN technical support | 1-866-346-9478 |
| NMLS Support | State licensing platform support | 1-855-665-7123 |

---

## 8. Document References

| Document | Path | Purpose |
|---|---|---|
| MSB Registration Guide | `docs/compliance/fincen/msb-registration-guide.md` | Step-by-step registration process |
| BSA/AML Program | `docs/compliance/fincen/bsa-aml-program.md` | Full compliance program documentation |
| State Licensing Analysis | `docs/compliance/fincen/state-licensing-analysis.md` | State-by-state licensing requirements |
| Data Retention Policy | `docs/compliance/soc2/data-retention-policy.md` | Record retention periods and procedures |
| Incident Response Plan | `docs/compliance/soc2/incident-response-plan.md` | Incident handling procedures |
| Regulatory Research | `docs/compliance/regulatory-compliance-research.md` | Comprehensive regulatory landscape analysis |

---

## 9. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-11 | Sardis Compliance | Initial document |
