# Facility Gate Threat Model

Status: pilot-readiness draft

Scope: Sardis Facility Gate control plane for partner-backed, non-custodial programmable facility access.

## Security Boundary

Facility Gate authorizes delegated facility access. It does not make Sardis the lender, issuer of record, or custodian. The critical authority chain is:

`organization -> principal/sponsor -> facility -> mandate -> agent identity -> request -> decision -> execution adapter`

Any request that cannot prove this chain must fail closed.

## Primary Assets

- Facility authority and revocation state.
- Mandate, facility, policy, risk, and adapter version references.
- Decision packets and event hash chains.
- Evidence references and hashes.
- Liability assignment.
- Simulated or partner execution credentials.
- Operator approvals, overrides, and exception resolutions.
- Provider webhook payload hashes, dedupe keys, and settlement updates.

## Threats And Required Controls

| Threat | Risk | Required Control |
|---|---|---|
| Client-supplied authority snapshot forgery | unauthorized facility draw | persisted mandate/facility/policy lookup before pilot |
| Cross-tenant request or audit access | data leakage or spend abuse | org-scoped authz on every route |
| Duplicate authorize | duplicate decision/credential path | idempotency and request-level serialization |
| Duplicate execute | multiple credentials for one approval | execution idempotency before adapter call |
| Revocation race | spend after kill switch | final revocation check before decision and execution append |
| False evidence generation | unsupported spend approved | typed evidence refs, hashes, source metadata, evidence considered list |
| Approval fatigue | human approves bad requests | approval fatigue guardrails and escalation |
| Merchant probing | low-value abuse/trust farming | org/agent/facility/merchant rate limits |
| Adapter capability mismatch | promised controls not enforced on provider | adapter contract tests and capability declarations |
| Provider webhook spoofing | false settlement/repayment state | signed webhook route, raw payload hash, dedupe key |
| Projection drift | operator/audit sees wrong state | replay/backfill tooling and drift verification |
| Operator hidden override | untraceable risk acceptance | append-only operator action events |

## Pilot Gate

Do not enable live provider execution until these controls pass:

- Postgres migration and idempotency tests.
- Projection replay and drift verification.
- Decision packet export with version refs and hash.
- Persisted mandate and facility authority lookup in strict mode.
- Duplicate authorize/execute tests.
- Revocation race tests.
- Adapter contract tests.
- Signed webhook tests if provider webhooks are enabled.
- Incident runbook tabletop.
