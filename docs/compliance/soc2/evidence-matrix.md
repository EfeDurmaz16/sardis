# SOC 2 Evidence Matrix

**Document ID:** SARDIS-SOC2-EM-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Compliance / Engineering
**Classification:** Internal

---

## 1. Purpose

This document maps SOC 2 Type II Trust Service Criteria (TSC) to the specific controls, evidence sources, and implementation details within the Sardis platform. It serves as the primary reference for auditors to locate evidence of control effectiveness.

## 2. Trust Service Categories

Sardis targets the following Trust Service Categories for SOC 2 Type II:

- **Security** (Common Criteria CC1-CC9) — Required for all SOC 2 reports
- **Availability** (A1) — Critical for a financial infrastructure platform
- **Confidentiality** (C1) — Customer financial data and PII protection
- **Processing Integrity** (PI1) — Accuracy of payment processing

## 3. Common Criteria Mapping

### CC1: Control Environment

The control environment establishes the foundation for all other controls through organizational commitment to integrity, ethical values, and competence.

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC1.1 — Commitment to integrity and ethical values | Code of conduct, security-first architecture principles | `CLAUDE.md` (Architecture Principles section) | Non-custodial-first, fail-closed, audit-everything principles documented and enforced in code |
| CC1.2 — Board oversight | Engineering leadership review of security controls | Change Management Policy, PR review logs | All security-sensitive changes require 2 approvals |
| CC1.3 — Organizational structure | Team roles, on-call rotation, escalation matrix | Incident Response Plan (Section 5) | Defined IC, Technical Lead, Communications Lead roles |
| CC1.4 — Commitment to competence | Code review standards, CI enforcement | `.github/workflows/ci.yml` | Automated lint (ruff), type checking, test suites |
| CC1.5 — Accountability | Audit logging, admin action tracking | `packages/sardis-api/src/sardis_api/audit_log.py` | All admin actions logged with user ID, timestamp, action details |

### CC2: Communication and Information

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC2.1 — Internal communication of security objectives | Architecture documentation, project configuration | `CLAUDE.md`, `docs/` directory | Security considerations, architecture principles documented in repository root |
| CC2.2 — Internal communication of security policies | Policy documentation, onboarding materials | `docs/compliance/soc2/` (this directory) | Complete SOC 2 policy suite, incident response plan, change management policy |
| CC2.3 — External communication | Customer-facing API documentation, status page | `/api/v2/docs` (OpenAPI), incident communication templates | Incident Response Plan includes customer notification templates (Section 9) |

### CC3: Risk Assessment

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC3.1 — Risk objectives | Security architecture, threat model | `CLAUDE.md` (Security Considerations), TDD Remediation design doc | Non-custodial architecture, fail-closed defaults, MPC custody |
| CC3.2 — Risk identification | Threat modeling, dependency scanning, secret scanning | `.github/workflows/secret-scan.yml`, gitleaks CI | Gitleaks runs on every push/PR; dependency vulnerabilities tracked |
| CC3.3 — Fraud risk | Spending policy engine, sanctions screening, KYC | `packages/sardis-core/src/sardis_v2_core/spending_policy.py`, `packages/sardis-compliance/` | 12-step policy evaluation pipeline: amount limits, scope checks, MCC filtering, merchant rules, goal drift detection, KYA attestation |
| CC3.4 — Change risk | Change management process, CI gates | `.github/workflows/ci.yml`, Change Management Policy | All changes must pass CI; security-sensitive changes require 2 approvals + threat assessment |

### CC4: Monitoring Activities

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC4.1 — Ongoing monitoring | Health checks, operational alerts | `packages/sardis-api/src/sardis_api/health.py`, `packages/sardis-api/src/sardis_api/operational_alerts.py` | Deep health check monitors 10+ components: database, Redis, Turnkey, Stripe, RPC, contracts, TAP JWKS, kill switch, compliance, webhooks |
| CC4.2 — Deficiency evaluation | Post-incident reviews, audit log analysis | Incident Response Plan (Phase 6) | Post-incident review required for all P0/P1 incidents within 72 hours |

### CC5: Control Activities

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC5.1 — Risk mitigation controls | Spending policy engine | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` | **12-step evaluation pipeline:** (1) Amount validation, (2) Scope check, (3) MCC check, (4) Per-transaction limit, (5) Total limit, (6) Time-window limits (daily/weekly/monthly), (7) On-chain balance, (8) Merchant rules, (9) Goal drift, (10) Merchant trust, (11) Approval threshold, (12) KYA attestation |
| CC5.1 | Kill switch / emergency controls | `packages/sardis-api/src/sardis_api/kill_switch_dep.py`, `packages/sardis-api/src/sardis_api/routers/emergency.py` | Multi-scope kill switch (global, org, agent, rail, chain); emergency freeze-all endpoint freezes all wallets + activates global kill switch |
| CC5.1 | Rate limiting | `packages/sardis-api/src/sardis_api/main.py`, Redis-backed rate limiter | Standard: 100 req/min; Admin: 10 req/min; Sensitive admin (freeze-all): 5 req/min |
| CC5.2 — Technology controls | Automated CI/CD, infrastructure-as-code | `.github/workflows/ci.yml`, `.github/workflows/deploy.yml` | CI runs on every push/PR: ruff lint, pytest, forge test, TypeScript type check, gitleaks |
| CC5.3 — Policy deployment | Policy enforcement before execution | `packages/sardis-core/src/sardis_v2_core/orchestrator.py` | PaymentOrchestrator enforces policy evaluation as Phase 1 before any chain execution; chain_executor is private in DI |

### CC6: Logical and Physical Access Controls

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC6.1 — Logical access security | API key authentication (SHA-256 hashed), JWT tokens | `packages/sardis-api/src/sardis_api/authz.py`, `packages/sardis-api/src/sardis_api/middleware/auth.py` | Dual auth model: API keys (SHA-256 hashed in DB, never stored plaintext) + JWT tokens; `require_principal` dependency enforces auth on all protected endpoints |
| CC6.2 — User authentication | Principal model, MFA for admin | `packages/sardis-api/src/sardis_api/authz.py` (Principal dataclass) | `Principal.kind` = "api_key" or "jwt"; `Principal.is_admin` checks scope or role; MFA enforcement via `require_mfa_if_enabled` dependency on emergency endpoints |
| CC6.3 — Credential management | Key hashing, rotation, secret scanning | Secrets Rotation Runbook, `.github/workflows/secret-scan.yml` | API keys SHA-256 hashed; agent keys support rotation with grace periods (`packages/sardis-core/src/sardis_v2_core/key_rotation.py`); gitleaks prevents credential exposure |
| CC6.4 — Access restriction | RBAC, scoped API keys | `packages/sardis-api/src/sardis_api/authz.py` | API keys carry scopes (e.g., "payments", "wallets", "admin"); `Principal.is_admin` checks for "admin" or "*" scope; anonymous access restricted to loopback addresses in dev only |
| CC6.5 — Data disposal | Retention policies, automated purge | Data Retention Policy | PII: account lifetime + 30 days; API logs: 90 days; sessions: 24 hours TTL in Redis |
| CC6.6 — MPC custody (non-custodial) | Turnkey MPC wallets | `packages/sardis-wallet/`, Turnkey integration | Private keys never stored by Sardis; MPC key shares managed by Turnkey; wallet operations require Turnkey API authentication |
| CC6.7 — Wallet isolation | Per-agent wallet segregation | `packages/sardis-wallet/src/sardis_wallet/manager.py` | Each agent has isolated wallet(s); Safe Smart Accounts v1.4.1 with Zodiac Roles module for policy enforcement |
| CC6.8 — Network security | TLS, CORS restrictions | API middleware, Vercel/Cloud Run TLS termination | TLS 1.3 enforced; CORS restricted to `checkout.sardis.sh` and configured origins; `embed_origin` per-merchant restriction |

### CC7: System Operations

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC7.1 — Detection of anomalies | Health monitoring, audit trail | `packages/sardis-api/src/sardis_api/health.py` | Deep health check covers: API, database (latency), cache (Redis), TAP JWKS, kill switch, Stripe, Turnkey, RPC, contracts, compliance, webhooks |
| CC7.2 — Incident monitoring | Operational alerts, log analysis | `packages/sardis-api/src/sardis_api/operational_alerts.py` | Automated alerting on error rate thresholds, latency spikes, health check failures |
| CC7.3 — Security event evaluation | Incident severity classification | Incident Response Plan (Section 3) | P0-P3 severity levels with defined response times, escalation matrix, resolution targets |
| CC7.4 — Incident response | Documented response procedures | Incident Response Plan | 6-phase process: Detection, Classification, Containment, Eradication, Recovery, Post-incident review |
| CC7.5 — Incident communication | Internal and external notification | Incident Response Plan (Section 9) | Templates for internal alerts, customer communication, regulatory notifications |

### CC8: Change Management

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC8.1 — Change authorization | PR review requirements | Change Management Policy, GitHub branch protection | `main` branch protected; standard changes: 1 approval; security-sensitive: 2 approvals |
| CC8.1 | CI gates | `.github/workflows/ci.yml` | 7 CI jobs: Python lint+test, idempotency E2E, contracts gas ceiling, contracts strict, TypeScript SDK, dashboard build, landing build |
| CC8.1 | Secret scanning | `.github/workflows/secret-scan.yml` | Gitleaks v2 runs on every push/PR with full git history scan (`fetch-depth: 0`) |
| CC8.2 — Change testing | Staging validation | `.github/workflows/deploy.yml` | Staging deployment includes: release gate (webhook conformance), database migration, Vercel deploy, automated health check |
| CC8.3 — Change deployment | Controlled deployment process | `.github/workflows/deploy.yml` | Staging -> Production pipeline; production requires manual workflow dispatch; health check post-deploy |

### CC9: Risk Mitigation

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| CC9.1 — Compliance controls | KYC verification, sanctions screening | `packages/sardis-compliance/` | iDenfy for KYC; Elliptic for AML/sanctions; compliance engine fail-closed in production |
| CC9.1 | Spending policy engine | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` | TrustLevel tiers (LOW/MEDIUM/HIGH/UNLIMITED), per-transaction limits, time-window caps, merchant allowlists/blocklists, MCC filtering |
| CC9.1 | Agent identity verification | `packages/sardis-protocol/`, TAP protocol | Ed25519 and ECDSA-P256 identity verification; AGIT fail-closed by default (`SARDIS_AGIT_FAIL_OPEN` override for dev) |
| CC9.2 — Vendor risk management | Third-party service monitoring | `packages/sardis-api/src/sardis_api/health.py` | Health check monitors all external dependencies (Turnkey, Stripe, Alchemy, TAP JWKS); degraded status reported if any vendor is unhealthy |

## 4. Availability Criteria (A1)

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| A1.1 — Availability commitment | Service architecture, health monitoring | `packages/sardis-api/src/sardis_api/health.py` | Liveness probe (`/health/live`), readiness probe (`/ready`), deep health check (`/health`) with component-level status |
| A1.2 — Recovery objectives | RTO/RPO targets | Disaster Recovery Runbook | RTO: 4 hours, RPO: 1 hour; Neon PITR for database; Cloud Run revision rollback for API |
| A1.3 — Recovery testing | Disaster recovery drills | Disaster Recovery Runbook (Section 6) | Monthly: database restore drill, kill switch drill, freeze-all drill; Quarterly: API failover test; Annually: full recovery simulation |

## 5. Confidentiality Criteria (C1)

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| C1.1 — Confidential data identification | Data classification, retention policy | Data Retention Policy | 7 data categories classified with specific retention periods and handling requirements |
| C1.2 — Confidential data disposal | Automated purge, cryptographic erasure | Data Retention Policy (Section 5) | PII: cryptographic erasure after account deletion + 30 days; API logs: 90-day TTL; sessions: 24-hour Redis TTL |

## 6. Processing Integrity Criteria (PI1)

| Criterion | Control | Evidence Source | Implementation |
|-----------|---------|----------------|----------------|
| PI1.1 — Processing completeness and accuracy | Append-only ledger, idempotency | `packages/sardis-ledger/src/sardis_ledger/engine.py`, idempotency E2E tests | Ledger engine with row-level locking, batch processing, optimistic concurrency; DB-level `idempotency_key` unique constraint prevents duplicate payments; `SELECT ... FOR UPDATE NOWAIT` prevents double-pay race |
| PI1.2 — Processing validation | Policy evaluation, mandate verification | `packages/sardis-core/src/sardis_v2_core/spending_policy.py`, `packages/sardis-protocol/src/sardis_v2_protocol/ap2.py` | Full AP2 mandate chain verification (Intent -> Cart -> Payment) before execution; 12-step spending policy evaluation |
| PI1.3 — Error handling | Fail-closed design, circuit breakers | `packages/sardis-core/src/sardis_v2_core/circuit_breaker.py` | Fail-closed default on all compliance/policy failures; circuit breakers on external service calls; AGIT defaults to fail-closed |

## 7. Evidence Collection Procedures

### Automated Evidence

| Evidence Type | Collection Method | Frequency | Retention |
|---------------|-------------------|-----------|-----------|
| CI/CD run logs | GitHub Actions workflow runs | Per commit/PR | GitHub default (400 days) |
| Health check results | `GET /health` endpoint | Continuous | Cloud Logging (90 days) |
| Audit log entries | `audit_log` table | Per event | Permanent |
| Emergency events | `emergency_freeze_events` table | Per event | Permanent |
| Secret scan results | Gitleaks workflow output | Per commit/PR | GitHub Actions logs |
| Code review records | GitHub PR reviews | Per PR | GitHub permanent |

### Manual Evidence

| Evidence Type | Collection Method | Frequency | Owner |
|---------------|-------------------|-----------|-------|
| Disaster recovery test results | Test execution report | Monthly/Quarterly/Annually | Infrastructure |
| Post-incident reviews | Review document | Per P0/P1 incident | Incident Commander |
| Policy review records | Review meeting notes | Annually | Compliance |
| Access review results | User/key access audit | Quarterly | Security |
| Vendor risk assessments | Assessment document | Annually | Compliance |

## 8. Control Gaps and Remediation

| Gap | Status | Remediation Plan | Target Date |
|-----|--------|------------------|-------------|
| Formal mypy type checking in CI | Planned | Add mypy check to CI pipeline | Q2 2026 |
| Automated database backup restore testing | Planned | Script monthly Neon PITR drill | Q2 2026 |
| Formal vendor risk assessment process | Planned | Create vendor assessment template and schedule | Q2 2026 |
| Status page for customer communication | Planned | Deploy status.sardis.sh | Q2 2026 |

## 9. Review Cadence

This evidence matrix is reviewed:

- **Quarterly** to verify evidence sources remain accurate
- **Annually** as part of the SOC 2 audit preparation
- **Upon material changes** to the platform architecture or controls

---

**Appendix A: Related Policy Documents**

| Document | Path |
|----------|------|
| Data Retention Policy | `docs/compliance/soc2/data-retention-policy.md` |
| Secrets Rotation Runbook | `docs/compliance/soc2/secrets-rotation-runbook.md` |
| Change Management Policy | `docs/compliance/soc2/change-management-policy.md` |
| Incident Response Plan | `docs/compliance/soc2/incident-response-plan.md` |
| Disaster Recovery Runbook | `docs/compliance/soc2/disaster-recovery-runbook.md` |
| Access Control Policy | `docs/compliance/soc2/access-control-policy.md` |

**Appendix B: Key Source Code References**

| Component | Path |
|-----------|------|
| Auth/authz | `packages/sardis-api/src/sardis_api/authz.py` |
| Emergency freeze | `packages/sardis-api/src/sardis_api/routers/emergency.py` |
| Kill switch | `packages/sardis-api/src/sardis_api/kill_switch_dep.py` |
| Health checks | `packages/sardis-api/src/sardis_api/health.py` |
| Spending policy | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` |
| Ledger engine | `packages/sardis-ledger/src/sardis_ledger/engine.py` |
| Key rotation | `packages/sardis-core/src/sardis_v2_core/key_rotation.py` |
| Audit logging | `packages/sardis-api/src/sardis_api/audit_log.py` |
| Operational alerts | `packages/sardis-api/src/sardis_api/operational_alerts.py` |
| CI pipeline | `.github/workflows/ci.yml` |
| Secret scanning | `.github/workflows/secret-scan.yml` |
| Deploy pipeline | `.github/workflows/deploy.yml` |
