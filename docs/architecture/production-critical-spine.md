# Production-Critical Spine

Every Sardis money-moving path should follow the same authority sequence:

```text
agent intent
  -> mandate lookup and verification
  -> policy evaluation
  -> approval or revocation check
  -> idempotency and replay guard
  -> provider capability check
  -> execution request
  -> provider response verification
  -> append-only evidence
```

There should be no alternate execution path that signs, pays, issues, refunds, settles, swaps, or subscribes before these checks run.

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| Agent / SDK | Submit explicit financial intent and idempotency metadata. |
| API boundary | Validate external input and authenticate the caller. |
| Mandate layer | Prove delegated authority and scope. |
| Policy layer | Deny actions that exceed limits, vendor scope, geography, category, risk, or compliance state. |
| Approval layer | Require human or higher-authority approval for configured thresholds. |
| Idempotency layer | Bind retries to a request fingerprint and block key reuse with different payloads. |
| Provider adapter | Execute only after the authority layer authorizes the action. |
| Evidence ledger | Record decision, execution, and failure evidence without mutation. |

## Failure Defaults

- Unknown caller: deny.
- Missing mandate: deny.
- Policy unavailable: deny.
- Compliance unavailable: deny.
- Provider capability unknown: deny.
- Webhook signature invalid: ignore or reject.
- Idempotency key reused with different payload: reject.
- Evidence write unavailable after provider execution: raise an operational incident.

## Contribution Guidance

Any change that touches this spine must include tests or a validation command proving that execution cannot bypass policy, mandate, approval, replay, and evidence checks.
