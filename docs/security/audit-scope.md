# Security Audit Scope — Sardis

## Overview

This document defines the scope for an independent security audit of the Sardis Payment OS platform. Sardis enables AI agents to make real financial transactions through non-custodial MPC wallets with policy-enforced spending controls.

## In-Scope Components

### 1. Smart Contracts (Solidity 0.8.24, Foundry)

| Contract | Purpose | Risk Level |
|----------|---------|------------|
| `SardisLedgerAnchor` | Append-only on-chain audit trail | Medium |
| `RefundProtocol` | Dispute resolution and refunds (Circle Apache 2.0) | High |
| `ERC8183Registry` | Agent capability registry | Medium |
| `ERC8183PolicyValidator` | On-chain spending policy validation | High |
| `ERC8183FeeCollector` | Protocol fee collection (1% cap, USDC-only) | High |
| `ERC8183AgentDelegation` | Agent delegation management | High |

**Location:** `contracts/src/`
**Dependencies:** OpenZeppelin Contracts v5.x, Safe Smart Accounts v1.4.1

### 2. API Authentication & Authorization

- API key authentication (SHA-256 hashed storage)
- JWT token validation (dashboard/admin UX)
- Principal-based authorization model (`Principal.is_admin`, scopes)
- MFA enforcement for admin actions
- Rate limiting (100/min standard, 10/min admin, 5/min sensitive)
- OAuth CSRF protection

**Location:** `packages/sardis-api/src/sardis_api/authz.py`, `middleware/`

### 3. MPC Signing Flow

- Turnkey MPC custody integration (non-custodial)
- Key generation and wallet creation
- Transaction signing flow
- Key recovery procedures

**Location:** `packages/sardis-wallet/`

### 4. Policy Engine

- Spending policy evaluation (<100ms p99 target)
- AGIT (Agent Identity Trust) policy chain
- Kill switch system (global, per-org, per-agent)
- Group policy evaluator with TTL

**Location:** `packages/sardis-core/src/sardis_v2_core/spending_policy.py`, `packages/sardis-guardrails/`

### 5. Payment Orchestration

- PreExecutionPipeline (compliance, policy, mandate verification)
- Chain executor (multi-chain EVM transaction execution)
- Idempotency enforcement (Redis dedup + DB unique constraints)
- Settlement flow

**Location:** `packages/sardis-core/src/sardis_v2_core/orchestrator.py`, `packages/sardis-chain/`

## Known Mitigations (TDD Remediation — March 2026)

The following issues were identified and fixed during the TDD remediation cycle:

| Finding | Status | Fix |
|---------|--------|-----|
| OAuth CSRF vulnerability | Fixed | State parameter validation added |
| Admin fail-open default | Fixed | Admin endpoints require explicit auth |
| Webhook signatures optional | Fixed | Required in all non-dev environments |
| AGIT fail-open default | Fixed | Default changed to fail-closed |
| Replay attacks | Fixed | Redis dedup store + mandate cache |
| Rate limiter bypass | Fixed | Redis-backed enforcement in production |
| Direct chain_executor access | Fixed | Private in DI, only orchestrator can access |

**Reference:** `docs/plans/2026-03-09-tdd-remediation-90-day-design.md`

## Trust Boundaries

```
[AI Agent] <--API Key Auth--> [API Gateway]
     |                             |
     |                      [Rate Limiter]
     |                             |
     v                             v
[AP2/TAP Protocol] <------> [Policy Engine]
     |                             |
     |                      [Kill Switch]
     |                             |
     v                             v
[Mandate Verifier] <------> [Wallet Manager]
     |                             |
     |                      [MPC Signing (Turnkey)]
     |                             |
     v                             v
[Compliance Engine] <------> [Chain Executor]
     |                             |
     v                             v
[Sanctions Screening] <---> [EVM Transaction]
```

## Out of Scope

- Third-party infrastructure (Neon PostgreSQL, Turnkey, Stripe)
- Frontend dashboard (React/Vite)
- Marketing website
- SDK client libraries (sardis-sdk-python, sardis-sdk-js)
- CI/CD pipeline security

## Deliverables Expected

1. Vulnerability report with severity ratings (Critical/High/Medium/Low/Informational)
2. Smart contract findings per SWC registry
3. API security findings per OWASP Top 10
4. Remediation recommendations
5. Executive summary suitable for investor due diligence

## Contact

Security audit inquiries: security@sardis.sh
