# Facility Gate Provider Capability Map

Status: pre-integration, simulator/mock-provider only.

## Contract Requirements

Facility Gate provider adapters must fail closed unless these controls are supported or explicitly simulated:

| Capability | Required Before Pilot Provider | Reason |
|---|---:|---|
| Approved-only execution | Yes | No credential/payment artifact without an immutable authorization event. |
| Idempotent execution | Yes | Retries must not create duplicate credentials or charges. |
| Merchant binding | Yes | Agent authority must not become reusable open credit. |
| Amount limit binding | Yes | Provider execution must match the approved amount envelope. |
| Revoke/void path | Yes | Operator kill switches must propagate. |
| Webhook signature verification | Yes | Provider async state must be authenticated. |
| Webhook dedupe | Yes | Provider retries must not duplicate settlement state. |
| Sandbox/live separation | Yes | Live execution must be disabled by default. |
| Raw payload hash retention | Yes | Audit and incident reconstruction require payload integrity. |

## Candidate Provider Assessment Template

| Surface | Required Answer | Provider Notes |
|---|---|---|
| Credential type | single-use or tightly scoped virtual card preferred | TBD |
| Merchant lock | exact merchant, MCC, or network token control | TBD |
| Amount control | exact auth amount, max amount, or spend limit | TBD |
| Expiry | credential or authorization expiry supported | TBD |
| Revoke semantics | immediate revoke, future auth block, or best-effort | TBD |
| Capture semantics | auth/capture distinction and partial capture behavior | TBD |
| Webhooks | auth, capture, void, decline, refund, dispute | TBD |
| Webhook auth | HMAC/JWS/mTLS/IP allowlist | TBD |
| Idempotency | provider idempotency key and retry behavior | TBD |
| Metadata | request id, authorization id, decision packet hash | TBD |
| Sandbox parity | whether sandbox matches live controls | TBD |
| Failure modes | timeout, duplicate webhook, late capture after revoke | TBD |

## Current Sardis Adapter Status

- `SimulatedFacilityAdapter` validates the authorization lifecycle without money movement.
- `MockProviderFacilityAdapter` exists for provider-shaped contract tests.
- `DisabledProviderFacilityAdapter` exists as a compile-time skeleton that cannot execute or revoke.
- Signed provider webhook ingestion is feature-flagged with `SARDIS_FACILITY_PROVIDER_WEBHOOKS_ENABLED`.
- Live provider execution remains out of scope until this map is completed for a named provider and the adapter contract suite passes.

## Go / No-Go Rules

Do not enable a real provider if any of these are unresolved:

- provider cannot bind merchant or equivalent spend scope
- provider cannot enforce amount or single-use semantics
- provider revoke is only cosmetic and cannot prevent future authorization
- webhook signatures cannot be verified
- sandbox behavior diverges materially from live
- decision packet hash cannot be carried in provider metadata
- duplicate execution cannot be made idempotent

