# Launch Readiness Execution Checklist

Owner: Sardis core team  
Stage: Design-partner onboarding  
Target: Push technical readiness from ~8.4 to 9.1+

## 1) Test Suite Stability (Critical Paths)
- [x] Fix auth bootstrap for API integration tests (`SARDIS_TEST_API_KEY` fixture).
- [x] Resolve staging/non-production expectation mismatch in middleware tests.
- [x] Re-run `packages/sardis-api/tests` and confirm pass.

Evidence:
- `packages/sardis-api/tests/conftest.py`
- `packages/sardis-api/tests/test_middleware_exceptions.py`

## 2) API Discovery Route Correctness (`/api`, `/api/v2`)
- [x] Remove proxy-level redirects forcing `/api*` to docs.
- [x] Keep upstream rewrite to Cloud Run only.
- [x] Validate live responses on `https://api.sardis.sh/api` and `/api/v2`.

Evidence:
- `api-proxy/vercel.json`

## 3) Webhook Production Controls (Replay / Idempotency / Rotation)
- [x] Run and document webhook conformance tests for all providers in production-like env.
- [x] Publish secret rotation operational playbook and rollback path.
- [x] Add release-gate check in deployment pipeline for webhook signature + replay tests.

Evidence (existing test surface):
- `tests/test_webhooks.py`
- `tests/test_checkout_webhook_security.py`
- `packages/sardis-api/tests/test_middleware_security.py`
- `tests/test_audit_f12_replay_cache.py`
- `scripts/release/webhook_conformance_check.sh`
- `docs/design-partner/webhook-conformance-runbook.md`
- `.github/workflows/deploy.yml`

## 4) Investor Demo Proof Flows (Allow + Deny)
- [x] Add a deterministic “allow” flow script with expected outputs.
- [x] Add a deterministic “deny” flow script (policy/compliance rejection) with expected reason codes.
- [x] Capture and store artifacts (request IDs, receipts, ledger entries) for replayable demos.

Candidate scripts:
- `scripts/investor_demo_flow.py`
- `scripts/yc_wow_demo.py`
- `scripts/release/demo_proof_check.sh`
- `docs/design-partner/demo-proof-flow-runbook.md`

## 5) Ops Readiness (Alerts / SLO / Rollback)
- [x] Define SLOs for API health, latency, and payment execution success.
- [x] Set alert policies (health status degradation, error-rate spikes, webhook failures).
- [x] Write rollback runbook with exact commands and validation checks.

Related artifacts:
- `scripts/health_monitor.sh`
- `.github/workflows/monitoring.yml`
- `docs/design-partner/ops-slo-alerts-rollback-runbook.md`
- `scripts/release/ops_readiness_check.sh`

## 6) Cryptographic Audit Trail (Merkle Verification)
- [x] Add receipt lookup by tx hash.
- [x] Add Merkle root retrieval APIs in ledger store.
- [x] Implement cryptographic receipt integrity verification (leaf/root checks).
- [x] Upgrade `/api/v2/ledger/entries/{tx_id}/verify` to return structured verification report.
- [x] Add/refresh tests for verify endpoint behavior.

Evidence:
- `packages/sardis-ledger/src/sardis_ledger/records.py`
- `packages/sardis-api/src/sardis_api/routers/ledger.py`
- `tests/test_ledger_entries_api.py`

## 7) Non-Custodial Posture Guardrails
- [x] Make signer selection explicit so `SARDIS_EOA_PRIVATE_KEY` does not silently override MPC mode.
- [x] Block `SARDIS_CHAIN_MODE=live` with `SARDIS_MPC__NAME=simulated`.
- [x] Add runtime custody posture visibility on `/health`.
- [x] Publish non-custodial messaging guidance for PH/design-partner communications.

Evidence:
- `packages/sardis-chain/src/sardis_chain/executor.py`
- `packages/sardis-api/src/sardis_api/main.py`
- `packages/sardis-api/src/sardis_api/health.py`
- `docs/design-partner/non-custodial-posture.md`

## 8) Fiat-First Treasury Operations
- [x] Publish design-partner runbook for USD-first ACH/card flow.
- [x] Publish ACH return support playbook with return-code decision matrix.
- [x] Publish treasury audit trail examples for partner evidence reviews.

Evidence:
- `docs/design-partner/fiat-treasury-design-partner-runbook.md`
- `docs/design-partner/ach-return-support-playbook.md`
- `docs/design-partner/treasury-audit-trail-examples.md`

## 9) Mainnet Proof + Rollback Drill
- [x] Publish mainnet proof runbook with allow/deny evidence requirements.
- [x] Add rollback drill steps with API validation checkpoints.
- [x] Add release-gate check script for proof/rollback artifacts.

Evidence:
- `docs/design-partner/mainnet-proof-and-rollback-runbook.md`
- `scripts/release/mainnet_ops_drill_check.sh`

## 10) 24/7 Incident Drill + Reconciliation Chaos/SLO
- [x] Publish 24/7 incident drill playbook with severity and response targets.
- [x] Define reconciliation SLOs for duplicate suppression and out-of-order handling.
- [x] Add load/chaos regression test for canonical reconciliation engine.
- [x] Add release-gate check script for reconciliation chaos coverage.

Evidence:
- `docs/design-partner/incident-response-247-drill.md`
- `docs/design-partner/reconciliation-load-chaos-slos.md`
- `tests/test_reconciliation_engine_load.py`
- `scripts/release/reconciliation_chaos_check.sh`

---

## Exit Criteria for 9+
- All items in sections 1, 2, and 6 complete and deployed.
- Sections 3, 4, 5 completed with evidence artifacts linked in this file.
- Production partner integrations (Lithic, Persona, Elliptic, Bridge) validated in controlled live lane.
