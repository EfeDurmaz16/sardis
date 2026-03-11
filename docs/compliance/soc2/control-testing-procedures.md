# SOC 2 Control Testing Procedures

**Document ID:** SARDIS-SOC2-CTP-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Engineering
**Classification:** Internal

---

## 1. Purpose

This document defines how each SOC 2 Trust Service Criteria control is tested and validated within the Sardis platform. It serves as the testing workbook for internal quarterly assessments and external auditor review. Each control maps to a specific test procedure, expected evidence, and testing cadence.

## 2. Scope

This procedure covers all controls identified in the Sardis SOC 2 Evidence Matrix (`evidence-matrix.md`) across the following Trust Service Categories:

- **Security** (Common Criteria CC1 -- CC9) -- Required for all SOC 2 reports
- **Availability** (A1)
- **Confidentiality** (C1)
- **Processing Integrity** (PI1)

## 3. Testing Methodology

### 3.1 Testing Types

| Type | Description | When Used |
|------|-------------|-----------|
| **Inquiry** | Interview control owner to understand design and operation | All controls; initial assessment |
| **Observation** | Watch the control being executed in real time | Operational controls (monitoring, incident response) |
| **Inspection** | Examine artifacts, logs, configurations, or documentation | Configuration-based controls, policy controls |
| **Re-performance** | Independently execute the control to verify it functions as designed | Technical controls (rate limiting, policy enforcement, access denial) |

### 3.2 Testing Frequency

| Risk Level | Frequency | Examples |
|------------|-----------|----------|
| **High** | Quarterly | Access control enforcement, policy engine, encryption, rate limiting |
| **Medium** | Semi-annually | Incident response drills, vulnerability scanning, IAM review |
| **Low** | Annually | Code of conduct acknowledgment, DR test, organizational documentation |

### 3.3 Evidence Retention

- All test results, screenshots, logs, and reports are retained for **5 years** per the Data Retention Policy (`data-retention-policy.md`).
- Evidence is stored in the compliance evidence repository with the naming convention: `evidence-YYYY-QN/test-id/`.
- Each test execution produces a test record containing: test ID, date executed, tester name, pass/fail result, evidence references, and remediation notes (if applicable).

### 3.4 Failure Handling

When a control test fails:
1. Log the failure in the compliance tracker with severity (Critical / Major / Minor).
2. Critical failures trigger a P1 incident per the Incident Response Plan.
3. Major failures require remediation within 30 days with a re-test.
4. Minor failures require remediation within 90 days.
5. All failures are reported in the next quarterly compliance review.

---

## 4. CC1: Control Environment

### CC1.1: Organizational Commitment to Integrity and Ethical Values

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC1.1-01 | Code of conduct acknowledgment | Verify code of conduct document exists, is current, and has been acknowledged by all team members. Cross-check acknowledgment records against the active employee roster. | Signed acknowledgment records, employee roster | Annual |
| CC1.1-02 | Architecture principles enforcement | Sample 10 recent PRs involving security-sensitive code. Verify that reviewers explicitly cite architecture principles from `CLAUDE.md` (non-custodial first, fail-closed, audit everything) in review comments. | PR review comments, `CLAUDE.md` | Quarterly |
| CC1.1-03 | Security-first culture | Interview 3 randomly selected team members on their understanding of Sardis security principles (non-custodial, fail-closed, policy-before-execution). | Interview notes | Annual |

### CC1.2: Board and Management Oversight

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC1.2-01 | Quarterly compliance reports | Verify that the compliance officer has delivered a written compliance report covering: open incidents, control test results, regulatory changes, and remediation progress. Confirm delivery via meeting minutes or email receipt. | Report documents, meeting minutes, email receipts | Quarterly |
| CC1.2-02 | Security budget allocation | Verify that security tooling, compliance, and audit costs have a dedicated budget line. Confirm actual spend against allocation. | Budget documents, invoices | Annual |

### CC1.3: Organizational Structure

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC1.3-01 | On-call rotation | Verify on-call rotation schedule exists and covers all 7 days. Confirm at least one engineer is assigned for each shift per the Incident Response Plan (Section 5). | On-call schedule export | Quarterly |
| CC1.3-02 | Escalation matrix | Verify escalation matrix is current and tested. Send a test page/alert through the escalation chain in a non-production context and confirm receipt at each tier. | Alert delivery records, escalation matrix document | Semi-annual |

### CC1.4: Commitment to Competence

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC1.4-01 | CI enforcement | Verify that the CI pipeline (`ci.yml`) enforces ruff (linting), mypy (type checking), pytest (tests), and gitleaks (secret scanning) on every PR. Attempt to merge a PR with a failing check and confirm it is blocked. | CI configuration file, blocked PR screenshot | Quarterly |
| CC1.4-02 | Code review standards | Sample 15 merged PRs. Verify each has at least 1 approval (2 for security-sensitive changes as defined in the Change Management Policy). | GitHub PR audit log | Quarterly |

### CC1.5: Accountability

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC1.5-01 | Admin action audit logging | Perform 5 admin actions in staging (create API key, revoke key, modify policy, change role, update config). Verify each is recorded in the audit log (`sardis_api/audit_log.py`) with user ID, timestamp, action, and affected resource. | Audit log entries | Quarterly |
| CC1.5-02 | Audit log immutability | Attempt to modify or delete an existing audit log entry via direct database access. Verify the operation is denied or logged as a tampering attempt. | Database access attempt logs, constraint error evidence | Semi-annual |

---

## 5. CC2: Communication and Information

### CC2.1: Internal Communication of Security Objectives

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC2.1-01 | Security awareness training | Verify all team members have completed security awareness training within the past 12 months. Cross-check completion records against the active roster. | Training platform completion logs, employee roster | Annual |
| CC2.1-02 | Incident notification channels | Send a test notification through each incident communication channel (Slack #incidents, email distribution list, PagerDuty). Verify delivery to all expected recipients within 5 minutes. | Notification delivery timestamps, recipient confirmation | Semi-annual |
| CC2.1-03 | Policy documentation accessibility | Verify all SOC 2 policy documents are accessible to the entire team via the `docs/compliance/soc2/` directory. Confirm no access restrictions prevent team members from reading policies. | Repository access logs, team member confirmation | Annual |

### CC2.2: Internal Communication of Policies

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC2.2-01 | Policy change notification | Verify that changes to any SOC 2 policy document trigger a notification to the team. Inspect git commit history for policy files and cross-reference with team notification records. | Git commit log for `docs/compliance/soc2/`, notification records | Semi-annual |

### CC2.3: External Communication

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC2.3-01 | Customer-facing API documentation | Verify OpenAPI docs at `/api/v2/docs` are current, reflect all active endpoints, and include authentication requirements. Compare spec against actual endpoint inventory. | OpenAPI spec export, endpoint inventory | Quarterly |
| CC2.3-02 | Incident communication templates | Verify incident communication templates in the Incident Response Plan (Section 9) are current and include all required fields (affected services, timeline, impact, remediation). | Template review, sample incident notification | Annual |

---

## 6. CC3: Risk Assessment

### CC3.1: Risk Identification and Objectives

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC3.1-01 | Threat model review | Verify threat model (`docs/security/threat-model.md`) has been reviewed and updated within the past 12 months. Confirm review includes new features, integrations, and attack vectors added since the last review. | Document version history, review approval (PR or sign-off) | Annual |
| CC3.1-02 | Vulnerability scanning | Run `pip audit` and `npm audit` against all packages. Verify no critical or high severity findings have been open for more than 30 days. Document any accepted risks with justification. | Scan reports, accepted risk register | Quarterly |
| CC3.1-03 | Secret scanning | Verify gitleaks CI runs on every PR and push. Intentionally introduce a test secret in a branch and confirm it is caught before merge. | CI run log showing gitleaks detection, blocked PR | Quarterly |

### CC3.2: Fraud Risk Assessment

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC3.2-01 | Spending policy engine validation | Submit 5 test transactions through the spending policy engine (`spending_policy.py`): (1) within limits -- should pass, (2) exceeding amount limit -- should fail, (3) blocked MCC -- should fail, (4) blocked merchant -- should fail, (5) goal drift detection -- should flag. Verify all 5 produce expected results. | Policy evaluation logs, test transaction records | Quarterly |
| CC3.2-02 | Sanctions screening accuracy | Submit 3 test addresses/entities through the sanctions screening module (`sardis_compliance/sanctions.py`): (1) known clean address, (2) address on OFAC SDN list, (3) address on EU sanctions list. Verify correct pass/block decisions. | Screening results, test case documentation | Quarterly |

### CC3.3: Change Risk

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC3.3-01 | Security-sensitive change classification | Review 10 recent PRs touching `sardis-wallet`, `sardis-compliance`, `sardis-protocol`, `sardis-chain`, or `authz.py`. Verify each was classified as security-sensitive and received 2 approvals per the Change Management Policy. | PR review logs, approval counts | Quarterly |

---

## 7. CC4: Monitoring Activities

### CC4.1: System Monitoring

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC4.1-01 | Health check endpoints | Hit `/api/v2/health` (deep check) and verify all 10+ component checks return healthy: database, Redis, Turnkey, Stripe, RPC, contracts, TAP JWKS, kill switch, compliance services, webhooks. Document any degraded components. | API response JSON, timestamp | Daily (automated), Quarterly (manual review) |
| CC4.1-02 | Error rate alerting | Verify error rate alert configuration triggers at >1% error rate threshold. In staging, artificially inflate error rate above threshold and confirm alert fires within the configured window. | Alert configuration, triggered alert screenshot | Quarterly |
| CC4.1-03 | Transaction anomaly detection | Verify the risk scoring module (`sardis_compliance/risk_scoring.py`) flags transactions matching suspicious patterns. Submit 3 test transactions with anomalous characteristics (unusual amount, unusual frequency, unusual geography) and confirm elevated risk scores. | Risk score outputs, test transaction logs | Semi-annual |
| CC4.1-04 | Kill switch monitoring | Verify the kill switch state is included in health checks. Activate kill switch in staging and confirm: (a) health check reports unhealthy, (b) all payment operations are halted, (c) alert fires. | Health check response, kill switch activation log | Quarterly |

### CC4.2: Deficiency Identification

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC4.2-01 | Control deficiency tracking | Review the compliance tracker for any open deficiencies. Verify each has an assigned owner, target remediation date, and severity classification. Confirm no Critical deficiencies are open beyond 30 days. | Compliance tracker export | Quarterly |

---

## 8. CC5: Control Activities

### CC5.1: Access Control Enforcement

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC5.1-01 | API key hashing | Query the `api_keys` table in the database. Verify all stored keys are SHA-256 hashes (64-character hex strings), not plaintext. Verify no plaintext keys exist in any column. | Database query result (redacted) | Quarterly |
| CC5.1-02 | RBAC enforcement | Using a non-admin API key, attempt the following admin actions via the API: (1) list all users, (2) revoke another user's key, (3) modify global configuration, (4) access audit logs. Verify all return HTTP 403 Forbidden. | API response logs (4 requests with 403 responses) | Quarterly |
| CC5.1-03 | MPC key isolation | Review Turnkey architecture documentation and access logs. Verify: (a) no single party (including Sardis) can reconstruct a full private key, (b) signing requires multi-party computation, (c) Turnkey access is restricted to the service account. | Turnkey architecture docs, access logs, IAM configuration | Annual |
| CC5.1-04 | Principal-based authorization | Review the `require_principal` middleware in `sardis_api/authz.py`. Verify it enforces authentication on all non-public endpoints. Test 5 protected endpoints without credentials and confirm 401 responses. | Code review evidence, API response logs | Quarterly |

### CC5.2: Logical Access Controls

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC5.2-01 | JWT token expiry | Issue a JWT token and verify it includes an `exp` claim within the configured TTL. Wait for expiry and confirm the token is rejected with HTTP 401. | Token decode output, rejection response | Quarterly |
| CC5.2-02 | Rate limiting enforcement | Send requests exceeding the configured rate limit threshold to a protected endpoint. Verify the rate limiter (`sardis_guardrails/rate_limiter.py`) returns HTTP 429 after the threshold is exceeded. Verify Redis-backed enforcement in non-dev environments. | Rate limit response headers, 429 response, Redis key inspection | Quarterly |
| CC5.2-03 | Session management | Verify checkout sessions (`client_secret` based) expire after the configured TTL. Attempt to use an expired session and confirm rejection. Verify `SELECT ... FOR UPDATE NOWAIT` prevents concurrent session manipulation. | Session expiry test, concurrent access test results | Quarterly |

---

## 9. CC6: System Operations

### CC6.1: Incident Management

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC6.1-01 | Incident response tabletop exercise | Execute a tabletop exercise using a scenario from the Incident Response Plan (e.g., compromised API key, data breach, chain reorg). Walk through detection, classification, containment, eradication, recovery, and post-incident review. Document time-to-respond and any process gaps. | Tabletop exercise report, lessons learned, attendee list | Semi-annual |
| CC6.1-02 | Kill switch activation test | In staging: (1) activate the kill switch, (2) verify all payment operations halt, (3) verify health check reports emergency state, (4) deactivate kill switch, (5) verify operations resume. Measure time from activation to full halt. | Kill switch activation/deactivation logs, timing measurements | Quarterly |
| CC6.1-03 | Incident classification accuracy | Review the last 5 incidents (or simulated incidents). Verify each was classified at the correct severity level (P0-P3) per the Incident Response Plan (Section 3). Verify escalation followed the defined matrix. | Incident records, classification justification | Quarterly |

### CC6.2: Change Management

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC6.2-01 | PR review requirement | Sample 20 merged PRs from the period. Verify: (a) all have at least 1 approval, (b) security-sensitive PRs (touching wallet, compliance, auth, chain packages) have at least 2 approvals, (c) no PRs were merged with failing CI checks. | GitHub PR audit export | Quarterly |
| CC6.2-02 | CI/CD pipeline integrity | Verify the CI pipeline configuration (`.github/workflows/ci.yml`) includes: ruff (linting), mypy (type checking), pytest (unit/integration tests), gitleaks (secret scanning). Verify pipeline cannot be bypassed by contributors. | CI configuration file, branch protection rules | Quarterly |
| CC6.2-03 | Deployment audit trail | Verify each production deployment has a corresponding entry in the deployment log with: deployer identity, timestamp, commit SHA, deployment target, and rollback plan. Sample 5 recent deployments. | Deployment log entries, Cloud Run revision history | Quarterly |

---

## 10. CC7: Logical and Physical Access Controls

### CC7.1: Infrastructure Access

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC7.1-01 | Cloud IAM review | Export IAM permissions from all cloud providers (Vercel, Neon, GCP Cloud Run, Upstash, Alchemy, Turnkey, Stripe). Verify each user/service account follows least-privilege. Identify and remediate any over-provisioned accounts. | IAM audit exports, remediation log | Semi-annual |
| CC7.1-02 | Secret rotation compliance | Verify all secrets have been rotated per the schedule defined in the Secrets Rotation Runbook (`secrets-rotation-runbook.md`). Cross-check rotation timestamps against the required cadence (30/90/180 days depending on classification). | Rotation log entries, secret metadata | Quarterly |
| CC7.1-03 | Database access restriction | Verify direct database access (Neon PostgreSQL) is restricted to: (a) the application service account (read/write), (b) engineering leads (read-only, for debugging). Verify no shared credentials exist. | Neon IAM configuration, connection log sample | Semi-annual |

### CC7.2: Physical Security

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC7.2-01 | Cloud provider physical security | Verify cloud providers (Vercel, Neon, GCP) maintain SOC 2 Type 2 reports or equivalent certifications for their physical data centers. Obtain and review current certificates. | Vendor SOC 2 reports, certification documentation | Annual |

### CC7.3: Security Event Evaluation

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC7.3-01 | Authentication failure monitoring | Verify that repeated authentication failures (>10 from same IP within 1 minute) trigger an automated alert and temporary block. Simulate the scenario in staging. | Alert trigger log, IP block evidence | Quarterly |
| CC7.3-02 | Webhook signature verification | Send a webhook request with an invalid HMAC signature to a webhook endpoint. Verify the request is rejected. Verify webhook signature verification is required in all non-dev environments. | Rejected request log, configuration evidence | Quarterly |

---

## 11. CC8: Risk Mitigation

### CC8.1: Transaction Controls

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC8.1-01 | Spending policy limit enforcement | Submit a payment request exceeding the agent's configured spending limit. Verify the policy engine rejects it with a clear denial reason. Verify the denial is logged in the audit trail. | Policy engine rejection log, audit trail entry | Quarterly |
| CC8.1-02 | Sanctions screening enforcement | Submit a test transaction involving an address/entity matching the OFAC Specially Designated Nationals (SDN) list. Verify the transaction is blocked. Verify a SAR is generated or flagged for review. | Screening result, SAR record | Quarterly |
| CC8.1-03 | KYC verification gate | Attempt to create a wallet or initiate a transaction without completing KYC verification. Verify the operation is blocked with an appropriate error message. | API error response, KYC gate log | Quarterly |
| CC8.1-04 | Replay protection | Capture a valid mandate/transaction payload. Replay the exact payload. Verify the system rejects the replay via the mandate cache or Redis dedup store. | Replay rejection log, dedup store evidence | Quarterly |
| CC8.1-05 | Idempotency enforcement | Submit two identical payment requests with the same `idempotency_key`. Verify only one transaction is executed and the second returns the original result. Verify the database-level unique constraint on `idempotency_key` prevents duplicates. | Transaction logs (single execution), database constraint evidence | Quarterly |

### CC8.2: Third-Party Risk

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC8.2-01 | Vendor security review | For each critical vendor (Turnkey, Stripe, Neon, Alchemy, iDenfy, Elliptic), verify: (a) current SOC 2 or equivalent certification, (b) security review completed within past 12 months, (c) no unresolved security findings. | Vendor certificates, review records | Annual |
| CC8.2-02 | Dependency vulnerability management | Run `pip audit` and `npm audit` across all packages. Verify: (a) no critical vulnerabilities, (b) high vulnerabilities resolved within 30 days, (c) medium within 90 days. | Audit reports, remediation timeline | Quarterly |

---

## 12. CC9: Communication

### CC9.1: External Communication

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| CC9.1-01 | Privacy policy accessibility | Verify the privacy policy is published at `sardis.sh/privacy`, is current (updated within past 12 months), and covers data collection, processing, retention, and deletion. | Website screenshot, policy document | Annual |
| CC9.1-02 | Terms of service | Verify terms of service are published, current, and include security responsibilities for both Sardis and customers. | Website screenshot, ToS document | Annual |
| CC9.1-03 | Status page | Verify a public status page exists and accurately reflects current system status. Verify it updates within 15 minutes of a detected incident. | Status page URL, incident correlation check | Semi-annual |

---

## 13. A1: Availability

### A1.1: System Availability

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| A1.1-01 | Uptime monitoring | Export uptime data for the reporting period. Verify the 99.9% availability target is met for all critical endpoints (`/api/v2/health`, payment endpoints, wallet endpoints). Document any downtime incidents with root cause. | Monitoring dashboard export, downtime incident log | Monthly |
| A1.1-02 | Disaster recovery test | Execute the full Disaster Recovery Runbook (`disaster-recovery-runbook.md`) in a staging environment. Measure: (a) RTO -- time to restore service, (b) RPO -- data loss window, (c) process gaps. Verify RTO and RPO meet defined targets. | DR test report, RTO/RPO measurements | Annual |
| A1.1-03 | Database backup verification | Verify Neon PostgreSQL automated backups are enabled and functioning. Perform a point-in-time restore test to a separate environment. Verify data integrity after restore. | Backup configuration, restore test results | Semi-annual |
| A1.1-04 | Auto-scaling validation | Verify Cloud Run auto-scaling is configured for the API service. Generate load exceeding baseline and confirm new instances are provisioned within acceptable latency. | Cloud Run scaling configuration, load test results | Semi-annual |

### A1.2: Capacity Planning

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| A1.2-01 | Resource utilization review | Review CPU, memory, database connection, and Redis utilization over the past quarter. Verify no resource is consistently above 80% utilization. Flag any capacity concerns. | Resource monitoring export | Quarterly |

---

## 14. C1: Confidentiality

### C1.1: Data Protection

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| C1.1-01 | Encryption at rest | Verify Neon PostgreSQL encryption at rest is enabled (AES-256 or equivalent). Obtain configuration evidence from Neon dashboard or API. | Neon encryption configuration | Annual |
| C1.1-02 | Encryption in transit | Run an SSL Labs scan (or equivalent) against all API endpoints. Verify TLS 1.3 is supported, TLS 1.0/1.1 are disabled, and the grade is A or A+. | SSL Labs scan results | Quarterly |
| C1.1-03 | PII handling | Review database schema for PII columns (email, name, address, phone, government ID). Verify each is either encrypted at the application layer or stored in compliance with the Data Retention Policy (`data-retention-policy.md`). | Schema review, encryption verification | Annual |
| C1.1-04 | Secret storage | Verify no secrets (API keys, database credentials, signing keys) are stored in source code. Run gitleaks against the full repository history. Verify all secrets are stored in environment variables or a secrets manager. | Gitleaks full-history scan report | Semi-annual |
| C1.1-05 | Data classification | Verify a data classification scheme exists covering: Public, Internal, Confidential, Restricted. Verify PII and financial data are classified as Confidential or Restricted. | Data classification document, schema annotations | Annual |

### C1.2: Data Disposal

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| C1.2-01 | Data retention enforcement | Verify automated data retention/purge jobs exist and run per the Data Retention Policy schedule. Inspect the database for records exceeding their retention period. | Retention job logs, database inspection | Semi-annual |

---

## 15. PI1: Processing Integrity

### PI1.1: Transaction Processing Accuracy

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| PI1.1-01 | Idempotent transaction processing | Submit 3 pairs of duplicate transactions (same `idempotency_key`). Verify each pair results in exactly one execution. Verify the database unique constraint on `idempotency_key` prevents row duplication. | Transaction logs, database constraint evidence | Quarterly |
| PI1.1-02 | Audit trail append-only integrity | Verify the `sardis-ledger` module enforces append-only writes. Attempt to UPDATE or DELETE an existing ledger entry via direct SQL. Verify the operation fails or is logged as a violation. | Database constraint evidence, attempt logs | Quarterly |
| PI1.1-03 | Replay protection validation | Capture a valid AP2 mandate payload. Replay the payload after the original has been processed. Verify the replay is rejected by the mandate cache or Redis dedup store with an appropriate error. | Replay rejection log, cache/dedup evidence | Quarterly |
| PI1.1-04 | End-to-end payment accuracy | Process 5 test payments of varying amounts and currencies through the full pipeline (policy check, chain execution, settlement). Verify the exact amount (minus fees) arrives at the destination. Reconcile against the ledger. | Payment receipts, ledger entries, on-chain transaction hashes | Quarterly |
| PI1.1-05 | Policy engine determinism | Submit the same transaction payload 10 times through the spending policy engine. Verify identical policy decisions each time (deterministic evaluation). | Policy evaluation logs (10 identical results) | Semi-annual |

### PI1.2: Error Handling

| Test ID | Control | Test Procedure | Evidence | Frequency |
|---------|---------|----------------|----------|-----------|
| PI1.2-01 | Transaction failure handling | Simulate 3 failure scenarios: (1) chain RPC timeout, (2) insufficient balance, (3) policy denial. Verify each produces an appropriate error response, no funds are lost, and the failure is logged. | Error responses, transaction logs, balance verification | Quarterly |
| PI1.2-02 | Webhook delivery reliability | Trigger a webhook event. Verify: (a) the webhook is delivered with a valid HMAC signature, (b) `event_id` is included for deduplication, (c) failed deliveries are retried per the configured backoff schedule, (d) delivery status is tracked in the `webhook_deliveries` table. | Webhook delivery logs, retry evidence | Quarterly |

---

## 16. Test Execution Record Template

Each test execution must be documented using the following template:

```
Test Execution Record
=====================
Test ID:         [e.g., CC5.1-01]
Test Date:       [YYYY-MM-DD]
Tester:          [Name and role]
Environment:     [Production / Staging]
Test Procedure:  [As defined above, with any deviations noted]

Result:          [PASS / FAIL / PARTIAL]

Evidence Collected:
- [File/screenshot/log reference 1]
- [File/screenshot/log reference 2]

Observations:
[Any notable findings, even if the test passed]

Remediation Required:  [Yes / No]
Remediation Details:   [If yes, describe required action]
Remediation Owner:     [Name]
Remediation Deadline:  [YYYY-MM-DD]
Re-test Date:          [YYYY-MM-DD, if applicable]
```

---

## 17. Quarterly Test Execution Schedule

### Q1 (January -- March)

| Week | Tests |
|------|-------|
| Week 1 | CC5.1-01 through CC5.1-04 (Access control) |
| Week 2 | CC5.2-01 through CC5.2-03 (Logical access) |
| Week 3 | CC8.1-01 through CC8.1-05 (Transaction controls) |
| Week 4 | PI1.1-01 through PI1.1-05 (Processing integrity) |

### Q2 (April -- June)

| Week | Tests |
|------|-------|
| Week 1 | CC4.1-01 through CC4.1-04 (Monitoring) |
| Week 2 | CC6.1-01 through CC6.1-03 (Incident management) |
| Week 3 | CC6.2-01 through CC6.2-03 (Change management) |
| Week 4 | C1.1-01 through C1.1-05 (Confidentiality) |

### Q3 (July -- September)

| Week | Tests |
|------|-------|
| Week 1 | CC3.1-01 through CC3.2-02 (Risk assessment) |
| Week 2 | CC7.1-01 through CC7.3-02 (Access controls) |
| Week 3 | A1.1-01 through A1.2-01 (Availability) |
| Week 4 | CC1.1-01 through CC1.5-02 (Control environment) |

### Q4 (October -- December)

| Week | Tests |
|------|-------|
| Week 1 | CC2.1-01 through CC2.3-02 (Communication) |
| Week 2 | CC9.1-01 through CC9.1-03 (External communication) |
| Week 3 | CC8.2-01 through CC8.2-02 (Third-party risk) |
| Week 4 | PI1.2-01 through PI1.2-02 (Error handling) + Annual tests |

---

## 18. Annual Tests

The following tests are executed once per year, typically in Q4:

- CC1.1-01: Code of conduct acknowledgment
- CC1.1-03: Security-first culture interviews
- CC1.2-02: Security budget allocation
- CC2.1-01: Security awareness training
- CC2.1-03: Policy documentation accessibility
- CC2.3-02: Incident communication templates
- CC3.1-01: Threat model review
- CC5.1-03: MPC key isolation
- CC7.2-01: Cloud provider physical security
- CC8.2-01: Vendor security review
- CC9.1-01: Privacy policy
- CC9.1-02: Terms of service
- A1.1-02: Disaster recovery test
- C1.1-01: Encryption at rest
- C1.1-03: PII handling
- C1.1-05: Data classification

---

## 19. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-11 | Compliance / Engineering | Initial release |
