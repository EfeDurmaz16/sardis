# SOC 2 Evidence Collection Automation

**Document ID:** SARDIS-SOC2-ECA-001
**Version:** 1.0
**Effective Date:** 2026-03-11
**Last Reviewed:** 2026-03-11
**Owner:** Compliance / Engineering
**Classification:** Internal

---

## 1. Purpose

This document defines the automated, semi-automated, and manual processes for collecting SOC 2 audit evidence within the Sardis platform. The goal is to enable continuous compliance monitoring rather than relying solely on point-in-time audits, reducing evidence collection burden and increasing audit confidence.

## 2. Scope

Evidence collection covers all controls in the Sardis SOC 2 Evidence Matrix (`evidence-matrix.md`) and all test procedures in the Control Testing Procedures (`control-testing-procedures.md`). This includes Security (CC1--CC9), Availability (A1), Confidentiality (C1), and Processing Integrity (PI1) Trust Service Categories.

## 3. Evidence Retention Policy

All evidence follows the retention schedule defined in the Data Retention Policy (`data-retention-policy.md`):

| Evidence Type | Retention Period |
|---------------|-----------------|
| Transaction audit trail (sardis-ledger) | 7 years |
| Compliance records (KYC, SAR, sanctions) | Account lifetime + 5 years |
| API access logs | 5 years |
| Policy enforcement logs | 5 years |
| CI/CD pipeline results | 5 years |
| Health check results | 1 year rolling |
| Error rate metrics | 1 year rolling |
| Rate limit enforcement logs | 90 days rolling |
| Test execution records | 5 years |

---

## 4. Evidence Categories

### 4.1 Category 1: Fully Automated (No Manual Intervention)

These evidence streams are collected automatically by production systems. No human action is required to generate or store the evidence.

| Evidence | Source System | Collection Method | Frequency | Storage Location | Retention |
|----------|-------------|-------------------|-----------|-----------------|-----------|
| API access logs | Vercel / Cloud Run | Built-in request logging pipeline; structured JSON logs forwarded to log aggregator | Real-time | Log aggregation store (Datadog/Grafana) | 5 years |
| Transaction audit trail | sardis-ledger (`packages/sardis-ledger/`) | PostgreSQL append-only table; every payment, policy decision, and settlement event is recorded | Real-time | Neon PostgreSQL `ledger_entries` table | 7 years |
| Health check results | `/api/v2/health` endpoint (`sardis_api/health.py`) | Cron job hits deep health check every 5 minutes; response stored in monitoring database | Every 5 min | Monitoring database / time-series store | 1 year rolling |
| CI/CD pipeline results | GitHub Actions (`.github/workflows/ci.yml`) | GitHub stores all workflow runs with logs, artifacts, and status | Per PR/push | GitHub (native retention) + quarterly export to evidence repo | 5 years |
| Error rate metrics | Prometheus / application metrics | Application emits error counters; Prometheus scrapes and stores | Real-time | Prometheus / Grafana | 1 year rolling |
| Rate limit enforcement | sardis-guardrails (`rate_limiter.py`) | Redis records rate limit hits and blocks; Prometheus counter for 429 responses | Real-time | Redis (90-day TTL) + Prometheus counter | 90 days rolling |
| Policy enforcement decisions | spending_policy.py | Every policy evaluation (approve/deny) logged to PostgreSQL with full decision context | Real-time | Neon PostgreSQL `policy_decisions` table | 5 years |
| Sanctions screening results | sardis-compliance (`sanctions.py`) | Every screening query and result stored with entity identifiers and decision | Per screening | Neon PostgreSQL `sanctions_screenings` table | 5 years |
| KYC verification results | sardis-compliance (`kyc.py`) + iDenfy | Verification status, timestamps, and outcome stored; no raw documents retained beyond provider | Per verification | Neon PostgreSQL `kyc_verifications` table | Account lifetime + 5 years |
| SAR generation events | sardis-compliance (`sar.py`) | SAR creation, filing status, and metadata logged | Per event | Neon PostgreSQL `sar_records` table | 5 years |
| Webhook delivery status | sardis-api webhook engine | Each delivery attempt, response status, and retry recorded in `webhook_deliveries` table | Per event | Neon PostgreSQL `webhook_deliveries` table | 5 years |
| Replay protection events | Redis dedup store / mandate cache | Replay attempts recorded with timestamp, payload hash, and rejection reason | Per attempt | Redis (TTL-based) + PostgreSQL audit log | 5 years (PostgreSQL) |

### 4.2 Category 2: Semi-Automated (Script-Assisted)

These evidence streams require running a collection script. The scripts automate data extraction and formatting, but a human must trigger execution and review results.

| Evidence | Source | Collection Script | Frequency | Owner |
|----------|--------|-------------------|-----------|-------|
| PR review statistics | GitHub API | `scripts/collect-pr-evidence.py` | Monthly | Engineering Lead |
| Dependency vulnerability scan | `pip audit` / `npm audit` | CI pipeline + `scripts/collect-vuln-report.py` | Monthly | Engineering Lead |
| IAM access review | Vercel / Neon / GCP / Turnkey / Stripe consoles | `scripts/collect-access-evidence.py` | Quarterly | Compliance Officer |
| Secret rotation verification | Secrets Rotation Runbook records | `scripts/verify-secret-rotation.py` | Per rotation schedule | DevOps |
| Uptime report generation | Monitoring data | `scripts/collect-health-evidence.py` | Monthly | Engineering Lead |
| Deployment audit trail | Cloud Run / Vercel deployment history | `scripts/collect-deployment-evidence.py` | Monthly | Engineering Lead |

### 4.3 Category 3: Manual (Requires Human Action)

These evidence items cannot be automated and require direct human effort.

| Evidence | Description | Frequency | Owner | Deliverable |
|----------|-------------|-----------|-------|-------------|
| Quarterly compliance report | Compliance officer summary of control status, incidents, regulatory changes, and remediation progress | Quarterly | Compliance Officer | PDF report + meeting minutes |
| Annual risk assessment | Comprehensive risk identification and scoring review | Annual | Compliance Officer | Risk assessment document |
| Incident post-mortems | Post-incident review documenting root cause, timeline, impact, and corrective actions | Per incident | Engineering Lead | Post-mortem document |
| Policy acknowledgments | Team member sign-off confirming review of security policies | Annual | Compliance Officer | Signed acknowledgment records |
| Third-party risk assessments | Security review of critical vendors (Turnkey, Stripe, Neon, Alchemy, iDenfy, Elliptic) | Annual | Compliance Officer | Vendor assessment reports |
| Code of conduct acknowledgments | Team member sign-off on code of conduct | Annual | Compliance Officer | Signed acknowledgment records |
| Tabletop exercise reports | Incident response drill documentation | Semi-annual | Engineering Lead | Drill report + lessons learned |
| DR test reports | Disaster recovery runbook execution results | Annual | Engineering Lead | DR test report with RTO/RPO measurements |
| Security awareness training records | Training completion tracking | Annual | Compliance Officer | Training completion roster |

---

## 5. Evidence Collection Scripts

### 5.1 `scripts/collect-pr-evidence.py`

**Purpose:** Extracts PR review statistics from the GitHub API for the specified period.

**Output data:**
- Total PRs merged in period
- PRs with at least 1 approval
- PRs with at least 2 approvals (security-sensitive changes)
- PRs with all CI checks passed at merge time
- PRs where CI checks were overridden or skipped (should be zero)
- Average time from PR open to first review
- Average time from PR open to merge
- List of security-sensitive PRs (touching `sardis-wallet`, `sardis-compliance`, `sardis-protocol`, `sardis-chain`, `authz.py`) with approval counts

**Output format:** JSON (machine-readable) + CSV (auditor-friendly)

**Usage:**
```bash
uv run python scripts/collect-pr-evidence.py \
  --repo sardis \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --output evidence-2026-Q1/change-management/
```

**Required environment variables:** `GITHUB_TOKEN` (read-only repo access)

### 5.2 `scripts/collect-health-evidence.py`

**Purpose:** Aggregates health check and availability data into an auditor-ready report.

**Output data:**
- Uptime percentage per component (database, Redis, Turnkey, Stripe, RPC, contracts, TAP JWKS, kill switch, compliance, webhooks)
- Overall service uptime percentage
- P50, P95, P99 response latency per critical endpoint
- Error rate by HTTP status code category (4xx, 5xx)
- Alert trigger history (alert name, trigger time, resolution time, duration)
- Downtime incidents with root cause and duration

**Output format:** JSON + PDF summary report

**Usage:**
```bash
uv run python scripts/collect-health-evidence.py \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --output evidence-2026-Q1/availability/
```

### 5.3 `scripts/collect-access-evidence.py`

**Purpose:** Exports IAM access data from infrastructure providers for least-privilege review.

**Output data:**
- Active API keys: key prefix (first 8 chars of hash), creation date, last-used date, associated principal, permission scope
- Admin user list: user ID, role, last login, MFA status
- Role assignments: principal-to-role mappings with effective permissions
- Access revocation log: revoked keys/users with revocation date and reason
- Service account inventory: service accounts, their purpose, and permission scope

**Output format:** JSON + CSV

**Usage:**
```bash
uv run python scripts/collect-access-evidence.py \
  --output evidence-2026-Q1/access-control/
```

**Note:** This script queries the Sardis database for API key and principal data. Cloud provider IAM (Vercel, Neon, GCP) must be exported manually from each provider's console and placed in the same output directory.

### 5.4 `scripts/collect-vuln-report.py`

**Purpose:** Runs dependency vulnerability scans across all packages and generates a consolidated report.

**Output data:**
- Vulnerability ID, severity, affected package, installed version, fixed version
- Days open (since first detected)
- Remediation status (open, in-progress, resolved, accepted-risk)
- Accepted risk entries with justification

**Output format:** JSON + CSV

**Usage:**
```bash
uv run python scripts/collect-vuln-report.py \
  --output evidence-2026-Q1/risk-assessment/
```

### 5.5 `scripts/verify-secret-rotation.py`

**Purpose:** Cross-references secret rotation timestamps against the required schedule from the Secrets Rotation Runbook.

**Output data:**
- Secret identifier (name, not value), classification (Critical/High/Standard)
- Required rotation cadence (30/90/180 days)
- Last rotation date
- Next rotation due date
- Compliance status (compliant / overdue / approaching deadline)

**Output format:** JSON + CSV

**Usage:**
```bash
uv run python scripts/verify-secret-rotation.py \
  --output evidence-2026-Q1/access-control/
```

### 5.6 `scripts/collect-deployment-evidence.py`

**Purpose:** Extracts production deployment history from Cloud Run and Vercel.

**Output data:**
- Deployment timestamp
- Deployer identity
- Commit SHA and PR reference
- Deployment target (service, region)
- Deployment status (success/rollback)
- Associated change management ticket/PR

**Output format:** JSON + CSV

**Usage:**
```bash
uv run python scripts/collect-deployment-evidence.py \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --output evidence-2026-Q1/change-management/
```

---

## 6. Evidence Package Structure

Each quarter, evidence is assembled into a standardized package for auditor review. The package follows this directory structure:

```
evidence-package-YYYY-QN/
├── README.md                              # Package manifest with collection dates and summary
├── access-control/
│   ├── api-key-audit.csv                  # Active API keys (hashed, with metadata)
│   ├── iam-review-vercel.csv              # Vercel IAM export
│   ├── iam-review-neon.csv                # Neon IAM export
│   ├── iam-review-gcp.csv                 # GCP Cloud Run IAM export
│   ├── iam-review-turnkey.csv             # Turnkey access export
│   ├── iam-review-stripe.csv              # Stripe IAM export
│   ├── admin-access-log.csv               # Admin action audit log
│   ├── access-revocation-log.csv          # Revoked keys/users
│   ├── secret-rotation-status.csv         # Secret rotation compliance
│   └── service-account-inventory.csv      # Service account listing
├── change-management/
│   ├── pr-review-stats.csv                # PR review statistics
│   ├── pr-review-stats.json               # Machine-readable PR data
│   ├── security-sensitive-prs.csv         # PRs touching security-critical packages
│   ├── ci-pipeline-configuration.yml      # CI pipeline config snapshot
│   ├── branch-protection-rules.json       # GitHub branch protection export
│   └── deployment-log.csv                 # Production deployment history
├── monitoring/
│   ├── health-check-report.pdf            # Uptime and health summary
│   ├── health-check-data.json             # Raw health check data
│   ├── error-rate-analysis.csv            # Error rates by category
│   ├── alert-history.json                 # Alert trigger and resolution log
│   └── latency-percentiles.csv            # P50/P95/P99 latency data
├── compliance/
│   ├── sar-filing-summary.csv             # SAR generation and filing status
│   ├── kyc-verification-stats.csv         # KYC verification outcomes
│   ├── sanctions-screening-log.csv        # Sanctions screening decisions
│   ├── policy-enforcement-summary.csv     # Policy approve/deny statistics
│   └── risk-scoring-distribution.csv      # Risk score distribution
├── availability/
│   ├── uptime-report.pdf                  # Availability summary
│   ├── uptime-data.json                   # Raw uptime data
│   ├── incident-log.csv                   # Downtime incidents with RCA
│   └── capacity-utilization.csv           # Resource utilization data
├── confidentiality/
│   ├── encryption-configuration.json      # TLS and at-rest encryption evidence
│   ├── ssl-scan-results.pdf               # SSL Labs scan report
│   ├── gitleaks-scan-report.json          # Secret scanning results
│   └── data-retention-compliance.csv      # Retention schedule adherence
├── processing-integrity/
│   ├── idempotency-test-results.json      # Idempotency validation evidence
│   ├── replay-protection-test.json        # Replay protection validation
│   ├── ledger-integrity-test.json         # Append-only ledger validation
│   └── webhook-delivery-stats.csv         # Webhook delivery reliability
├── risk-assessment/
│   ├── vulnerability-scan-report.csv      # Dependency vulnerability scan
│   ├── accepted-risks.csv                 # Accepted risk register
│   └── threat-model-review.md             # Threat model review notes
├── governance/
│   ├── quarterly-compliance-report.pdf    # Compliance officer report
│   ├── policy-acknowledgments.csv         # Team policy sign-off records
│   └── training-completion.csv            # Security training records
└── test-records/
    ├── CC5.1-01-YYYY-MM-DD.md             # Individual test execution records
    ├── CC5.1-02-YYYY-MM-DD.md
    └── ...                                # One file per test execution
```

---

## 7. Auditor Access Portal

### 7.1 Read-Only Dashboard Access

During audit periods, auditors receive time-limited, read-only access to the following resources. Access is provisioned via dedicated auditor accounts with MFA required and expires automatically at the end of the audit engagement.

| Resource | Access Method | Data Scope | PII Handling |
|----------|--------------|------------|--------------|
| Transaction audit logs | Read-only database view (`v_auditor_ledger`) | All transactions, sanitized | Wallet addresses truncated, no personal identifiers |
| Health monitoring dashboard | Grafana read-only role | Current + historical health data | No PII present |
| CI/CD pipeline results | GitHub read-only collaborator | PR reviews, CI runs, deployments | Author names visible (public GitHub data) |
| Policy enforcement logs | Read-only database view (`v_auditor_policy`) | All policy decisions | Agent IDs only, no personal identifiers |
| SAR filing status | Read-only database view (`v_auditor_sar_meta`) | Filing metadata only | No SAR content, no subject identifiers |
| Error and alert history | Grafana read-only role | Alert triggers, durations, resolutions | No PII present |

### 7.2 Access Provisioning Process

1. Compliance officer receives auditor engagement letter with named auditors.
2. Compliance officer creates time-limited auditor accounts (maximum 90-day expiry).
3. Auditors complete MFA enrollment.
4. Access is limited to read-only views with no export of raw PII.
5. All auditor access is logged in the access audit trail.
6. Accounts are automatically disabled at expiry; compliance officer confirms deprovisioning.

### 7.3 Evidence Package Delivery

The quarterly evidence package is delivered to the auditor via:
1. **Primary:** Secure file share (encrypted ZIP, password communicated out-of-band).
2. **Secondary:** Direct access to the evidence repository (read-only, time-limited).
3. All evidence transfers are logged with timestamp, recipient, and content manifest.

---

## 8. Continuous Compliance Monitoring

### 8.1 Real-Time Controls

These controls are monitored continuously in production. Violations trigger automated responses.

| Control | Monitoring Mechanism | Alert Threshold | Automated Response | Escalation |
|---------|---------------------|-----------------|-------------------|------------|
| Unauthorized access attempts | API authentication failure counter | >10 failures/min from same IP | Auto-block IP for 15 min | Alert to on-call engineer |
| Potential data exfiltration | Database query volume monitoring | >1000 record reads/min from single principal | Rate limit applied | Alert to security lead |
| Service degradation | Health check endpoint | Any component unhealthy for >5 min | PagerDuty alert | P1 incident if >15 min |
| Policy bypass attempt | Policy engine audit log | Any transaction bypassing policy evaluation | Block transaction + alert | Immediate security review |
| Spending limit breach | Policy enforcement decision | Any approved transaction exceeding configured limit | Should not occur (fail-closed) | P0 incident |
| Kill switch state change | Kill switch toggle monitoring | Any activation/deactivation | Log + alert all engineers | Compliance officer notification |
| Sanctions match | Sanctions screening module | Any positive match | Block transaction | SAR review process |
| Secret in codebase | Gitleaks CI check | Any secret detected in PR | Block merge | Engineering lead notification |

### 8.2 Weekly Compliance Summary

An automated weekly summary is generated and sent to the compliance officer every Monday at 09:00 UTC. The summary includes:

- **Transaction volume:** Total transactions processed, total value, by currency and chain
- **Suspicious activity:** Count of elevated risk scores, SAR filings initiated, sanctions matches
- **KYC activity:** New verifications completed, failures, pending reviews
- **Policy enforcement:** Total evaluations, approve/deny ratio, top denial reasons
- **System health:** Uptime percentage, P99 latency, error rate
- **Alerts:** Outstanding alerts requiring review, new alerts triggered
- **Incidents:** Open incidents with severity and age, incidents closed this week
- **Access events:** New API keys created, keys revoked, admin actions performed

**Generation script:** `scripts/generate-weekly-compliance-summary.py`

**Delivery:** Email to compliance officer distribution list + stored in evidence repository.

### 8.3 Monthly Compliance Dashboard

A monthly dashboard view provides trend analysis:

- Transaction volume trends (month-over-month)
- Policy denial rate trends
- Error rate trends
- Uptime trends
- Open deficiency count and aging
- Secret rotation compliance status
- Vulnerability scan status

---

## 9. Automation Roadmap

### Currently Implemented

- Transaction audit trail (sardis-ledger, append-only)
- Policy enforcement logging
- Health check endpoint with 10+ component checks
- CI/CD pipeline with ruff, mypy, pytest, gitleaks
- Rate limiting with Redis enforcement
- Webhook delivery tracking with `event_id` deduplication
- KYC and sanctions screening result logging
- SAR generation event logging

### Planned (Q2 2026)

- Centralized log aggregation (Datadog or Grafana Cloud)
- Automated weekly compliance summary email
- Evidence collection scripts (PR stats, health report, access audit, vulnerability report)
- Auditor read-only database views
- Automated evidence package assembly script

### Future (Q3-Q4 2026)

- SIEM integration for security event correlation
- Automated control testing for Category 1 automated tests (CC5.1-01, CC5.2-02, PI1.1-01)
- Compliance dashboard (real-time view of all control statuses)
- Automated third-party certificate tracking (vendor SOC 2 expiry alerts)
- Machine learning anomaly detection on transaction patterns

---

## 10. Responsibilities

| Role | Responsibilities |
|------|-----------------|
| **Compliance Officer** | Own evidence collection schedule, review all evidence packages, manage auditor relationship, deliver quarterly reports, maintain manual evidence |
| **Engineering Lead** | Run semi-automated collection scripts, review technical evidence for accuracy, own incident post-mortems, maintain collection scripts |
| **DevOps** | Maintain log aggregation pipeline, manage auditor access provisioning, ensure monitoring infrastructure availability, run secret rotation verification |
| **All Engineers** | Ensure audit logging is not bypassed in code changes, complete security training, acknowledge policies |

---

## 11. Evidence Collection Calendar

| Month | Automated | Semi-Automated | Manual |
|-------|-----------|----------------|--------|
| January | Continuous | PR evidence, health report, deployment log | Q4 compliance report |
| February | Continuous | Vulnerability scan | -- |
| March | Continuous | PR evidence, health report, deployment log | Q1 IAM review |
| April | Continuous | PR evidence, health report, deployment log | Q1 compliance report |
| May | Continuous | Vulnerability scan | -- |
| June | Continuous | PR evidence, health report, deployment log | Q2 IAM review, tabletop exercise |
| July | Continuous | PR evidence, health report, deployment log | Q2 compliance report |
| August | Continuous | Vulnerability scan | -- |
| September | Continuous | PR evidence, health report, deployment log | Q3 IAM review |
| October | Continuous | PR evidence, health report, deployment log | Q3 compliance report, annual risk assessment |
| November | Continuous | Vulnerability scan, full gitleaks history scan | Annual policy acknowledgments, training |
| December | Continuous | PR evidence, health report, deployment log | Q4 IAM review, vendor assessments, DR test |

---

## 12. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-11 | Compliance / Engineering | Initial release |
