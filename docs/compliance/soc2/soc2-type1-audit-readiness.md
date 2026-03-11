# SOC 2 Type 1 Audit Readiness Checklist

**Document ID:** SARDIS-SOC2-ARC-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Engineering
**Classification:** Internal

---

## 1. Overview

A SOC 2 Type 1 report evaluates the **design** of an organization's controls at a specific point in time. Unlike Type 2, which tests operating effectiveness over a period (typically 6--12 months), Type 1 confirms that controls are suitably designed to meet the Trust Service Criteria.

This checklist ensures all Sardis controls are designed, documented, and evidence-ready before engaging the audit firm.

## 2. Audit Planning

### 2.1 Target Timeline

| Milestone | Target Date | Status |
|-----------|------------|--------|
| All policy documentation complete | Q1 2026 | Done |
| Control testing procedures documented | Q1 2026 | Done |
| Evidence collection automation in place | Q2 2026 | In Progress |
| Internal readiness assessment | Q2 2026 | Not Started |
| Auditor selection and engagement | Q2 2026 | Not Started |
| Pre-audit remediation complete | Q2 2026 | Not Started |
| Type 1 audit fieldwork | Q3 2026 | Not Started |
| Type 1 report issued | Q3 2026 | Not Started |
| Type 2 observation period begins | Q3 2026 | Not Started |
| Type 2 report issued | Q2 2027 | Not Started |

### 2.2 Estimated Costs

| Item | Estimated Cost | Notes |
|------|---------------|-------|
| Pre-audit readiness assessment (optional) | $5,000 -- $10,000 | Recommended if this is the first SOC 2 audit |
| Type 1 audit (CPA firm) | $20,000 -- $35,000 | Depends on scope and firm; 4 TSC categories |
| Remediation (if needed) | $5,000 -- $15,000 | Based on readiness assessment findings |
| Compliance tooling (Vanta/Drata/Secureframe) | $10,000 -- $20,000/yr | Optional; automates evidence collection and monitoring |
| Type 2 audit (future, 2027) | $25,000 -- $60,000 | 6--12 month observation period |

### 2.3 Trust Service Criteria in Scope

| Category | In Scope | Justification |
|----------|----------|---------------|
| Security (CC1--CC9) | Yes (required) | Required for all SOC 2 reports |
| Availability (A1) | Yes | Critical for financial infrastructure; customers depend on uptime SLAs |
| Confidentiality (C1) | Yes | Customer financial data and PII must be protected |
| Processing Integrity (PI1) | Yes | Payment accuracy and ledger integrity are core to the product |
| Privacy | No (deferred) | Deferred to Type 2; privacy controls are in place but formal privacy criteria add scope |

---

## 3. Pre-Audit Checklist

### 3.1 Governance and Organization

| # | Requirement | Status | Evidence / Location |
|---|------------|--------|-------------------|
| 3.1.1 | Company organizational chart defined | Done | Internal documentation |
| 3.1.2 | Compliance officer designated | Done | Founder/compliance lead |
| 3.1.3 | Architecture principles documented | Done | `CLAUDE.md` (Architecture Principles section) |
| 3.1.4 | Code of conduct document created | To Do | Needs formal document; principles exist in `CLAUDE.md` |
| 3.1.5 | Board/management oversight documentation | To Do | Quarterly compliance reports need to begin |
| 3.1.6 | Employee handbook with security policies | To Do | Needed for formal onboarding process |
| 3.1.7 | On-call rotation schedule | Done | Incident Response Plan (Section 5) |
| 3.1.8 | Escalation matrix | Done | Incident Response Plan (Section 5) |

### 3.2 Policy Documentation

| # | Requirement | Status | Evidence / Location |
|---|------------|--------|-------------------|
| 3.2.1 | Incident response plan | Done | `docs/compliance/soc2/incident-response-plan.md` |
| 3.2.2 | Access control policy | Done | `docs/compliance/soc2/access-control-policy.md` |
| 3.2.3 | Secrets rotation runbook | Done | `docs/compliance/soc2/secrets-rotation-runbook.md` |
| 3.2.4 | Data retention policy | Done | `docs/compliance/soc2/data-retention-policy.md` |
| 3.2.5 | Change management policy | Done | `docs/compliance/soc2/change-management-policy.md` |
| 3.2.6 | Disaster recovery runbook | Done | `docs/compliance/soc2/disaster-recovery-runbook.md` |
| 3.2.7 | Evidence matrix | Done | `docs/compliance/soc2/evidence-matrix.md` |
| 3.2.8 | Control testing procedures | Done | `docs/compliance/soc2/control-testing-procedures.md` |
| 3.2.9 | Evidence collection automation guide | Done | `docs/compliance/soc2/evidence-collection-automation.md` |
| 3.2.10 | Acceptable use policy | To Do | Defines acceptable use of Sardis systems by team members |
| 3.2.11 | Vendor management policy | To Do | Formalizes third-party risk assessment process |
| 3.2.12 | Data classification policy | To Do | Formalizes Public/Internal/Confidential/Restricted scheme |
| 3.2.13 | Vulnerability disclosure policy | To Do | Public-facing responsible disclosure process |

### 3.3 Technical Controls -- Security

| # | Control | Status | Implementation |
|---|---------|--------|----------------|
| 3.3.1 | API authentication (SHA-256 hashed keys) | Done | `packages/sardis-api/src/sardis_api/authz.py` |
| 3.3.2 | JWT token authentication | Done | `packages/sardis-api/src/sardis_api/authz.py` |
| 3.3.3 | RBAC enforcement (Principal model) | Done | `packages/sardis-api/src/sardis_api/authz.py` with `require_principal` |
| 3.3.4 | Rate limiting | Done | `packages/sardis-guardrails/rate_limiter.py`, Redis-backed in non-dev |
| 3.3.5 | Encryption in transit (TLS 1.3) | Done | Enforced by Vercel and Cloud Run |
| 3.3.6 | Database encryption at rest | Done | Neon PostgreSQL managed encryption |
| 3.3.7 | MPC key management (no single-party key access) | Done | Turnkey integration in `packages/sardis-wallet/` |
| 3.3.8 | Webhook signature verification (HMAC) | Done | Required in all non-dev environments (TDD remediation) |
| 3.3.9 | Replay protection | Done | Mandate cache + Redis dedup store |
| 3.3.10 | Kill switch (emergency halt) | Done | `packages/sardis-api/` kill switch capability |
| 3.3.11 | Secret scanning in CI | Done | Gitleaks in `.github/workflows/ci.yml` |
| 3.3.12 | AGIT fail-closed default | Done | TDD remediation; override via `SARDIS_AGIT_FAIL_OPEN=true` |
| 3.3.13 | Idempotency enforcement (DB unique constraint) | Done | `idempotency_key` unique constraint on checkout sessions |
| 3.3.14 | Concurrent payment protection | Done | `SELECT ... FOR UPDATE NOWAIT` on checkout sessions |

### 3.4 Technical Controls -- Policy Engine

| # | Control | Status | Implementation |
|---|---------|--------|----------------|
| 3.4.1 | 12-step spending policy pipeline | Done | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` |
| 3.4.2 | Amount limit enforcement | Done | Policy step: amount check |
| 3.4.3 | MCC (Merchant Category Code) filtering | Done | Policy step: MCC check |
| 3.4.4 | Merchant allowlist/blocklist | Done | Policy step: merchant check |
| 3.4.5 | Goal drift detection | Done | Policy step: goal alignment check |
| 3.4.6 | KYA (Know Your Agent) attestation | Done | Policy step: KYA check |
| 3.4.7 | PaymentOrchestrator enforcement | Done | All routers go through PaymentOrchestrator; chain_executor is private in DI |

### 3.5 Technical Controls -- Compliance

| # | Control | Status | Implementation |
|---|---------|--------|----------------|
| 3.5.1 | KYC verification | Done | `packages/sardis-compliance/kyc.py` (iDenfy integration) |
| 3.5.2 | Sanctions screening | Done | `packages/sardis-compliance/sanctions.py` (Elliptic integration) |
| 3.5.3 | SAR filing capability | Done | `packages/sardis-compliance/sar.py` |
| 3.5.4 | Travel rule compliance | Done | `packages/sardis-compliance/travel_rule.py` |
| 3.5.5 | MiCA compliance framework | Done | `packages/sardis-compliance/mica.py` |
| 3.5.6 | Risk scoring | Done | `packages/sardis-compliance/risk_scoring.py` |

### 3.6 Monitoring and Logging

| # | Control | Status | Implementation |
|---|---------|--------|----------------|
| 3.6.1 | Health check endpoints (10+ components) | Done | `packages/sardis-api/src/sardis_api/health.py` |
| 3.6.2 | Error rate monitoring | Done | Prometheus metrics |
| 3.6.3 | Transaction audit trail (append-only) | Done | sardis-ledger package |
| 3.6.4 | CI/CD pipeline (ruff, mypy, pytest, gitleaks) | Done | `.github/workflows/ci.yml` |
| 3.6.5 | Admin action audit logging | Done | `packages/sardis-api/src/sardis_api/audit_log.py` |
| 3.6.6 | Centralized log aggregation | To Do | Need to configure Datadog or Grafana Cloud |
| 3.6.7 | SIEM integration | To Do | Future consideration; not required for Type 1 |

### 3.7 Business Continuity and Availability

| # | Control | Status | Implementation |
|---|---------|--------|----------------|
| 3.7.1 | Disaster recovery runbook | Done | `docs/compliance/soc2/disaster-recovery-runbook.md` |
| 3.7.2 | Database backup procedures | Done | Neon PostgreSQL automated backups |
| 3.7.3 | DR test execution and results | To Do | Need to execute DR runbook in staging and document results |
| 3.7.4 | RTO/RPO targets defined | Done | Disaster Recovery Runbook |
| 3.7.5 | RTO/RPO validation test results | To Do | Need to measure actual RTO/RPO during DR test |
| 3.7.6 | Customer notification procedures | Done | Incident Response Plan (Section 9) communication templates |

### 3.8 Risk Assessment

| # | Control | Status | Implementation |
|---|---------|--------|----------------|
| 3.8.1 | Threat model | Done | `docs/security/threat-model.md` |
| 3.8.2 | Audit scope definition | Done | `docs/security/audit-scope.md` |
| 3.8.3 | Annual risk assessment document | To Do | Formal annual risk assessment with scoring matrix |
| 3.8.4 | Third-party risk assessments | To Do | Formal vendor security reviews for Turnkey, Stripe, Neon, Alchemy, iDenfy, Elliptic |
| 3.8.5 | Penetration test results | To Do | Schedule external penetration test |

---

## 4. Gap Analysis Summary

### 4.1 Gaps Requiring Remediation Before Type 1

These items must be completed before the Type 1 audit fieldwork begins. They represent gaps in control design documentation that an auditor would flag.

| # | Gap | Priority | Effort | Target Date |
|---|-----|----------|--------|-------------|
| G-01 | Code of conduct document | High | 1 day | Q2 2026 |
| G-02 | Acceptable use policy | Medium | 1 day | Q2 2026 |
| G-03 | Vendor management policy | High | 2 days | Q2 2026 |
| G-04 | Data classification policy | Medium | 1 day | Q2 2026 |
| G-05 | Vulnerability disclosure policy | Medium | 1 day | Q2 2026 |
| G-06 | Annual risk assessment (formal) | High | 3 days | Q2 2026 |
| G-07 | Third-party risk assessments (6 vendors) | High | 5 days | Q2 2026 |
| G-08 | First quarterly compliance report | High | 2 days | Q2 2026 |
| G-09 | Centralized log aggregation setup | Medium | 3 days | Q2 2026 |
| G-10 | DR test execution and results | Medium | 2 days | Q2 2026 |
| G-11 | External penetration test | High | 2--4 weeks (vendor) | Q2 2026 |
| G-12 | Employee handbook with security section | Medium | 2 days | Q2 2026 |

**Total remediation effort:** Approximately 3--4 weeks of work, plus penetration test vendor lead time.

### 4.2 Items Not Required for Type 1 (Deferred)

These items improve audit posture but are not strictly required for a Type 1 report on control design:

- SIEM integration (beneficial for Type 2)
- Automated control testing (beneficial for Type 2)
- Compliance dashboard (beneficial for Type 2)
- Privacy criteria (deferred to Type 2)
- Machine learning anomaly detection (future enhancement)

---

## 5. Auditor Preparation

### 5.1 Documentation Package for Auditor

The following documentation package should be assembled and provided to the auditor at the start of engagement:

| # | Document | Location | Purpose |
|---|----------|----------|---------|
| 1 | System description | To be written (see 5.2) | Auditor needs to understand the system architecture, data flows, and trust boundaries |
| 2 | Incident Response Plan | `docs/compliance/soc2/incident-response-plan.md` | CC7.3, CC7.4, CC7.5 |
| 3 | Access Control Policy | `docs/compliance/soc2/access-control-policy.md` | CC6.1, CC6.2, CC6.3, CC6.4 |
| 4 | Secrets Rotation Runbook | `docs/compliance/soc2/secrets-rotation-runbook.md` | CC6.3 |
| 5 | Data Retention Policy | `docs/compliance/soc2/data-retention-policy.md` | C1.1 |
| 6 | Change Management Policy | `docs/compliance/soc2/change-management-policy.md` | CC8.1 |
| 7 | Disaster Recovery Runbook | `docs/compliance/soc2/disaster-recovery-runbook.md` | A1.2 |
| 8 | Evidence Matrix | `docs/compliance/soc2/evidence-matrix.md` | Maps all controls to TSC |
| 9 | Control Testing Procedures | `docs/compliance/soc2/control-testing-procedures.md` | Defines how controls are tested |
| 10 | Evidence Collection Automation | `docs/compliance/soc2/evidence-collection-automation.md` | Shows automation approach |
| 11 | Architecture principles | `CLAUDE.md` (Architecture Principles) | CC1.1 |
| 12 | Threat model | `docs/security/threat-model.md` | CC3.1 |
| 13 | Audit scope | `docs/security/audit-scope.md` | Defines audit boundaries |
| 14 | Vendor list with security assessments | To be compiled | CC8.2 |
| 15 | Organizational chart | To be compiled | CC1.3 |

### 5.2 System Description (Auditor Narrative)

The system description is a key deliverable for SOC 2. It must cover:

1. **Nature of services:** Sardis is a Payment Operating System for AI agents, providing non-custodial MPC wallets, natural language spending policies, and stablecoin payment execution.
2. **Principal service commitments:** Security, availability, confidentiality, processing integrity.
3. **System boundaries:** API endpoints, PostgreSQL database, MPC wallet infrastructure (Turnkey), blockchain execution (Base, Polygon, Ethereum, Arbitrum, Optimism), virtual card issuance (Stripe), compliance services (iDenfy, Elliptic).
4. **Infrastructure:** Vercel (frontend/API), Cloud Run (backend), Neon (database), Upstash (Redis), Alchemy (RPC).
5. **Data flows:** Agent request -> API -> Policy engine -> Chain execution -> Settlement -> Audit log.
6. **Trust boundaries:** API authentication boundary, policy enforcement boundary, MPC signing boundary, blockchain execution boundary.
7. **Relevant aspects of the control environment:** Non-custodial architecture, fail-closed defaults, append-only audit trail, MPC key management.

### 5.3 Auditor Walkthrough Topics

Prepare demonstrations or walkthroughs for the following areas. The auditor will want to observe control design in action:

| # | Topic | Demonstrator | Key Points |
|---|-------|-------------|------------|
| 1 | Authentication and authorization flow | Engineering Lead | API key hashing, JWT validation, RBAC with `require_principal`, 401/403 responses |
| 2 | MPC wallet creation and transaction signing | Engineering Lead | Turnkey integration, multi-party computation, no single key holder |
| 3 | Spending policy evaluation pipeline | Engineering Lead | 12-step pipeline, amount limits, MCC filtering, goal drift, fail-closed behavior |
| 4 | SAR generation and filing process | Compliance Officer | Risk scoring triggers, SAR creation, filing workflow |
| 5 | Incident response procedures | Engineering Lead | Severity classification, escalation matrix, communication templates, kill switch |
| 6 | Change management and deployment | Engineering Lead | PR reviews, CI pipeline, branch protection, deployment process |
| 7 | Monitoring and alerting | Engineering Lead | Health checks (10+ components), error rate alerts, kill switch monitoring |
| 8 | Data retention and destruction | Compliance Officer | Retention schedules, purge procedures, encryption |
| 9 | Rate limiting and abuse prevention | Engineering Lead | Redis-backed rate limiter, IP blocking, replay protection |
| 10 | Checkout session security | Engineering Lead | Client secrets, `FOR UPDATE NOWAIT`, idempotency keys, webhook signatures |

### 5.4 Evidence Samples to Prepare

Have the following evidence samples ready before the auditor's first day:

| Evidence | Sample Size | Purpose |
|----------|------------|---------|
| Recent PRs showing review process | 10 PRs (include 3 security-sensitive) | Demonstrates change management |
| Health check logs | 30 consecutive days | Demonstrates monitoring |
| Policy enforcement decisions | 20 decisions (mix of approve/deny) | Demonstrates policy engine |
| Incident response records | 3 incidents or drills | Demonstrates incident management |
| Current IAM access list (all providers) | Complete list | Demonstrates access control |
| Vulnerability scan results | Most recent scan | Demonstrates risk management |
| API authentication rejection logs | 10 rejection events | Demonstrates access enforcement |
| Rate limiting enforcement logs | 5 rate limit events | Demonstrates abuse prevention |
| Deployment log | 10 recent deployments | Demonstrates change management |
| Secret rotation log | Most recent rotation cycle | Demonstrates credential management |

---

## 6. Auditor Selection Criteria

When selecting a CPA firm for the SOC 2 Type 1 audit, evaluate against these criteria:

| Criterion | Importance | Notes |
|-----------|-----------|-------|
| AICPA peer review current | Required | Must have current peer review; verify on AICPA website |
| Fintech/payments industry experience | High | Experience with payment processors, digital wallets, or blockchain companies |
| Startup-friendly engagement model | High | Fixed-fee preferred over hourly; clear scope definition |
| SOC 2 report volume | Medium | Firms issuing 50+ SOC 2 reports/year have established processes |
| Blockchain/crypto familiarity | Medium | Understanding of MPC wallets, stablecoins, and on-chain transactions |
| Type 2 continuity | High | Select a firm willing to continue to Type 2 for consistency |
| Timeline flexibility | Medium | Ability to start fieldwork in Q3 2026 |

**Recommended approach:** Request proposals from 3 firms. Provide the system description and document inventory upfront so firms can scope accurately.

---

## 7. Post-Audit Actions

### 7.1 Upon Receipt of Type 1 Report

1. Review the auditor's opinion for any qualifications or exceptions.
2. Review the management letter for observations and recommendations.
3. Create a remediation plan for any findings, with owners and deadlines.
4. Share the report with customers/prospects who have requested it (under NDA if needed).

### 7.2 Transition to Type 2

| Action | Timeline | Owner |
|--------|----------|-------|
| Address any Type 1 findings | Within 30 days of report | Compliance Officer |
| Begin Type 2 observation period | Immediately after Type 1 | Compliance Officer |
| Execute quarterly control tests per testing procedures | Quarterly | Engineering Lead |
| Collect evidence per automation guide | Ongoing | Engineering Lead |
| Run first quarterly compliance review | End of Q3 2026 | Compliance Officer |
| Engage auditor for Type 2 fieldwork | Q1 2027 | Compliance Officer |
| Type 2 report issued | Q2 2027 | Auditor |

### 7.3 Ongoing Compliance Maintenance

After Type 1, maintain audit readiness continuously:

- **Weekly:** Review automated compliance summary (see evidence-collection-automation.md Section 8.2)
- **Monthly:** Review uptime and error rate reports
- **Quarterly:** Execute control tests per schedule (see control-testing-procedures.md Section 17), deliver compliance report, review IAM access
- **Semi-annually:** Conduct incident response tabletop exercise, review DR test results
- **Annually:** Formal risk assessment, vendor security reviews, policy acknowledgments, security training, DR test, penetration test

---

## 8. Risk Register for Audit Preparation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auditor finds undocumented control gaps | Medium | High | Internal readiness assessment before engagement; this checklist |
| Penetration test reveals critical vulnerabilities | Low | High | Conduct pentest early in Q2 to allow remediation time |
| Key personnel unavailable during fieldwork | Medium | Medium | Document all processes; ensure at least 2 people can demo each control area |
| Evidence collection scripts not ready | Medium | Medium | Prioritize script development in Q2; manual collection as fallback |
| Vendor (Turnkey/Stripe/Neon) cannot provide SOC 2 report | Low | High | Request vendor certifications early; substitute with security questionnaire if needed |
| Scope creep during audit | Medium | Medium | Define scope clearly in engagement letter; push back on out-of-scope requests |

---

## 9. Quick Reference: What Auditors Typically Ask

Based on common SOC 2 Type 1 audit inquiries for fintech companies:

| Question Area | Expected Questions | Where to Find Answers |
|---------------|-------------------|----------------------|
| System boundaries | "What systems are in scope? What is excluded?" | Audit scope document, system description |
| Authentication | "How do you authenticate API requests? How are credentials stored?" | Access Control Policy, `authz.py` |
| Key management | "Who has access to private keys? How are keys protected?" | Turnkey architecture, MPC documentation |
| Change management | "How do code changes get to production? Who approves?" | Change Management Policy, CI pipeline config |
| Incident response | "What happens when you detect a security incident?" | Incident Response Plan |
| Monitoring | "How do you know when something goes wrong?" | Health checks, alerting configuration, operational alerts |
| Data handling | "Where is customer data stored? How is it protected?" | Data Retention Policy, database architecture |
| Third parties | "What third parties have access to data?" | Vendor list, third-party risk assessments |
| Business continuity | "What happens if your primary infrastructure fails?" | Disaster Recovery Runbook |
| Compliance | "How do you handle regulatory requirements (AML/KYC)?" | Compliance modules, SAR process |

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-11 | Compliance / Engineering | Initial release |
