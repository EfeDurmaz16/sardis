# SOC 2 Type II Readiness Assessment

**Last updated:** March 2026
**Target completion:** Q3 2026

## Current Control Status

### Security (Trust Service Criteria)

| Control | Status | Evidence |
|---------|--------|----------|
| Access control (authentication) | Implemented | Argon2 password hashing, JWT with JTI revocation, API key SHA-256 hashing |
| Multi-factor authentication | Implemented | TOTP-based MFA via pyotp |
| Role-based access control | Implemented | Owner/admin/member/viewer roles, org-scoped data isolation |
| Encryption in transit | Implemented | TLS 1.3 with HSTS (1yr, includeSubDomains, preload) |
| Encryption at rest | Implemented | AES-256 via cloud provider (Neon PostgreSQL, GCP) |
| Rate limiting | Implemented | Per-IP and per-org, Redis-backed with in-memory fallback |
| Secret scanning | Implemented | Gitleaks in CI on every push |
| Vulnerability scanning | Implemented | Trivy (containers), pip-audit (dependencies), Bandit (SAST) |
| Webhook verification | Implemented | HMAC-SHA256 with 5-minute replay window |
| SSRF prevention | Implemented | Webhook URL validation blocks private IPs, metadata endpoints |
| Kill switch | Implemented | Multi-scope emergency stop (global, org, agent, rail, chain) |
| Input validation | Implemented | Pydantic models, parameterized SQL queries throughout |
| Security headers | Implemented | CSP, X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy |

### Availability

| Control | Status | Evidence |
|---------|--------|----------|
| Health checks | Implemented | Multi-level: liveness, readiness, deep component checks |
| Monitoring | Implemented | Prometheus metrics (50+), Cloud Run alerting |
| Graceful shutdown | Implemented | 30-second drain period, readiness probe returns 503 |
| Circuit breakers | Implemented | Per-service with configurable thresholds |
| Retry logic | Implemented | Exponential backoff with jitter (MPC, RPC, DB, webhooks) |
| Incident response | Documented | Severity-based response times (P0: 30min, P1: 2hr) |
| Uptime target | Documented | 99.9% monthly target |
| Backup | Partial | Neon managed backups; no restore testing documented |

### Processing Integrity

| Control | Status | Evidence |
|---------|--------|----------|
| Idempotency | Implemented | DB unique constraints on idempotency_key |
| Concurrency safety | Implemented | SELECT FOR UPDATE on spending, payments |
| Audit trail | Implemented | Append-only ledger with Merkle anchoring |
| Policy enforcement | Implemented | 12-check pipeline, fail-closed |
| Transaction integrity | Implemented | Platform fee calculation with min threshold |

### Confidentiality

| Control | Status | Evidence |
|---------|--------|----------|
| Data classification | Implemented | PII classification tables in DB (migration 042) |
| Log masking | Implemented | Sensitive headers/params masked in structured logs |
| API key display | Implemented | Prefix-only display, full key shown once at creation |
| Credential storage | Implemented | Never stored in plaintext (Argon2/SHA-256/Fernet) |
| Data retention | Documented | Accounts 3yr, transactions 7yr, KYC 5-7yr |

### Privacy

| Control | Status | Evidence |
|---------|--------|----------|
| Privacy policy | Published | GDPR/CCPA compliant, updated Jan 2026 |
| Data export (GDPR Art. 20) | Implemented | POST /account/export with real DB queries |
| Account deletion (GDPR Art. 17) | Implemented | DELETE /auth/account with cascading delete |
| Consent management | Implemented | Terms acceptance on signup |
| DPA availability | Documented | Available on request via legal@sardis.sh |
| Subprocessor list | Published | 9 subprocessors listed in Trust Center |

## Gaps to Address Before Audit

### High Priority
1. **Backup restore testing** — Need documented restore procedure and quarterly testing
2. **Formal risk assessment** — Need written risk register with likelihood/impact matrix
3. **Employee onboarding/offboarding** — Need documented procedures (N/A for solo founder, needed at first hire)
4. **Change management policy** — Need formal change approval process (currently PR-based)
5. **Vendor management** — Need documented review process for subprocessors

### Medium Priority
6. **Penetration testing** — Need external pentest report (schedule for Q2 2026)
7. **Business continuity plan** — Need documented BCP with RTO/RPO targets
8. **Access review** — Need quarterly access review process
9. **Security awareness training** — Need documented training (N/A solo, needed at hire)
10. **Incident post-mortem template** — Need standardized post-incident review

## Recommended Platform

Use **Vanta** or **Drata** for automated evidence collection:
- Both integrate with GCP, GitHub, PostgreSQL
- Continuous monitoring of controls
- Automated evidence collection for 80%+ of criteria
- Auditor marketplace for Type II engagement

## Timeline

| Month | Milestone |
|-------|-----------|
| March 2026 | Internal readiness assessment (this document) |
| April 2026 | Sign up for Vanta/Drata, begin evidence collection |
| May 2026 | Write formal policies (using platform templates) |
| June 2026 | Remediate gaps, schedule pentest |
| July 2026 | Engage auditor for Type II observation period |
| Sept 2026 | Type II report issued (3-month observation window) |
