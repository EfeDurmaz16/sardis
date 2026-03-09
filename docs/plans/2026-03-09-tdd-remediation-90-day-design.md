# TDD Remediation — 90-Day Design

**Date:** 2026-03-09
**Status:** Approved
**Approach:** B — Correctness First, Then Architecture

## Context

The TDD (technical due diligence) report scored Sardis at 7.5/10 moat, Medium execution confidence, recommending a $20-26M seed valuation. The report identified 11 open issues across security, correctness, and architecture. This plan addresses all of them in three phases to reach 8.5/10 moat, High confidence.

## Conservative Caps (from ERC-8183 deployment)

Already deployed alongside this plan:
- ERC-8183 contracts on Base mainnet with 1% fee, USDC-only, trust hooks disabled
- Post-audit relaxation path documented in deploy scripts

---

## Phase 1: Security + Correctness (Days 1-30)

**Goal:** Survive investor diligence and live product testing.

### Security Fixes

#### S1. OAuth CSRF — Add state parameter verification
- **File:** `packages/sardis-api/src/sardis_api/routers/auth.py:690`
- **Fix:** Generate cryptographic `state` token on OAuth initiation, store in session/cookie. Reject callback if state doesn't match.
- **Scope:** ~20 lines, one file.

#### S2. Admin fail-open — Remove silent fallback
- **File:** `packages/sardis-api/src/sardis_api/routers/auth.py:243`
- **Fix:** Remove bare `except Exception: pass`. If primary auth fails, log reason and return 401. Keep dev-only default password gated behind explicit env check.
- **Scope:** ~15 lines, one file.

#### S3. Webhook signatures — Fail-closed in non-dev
- **Files:** `treasury.py:455`, `cpn.py:178`
- **Fix:** Require webhook_secret in all environments except dev. Return 500 if not configured.
- **Scope:** ~10 lines, two files.

#### S4. Secret rotation + scanning
- **New files:** `.gitleaks.toml`, `.github/workflows/secret-scan.yml`
- **Fix:** Add gitleaks CI workflow. Add env files to `.gitignore`. Document secret management in CLAUDE.md.
- **Manual:** Rotate all exposed keys (OpenAI, Turnkey, Lithic, DB, JWT, admin, Redis, Groq).

### Correctness Bug Fixes

#### C1. Group-policy TTL — Period-appropriate TTLs
- **File:** `packages/sardis-core/src/sardis_v2_core/group_policy.py:238`
- **Fix:** Split counters into per-period keys with correct TTLs: daily=86400, monthly=2678400, total=no expiry.
- **Scope:** ~30 lines, one file.

#### C2. Group-budget decrement — Record spend after payment
- **File:** `packages/sardis-core/src/sardis_v2_core/orchestrator.py:736`
- **Fix:** Add `group_policy.record_spend()` call after successful payment. Thread group_policy through DI.
- **Scope:** ~15 lines, one file + DI wiring.

#### C3. Queue interface mismatch — Fix method name
- **File:** `packages/sardis-core/src/sardis_v2_core/orchestrator.py:759`
- **Fix:** Change `.append()` to `.enqueue()` to match `ReconciliationQueuePort` protocol.
- **Scope:** 1 line.

#### C4. AGIT fail-close — Reject on verification error
- **File:** `packages/sardis-core/src/sardis_v2_core/control_plane.py:186`
- **Fix:** Change except handler to reject payment. Add `SARDIS_AGIT_FAIL_OPEN=false` config flag (default: fail-closed).
- **Scope:** ~10 lines, one file + one config field.

### Phase 1 Deliverables
- 8 PRs (one per fix), each with tests
- Secret scanning CI workflow
- Updated `.gitignore`
- Credential rotation checklist

---

## Phase 2: Single Execution Path (Days 31-60)

**Goal:** Every money-moving operation through one gateway.

### A1. Pre-execution pipeline
- Extract AGIT, KYA, FIDES, trust-scoring from `control_plane.py` into `PreExecutionPipeline`.
- Pipeline is a list of async callables returning `Approve | Reject | Skip`.
- `ControlPlane` becomes deprecated facade delegating to `PaymentOrchestrator`.
- ~150 lines new, ~100 removed, ~40 added to orchestrator.

### A2. Kill direct dispatch_payment in routers
- `wallets.py:767` — Replace with `orchestrator.execute(intent)`.
- `mandates.py:415` — Same. Remove ad-hoc `async_record_spend`.
- `ap2.py:467` — Same. Move inline policy validation to pipeline.
- ~200 lines removed, ~60 lines added.

### A3. DI lockdown
- Remove `chain_executor` from router dependency injection.
- Only `PaymentOrchestrator` gets it.
- ~20 lines in `dependencies.py`.

### A4. Unified result type
- `PaymentResult` with: status, reason codes, policy evidence, compliance evidence, chain receipt, ledger entry ID.
- All routers serialize this instead of ad-hoc dicts.
- ~50 lines new, ~80 changed.

### Phase 2 Deliverables
- `PreExecutionPipeline` module
- `ControlPlane` deprecated
- 3 router migrations (separate PRs)
- DI lockdown
- Unified `PaymentResult`
- Integration tests

---

## Phase 3: Durable State + Moat Tightening (Days 61-90)

**Goal:** Survive horizontal scaling. Productize strongest IP. Honest claims.

### Durable State

#### D1. Redis-backed dedup
- Replace in-memory `_executed_mandates` with Redis store.
- Key: `sardis:dedup:{mandate_id}`, TTL: 24h. Fail-closed if Redis unavailable.
- ~60 lines new, ~20 changed.

#### D2. Persistent reconciliation queue
- Postgres-backed queue replacing `InMemoryReconciliationQueue`.
- Table: `reconciliation_queue (id, entry_type, payload_json, status, created_at, processed_at)`.
- Production config rejects in-memory queue.
- ~80 lines new, 1 migration.

#### D3. Durable replay cache
- Redis-backed `ReplayCache` replacing in-memory dict.
- Key: `sardis:replay:{mandate_hash}`, TTL: 24h. Fail-closed.
- ~40 lines new, ~10 changed.

#### D4. Rate limiter enforcement
- Require `redis_url` in non-dev environments. Fail at startup if missing.
- ~8 lines changed.

### Evidence Productization

#### E1. Policy attestation envelope
- Signed JSON envelope: `{ attestation_id, timestamp, agent_did, policy_rules_applied[], evidence_chain[], ap2_mandate_ref, signature }`.
- Endpoint: `GET /api/v2/payments/{id}/attestation`.
- ~120 lines new, ~30 changed.

#### E2. Verifier output envelope
- Structured verification report attached to `PaymentResult`.
- ~50 lines new, ~20 changed.

### Claim Surface

#### E3. README accuracy
- Three tiers: Production, Pilot, Experimental.
- Remove "full protocol coverage" claims for stubbed protocols.

#### E4. Deployment manifest audit
- Lifecycle fields match reality across all deployment JSONs.

### Phase 3 Deliverables
- 4 durable state modules
- 1 migration
- Production config validation hardened
- Attestation endpoint
- Verification report
- README rewrite
- GH description update
- Landing page updates if needed

---

## Score Trajectory

| Metric | Current | Day 30 | Day 60 | Day 90 |
|--------|---------|--------|--------|--------|
| Moat Score | 7.5/10 | 7.5 | 8.0 | 8.5 |
| Execution Confidence | Medium | Medium-High | High | High |
| Valuation Range | $20-26M | $22-28M | $25-30M | $28-34M |

---

## Key Files Reference

| File | Issues |
|------|--------|
| `auth.py` | S1 (OAuth CSRF), S2 (admin fail-open) |
| `treasury.py`, `cpn.py` | S3 (webhook signatures) |
| `group_policy.py` | C1 (TTL bug), C2 (decrement) |
| `orchestrator.py` | C2 (decrement), C3 (interface mismatch), D1 (dedup), D2 (reconciliation) |
| `control_plane.py` | C4 (AGIT fail-close), A1 (pre-execution pipeline) |
| `verifier.py` | D3 (replay cache) |
| `wallets.py`, `mandates.py`, `ap2.py` | A2 (direct dispatch) |
| `dependencies.py` | A3 (DI lockdown) |
| `rate_limiter.py` | D4 (enforcement) |
| `policy_attestation.py`, `policy_evidence.py` | E1 (envelope) |
| `README.md` | E3 (accuracy) |
