# Sardis Rail Model: Stablecoin vs Fiat (Custody Boundaries)

## Why this matters

Sardis has two distinct execution models:

1. Stablecoin rail: policy-governed blockchain execution.
2. Fiat/card rails: policy-governed orchestration over regulated partners.

They should not be described with the same custody language.

## A. Stablecoin rail (wallet-native execution)

Execution path (current):

1. Agent requests payment.
2. Sardis policy engine evaluates limits, domain, and compliance checks.
3. Chain executor submits payment.
   - `mpc_v1`: EIP-1559 transaction (`execution_path=legacy_tx`).
   - `erc4337_v2` preview: UserOperation route (`execution_path=erc4337_userop`) behind feature flags.
4. Ledger anchors receipt (`audit_anchor`).

Custody posture:

- In live MPC mode (`SARDIS_CHAIN_MODE=live` + Turnkey/Fireblocks), Sardis can be operated with a non-custodial posture.
- In local/simulated signer modes, this claim does not apply.

## B. Fiat/card rails (partner-mediated settlement)

Execution path (current architecture):

1. Funding and payout orchestration via on-ramp/off-ramp providers (Onramper/Bridge lanes).
2. Card issuing and authorization via Lithic provider integration.
3. Sardis still enforces policy and audit trail around these operations.
4. Final fiat movement and card network settlement happen in partner systems.

Custody posture:

- Sardis is a control plane for fiat/card rails, not the final settlement/custody entity.
- Regulated providers/issuers hold settlement/custody responsibilities for their rail.

## C. How wallet funds reach Lithic virtual cards

Typical flow for stablecoin-backed card spend:

1. Wallet holds USDC on supported chain.
2. Sardis requests off-ramp quote and execute flow.
3. Bridge-style provider converts USDC to fiat and settles to card funding account.
4. Lithic card authorizations spend against funded fiat account.
5. Sardis records policy decision + transaction references for audit.

## D. Production dependencies for full fiat readiness

To move from sandbox/design-partner lane to production:

1. Lithic production program approval + live card funding account.
2. Bridge production account and settlement ops playbook.
3. Persona KYB/KYC production workflow and fallback handling.
4. Elliptic AML screening with alert operations.
5. Reconciliation SLAs across provider webhooks and ledger states.

## E. Messaging rules (recommended)

Use this wording:

- "Non-custodial posture in live MPC mode for stablecoin execution."
- "Fiat and card rails are policy-governed by Sardis and settled by regulated partners."

Avoid this wording:

- "Fully non-custodial across all rails".
- "Gasless live on all chains" (until per-chain proof artifacts exist).
