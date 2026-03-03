# Escrow Governance Timelock Runbook

Date: 2026-02-26  
Owner: Sardis Security + Smart Contract Engineering

## Scope

This runbook defines the governance control surfaces for escrow/refund settlement contracts.
Current active source tree uses `RefundProtocol.sol`; legacy timelock flow remains documented for `SardisEscrow.sol`.

Covered controls:
1. Arbiter-only refund and lockup controls (`RefundProtocol.sol`)
2. Early-withdrawal EIP-712 authorization + replay protection (`withdrawalHashes`)
3. Recipient lockup ceiling enforcement (`MAX_LOCKUP_SECONDS`)
4. Legacy timelocked arbiter/governance/ownership updates (`SardisEscrow.sol`)
5. Audit evidence for governance decisions

## Current Contract Surface (`RefundProtocol.sol`)

The active contract includes:
- `modifier onlyArbiter`
- `setLockupSeconds(recipient, seconds)` guarded with `MAX_LOCKUP_SECONDS`
- `refundByArbiter(paymentID)`
- `earlyWithdrawByArbiter(...)` with EIP-712 hash + `withdrawalHashes` replay protection
- `updateRefundTo(paymentID, newRefundTo)` controlled by current `refundTo` principal

Operational expectation:
- Arbiter key changes are managed at signer/ops layer (HSM/MPC), with dual approval.
- Any lockup-policy or early-withdrawal operation is ticketed and evidenced.
- Replay/hash expiry failures are treated as security events and investigated.

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

In strict mode, ownership operations are also governance-executor gated:
- `transferOwnership`
- `executeOwnershipTransfer`
- `cancelOwnershipTransfer`

This removes single-owner proposal/execute ability after strict mode is enabled.

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
