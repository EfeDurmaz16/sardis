---
name: sardis-payments
description: Teach an OpenClaw agent to use Sardis payment verbs with policy checks, reversibility awareness, and fail-closed handling.
homepage: https://sardis.sh
user-invocable: false
---

# Sardis Payments

Use this skill only when `SARDIS_API_KEY` is present. If it is missing, do not create wallets, issue cards, or attempt payments.

## Payment Verbs

Use `sardis_give_wallet` to provision the agent payment identity.

Use `sardis_spend` only after a successful `sardis_check_policy` result.

Use `sardis_pay_invoice` for invoice-shaped requests instead of manually constructing a payment when invoice metadata is available.

Use `sardis_issue_card` only when the user has explicitly requested a card and the policy result permits it.

Use `sardis_freeze_card` when a card is revoked, compromised, outside mandate, or no longer needed.

## Fail-Closed Rules

If Sardis returns `requires_approval`, surface the approval requirement and wait.

If Sardis returns `deny`, stop the payment path.

If Sardis is unavailable, treat the action as denied until the service is reachable again.

Never expose raw card data, private keys, API keys, signing secrets, or provider tokens.
