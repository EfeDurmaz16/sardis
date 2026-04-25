# First Card Provider Capability Map

Status: provider-selection worksheet. No live provider is selected or enabled by this document.

## Candidate Shortlist

| Candidate | Why It Might Fit | Primary Questions Before Code |
|---|---|---|
| Lithic | card issuing and spend-control oriented API surface | merchant lock strength, auth/capture event semantics, sandbox parity |
| Stripe Issuing | broad issuing/webhook ecosystem | whether facility-level controls and metadata are sufficient for agent authority decisions |
| Rain / Bridge Cards / CardStack-style provider | crypto/company card adjacency may fit partner-backed facilities | custody boundary, card controls, webhook completeness, live/sandbox maturity |

## Required Fit Before Sandbox Integration

| Surface | Required Facility Gate Behavior | Provider Evidence Required |
|---|---|---|
| Approved-only execution | no credential without `facility.authorization.approved` | provider credential creation can be gated by Sardis call |
| Idempotent execution | retry cannot issue duplicate usable credentials | provider idempotency keys and Sardis execution idempotency both work |
| Merchant binding | credential cannot become general-purpose credit | merchant/MCC/network-token controls documented |
| Amount binding | approved amount envelope is enforced | max amount or single-use limit supported |
| Revocation | operator kill switch prevents future use | revoke/close/void semantics and latency documented |
| Webhooks | async provider truth is signed and deduped | signature scheme, provider event ids, retry rules |
| Metadata | Sardis refs survive provider lifecycle | request id, decision id, decision packet hash attachable |
| Settlement model | auth/capture/void/reversal/dispute mapped | event taxonomy complete enough for audit export |
| Sandbox/live separation | live path disabled by default | separate credentials, environment guardrails |

## No-Go Conditions

- No provider webhook authenticity story.
- No reliable idempotency key on execution or credential creation.
- No amount or single-use control.
- Revocation is only a UI state and cannot prevent future authorization.
- Sandbox behavior differs from live on merchant/amount controls.
- Provider cannot carry Sardis request, authorization, or decision packet references.

## Next Provider Work

1. Pick one candidate for a written capability review.
2. Map exact API endpoints and webhook event names to the Facility Gate adapter contract.
3. Add mocked sandbox tests for that provider behind a disabled flag.
4. Only then wire real sandbox credentials.
