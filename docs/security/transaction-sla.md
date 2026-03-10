# Transaction Confirmation SLA

**Document Version:** 1.0
**Last Updated:** 2026-03-10
**Classification:** Internal / Investor / Auditor

## Overview

This document defines the Service Level Agreements (SLAs) for transaction confirmation, policy evaluation, card authorization, and end-to-end payment processing across all supported chains in the Sardis Payment OS. These SLAs apply to production environments running with Alchemy RPC endpoints and the recommended infrastructure stack.

All timing guarantees assume normal network conditions. Degraded network states (chain congestion, RPC provider outages) are addressed in the Retry Policies section.

---

## 1. Block Confirmation Requirements by Chain

Sardis waits for a chain-specific number of block confirmations before marking a transaction as finalized. These thresholds balance finality guarantees against user experience.

| Chain | Confirmations Required | Avg Block Time | Expected Confirmation Latency | Finality Model |
|-----------|------------------------|----------------|-------------------------------|---------------------|
| Base | 2 blocks | ~2s | ~4s | Optimistic (L2) |
| Ethereum | 12 blocks | ~12s | ~2.5 min | PoS (Gasper) |
| Polygon | 128 blocks | ~2.1s | ~4.5 min | PoS + Heimdall |
| Arbitrum | 1 block | ~0.25s | ~0.25s | Optimistic (L2) |
| Optimism | 1 block | ~2s | ~2s | Optimistic (L2) |

### Notes on Confirmation Thresholds

- **L2 chains (Base, Arbitrum, Optimism):** Transactions are considered safe after minimal confirmations because L2 sequencers provide soft confirmations. Full L1 finality (when the L2 batch is posted to Ethereum) takes longer (~7 days for optimistic rollups) but is not required for payment confirmation.
- **Ethereum:** 12 blocks provides economic finality under Gasper consensus. After 2 epochs (~12.8 min), finality is cryptographic, but 12 blocks is the industry standard for high-value transfers.
- **Polygon:** The higher confirmation count (128 blocks) accounts for Polygon's checkpoint mechanism. Sardis considers a transaction confirmed at 128 blocks; full Heimdall checkpoint finality takes ~30 minutes.

### Chain-Specific Configuration

Confirmation thresholds are configured in `packages/sardis-core/src/sardis_v2_core/config.py` and can be overridden per deployment via environment variables:

```
SARDIS_BASE_CONFIRMATIONS=2
SARDIS_ETH_CONFIRMATIONS=12
SARDIS_POLYGON_CONFIRMATIONS=128
SARDIS_ARBITRUM_CONFIRMATIONS=1
SARDIS_OPTIMISM_CONFIRMATIONS=1
```

---

## 2. Policy Engine Latency SLA

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| p50 latency | < 10ms | Policy `evaluate()` return |
| p95 latency | < 50ms | Policy `evaluate()` return |
| **p99 latency** | **< 100ms** | **Policy `evaluate()` return** |
| p99.9 latency | < 250ms | Policy `evaluate()` return |

### What the Policy Engine Evaluates (per request)

The `SpendingPolicy.evaluate()` method runs up to 12 sequential checks:

1. Amount validation
2. Spending scope check
3. MCC (Merchant Category Code) blocking
4. Per-transaction limit
5. Cumulative lifetime limit
6. Time-window limits (daily / weekly / monthly)
7. On-chain balance query (async, cached)
8. Merchant allow/deny rules
9. Goal drift detection
10. Merchant trust scoring
11. Approval threshold routing
12. KYA attestation verification

### Performance Characteristics

- **Checks 1-6** are pure computation against in-memory or database-cached state. Each check completes in < 1ms.
- **Check 7** (on-chain balance) is the most variable. With Alchemy RPC, median latency is ~30ms. Results are cached in Redis (Upstash) with a 10-second TTL.
- **Check 8** (merchant rules) is O(n) on the rule count. Policies with fewer than 100 rules complete in < 1ms.
- **Check 10** (merchant trust) involves a database lookup with Redis caching, adding ~5ms.
- **Check 12** (KYA attestation) requires an on-chain read when the cache is cold, adding up to ~50ms. Hot cache: < 1ms.

### Velocity Check

The policy store performs a velocity check (rapid-fire prevention) before the main evaluation pipeline. This is a single Redis `INCR` + `EXPIRE` operation with < 2ms latency.

### Degradation Behavior

If Redis is unavailable, the policy engine falls back to in-memory state for time-window checks. The p99 latency may increase to ~200ms as on-chain queries bypass the cache.

---

## 3. Card Authorization Webhook Response SLA

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| **Response time** | **< 3 seconds** | Webhook receipt to HTTP response |
| Decision time (policy) | < 100ms | Policy evaluation within webhook handler |
| Network overhead | < 200ms | Stripe/card network round-trip |
| Available budget | ~2.7s | For compliance checks and edge cases |

### Card Authorization Flow

When a virtual card (Stripe Issuing) is used at a merchant, Stripe sends a real-time authorization webhook:

```
Merchant POS -> Card Network -> Stripe -> Sardis Webhook -> Policy Engine -> Approve/Decline -> Stripe -> Card Network -> Merchant POS
```

**Critical constraint:** Card networks require authorization responses within 3 seconds. If Sardis does not respond in time, the network defaults to **decline** (fail-closed).

### Webhook Processing Pipeline

| Step | Budget | Description |
|------|--------|-------------|
| Signature verification | 5ms | HMAC-SHA256 webhook signature validation |
| Event parsing | 2ms | Deserialize and validate event payload |
| Card-to-agent lookup | 15ms | Map card ID to agent and policy |
| Policy evaluation | 100ms | Full SpendingPolicy.evaluate() |
| Subscription matching | 20ms | Check if charge matches a known subscription |
| MCC categorization | 5ms | Resolve merchant category from MCC code |
| Response formatting | 3ms | Construct approve/decline response |
| **Total internal** | **~150ms** | Well within 3s budget |

### Failure Modes

| Scenario | Behavior | Rationale |
|----------|----------|-----------|
| Policy engine timeout (> 2s) | Decline | Fail-closed protects agent funds |
| Card-to-agent lookup fails | Configurable | `SARDIS_ASA_FAIL_CLOSED_ON_CARD_LOOKUP_ERROR` (default: decline in production) |
| Subscription match error | Configurable | `SARDIS_ASA_FAIL_CLOSED_ON_SUBSCRIPTION_ERROR` (default: decline in production) |
| Webhook signature invalid | Reject (HTTP 401) | Prevents spoofed authorization requests |

---

## 4. End-to-End Payment Confirmation SLA

End-to-end latency is measured from API request receipt to the `PaymentResult` being returned with a confirmed `tx_hash` and `ledger_tx_id`.

| Chain Category | Target | Components |
|----------------|--------|------------|
| **L2 chains** (Base, Arbitrum, Optimism) | **< 30 seconds** | Policy + Compliance + Chain TX + Confirmations + Ledger |
| **L1 chains** (Ethereum) | **< 5 minutes** | Policy + Compliance + Chain TX + Confirmations + Ledger |
| **Polygon** | **< 6 minutes** | Policy + Compliance + Chain TX + Confirmations + Ledger |

### Latency Breakdown (L2 Typical Path)

| Phase | Latency | Notes |
|-------|---------|-------|
| Phase 0: KYA Verification | 5-50ms | Cached attestation check |
| Phase 1: Policy Validation | 10-100ms | Full 12-check pipeline |
| Phase 1.5: Group Policy | 5-20ms | Only if agent belongs to a group |
| Phase 2: Compliance Check | 50-500ms | KYC status cached; sanctions screening |
| Phase 3: Chain Execution | 2-15s | MPC signing (Turnkey) + TX broadcast + confirmations |
| Phase 3.5: Policy State Update | 10-50ms | DB write with `SELECT FOR UPDATE` |
| Phase 4: Ledger Append | 10-30ms | Append-only audit write |
| **Total (L2)** | **~3-16s** | Well within 30s target |

### Latency Breakdown (Ethereum)

| Phase | Latency | Notes |
|-------|---------|-------|
| Phases 0-2 | 70-670ms | Same as L2 |
| Phase 3: Chain Execution | 120-180s | 12 block confirmations at ~12s each |
| Phases 3.5-4 | 20-80ms | Same as L2 |
| **Total (Ethereum)** | **~2-3 min** | Well within 5 min target |

---

## 5. Retry Policies and Timeout Handling

### Transaction Submission Retries

| Parameter | Value | Notes |
|-----------|-------|-------|
| Max retries | 3 | Exponential backoff |
| Initial backoff | 1 second | Doubles each retry |
| Max backoff | 8 seconds | Cap on retry delay |
| Retry conditions | Nonce errors, RPC timeouts, gas estimation failures | Never retry on revert or insufficient funds |
| Idempotency | Enforced | DB-level `idempotency_key` unique constraint prevents duplicate payments |

### Confirmation Polling

| Parameter | Value | Notes |
|-----------|-------|-------|
| Poll interval | 2 seconds (L2), 12 seconds (L1) | Aligned with block times |
| Max poll duration | 60s (L2), 10 min (L1/Polygon) | After which TX is marked `pending_confirmation` |
| Stale TX handling | Reconciliation queue | Background job retries confirmation checks |

### RPC Failover

| Priority | Provider | Latency |
|----------|----------|---------|
| Primary | Alchemy | ~30ms |
| Fallback | Public RPC (chain-specific) | ~100-500ms |

If the primary RPC provider (Alchemy) is unreachable after 3 attempts with 2-second timeouts, Sardis falls back to the chain's public RPC endpoint. The fallback is automatic and transparent to the caller.

### Timeout Hierarchy

```
API Request Timeout:          30s (HTTP client default)
  |
  +-- Policy Evaluation:       2s  (hard timeout, fail-closed on breach)
  |
  +-- Compliance Check:        5s  (hard timeout, fail-closed on breach)
  |
  +-- MPC Signing (Turnkey):  10s  (hard timeout, retry once)
  |
  +-- TX Broadcast:            5s  (per attempt, 3 attempts)
  |
  +-- Confirmation Wait:      60s  (L2) / 600s (L1)
       (async, does not block API response for long-running chains)
```

### Asynchronous Confirmation for L1

For Ethereum and Polygon, where confirmation can take minutes, the API returns immediately after TX broadcast with `status: "submitted"`. The client can:

1. **Poll** the `/api/v2/transactions/{tx_id}/status` endpoint.
2. **Subscribe** to SSE updates via `/api/v2/transactions/{tx_id}/stream`.
3. **Register a webhook** to receive a callback when the transaction is confirmed.

---

## 6. Monitoring and Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Policy p99 latency | > 80ms | > 150ms | Scale Redis, investigate slow queries |
| Card auth response | > 2s | > 2.7s | Immediate investigation (risk of network decline) |
| L2 E2E latency | > 20s | > 30s | Check RPC provider, gas prices |
| L1 E2E latency | > 4 min | > 5 min | Check chain congestion, gas strategy |
| TX retry rate | > 5% | > 15% | Investigate nonce management, RPC health |
| Confirmation timeout rate | > 1% | > 5% | Check chain health, block production |

---

## 7. SLA Exclusions

The following scenarios are excluded from SLA calculations:

- **Chain halts or reorganizations** affecting block production.
- **Scheduled maintenance windows** (announced 48 hours in advance).
- **Force majeure events** affecting cloud infrastructure (AWS, GCP, Vercel).
- **Client-side issues** including invalid requests, insufficient wallet balance, or expired mandates.
- **Third-party provider outages** (Turnkey MPC, Stripe Issuing, Alchemy) beyond Sardis's control.

During excluded events, Sardis maintains fail-closed behavior: no payments are processed, and all pending transactions are queued for retry once service is restored.
