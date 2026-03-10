# Threat Model — Sardis Payment OS

## Overview

STRIDE analysis of the Sardis platform covering key components and trust boundaries. Each threat includes existing mitigations.

## Architecture Components

| Component | Description | Criticality |
|-----------|-------------|-------------|
| API Gateway | FastAPI REST API with auth middleware | Critical |
| Policy Engine | Spending policy evaluation + AGIT chain | Critical |
| Wallet Manager | MPC wallet lifecycle (Turnkey) | Critical |
| Chain Executor | Multi-chain EVM transaction execution | Critical |
| Card Issuer | Virtual card issuance (Stripe Issuing) | High |
| Ledger | Append-only audit trail (PostgreSQL + on-chain) | High |
| Compliance Engine | KYC (iDenfy) + AML (sanctions screening) | High |
| Kill Switch | Emergency payment freeze system | High |

---

## STRIDE Analysis

### S — Spoofing

| Threat | Target | Mitigation |
|--------|--------|------------|
| API key theft | API Gateway | Keys SHA-256 hashed in DB; never logged; rotation support |
| JWT token forgery | Dashboard auth | HMAC-SHA256 signing with `SECRET_KEY` (min 32 chars) |
| Agent identity spoofing | AP2/TAP Protocol | Ed25519/ECDSA-P256 signature verification on mandate chain |
| Wallet address spoofing | Chain Executor | Address verified against Turnkey wallet registry |
| Webhook source spoofing | Card webhooks | HMAC signature verification required (non-dev environments) |

### T — Tampering

| Threat | Target | Mitigation |
|--------|--------|------------|
| Transaction amount manipulation | Payment flow | Amount verified in mandate chain; policy engine re-checks |
| Policy bypass | Policy Engine | AGIT fail-closed default; policies stored in DB with version history |
| Ledger modification | Audit trail | Append-only PostgreSQL table + on-chain Merkle anchoring |
| Database manipulation | PostgreSQL | Neon serverless with point-in-time restore; connection encryption |
| Request body tampering | API Gateway | Content-Type validation; request body size limits (10MB default) |

### R — Repudiation

| Threat | Target | Mitigation |
|--------|--------|------------|
| Denied transactions | Payment flow | Full mandate chain recorded in ledger (intent -> cart -> payment) |
| Admin action denial | Admin endpoints | All admin actions logged to `access_audit_log` table |
| Policy change denial | Policy Engine | Policy version history with `updated_by` field |
| Emergency action denial | Kill switch | `emergency_freeze_events` table with operator ID + timestamp |

### I — Information Disclosure

| Threat | Target | Mitigation |
|--------|--------|------------|
| API key exposure in logs | Logging | Key prefixes only logged; full keys never in structured logs |
| PII leakage | Database | Column-level access control; PII retention policy (account lifetime + 30d) |
| Private key exposure | MPC Signing | Non-custodial: Turnkey holds key shares, Sardis never sees private keys |
| Error message leakage | API responses | RFC 7807 Problem Details format; stack traces only in dev mode |
| Database credential exposure | Config | Environment variables only; `gitleaks` CI scan; no hardcoded secrets |

### D — Denial of Service

| Threat | Target | Mitigation |
|--------|--------|------------|
| API flooding | API Gateway | Rate limiting: 100/min standard, 10/min admin, per-IP + per-key |
| Admin lockout via brute force | Admin endpoints | 10-attempt lockout (15 min); sliding window rate limiting |
| Database connection exhaustion | PostgreSQL | Connection pooling (5-30 connections); Neon serverless autoscaling |
| Chain RPC overload | Chain Executor | Alchemy RPC with rate limits; public RPCs as fallback only |
| Webhook amplification | Card webhooks | Idempotency keys; dedup via `event_id` + delivery tracking |

### E — Elevation of Privilege

| Threat | Target | Mitigation |
|--------|--------|------------|
| Non-admin accessing admin endpoints | Admin router | `Principal.is_admin` check on every admin endpoint |
| Cross-org data access | Multi-tenant | `organization_id` scoping on all queries; tested in CI |
| Agent exceeding spending policy | Policy Engine | Policy checked before every transaction; kill switch for emergencies |
| Wallet access across organizations | Wallet Manager | Wallet ownership verified against `Principal.organization_id` |
| MFA bypass | Admin actions | `require_mfa_if_enabled` dependency on all admin routers |

---

## Trust Boundaries

### Boundary 1: Agent <-> API
- **Auth:** API key (SHA-256) or JWT
- **Controls:** Rate limiting, request body limits, CORS, CSP headers
- **Protocol:** AP2 mandate chain verification, TAP identity attestation

### Boundary 2: API <-> Policy Engine
- **Controls:** AGIT fail-closed, group policy TTL, kill switch
- **Invariant:** No payment executes without policy approval

### Boundary 3: Policy Engine <-> Wallet Manager
- **Controls:** Payment orchestrator is sole entry point (DI-enforced)
- **Invariant:** Direct chain_executor access blocked

### Boundary 4: Wallet Manager <-> Chain
- **Controls:** MPC signing (Turnkey), ERC-4337 gasless execution, Circle Paymaster
- **Invariant:** Private keys never leave Turnkey infrastructure

### Boundary 5: API <-> Card Issuer
- **Controls:** Webhook signature verification, authorization decision SLA (<3s)
- **Invariant:** Every card auth triggers real-time policy check

---

## Risk Matrix

| Risk | Likelihood | Impact | Priority |
|------|-----------|--------|----------|
| API key compromise | Medium | High | P0 |
| Smart contract vulnerability | Low | Critical | P0 |
| Policy engine bypass | Low | Critical | P0 |
| Database breach | Low | High | P1 |
| DDoS attack | Medium | Medium | P1 |
| Insider threat | Low | High | P1 |
| Third-party service compromise | Low | Medium | P2 |

## References

- `docs/security/audit-scope.md` — Audit scope definition
- `docs/security/transaction-sla.md` — Transaction confirmation SLAs
- `docs/compliance/soc2/incident-response-plan.md` — Incident response procedures
- `docs/plans/2026-03-09-tdd-remediation-90-day-design.md` — TDD remediation details
