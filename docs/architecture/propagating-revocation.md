# Propagating Revocation — one kill switch across every rail

> "AI agents can reason, but they cannot be trusted with money."
> The kill switch is how you take that trust back in under a second, with proof.

Revoking a `SpendingMandate` already makes the orchestrator deny *future*
payments for it (the mandate lookup returns only `status = 'active'` rows). That
is necessary but not sufficient. The differentiating promise is bigger:

**ONE revoke atomically propagates across EVERY rail** — it marks the
mandate(s) revoked, freezes the agent's cards, revokes its outstanding spend
objects / one-time passes, denies its pending approvals, blocks its in-flight
payments — and returns a **signed, independently-verifiable proof-of-revocation**
listing exactly what was killed and when.

No single rail-owner (a card issuer, a chain, a checkout) can build this: it
requires neutrality *across* all rails. **Sardis owns the revocation decision and
its signed proof — that is the moat.** The per-rail kill is swappable execution.

## The model

| Concept | What it is |
| --- | --- |
| `Revocation` (`rev_…`) | The durable decision: target (agent / mandate / principal), scope, who requested it, status, and the full list of propagation targets. |
| `PropagationTarget` | One derived authority the kill touched — its `kind` (mandate / spend_object / card / approval / in_flight), its `ref`, and its honest `kill_status`. |
| `RevocationProof` | The signed proof: binds the revocation identity + the full target list + the overall outcome + the timestamp, HMAC-SHA256 over the decision hash. |

### Kill statuses (per target)

- `killed` — confirmed dead on its rail.
- `already_dead` — was already terminal (no-op; counts as confirmed dead).
- `blocked_pending` — the kill could **not** be confirmed downstream. The
  authority is **still denied at execution** (the mandate is revoked) but the
  object may still be alive on its rail. Never reported as killed.
- `failed` — a hard failure (also blocked at execution); `detail` records why.

### Overall outcome (per revocation) — fail-closed

- `propagated` — every target confirmed dead.
- `blocked_pending_downstream` — at least one target is **not** confirmed dead.
  A partial propagation is **NEVER** reported as `propagated`. The authority is
  still blocked at execution time; a background `reconcile` sweep retries the
  blocked rails and, once a provider recovers, upgrades the target to `killed`
  and re-signs the proof.

This is the hard rule: **a partial propagation must not leave authority alive
silently.** Every target is recorded; an unconfirmed downstream kill is denied at
execution AND surfaced in the proof as "blocked-at-execution pending downstream
confirmation".

## The API

| Route | Purpose |
| --- | --- |
| `POST /api/v2/revocations` | Revoke an agent / mandate / principal. Returns the propagation **summary** (N cards frozen, M spend objects killed, K pending blocked, mandates revoked) + the signed proof. Idempotent. |
| `GET  /api/v2/revocations` | List this org's recent revocations (each with its proof). |
| `GET  /api/v2/revocations/{id}` | Fetch one revocation + its proof. Org-scoped. |
| `POST /api/v2/revocations/verify` | Independently verify a proof from its own fields — no live lookup. |

All routes require `require_principal` (API key or JWT) and are org-scoped: a
revocation created by one org is invisible (404) to another. The actor is the
authenticated principal — a forged `requested_by` in the body cannot move money
or tenancy. If the engine is not configured the surface fails closed (`503`).

### The propagation summary (what the UI consumes)

```jsonc
{
  "outcome": "propagated",            // or "blocked_pending_downstream"
  "fully_propagated": true,
  "total_targets": 5,
  "confirmed_dead": 5,
  "blocked_pending": 0,
  "mandates_revoked": 1,
  "cards_frozen": 1,
  "spend_objects_killed": 2,
  "approvals_blocked": 1,
  "in_flight_blocked": 1
}
```

Per-rail counts count only **confirmed-dead** targets toward "frozen / killed",
so the UI never over-claims. A `blocked_pending` card is in `blocked_pending`,
never in `cards_frozen`.

## Proof verification (the auditor's check)

A `RevocationProof` is **self-contained**: every field needed to recompute the
`decision_hash` and check the `signature` is carried on the proof itself. An
auditor holding the HMAC key can verify it **offline** — round-trip the stored
proof straight into `POST /api/v2/revocations/verify`:

```jsonc
// response
{
  "valid": true,
  "hash_matches": true,        // false ⇒ target list / identity fields tampered
  "signature_matches": true,   // false ⇒ wrong signing key or forged signature
  "revocation_id": "rev_…",
  "outcome": "propagated",
  "detail": "proof is authentic: decision hash and signature both verify"
}
```

The two checks are split so a **tampered or truncated target list** (hash fails)
is distinguishable from a **wrong / forged key** (signature fails). `valid`
requires both.

## Signing key

`SARDIS_REVOCATION_HMAC_KEY` signs (and verifies) every proof — a key separate
from approvals (`SARDIS_APPROVAL_HMAC_KEY`) and recourse
(`SARDIS_RECOURSE_HMAC_KEY`). It is **REQUIRED in prod/staging**: a missing key
fails closed (refuses to sign or verify a proof). Outside prod a `dev-` fallback
runs with no keys so dev/tests work out of the box. See `.env.example`.

## What is real vs sandbox

- **Decision + proof + propagation algorithm + fail-closed semantics** are real,
  pure-Python, and fully covered (`packages/sardis/tests/test_revocation*.py`,
  `apps/api/tests/test_revocation_api.py`).
- **Mandate + spend-object legs** write through the canonical Postgres path
  (`spending_mandates` + `mandate_state_transitions`, `payment_objects`) in
  production; in-memory mocks in dev.
- **Card freeze** goes through the provider-layer `CardPort` — a real issuer when
  keys are set, a sandbox impl otherwise.
- **Approvals** deny through the same signed `ApprovalGate` the orchestrator
  re-executes from. **In-flight** blocks via the transactions ledger.
- The execution-time backstop (the orchestrator denying a revoked mandate) is
  real and independent of any downstream rail confirmation.
