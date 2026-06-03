---
name: sardis-spending-policy
description: Teach an OpenClaw agent to set budgets, check policy before spend, and honor Sardis allow / requires_approval / deny outcomes.
homepage: https://sardis.sh
user-invocable: false
---

# Sardis Spending Policy

Use this skill only when `SARDIS_API_KEY` is present. If it is missing, stop and ask the operator to configure Sardis before attempting any money movement.

## Required Flow

1. Create or update a budget with `sardis_set_budget` before the first spend.
2. Run `sardis_check_policy` before every `sardis_spend`.
3. Continue only when the policy result is `allow`.
4. Pause when the result is `requires_approval`.
5. Refuse when the result is `deny`.

## Guardrails

Never infer authority from user wording alone. The Sardis policy result is the authority boundary.

Never split one payment into smaller payments to bypass a budget, approval threshold, merchant block, token block, or time window.

Never retry a denied action with changed fields unless the operator explicitly changes the budget or mandate first.
