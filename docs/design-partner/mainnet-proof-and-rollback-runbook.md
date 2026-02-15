# Mainnet Proof And Rollback Runbook

Owner: Sardis on-call (API + Infra)  
Scope: Mainnet proof run + rollback drill for payment-critical changes

## 1) Preconditions
1. Deploy candidate to staging and pass:
   - `bash scripts/release/readiness_check.sh`
   - `bash scripts/release/webhook_conformance_check.sh`
2. Confirm production secrets exist:
   - `LITHIC_API_KEY`
   - `LITHIC_WEBHOOK_SECRET`
   - `SARDIS_REDIS_URL`
3. Confirm incident channel and owner on-call for the drill window.

## 2) Mainnet Proof Steps
1. Create a proof ticket ID: `proof_<date>_<commit>`.
2. Run one controlled payment flow:
   - success path
   - deny path (policy or compliance)
3. Capture evidence:
   - request id
   - tx hash / user op hash
   - canonical journey id
   - ledger verification output (`/api/v2/ledger/entries/{tx_id}/verify`)
   - webhook event ids
4. Export operator evidence:
   - `GET /api/v2/treasury/ops/audit-evidence/export?format=json`
5. Store artifact under `reports/proof/<proof_ticket>.json`.

## 3) Rollback Drill (Mandatory)
1. List Cloud Run revisions:
   - `gcloud run services describe sardis-api-staging --region us-east1 --format='value(status.traffic)'`
2. Shift traffic to previous stable revision (staging rehearsal).
3. Validate:
   - `curl -sS https://api.sardis.sh/api/v2/health`
   - `curl -sS https://api.sardis.sh/api/v2/treasury/ops/journeys`
4. Restore traffic to latest revision.
5. Record timings:
   - detect to rollback start
   - rollback completion
   - service recovery confirmation

## 4) Exit Criteria
1. Proof artifact includes both allow and deny evidence.
2. Rollback completed and validated in less than 10 minutes.
3. No data loss in canonical journeys/events during drill.

