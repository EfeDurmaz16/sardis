# Non-Custodial Posture (Design Partner and PH)

Last updated: 2026-02-14

## Canonical Definition

Sardis should be described as **non-custodial** only when all conditions below are true:

1. `SARDIS_CHAIN_MODE=live`
2. `SARDIS_MPC__NAME=turnkey` or `fireblocks`
3. No local signer execution path is used for payment signing

If `SARDIS_MPC__NAME=local` or `simulated`, do not market the system as non-custodial.

## Operational Modes

| Mode | Signing Path | Custody Posture | Launch Copy |
| --- | --- | --- | --- |
| `simulated` | Mock signer | Not non-custodial | "Testnet/dev simulation" |
| `live + local` | Env private key (`SARDIS_EOA_PRIVATE_KEY`) | Custodial | "Controlled dev/sandbox live lane" |
| `live + turnkey/fireblocks` | MPC signing provider | Non-custodial | "Non-custodial MPC wallets" |

## What to Say Publicly Right Now

Use this wording for Product Hunt and design partner calls:

"Sardis provides policy-controlled agent payments. In live MPC mode (Turnkey/Fireblocks), Sardis operates with a non-custodial wallet posture. Current launch stage is testnet/design-partner onboarding."

## Technical Verification

Use health endpoint output:

- `GET /health` -> `components.custody.non_custodial`
- `GET /health` -> `components.custody.status`

Expected values for non-custodial mode:

- `non_custodial: true`
- `status: "non_custodial_mpc"`

