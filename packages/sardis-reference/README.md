# @sardis/reference

**How Sardis decides if an agent may spend** — a pure, deterministic, money-free
TypeScript mirror of the Sardis authority-decision and protocol-verification
logic.

AI agents can reason, but they cannot be trusted with money. Before Sardis moves
a single cent, a payment passes through a decision engine: per-transaction caps,
lifetime totals, merchant allow/deny lists, blocked categories, approval
thresholds, attenuated delegation, and protocol verification (AP2 mandate chains,
TAP identity, x402/EIP-3009 authorizations). **This package is that decision
logic, open and offline.**

It lets anyone:

- run the **policy simulator** against a proposed spend and get
  `allow | requires_approval | deny` + a reason code — offline, no backend call;
- **offline-verify** a portable AuthorityProof, an AP2 mandate chain, a TAP
  request, and an x402 (EIP-3009) authorization — with **zero money at risk**.

## What it is NOT

This is **not** the money-mover. There is no RPC, no provider client, no
database, no key custody, no `fetch`. It never executes a payment. The private
Sardis backend owns execution; this package owns the *decision contract* and lets
the ecosystem audit it. Every decision/verify function is a pure function of its
inputs (plus an injectable `now` for determinism).

## Install

```bash
npm install @sardis/reference
```

Two zero-dependency MIT crypto libraries come along: `@noble/ed25519` (proof
verification) and `@noble/hashes` (SHA-256 / HMAC / keccak256). Nothing else.

## "Would Sardis allow this?" — the simulator

```ts
import { simulateSpend, createDefaultPolicy } from '@sardis/reference';

// A LOW-trust policy: $50/tx, $100/day, ... (minor units, 2 decimals).
const policy = createDefaultPolicy('agent_123', 'low');
policy.approvalThreshold = { minor: 4_000n, currency: 'USDC' }; // $40

// $30 → allowed
simulateSpend(policy, { amount: { minor: 3_000n, currency: 'USDC' } });
// → { outcome: 'allow', reason: 'OK' }

// $45 → over the approval threshold, under the per-tx cap → needs a human
simulateSpend(policy, { amount: { minor: 4_500n, currency: 'USDC' } });
// → { outcome: 'requires_approval', reason: 'requires_approval' }

// $80 → over the $50 per-tx cap → denied
simulateSpend(policy, { amount: { minor: 8_000n, currency: 'USDC' } });
// → { outcome: 'deny', reason: 'per_transaction_limit' }
```

The reason codes and check order are a byte-for-byte mirror of the production
Python engine (`SpendingPolicy.validate_payment`). The checks that need live
state — on-chain balance, DB velocity, KYA attestation, merchant trust — are
expressed as **ports** (`WalletPort`, `PolicyStatePort`, `KyaPort`,
`MerchantTrustPort`, …) the private backend implements, and are omitted here
exactly as the synchronous Python path omits them.

## Offline proof verification — the moat

A merchant, auditor, or regulator verifies that an action *was authorized* using
only a **published public key** — no Sardis, no database, no live system:

```ts
import { fromJws, verifyAuthorityProof } from '@sardis/reference';

const proof = fromJws(jwsFromSardis);          // "<payload>.<signature>"
const ok = verifyAuthorityProof(proof, publishedEd25519PublicKeyB64url);
// true iff the Ed25519 signature is valid over the canonical claim.
// Any tamper — a widened amount, a reordered/truncated delegation hop, the
// wrong key — makes this false.
```

## Mandates, delegation, and protocol verifiers

```ts
import {
  checkMandate,        // SpendingMandate.check_payment mirror (MANDATE_* codes)
  checkAttenuation,    // delegation cardinal rule (cap/expiry/scope/depth)
  resolveChain,        // fail-closed whole-chain re-check
  verifyChainStructure,// AP2 Intent→Cart→Payment structural verification
  verifyTapRequest,    // TAP Signature-Input structural verification
  validateAuthorizationTiming, // x402 / ERC-3009 timing window
  eip712Digest,        // x402 EIP-712 signing digest (byte-identical to chain)
} from '@sardis/reference';
```

## Fidelity guarantee

The acceptance bar is **cross-language fidelity, not just "tests pass"**. Golden
vectors are generated from the production Python implementation and committed
under `__tests__/vectors/`; the TS suite asserts identical decisions and
**byte-identical** canonical signing bytes. A proof signed in Python verifies in
TS; an EIP-712 digest computed in TS equals the one the chain signs.

## License

MIT.
