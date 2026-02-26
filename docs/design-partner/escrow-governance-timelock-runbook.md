# Escrow Governance Timelock Runbook

Date: 2026-02-26  
Owner: Sardis Security + Smart Contract Engineering

## Scope

This runbook defines the operational path for arbiter governance updates in `SardisEscrow.sol`.

Covered controls:
1. Timelocked arbiter updates (`proposeArbiter` -> `executeArbiterUpdate`)
2. Pending update cancellation (`cancelArbiterUpdate`)
3. Audit evidence for governance decisions

## Contract Guarantees

The escrow contract includes:
- `ARBITER_UPDATE_TIMELOCK` (2 days)
- `pendingArbiter`
- `pendingArbiterEta`
- `proposeArbiter(address)`
- `executeArbiterUpdate()`
- `cancelArbiterUpdate()`

This enforces a review window before arbiter authority changes.

## Change Procedure

1. Create governance change ticket with:
   - current arbiter
   - proposed arbiter
   - risk assessment
   - rollback owner
2. Submit `proposeArbiter(newArbiter)` transaction.
3. Notify stakeholders and start timelock watch window.
4. After ETA, execute `executeArbiterUpdate()`.
5. Validate post-change state:
   - `arbiter == newArbiter`
   - `pendingArbiter == address(0)`
   - `pendingArbiterEta == 0`
6. Archive evidence:
   - proposal tx hash
   - execution tx hash
   - request + approver identities
   - timestamps

## Emergency Cancellation

If risk is detected during the timelock:
1. Call `cancelArbiterUpdate()`.
2. Confirm pending values are reset.
3. Record cancellation reason in incident log.

## Release Gate

`bash scripts/release/escrow_governance_check.sh` verifies:
- timelock contract surface exists
- governance runbook exists
- governance tests are executable (strict mode) or warned (non-strict mode)
