# Attenuated Delegation + Portable Proof-of-Authority

> "AI agents can reason, but they cannot be trusted with money."
> Delegation lets one agent hand a *smaller* slice of its authority to another —
> and Proof-of-Authority lets anyone confirm, offline, that a spend was allowed.

These are two object-capability primitives for money. They build on the existing
signed-evidence pattern (`DecisionEvidence` / `RevocationProof` /
`ExecutionReceipt`) and plug into the orchestrator's single fail-closed path and
the propagating Revocation engine.

---

## Primitive 1 — Attenuated Delegation Graph

An agent (or principal) delegates a **scoped, bounded, revocable** slice of its
own authority to a sub-agent. The sub-agent may delegate a still-smaller slice of
*that* to a tool, and so on — an **attenuating capability chain**:

```
human ── $500 mandate ──▶ Agent A
                             │  delegate $50 (subset of scope)
                             ▼
                          Agent B (sub-agent)
                             │  delegate $20 (subset of B's scope)
                             ▼
                          Tool C
```

### The cardinal rule — a delegate can NEVER exceed its delegator

Every hop must *narrow*. The `DelegationEngine` rejects a mint fail-closed unless,
against the delegator's **current** authority:

| Dimension | Attenuation rule |
| --- | --- |
| Amount | `amount_cap <= delegator remaining` (not the parent's original cap). |
| Expiry | `expires_at <= delegator expiry` (a child can never outlive its parent). Omit it to inherit. |
| Scope | `counterparties / categories / mcc / rails` must each be a **subset** of the delegator's. An empty parent dimension is unrestricted; a child set with a value absent from a non-empty parent set is a widening → reject. |
| Currency | Must match the delegator's. |
| Depth | `parent depth + 1 <= MAX_DELEGATION_DEPTH` (8). The root mandate is depth 0. |
| Liveness | The delegator must itself be active (non-revoked, non-expired, non-exhausted). |

A `Delegation` (`dlg_…`) is a *derived* authority — never a free-standing grant.

### Enforced twice: at mint AND at execution

1. **At mint** (`POST /api/v2/delegations`) the engine attenuates against the
   delegator's current authority and refuses (`409`) any widening.
2. **At execution** the orchestrator's Phase 0.5 re-checks the **whole chain**
   link-by-link (`DelegationAwareMandateLookup` → `engine.check_chain`): every
   link must be non-revoked + within its remaining cap + in scope + non-expired.
   Any break anywhere up the chain → **DENY** before any money moves. A delegate
   spend draws down the leaf **and every ancestor** delegation (the cardinal rule
   enforced at spend time), without double-counting the root mandate.

### Revocation propagates to the whole subtree

Revoking a parent (mandate, agent, or a single delegation hop) propagates to the
**entire delegation subtree** via the propagating Revocation engine
(`DelegationSubtreeRevoker`): every descendant delegation is flipped to `revoked`
and the execution-time chain re-check denies any payment under that subtree.
Even if a downstream row were missed, the dead parent link denies the chain — so
authority is gone fail-closed regardless.

### Routes

| Route | Purpose |
| --- | --- |
| `POST /api/v2/delegations` | Mint an attenuated delegation (delegator → delegatee). Returns the delegation + its signed `DelegationEvidence`. |
| `GET /api/v2/delegations` | List this org's delegations (optional `?delegatee=`). |
| `GET /api/v2/delegations/{id}` | Fetch one hop + evidence (org-scoped). |
| `GET /api/v2/delegations/agent/{agent}/chain` | Resolve the full chain (root mandate → leaf) for an acting sub-agent. |
| `POST /api/v2/delegations/{id}/revoke` | Revoke a hop; propagates to the subtree. Returns the signed proof-of-revocation. |
| `POST /api/v2/delegations/verify` | Independently verify a `DelegationEvidence` (HMAC — the Sardis-internal tamper check). |

Signing key: `SARDIS_DELEGATION_HMAC_KEY` (HMAC-SHA256; fail-closed in
prod/staging). Money is `Decimal` token (major) units throughout.

---

## Primitive 2 — Portable Proof-of-Authority

A **signed, self-contained credential** proving that a specific action *was
authorized by Sardis*. It is emitted on **every authorized execution** (bound
onto the orchestrator's `PaymentResult.authority_proof`) and binds:

`policy_hash` + `mandate_hash` + `delegation_chain` + `decision (=ALLOWED)` +
`inputs` + `amount_minor`/`currency` + `counterparty` + `agent` + `issued_at`.

### Why it verifies OFFLINE without trusting Sardis

The HMAC proofs above are *symmetric*: verifying requires the same secret that
signed. Handing a merchant that secret would let them forge proofs. So
Proof-of-Authority signs with **Ed25519 (asymmetric)**: Sardis signs with a
**private** key; anyone verifies with the **published public** key. Possessing
the public key grants verification, never forgery — it is safe to publish in a
JWK / `.well-known` / docs.

### How a third party verifies (no Sardis access)

1. Obtain the published key once — `GET /api/v2/authority/proofs/jwk`
   (returns the JWK + `public_key_b64url`), or pin it from your own records.
2. Take the proof — either the structured JSON (`proof.to_dict()`) or the compact
   JWS envelope (`<payload_b64url>.<signature_b64url>` from `proof.to_jws()`).
3. Verify it. Offline, with any Ed25519 verifier, OR by POSTing it to
   `POST /api/v2/authority/proofs/verify` with your own copy of the public key:

   ```json
   { "proof": { ... }, "public_key": "<base64url ed25519 public key>" }
   ```

   Verification **recomputes** the canonical claim from the bound fields (the
   carried `content_hash` is never trusted) and checks the signature. Any
   tampering — a widened delegation cap, a swapped scope, a truncated or
   reordered chain, a changed amount — breaks the signature and returns
   `valid: false`.

Both verification routes are **public** (no auth) by design: a portable proof is
meant to be checked by anyone, anywhere.

Signing key: `SARDIS_AUTHORITY_PROOF_PRIVATE_KEY` — a 32-byte Ed25519 seed (hex
or base64/base64url; fail-closed in prod/staging). Money is integer **minor
units** on the proof.

---

## What is real vs. needs live keys

- **Real now (no live keys, no chain, no DB):** the attenuation algebra, the
  execution-time chain re-check, subtree revocation propagation, evidence + proof
  signing/verification, and all routes — all covered by the in-memory test suites
  (`apps/api/tests/test_delegation_api.py`,
  `packages/sardis/tests/test_delegation_*.py`,
  `packages/sardis/tests/test_authority_proof.py`). A `dev-` HMAC fallback and a
  deterministic Ed25519 dev seed run outside prod.
- **Needs configuration in prod/staging:** the three signing keys above (each
  fail-closed — a missing key refuses to sign), and Postgres for durable
  delegations (the `delegations` table, migration `110_delegations.sql`). In
  dev/in-memory mode there is no delegations table, so the mutating delegation
  routes fail closed with `503`; the public Proof-of-Authority routes need no
  engine and are always available.
