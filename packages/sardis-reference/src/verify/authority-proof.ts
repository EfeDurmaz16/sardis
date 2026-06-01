/**
 * verifyAuthorityProof — offline, trustless verification of a portable
 * Proof-of-Authority with only a PUBLISHED public key. Mirrors
 * `AuthorityProof.verify` / `_claim` / `_canonical_bytes` / `from_jws`.
 *
 * The canonical claim is recomputed from the bound fields (the carried
 * `contentHash`/`signature` are never trusted for the claim contents), then the
 * Ed25519 signature is checked over the canonical bytes. Returns false on a
 * tampered field, a widened/reordered/truncated delegation chain, a wrong key,
 * a missing signature, or a non-ALLOWED decision.
 */
import type { ProofOfAuthority, DelegationChainHop } from '../types/proof.js';
import { canonicalize, canonicalBytes, type CanonicalValue } from './canonical-json.js';
import { b64urlEncode, b64urlDecode } from '../crypto/base64url.js';
import { verifyEd25519 } from '../crypto/ed25519.js';

const TYP = 'sardis-authority-proof+v1';
const ALG = 'EdDSA';

/** Stable, sorted view of the evaluated inputs — mirrors `_canonical_inputs`. */
function canonicalInputs(inputs: Record<string, unknown>): Record<string, CanonicalValue> {
  const out: Record<string, CanonicalValue> = {};
  for (const k of Object.keys(inputs).sort()) {
    const v = inputs[k];
    if (typeof v === 'number' && !Number.isInteger(v)) {
      throw new TypeError(`float input ${JSON.stringify(k)} forbidden on authority-proof path`);
    }
    out[String(k)] = v as CanonicalValue;
  }
  return out;
}

/** Rebuild the exact immutable claim that is hashed and signed (mirrors `_claim`). */
export function buildClaim(proof: ProofOfAuthority): Record<string, CanonicalValue> {
  const sortedChain = [...proof.delegationChain].sort((a, b) => {
    const da = a.depth | 0;
    const db = b.depth | 0;
    if (da !== db) return da - db;
    if (a.kind !== b.kind) return a.kind < b.kind ? -1 : 1;
    if (a.ref !== b.ref) return a.ref < b.ref ? -1 : 1;
    return 0;
  });
  return {
    typ: proof.typ,
    alg: proof.alg,
    issuer: proof.issuer,
    proof_id: proof.proofId,
    action_id: proof.actionId,
    agent: proof.agent,
    // amount_minor is an integer in the Python claim. bigint within JS-safe
    // range serializes identically; larger values still serialize as digits.
    amount_minor: proof.amountMinor,
    amount: proof.amount,
    currency: proof.currency,
    counterparty: proof.counterparty,
    policy_hash: proof.policyHash,
    mandate_hash: proof.mandateHash,
    spending_mandate_id: proof.spendingMandateId,
    decision: proof.decision,
    issued_at: proof.issuedAt,
    inputs: canonicalInputs(proof.inputs),
    delegation_chain: sortedChain.map((h: DelegationChainHop) => ({
      kind: h.kind,
      ref: h.ref,
      depth: h.depth | 0,
      amount_cap: h.amountCap,
      currency: h.currency,
      scope_hash: h.scopeHash,
    })),
  };
}

/** The canonical bytes that were signed. */
export function toCanonicalBytes(proof: ProofOfAuthority): Uint8Array {
  return canonicalBytes(buildClaim(proof));
}

/** Recompute the SHA-256 content hash (hex). Exposed for parity checks. */
export function canonicalString(proof: ProofOfAuthority): string {
  return canonicalize(buildClaim(proof));
}

/** Verify with a PUBLISHED Ed25519 public key (raw 32 bytes, hex, or base64url). */
export function verifyAuthorityProof(proof: ProofOfAuthority, publicKey: Uint8Array | string): boolean {
  if (!proof.signature || proof.decision !== 'ALLOWED') {
    return false;
  }
  const pub = coercePublicKey(publicKey);
  let sig: Uint8Array;
  try {
    sig = b64urlDecode(proof.signature);
  } catch {
    return false;
  }
  return verifyEd25519(sig, toCanonicalBytes(proof), pub);
}

function coercePublicKey(publicKey: Uint8Array | string): Uint8Array {
  if (publicKey instanceof Uint8Array) return publicKey;
  // try base64url, then hex (mirrors `_coerce_public_key`)
  try {
    const b = b64urlDecode(publicKey);
    if (b.length === 32) return b;
  } catch {
    /* fall through to hex */
  }
  return hexToBytes(publicKey);
}

function hexToBytes(hex: string): Uint8Array {
  const h = hex.startsWith('0x') ? hex.slice(2) : hex;
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

/**
 * Parse a compact JWS envelope `<payload_b64url>.<signature_b64url>` into a
 * ProofOfAuthority. Mirrors `AuthorityProof.from_jws`.
 */
export function fromJws(token: string): ProofOfAuthority {
  const dot = token.indexOf('.');
  if (dot < 0) {
    throw new Error('malformed authority-proof token');
  }
  const payloadB64 = token.slice(0, dot);
  const signature = token.slice(dot + 1);
  const claim = JSON.parse(new TextDecoder().decode(b64urlDecode(payloadB64))) as Record<string, unknown>;
  return {
    typ: (claim.typ as ProofOfAuthority['typ']) ?? TYP,
    alg: (claim.alg as ProofOfAuthority['alg']) ?? ALG,
    issuer: (claim.issuer as string) ?? 'sardis',
    proofId: claim.proof_id as string,
    actionId: claim.action_id as string,
    agent: claim.agent as string,
    amountMinor: BigInt((claim.amount_minor as number | string) ?? 0),
    amount: (claim.amount as string) ?? '',
    currency: (claim.currency as string) ?? '',
    counterparty: (claim.counterparty as string) ?? '',
    policyHash: (claim.policy_hash as string) ?? '',
    mandateHash: (claim.mandate_hash as string) ?? '',
    spendingMandateId: (claim.spending_mandate_id as string) ?? '',
    decision: (claim.decision as 'ALLOWED') ?? 'ALLOWED',
    issuedAt: claim.issued_at as string,
    inputs: (claim.inputs as Record<string, unknown>) ?? {},
    delegationChain: ((claim.delegation_chain as Record<string, unknown>[]) ?? []).map((h) => ({
      kind: h.kind as DelegationChainHop['kind'],
      ref: h.ref as string,
      depth: (h.depth as number) | 0,
      amountCap: (h.amount_cap as string | null) ?? null,
      currency: (h.currency as string) ?? '',
      scopeHash: (h.scope_hash as string) ?? '',
    })),
    contentHash: '',
    signature,
  };
}

/** Serialize a proof to the compact JWS envelope (mirrors `to_jws`). */
export function toJws(proof: ProofOfAuthority): string {
  if (!proof.signature) {
    throw new Error('proof is unsigned');
  }
  return `${b64urlEncode(toCanonicalBytes(proof))}.${proof.signature}`;
}

/** The published verification key as a JWK (mirrors `public_jwk`). */
export function publicJwk(xB64url: string, kid = 'sardis-authority-proof'): Record<string, string> {
  return { kty: 'OKP', crv: 'Ed25519', x: xB64url, kid, use: 'sig', alg: 'EdDSA' };
}
