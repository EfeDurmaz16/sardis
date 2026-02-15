# Fiat-First Treasury Design (Multi-Currency Ready, USD-First Launch)

## 1) Scope and launch posture

This design keeps Sardis as control plane while settlement and custody remain with regulated partners.

Launch mode:

1. USD-first treasury for card spend and ACH movement (Lithic financial accounts + payments).
2. Multi-currency ready schema and routing abstractions from day one.
3. Stablecoin rail stays optional and quote-based.

Out of scope in this phase:

1. Non-ACH international rails.
2. Credit issuing products.
3. Multi-sponsor bank optimization.

## 2) Capability matrix (sandbox vs production)

| Capability | Sandbox | Production | Notes |
|---|---|---|---|
| Financial accounts (ISSUING/OPERATING/RESERVE) | Yes | Yes | Program + account-holder context |
| External bank account lifecycle | Yes | Yes | MICRO_DEPOSIT / PRENOTE / EXTERNALLY_VERIFIED per program config |
| ACH origination and lifecycle events | Simulated + API | Live network schedule | Events must drive internal state machine |
| Card authorization and settlement | Yes | Yes | ISSUING balance backed |
| Retry for R01/R09 | Yes | Yes | Max retries controlled by policy |
| FX/multi-currency routing | Limited | Partner-dependent | Sardis route engine is currency-aware even in USD-first mode |

## 3) Financial account usage contract

Program-level:

1. `OPERATING` stores treasury funds for non-card rails and operations.
2. `RESERVE` is risk-reserve bucket required by issuer and bank partner.

Account-holder level:

1. `ISSUING` is card spend bucket.
2. `OPERATING` is cash movement bucket for ACH and book transfers.

Sardis route policy:

1. Card spend defaults to `ISSUING` funding path.
2. ACH collection defaults to `OPERATING`.
3. Treasury reallocation between accounts is explicit and audited.

## 4) ACH policy decisions

SEC policy:

1. `CCD` default for business-originated flows.
2. `PPD` for consumer flows when explicitly allowed.
3. `WEB` only for internet-initiated consumer flows with stronger fraud controls.

Hold policy:

1. Default debit release hold: 2 banking days.
2. Configurable per org from 1-4 days.
3. High-risk orgs can enforce longer hold and manual release.

## 5) Return-code handling matrix

| Code | Meaning | Default action | Retry |
|---|---|---|---|
| `R01` | Insufficient funds | Mark payment `RETURNED`; keep EBA active | Yes (bounded) |
| `R09` | Uncollected funds | Mark payment `RETURNED`; keep EBA active | Yes (bounded) |
| `R29` | Corporate unauthorized | Pause EBA, require manual review | No auto-retry |
| `R02` | Account closed | Set EBA state `CLOSED` and block | No |
| `R03` | No account/unable to locate | Pause or close EBA based on provider signal | No |

Retry policy:

1. R01 and R09 only.
2. Max 2 retries per origination.
3. Retry requires fresh risk checks and org velocity checks.

## 6) Multi-currency readiness model

USD-first launch does not mean USD-only architecture.

Design rules:

1. Persist all amounts as minor units with explicit `currency`.
2. Keep `currency_config` and `rail_capabilities` per org.
3. Route by `(currency, rail, risk_tier, speed_sla)` decision.
4. Conversion always quote-based with provider references.

First launch default:

1. Treasury base currency `USD`.
2. Card settlement currency `USD`.
3. Stablecoin optional route (for example USDC) behind route policy.

## 7) Security and compliance controls

Required controls:

1. Signed webhook verification and replay protection.
2. Idempotency keys on all fund/withdraw actions.
3. Immutable audit trail for every state transition.
4. PII masking in logs and API responses.
5. KYB/KYC and sanctions gates for high-risk movement.

## 8) Operational SLOs

1. Webhook ingestion success: >= 99.9%.
2. Reconciliation mismatch closure: <= 1 business day for non-critical deltas.
3. ACH return handling decision SLA: <= 4 hours for blocked accounts.
4. Treasury balance snapshot freshness: <= 15 minutes.

