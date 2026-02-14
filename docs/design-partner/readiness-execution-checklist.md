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
- [ ] Run and document webhook conformance tests for all providers in production-like env.
- [ ] Publish secret rotation operational playbook and rollback path.
- [ ] Add release-gate check in deployment pipeline for webhook signature + replay tests.

Evidence (existing test surface):
- `tests/test_webhooks.py`
- `tests/test_checkout_webhook_security.py`
- `packages/sardis-api/tests/test_middleware_security.py`
- `tests/test_audit_f12_replay_cache.py`

## 4) Investor Demo Proof Flows (Allow + Deny)
- [ ] Add a deterministic “allow” flow script with expected outputs.
- [ ] Add a deterministic “deny” flow script (policy/compliance rejection) with expected reason codes.
- [ ] Capture and store artifacts (request IDs, receipts, ledger entries) for replayable demos.

Candidate scripts:
- `scripts/investor_demo_flow.py`
- `scripts/yc_wow_demo.py`

## 5) Ops Readiness (Alerts / SLO / Rollback)
- [ ] Define SLOs for API health, latency, and payment execution success.
- [ ] Set alert policies (health status degradation, error-rate spikes, webhook failures).
- [ ] Write rollback runbook with exact commands and validation checks.

Related artifacts:
- `scripts/health_monitor.sh`
- `.github/workflows/monitoring.yml`

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

---

## Exit Criteria for 9+
- All items in sections 1, 2, and 6 complete and deployed.
- Sections 3, 4, 5 completed with evidence artifacts linked in this file.
- Production partner integrations (Lithic, Persona, Elliptic, Bridge) validated in controlled live lane.
