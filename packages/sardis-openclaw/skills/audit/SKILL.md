---
name: sardis-audit
description: Teach an OpenClaw agent to inspect Sardis transactions, preserve evidence, and verify authority before reporting payment state.
homepage: https://sardis.sh
user-invocable: false
---

# Sardis Audit

Use this skill only when `SARDIS_API_KEY` is present. If it is missing, state that Sardis audit data is unavailable.

## Audit Flow

Use `sardis_list_transactions` to inspect the activity ledger before summarizing payment history, card activity, or budget usage.

Use `sardis_check_balance` before claiming available spend capacity.

Use `sardis_check_policy` before saying a future spend is allowed.

## Reporting Rules

Report Sardis transaction identifiers, status, merchant, amount, currency, and evidence references when available.

Distinguish `pending`, `requires_approval`, `denied`, `settled`, and `revoked` states.

Never claim a payment completed from intent text alone. The ledger status is the source of truth.
