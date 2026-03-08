# PR: Add Sardis payment blocks

## Target Repo
`Significant-Gravitas/AutoGPT`

## Branch
`feat/add-sardis-payment-blocks`

## Files
- `autogpt_platform/backend/backend/blocks/sardis.py`

## PR Title
feat: add Sardis payment blocks

## PR Body

## Summary
- Adds Sardis payment blocks for AutoGPT platform
- `SardisPayBlock` — execute policy-controlled payments
- `SardisBalanceBlock` — check wallet balance and limits

## What is Sardis?
Sardis is the Payment OS for the Agent Economy. It provides non-custodial MPC wallets with spending policy guardrails, enabling AI agents to make real stablecoin payments safely.

## Blocks
| Block | Description |
|-------|-------------|
| Sardis Pay | Execute a payment with policy checks |
| Sardis Balance | Check wallet balance and spending limits |

## Prerequisites
- `sardis` package (`pip install sardis`)
- Sardis API key (free sandbox available)
- Agent wallet ID

## Note
This was discussed in the AutoGPT Discord before submission. The `sardis-autogpt` package is also available on PyPI for standalone use.

## Links
- Website: https://sardis.sh
- PyPI: https://pypi.org/project/sardis-autogpt/
- GitHub: https://github.com/EfeDurmaz16/sardis
