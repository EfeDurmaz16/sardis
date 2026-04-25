# Facility Gate Incident Runbook

Status: pilot-readiness draft

## Immediate Triage

1. Identify scope: `global`, `organization`, `facility`, `mandate`, `agent`, `merchant`, or `authorization`.
2. Check `/api/v2/facility-requests/{request_id}/audit/export` for the decision packet, evidence, liability, provider webhooks, settlement updates, and event hash chain.
3. If spend authority may still be usable, create a revocation event immediately.
4. If adapter propagation fails, verify an exception event exists and pause execution for the affected provider or org.

## Compromised Agent Key

- Revoke scope: `agent` or narrower `authorization` if isolated.
- Inspect recent requests by `agent_id`.
- Export audits for approved requests.
- Raise manual review threshold for the org until key rotation is confirmed.

## Credential Issued Incorrectly

- Revoke scope: `authorization`.
- Confirm duplicate execute did not create multiple credentials.
- Check adapter event metrics and exceptions.
- Export audit and event hash-chain verification.
- If provider-backed, notify provider and preserve webhook payload hashes.

## Projection Drift

- Run replay in dry-run mode: `python packages/sardis-api/scripts/facility_gate_replay.py <org_id>`.
- If drift is expected and event stream is valid, rerun with `--apply`.
- If hash-chain verification fails, preserve DB snapshot and escalate.

## Approval Stuck Or Duplicated

- Inspect manual review queue.
- Check approval request and approval recorded events.
- Recheck request expiry and revocation state before resuming.
- Do not manually append approval outcomes without operator reason metadata.

## Suspicious Merchant Probing

- Filter requests by org, agent, and merchant.
- Apply merchant or agent revocation if active risk exists.
- Increase rate-limit sensitivity for the org.
- Export sample audits for risk review.

## Provider Outage

- Disable provider feature flag.
- Keep request, authorization, and audit APIs available if the event store is healthy.
- Do not silently fall back to another provider.
- Create exception events for failed executions or revocations.
