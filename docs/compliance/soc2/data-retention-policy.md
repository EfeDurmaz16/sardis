# Data Retention Policy

**Document ID:** SARDIS-SOC2-DRP-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Engineering / Compliance
**Classification:** Internal

---

## 1. Purpose

This policy defines the data retention, archival, and disposal requirements for all data categories within the Sardis platform. It ensures compliance with applicable financial regulations, privacy laws, and SOC 2 Trust Service Criteria (specifically CC6.5 — disposal of confidential information and CC7.1 — detection of anomalies through log availability).

## 2. Scope

This policy applies to all data stored, processed, or transmitted by Sardis systems, including but not limited to:

- Sardis API (`packages/sardis-api`)
- PostgreSQL databases (Neon serverless)
- Redis caches (Upstash)
- Append-only audit ledger (`packages/sardis-ledger`)
- Blockchain transaction records
- Third-party service logs (Turnkey, Stripe Issuing, iDenfy, Elliptic)

## 3. Data Categories and Retention Periods

### 3.1 Transaction Logs

| Attribute | Value |
|-----------|-------|
| **Retention Period** | 7 years from transaction date |
| **Regulatory Basis** | Bank Secrecy Act (BSA), Anti-Money Laundering (AML), IRS record-keeping requirements |
| **Storage Location** | PostgreSQL (Neon) — `transactions`, `payment_executions`, `checkout_sessions` tables |
| **Backup** | Neon automated backups + point-in-time recovery |
| **Disposal Method** | Automated purge job with cryptographic verification of deletion |

Transaction logs include:

- Payment execution records (amount, currency, chain, token, status)
- AP2 mandate chains (intent, cart, payment)
- A2A payment records
- Checkout session data (post-settlement)
- On-chain transaction hashes and confirmations
- Settlement records and reconciliation data

### 3.2 Personally Identifiable Information (PII)

| Attribute | Value |
|-----------|-------|
| **Retention Period** | Account lifetime + 30 calendar days after account deletion |
| **Regulatory Basis** | GDPR Art. 17, CCPA, state privacy laws |
| **Storage Location** | PostgreSQL (Neon) — `users`, `organizations`, `kyc_verifications` tables |
| **Encryption** | AES-256 at rest (Neon encryption), TLS 1.3 in transit |
| **Disposal Method** | Cryptographic erasure; PII fields overwritten then rows purged |

PII includes:

- User names, email addresses, phone numbers
- Organization details and billing information
- KYC verification results (iDenfy reference IDs; raw KYC documents are NOT stored by Sardis — they are held by iDenfy per their retention policy)
- IP addresses associated with authentication events

**Deletion Process:**

1. Account deletion request received (API or dashboard)
2. Account marked as `pending_deletion` immediately
3. All active sessions and API keys revoked
4. 30-day grace period begins (allows for reversal)
5. After 30 days: PII fields cryptographically erased, non-PII transaction data anonymized and retained per Section 3.1

### 3.3 Audit Logs

| Attribute | Value |
|-----------|-------|
| **Retention Period** | Permanent (no scheduled deletion) |
| **Regulatory Basis** | SOC 2 CC7.2, financial audit requirements |
| **Storage Location** | Append-only ledger (`packages/sardis-ledger`), PostgreSQL `audit_log` table |
| **Integrity** | Row-level locking, optimistic concurrency control, on-chain anchoring via `SardisLedgerAnchor` contract |
| **Disposal Method** | Not applicable — permanent retention |

Audit logs include:

- All admin actions (`log_admin_action` in `packages/sardis-api/src/sardis_api/audit_log.py`)
- Emergency freeze/unfreeze events (`emergency_freeze_events` table)
- Kill switch activations and deactivations
- Policy evaluation decisions (allow/deny/approval-required)
- Key rotation events (`RotationEvent` in `packages/sardis-core/src/sardis_v2_core/key_rotation.py`)
- Authentication events (login, API key usage, MFA challenges)
- Configuration changes

**Immutability Guarantees:**

- The ledger engine (`packages/sardis-ledger/src/sardis_ledger/engine.py`) enforces append-only semantics with row-level locking
- Ledger entries are periodically anchored to on-chain state via `SardisLedgerAnchor` for tamper evidence
- Database role permissions prevent UPDATE or DELETE on audit tables

### 3.4 API Request Logs

| Attribute | Value |
|-----------|-------|
| **Retention Period** | 90 days from request timestamp |
| **Storage Location** | Cloud Run structured logging (Google Cloud Logging) |
| **Content** | Request method, path, response status, latency, requesting principal ID (no request/response bodies) |
| **Disposal Method** | Automatic expiry via Cloud Logging retention settings |

**Exclusions:** Request and response bodies are NOT logged. API keys appear only as hashed values (SHA-256). Sensitive headers (`Authorization`, `Cookie`) are redacted at the middleware layer.

### 3.5 Session Data

| Attribute | Value |
|-----------|-------|
| **Retention Period** | 24 hours from creation |
| **Storage Location** | Redis (Upstash) with TTL enforcement |
| **Content** | JWT session tokens, CSRF state, checkout session working state |
| **Disposal Method** | Automatic TTL expiry in Redis; no manual intervention required |

Session data includes:

- Authenticated user session tokens
- OAuth CSRF nonces
- In-progress checkout session state (pre-settlement)
- Rate limiter counters
- Kill switch state cache

### 3.6 Database Backups

| Attribute | Value |
|-----------|-------|
| **Retention Period** | 30 days from backup creation |
| **Storage Location** | Neon automated backup infrastructure |
| **Frequency** | Continuous (Neon point-in-time recovery with WAL streaming) |
| **Encryption** | Encrypted at rest by Neon infrastructure |
| **Disposal Method** | Automatic expiry per Neon retention window |

### 3.7 Blockchain Records

| Attribute | Value |
|-----------|-------|
| **Retention Period** | Permanent (immutable on-chain) |
| **Storage Location** | Public blockchain (Base, Ethereum, Polygon, Arbitrum, Optimism) |
| **Content** | Transaction hashes, wallet addresses, token transfer amounts, contract events |
| **Disposal Method** | Not applicable — blockchain data is immutable |

Note: Sardis does not store private keys. MPC key shares are managed by Turnkey in their non-custodial infrastructure and are subject to Turnkey's retention policies.

## 4. Retention Schedule Summary

| Data Category | Retention Period | Regulatory Driver |
|---------------|-----------------|-------------------|
| Transaction logs | 7 years | BSA/AML, IRS |
| PII | Account lifetime + 30 days | GDPR, CCPA |
| Audit logs | Permanent | SOC 2, financial audit |
| API request logs | 90 days | Operational, SOC 2 |
| Session data | 24 hours | Security best practice |
| Database backups | 30 days | Business continuity |
| Blockchain records | Permanent | Immutable by design |

## 5. Data Disposal Procedures

### 5.1 Automated Disposal

A scheduled background job runs daily to:

1. Identify API request logs older than 90 days and confirm Cloud Logging TTL enforcement
2. Verify Redis TTL enforcement for session data
3. Identify transaction logs older than 7 years and queue for archival/purge
4. Generate a disposal audit entry in the append-only ledger

### 5.2 Manual Disposal (Account Deletion)

1. Operator or automated system triggers account deletion
2. All API keys for the account are immediately revoked (SHA-256 hashes removed from `api_keys` table)
3. Active sessions are invalidated in Redis
4. PII fields are overwritten with anonymized values after the 30-day grace period
5. A permanent audit log entry records the deletion event (without PII)

### 5.3 Disposal Verification

- Disposal events are logged in the append-only audit ledger
- Monthly review of disposal job execution logs
- Quarterly sampling audit to verify data is not retained beyond policy limits

## 6. Legal Hold

When a legal hold is in effect:

1. All automated disposal jobs are suspended for data in scope
2. The hold is documented in the audit log with the requesting authority and scope
3. Data subject to the hold is tagged and excluded from purge jobs
4. Upon hold release, normal retention schedules resume from the release date

## 7. Exceptions

Requests for exceptions to this policy must be submitted in writing to the Compliance team and approved by the CTO. All exceptions are:

- Time-bounded (maximum 12 months)
- Documented in the audit log
- Reviewed at each renewal

## 8. Review Cadence

This policy is reviewed:

- **Annually** as part of the SOC 2 audit cycle
- **Upon material change** to data processing, storage infrastructure, or regulatory requirements
- **After any incident** involving data retention or disposal failures

---

**Appendix A: Related Documents**

- Incident Response Plan (`docs/compliance/soc2/incident-response-plan.md`)
- Access Control Policy (`docs/compliance/soc2/access-control-policy.md`)
- Disaster Recovery Runbook (`docs/compliance/soc2/disaster-recovery-runbook.md`)
