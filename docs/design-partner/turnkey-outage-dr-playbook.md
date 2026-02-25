# Turnkey Outage Runbook + DR Playbook (RTO/RPO + Failover)

This runbook defines deterministic behavior when Turnkey signing is degraded or unavailable.

## Scope

- Payment execution paths using Turnkey MPC signing.
- Applies to `wallets.transfer`, `wallets.pay_onchain`, `ap2.payments.execute`, `mvp.payments.execute`.
- Objective: preserve funds and policy guarantees under signer outage.

## Targets

- `RTO`: 15 minutes for degraded failover mode activation.
- `RTO`: 60 minutes for primary-path recovery after Turnkey health is restored.
- `RPO`: 0 for policy/audit state (all decisions persisted before execution).

## Detection Signals

Treat Turnkey as degraded when one of these crosses threshold:

1. `sardis_mpc_signing_requests_total{provider="turnkey",status="error"}` spike for 5 minutes.
2. p95 signing latency > 10 seconds for 5 minutes.
3. healthcheck failures from Turnkey API across 3 consecutive probes.

## Deterministic Failover Modes

### Mode 0 — Normal

- Turnkey signer path enabled.
- Fireblocks/local signer path available only for approved staged environments.

### Mode 1 — Degraded (recommended first step)

- Keep policy/compliance/approval checks active.
- Block high-risk executions; only allow low-risk operations that match strict policy rails.
- Require explicit approval for operations above org threshold.

### Mode 2 — Containment

- Deny all new payment executions (fail-closed).
- Keep read/list/admin/audit endpoints available.
- Continue ingesting webhooks/events and approvals for later replay.

## Operator Procedure

1. Confirm incident from metrics + logs.
2. Announce incident and set incident channel owner.
3. Switch to Mode 1 or Mode 2 based on blast radius.
4. Verify deny/allow behavior on staging smoke routes.
5. Keep audit trail running and export incident timeline.
6. Recover primary signer path.
7. Exit failover mode gradually (Mode 2 -> Mode 1 -> Mode 0).
8. Publish postmortem within 24h.

## Runtime Controls (recommended)

- `SARDIS_CHAIN_MODE=live|simulated`
- `SARDIS_MPC__NAME=turnkey|fireblocks|local|simulated`
- `SARDIS_AI_ADVISORY_ONLY=true` (keeps deterministic enforcement authoritative)
- Agent-level endpoint limiter (enabled by default):  
  `SARDIS_AGENT_PAYMENT_RATE_LIMIT_ENABLED=true`

## Validation Checklist

1. Policy decisions remain deterministic and fail-closed.
2. Approval escalations still function.
3. No direct bypass from agent prompt path to signer path.
4. Audit entries include denial reasons and operation metadata.
5. Replay-safe idempotency behavior preserved.

## Exit Criteria

- Turnkey health checks stable for 30 minutes.
- No elevated signing error rates.
- Canary payment flow success on staging and production canary org.
- Incident commander signs off and records closure in incident log.

