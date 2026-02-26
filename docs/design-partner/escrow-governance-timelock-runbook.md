# Escrow Governance Timelock Runbook

Date: 2026-02-26  
Owner: Sardis Security + Smart Contract Engineering

## Scope

This runbook defines the operational path for arbiter governance updates in `SardisEscrow.sol`.

Covered controls:
1. Timelocked arbiter updates (`proposeArbiter` -> `executeArbiterUpdate`)
2. Timelocked governance executor updates (`proposeGovernanceExecutor` -> `executeGovernanceExecutorUpdate`)
3. One-way strict governance mode (`enableGovernanceStrictMode`)
4. Timelocked ownership transfer (`transferOwnership` -> `executeOwnershipTransfer`)
5. Pending update cancellation (`cancelArbiterUpdate`, `cancelGovernanceExecutorUpdate`, `cancelOwnershipTransfer`)
6. Audit evidence for governance decisions

## Contract Guarantees

The escrow contract includes:
- `ARBITER_UPDATE_TIMELOCK` (2 days)
- `GOVERNANCE_EXECUTOR_UPDATE_TIMELOCK` (2 days)
- `OWNERSHIP_TRANSFER_TIMELOCK` (2 days)
- `pendingArbiter`
- `pendingArbiterEta`
- `governanceExecutor`
- `pendingGovernanceExecutor`
- `pendingGovernanceExecutorEta`
- `governanceStrictMode`
- `pendingOwner`
- `ownershipTransferEta`
- `proposeArbiter(address)`
- `executeArbiterUpdate()`
- `cancelArbiterUpdate()`
- `setGovernanceExecutor(address)` (bootstrap-only, owner)
- `proposeGovernanceExecutor(address)`
- `executeGovernanceExecutorUpdate()`
- `cancelGovernanceExecutorUpdate()`
- `enableGovernanceStrictMode()`
- timelocked ownership transfer functions

This enforces a review window before arbiter/governance/ownership authority changes.

## Change Procedure

1. Create governance change ticket with:
   - current arbiter
   - proposed arbiter
   - current governance executor
   - acting governance admin (`owner` or `governanceExecutor`; strict mode requires executor)
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

## Strict Mode Activation

1. Configure governance executor as deployed multisig/timelock contract (`setGovernanceExecutor` during bootstrap).
2. Verify executor contract address and signer policy off-chain.
3. Execute `enableGovernanceStrictMode()`.
4. Validate:
   - `governanceStrictMode == true`
   - owner can no longer run governance-admin actions directly.

Strict mode is intentionally one-way.

## Ownership Rotation

1. Submit `transferOwnership(newOwner)` (proposes transfer with timelock).
2. Wait `OWNERSHIP_TRANSFER_TIMELOCK`.
3. Execute `executeOwnershipTransfer()`.
4. Validate:
   - `owner == newOwner`
   - pending ownership fields reset to zero values.

## Emergency Cancellation

If risk is detected during the timelock:
1. Call `cancelArbiterUpdate()`.
2. Confirm pending values are reset.
3. Record cancellation reason in incident log.

## Release Gate

`bash scripts/release/escrow_governance_check.sh` verifies:
- timelock contract surface exists
- strict governance contract surface exists
- timelocked ownership transfer surface exists
- governance runbook exists
- governance tests are executable (strict mode) or warned (non-strict mode)
