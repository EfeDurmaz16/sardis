# Demo Proof Flow Runbook (Allow + Deny + Audit)

## Goal
Produce deterministic artifacts for investor/design-partner demos showing:
- Allowed policy path
- Denied policy path
- Cryptographic ledger verification output

## Command

```bash
SARDIS_API_URL=https://api.sardis.sh \
SARDIS_ADMIN_USERNAME=admin \
SARDIS_ADMIN_PASSWORD='<password>' \
bash scripts/release/demo_proof_check.sh
```

Optional strict mode (requires ledger verification step to be `ok`):

```bash
STRICT_DEMO_PROOF=1 bash scripts/release/demo_proof_check.sh
```

## Artifacts
Generated under `artifacts/investor-demo/`:
- `investor-demo-<run_id>.json`
- `investor-demo-<run_id>.md`

## Required Signals in Artifact
- `simulate_denied_purchase` step shows deny signal (`policy_outcome=denied/blocked` or `decline_reason`).
- `simulate_allowed_purchase` step shows approval signal (no decline reason).
- `verify_ledger_entry` step present; in strict mode it must be `ok`.

## If It Fails
1. Check auth/bootstrap steps.
2. Check policy application and card simulation endpoints.
3. Check transfer path and `ledger_tx_id` emission.
4. Re-run and archive fresh artifacts for the next meeting.
