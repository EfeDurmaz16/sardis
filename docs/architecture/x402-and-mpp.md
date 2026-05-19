# x402 and MPP in Sardis

Sardis treats x402 and MPP as protocol adapters into the same policy,
execution, and evidence control plane. They are not separate products.

Contributor navigation rule: x402 and MPP should feel like two protocol
adapters, not two different Sardis applications. The reusable protocol/client
semantics live in protocol packages; the HTTP request handlers live in the
reference API.

## Current Boundary

| Surface | Role | Code owner |
| --- | --- | --- |
| `packages/sardis-protocol/src/sardis_protocol/x402*.py` | x402 challenge, verification, ERC-3009, and settlement primitives. | Protocol package |
| `packages/sardis-core/src/sardis_v2_core/x402_policy_guard.py` | Shared x402 policy-before-settlement guard used by higher-level surfaces. | Core policy package |
| `packages/reference-api/server/routes/protocol/x402.py` | x402 facilitator API: generate, verify, dry-run, settle, and inspect x402 payments. | API protocol routes |
| `packages/reference-api/server/middleware/x402.py` | Optional server-side x402 paid-endpoint middleware. | API middleware |
| `packages/sardis-mpp/` | Sardis policy-governed MPP client, session helpers, payment records, and payment methods. | MPP package |
| `packages/reference-api/server/routes/protocol/mpp.py` | Sardis-hosted MPP session lifecycle and budgeted payment execution API. | API protocol routes |
| `packages/reference-api/server/middleware/mpp_gate.py` | Per-endpoint MPP 402 challenge dependency for public paid APIs. | API middleware |
| `packages/sardis-sdk-python/src/sardis_sdk/client.py` | Public Python SDK client methods that call Sardis API protocol endpoints. | Python SDK |
| `packages/sardis-mcp-server/src/tools/x402.ts` | MCP tool wrapper for x402 protocol operations. | MCP package |
| `packages/sardis-mcp-server/src/tools/mpp.ts` | MCP tool wrapper for MPP protocol operations. | MCP package |
| `packages/reference-api/server/routes/protocol/a2a.py` | Agent-to-agent protocol messaging, trust checks, and payment requests. | API protocol routes |
| `packages/reference-api/server/routes/protocol/a2a_payments.py` | A2A escrow and settlement route surface. | API protocol routes |
| `packages/reference-api/server/routes/protocol/acp.py` | Agentic Commerce Protocol checkout and delegated payment session surface. | API protocol routes |
| `packages/reference-api/server/routes/protocol/erc8183.py` | ERC-8183 agentic commerce job lifecycle surface. | API protocol routes |
| `packages/reference-api/server/routes/protocol/spt.py` | Shared Payment Token grant and use surface. | API protocol routes |

## Request Flow Difference

### x402

x402 is direct HTTP-native payment. The server returns an x402 payment
challenge and the client retries with a payment signature.

```text
client -> protected endpoint
server -> 402 + PaymentRequired challenge
client -> retry with PAYMENT-SIGNATURE
Sardis -> verify x402 payload, enforce policy, settle, emit evidence
server -> response + PAYMENT-RESPONSE receipt
```

Use x402 when the API already wants direct pay-per-request behavior and the
payment method is stablecoin-oriented.

### MPP

MPP is machine-payment negotiation. The server returns a `WWW-Authenticate`
challenge and the client retries with `Authorization: Payment ...`.

```text
client -> protected endpoint
server -> 402 + WWW-Authenticate challenge
client -> retry with Authorization: Payment ...
Sardis -> validate credential, enforce policy, record receipt
server -> response + optional Payment-Receipt
```

Use MPP when the payment method is negotiated or method-agnostic: Tempo, Stripe
SPT, Lightning, or another MPP-compatible method.

## Package Decision

Keep x402 and MPP as separate protocol surfaces because their public APIs and
wire formats are different:

- x402 belongs in `sardis-protocol` because it is a protocol primitive Sardis
  can verify, settle, and compose with AP2/TAP.
- MPP belongs in `sardis-mpp` because it wraps `pympp`, payment methods, and
  client-side HTTP transport behavior.

The API should group their HTTP routes together under
`server.routes.protocol` because contributors looking for protocol
adapters should not search the legacy flat `routers/` directory.

Do not split the reference API into `sardis-x402-api` and `sardis-mpp-api`
packages at the current maturity level. That would create more folders and
release surfaces without improving the public contract. Split only if one of
these becomes true:

- a protocol needs a materially different deployment/runtime profile
- a protocol needs heavy optional dependencies that should not load with the
  reference API
- a protocol needs independent versioning or release cadence
- conformance tests prove the shared paid-request adapter is stable enough to
  publish separately

## Current Cleanup Target

`packages/reference-api/server/routes/protocol/mpp.py` is too large for a route
adapter. It should remain at the same public HTTP path, but new work should move
non-HTTP logic out of the route file:

| Concern | Target location |
| --- | --- |
| Request/response models | `server/models/mpp.py` |
| Session persistence | `server/repositories/` |
| Policy/session orchestration | `server/domains/` or `server/services/` |
| Provider-specific execution | provider or service modules |
| FastAPI path functions | `server/routes/protocol/mpp.py` |

This keeps the contributor path shallow while preventing a single route file
from becoming a hidden application.

## Shared Sardis Invariant

Both flows must eventually pass through the same Sardis invariants:

1. Policy checks happen before payment execution or settlement.
2. Payment receipts are recorded with enough context for audit and replay
   analysis.
3. Public API paths remain stable unless an explicit API migration is approved.
4. Middleware and facilitator/session APIs stay separate:
   - middleware protects Sardis-hosted endpoints
   - facilitator/session routes expose protocol management APIs

## Migration Direction

Short term:

- Keep public routes stable: `/api/v2/x402`, `/api/v2/mpp`, and `/api/v2/demo`.
- Keep protocol route implementations in `server.routes.protocol`.

Later:

- Add a small internal adapter interface for paid request protocols:
  `PaidRequestChallenge`, `PaidRequestCredential`, `PaidRequestReceipt`, and
  `PaidRequestAdapter`.
- Implement `X402Adapter` and `MPPAdapter` against that interface only after the
  duplicate behavior is clear.
- Add conformance tests that prove both adapters call policy before execution
  and produce evidence records.
