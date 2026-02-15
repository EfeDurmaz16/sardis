# Sardis Rail Model: Stablecoin vs Fiat (Custody + Unit Economics)

## 1. What is true right now

Sardis has two execution rails:

1. Stablecoin rail: wallet-native execution with policy checks.
2. Fiat/card rail: policy-governed orchestration, partner-settled movement.

They are not the same custody model.

## 2. Stablecoin rail (wallet-native)

Execution path:

1. Agent asks to pay.
2. Sardis evaluates policy and compliance rules.
3. Chain executor submits transaction.
   - `mpc_v1`: EIP-1559 (`execution_path=legacy_tx`).
   - `erc4337_v2` preview: UserOperation (`execution_path=erc4337_userop`) behind flags.
4. Ledger anchors receipt and evidence.

Custody posture:

- In live MPC mode (`SARDIS_CHAIN_MODE=live` and Turnkey/Fireblocks), this can run in a non-custodial posture.
- In local or simulated signer modes, this claim does not apply.

## 3. Fiat and card rail (partner-settled)

Execution path:

1. On-ramp or off-ramp quote and execution through partners (Onramper or Bridge lane).
2. Card issuing and authorization through Lithic.
3. Sardis enforces policy, idempotency, and audit entries.
4. Settlement and custody happen in regulated partner systems.

Custody posture:

- Sardis is control plane plus policy engine.
- Final fiat settlement and custody are partner responsibilities.

## 4. The key question: is there forced double conversion?

No. Double conversion is optional, not mandatory.

### Mode A: Fiat-first card treasury (lowest operational friction)

1. User funds fiat account (ACH or wire).
2. Card spends are debited directly from fiat treasury.
3. Stablecoin conversion happens only for explicit crypto payouts.

Use when card share is high and users are not crypto-native.

### Mode B: Stablecoin-first with JIT off-ramp (best for crypto-native inflows)

1. Funds sit as USDC.
2. Card spend triggers quote + off-ramp for required amount.
3. USD settles to Lithic funding account.

Use when most inflow is crypto or cross-border.

### Mode C: Hybrid with pre-funding thresholds (recommended default)

1. Keep a USD buffer for expected card volume (for example next 3 to 7 days).
2. Refill buffer by batched off-ramp when threshold is reached.
3. Avoid per-swipe conversion and reduce fee drag.

This is usually the best balance for design partners.

## 5. How Sardis code maps to this model

- Card funding supports stablecoin-backed path with quote and execute flow:
  `packages/sardis-api/src/sardis_api/routers/cards.py:282`
- Lithic funding account is required for that path:
  `packages/sardis-api/src/sardis_api/routers/cards.py:331`
- Ramp endpoints expose on-ramp widget, quote, off-ramp execute/status:
  `packages/sardis-api/src/sardis_api/routers/ramp.py:169`
- Bridge off-ramp provider quote and transfer integration:
  `packages/sardis-cards/src/sardis_cards/offramp.py:225`

## 6. Unit economics model (operator view)

Per-dollar gross margin should be modeled as:

`margin = platform_take_rate - partner_fees - network_fees - fraud_loss - support_cost`

Practical levers:

1. Route high-volume card users to Mode C (batched refill).
2. Add minimum platform fee floor for small tickets.
3. Use approval and policy rails to cut fraud and chargeback costs.
4. Tier pricing by monthly volume and SLA.
5. Keep quote transparency so end users can choose speed versus cost.

## 7. Production dependencies before scaling volume

1. Lithic production program and live funding account.
2. Bridge production account and settlement operations playbook.
3. Persona KYB and KYC production flows.
4. Elliptic AML monitoring and escalation runbook.
5. Daily reconciliation and exception handling across provider webhooks.

## 8. Messaging guidance

Use:

- "Non-custodial posture for stablecoin execution in live MPC mode."
- "Fiat and card rails are policy-governed by Sardis and settled by regulated partners."

Avoid:

- "Fully non-custodial across all rails."
- "Every card payment requires two conversions."
