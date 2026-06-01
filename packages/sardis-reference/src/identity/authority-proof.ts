/**
 * Agent identity — the ISSUE side of the portable Proof-of-Authority.
 *
 * This is the TS mirror of `AuthorityProof.sign` / `build_authority_proof` /
 * `reduce_delegation_chain` and the key helpers in the Python
 * `sardis.core.authority_proof`. The verify side already lives in
 * `../verify/authority-proof.ts`; this module lets a TS-side issuer (an agent
 * runtime, an MCP server, a test harness) MINT a proof that the Python side
 * verifies, and vice-versa, because both sign byte-identical canonical claims.
 *
 * It is pure and money-free: it signs a *claim about authority*, it never moves
 * money. The Ed25519 private seed is supplied by the caller — there is NO env /
 * key custody in this package (the production signing key lives in the private
 * backend, fail-closed; this is the open mirror of the algorithm only).
 *
 * Asymmetric (Ed25519), not HMAC: Sardis signs with a private key, anyone
 * verifies with the published public key — possessing the public key grants
 * verification, never forgery.
 */
import type { ProofOfAuthority, DelegationChainHop } from '../types/proof.js';
import { toCanonicalBytes } from '../verify/authority-proof.js';
import { b64urlEncode } from '../crypto/base64url.js';
import { signEd25519, publicKeyFromSeed } from '../crypto/ed25519.js';
import { sha256Hex } from '../crypto/hmac.js';

const TYP = 'sardis-authority-proof+v1' as const;
const ALG = 'EdDSA' as const;
const ISSUER = 'sardis';

/** base36 of a non-negative integer — mirrors Python `_to_base36`. */
function toBase36(num: number): string {
  const chars = '0123456789abcdefghijklmnopqrstuvwxyz';
  if (num === 0) return '0';
  let n = num;
  let out = '';
  while (n > 0) {
    out = chars[n % 36]! + out;
    n = Math.floor(n / 36);
  }
  return out;
}

/** Random 4-byte hex token (8 chars), mirrors Python `secrets.token_hex(4)`. */
function randomHex4(): string {
  const bytes = new Uint8Array(4);
  if (typeof globalThis.crypto?.getRandomValues === 'function') {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 4; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

/** `poauth_<base36 ts>_<rand>` — mirrors Python `new_proof_id`. */
export function newProofId(now: Date = new Date()): string {
  const ts = toBase36(Math.floor(now.getTime() / 1000));
  return `poauth_${ts}_${randomHex4()}`;
}

/**
 * Decode a 32-byte Ed25519 private seed from a raw `Uint8Array`, a 64-char hex
 * string, or base64/base64url. Mirrors Python `_decode_seed`.
 */
export function decodeSeed(raw: Uint8Array | string): Uint8Array {
  if (raw instanceof Uint8Array) {
    if (raw.length !== 32) throw new Error('Ed25519 seed must be 32 bytes');
    return raw;
  }
  const s = raw.trim();
  // hex (64 chars)
  if (/^[0-9a-fA-F]{64}$/.test(s)) {
    const out = new Uint8Array(32);
    for (let i = 0; i < 32; i++) out[i] = parseInt(s.slice(i * 2, i * 2 + 2), 16);
    return out;
  }
  // base64 / base64url
  try {
    const b = b64urlDecodeLocal(s);
    if (b.length === 32) return b;
  } catch {
    /* fall through */
  }
  throw new Error(
    'Ed25519 seed must be a 32-byte value as raw bytes, hex (64 chars), or base64/base64url.',
  );
}

function b64urlDecodeLocal(value: string): Uint8Array {
  const padLen = (4 - (value.length % 4)) % 4;
  const b64 = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(padLen);
  if (typeof atob === 'function') {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  return new Uint8Array(Buffer.from(b64, 'base64'));
}

/**
 * The deterministic DEV seed — identical to Python `_dev_seed`
 * (`sha256(b"dev-authority-proof-key")`). TEST/DEV ONLY: production signing
 * never uses this (the private backend fails closed without an env key).
 */
export function devSeed(): Uint8Array {
  // sha256("dev-authority-proof-key") — precomputed to avoid a sync hash import here.
  return decodeSeed('3e8e6c406e3651a5131e2b737a6ec389a561df22decf98f7e80e67c276917c0c');
}

/** The raw 32-byte public key for a seed (mirrors `public_key_bytes`). */
export function publicKeyBytes(seed: Uint8Array | string): Uint8Array {
  return publicKeyFromSeed(decodeSeed(seed));
}

/** The published public key as base64url (mirrors `public_key_b64url`). */
export function publicKeyB64url(seed: Uint8Array | string): string {
  return b64urlEncode(publicKeyBytes(seed));
}

/** The published verification key as a JWK (mirrors `public_jwk`). */
export function publicJwk(
  seed: Uint8Array | string,
  kid = 'sardis-authority-proof',
): Record<string, string> {
  return { kty: 'OKP', crv: 'Ed25519', x: publicKeyB64url(seed), kid, use: 'sig', alg: 'EdDSA' };
}

/** A resolved delegation-chain link as the orchestrator hands it in. */
export interface ChainLink {
  kind: 'mandate' | 'delegation';
  ref?: string;
  depth?: number;
  /** token-unit cap as a string, or null. */
  amountCap?: string | null;
  currency?: string;
  scopeHash?: string;
}

/**
 * Reduce a resolved chain to its bound authority facts (mirrors
 * `reduce_delegation_chain`). The inputs are already the per-hop facts; this
 * normalizes them to the exact shape that gets bound into the claim. Any tamper
 * (widened cap, swapped scope, truncation, reorder) invalidates the signature.
 */
export function reduceDelegationChain(chain: ChainLink[] | null | undefined): DelegationChainHop[] {
  if (!chain || chain.length === 0) return [];
  return chain.map((link) => ({
    kind: link.kind,
    ref: link.ref ?? '',
    depth: (link.depth ?? (link.kind === 'mandate' ? 0 : 1)) | 0,
    amountCap: link.amountCap ?? null,
    currency: link.currency ?? '',
    scopeHash: link.scopeHash ?? '',
  }));
}

/** Compute the SHA-256 content hash (hex) over the canonical claim bytes. */
export function computeContentHash(proof: ProofOfAuthority): string {
  return sha256Hex(toCanonicalBytes(proof));
}

export interface IssueAuthorityProofInput {
  actionId: string;
  agent: string;
  /** Money in minor units (integer, never float). */
  amountMinor: bigint | number | string;
  currency: string;
  counterparty: string;
  policyHash?: string;
  mandateHash?: string;
  spendingMandateId?: string;
  /** token-major display string; defaults to the minor amount stringified. */
  amount?: string;
  inputs?: Record<string, unknown>;
  delegationChain?: ChainLink[] | null;
  /** RFC3339 timestamp; defaults to now (UTC, ISO). */
  issuedAt?: string;
  /** override the generated proof id (tests / determinism). */
  proofId?: string;
}

function asMinor(value: bigint | number | string): bigint {
  if (typeof value === 'bigint') return value;
  if (typeof value === 'number') {
    if (!Number.isInteger(value)) {
      throw new TypeError('float amounts are forbidden on authority-proof money paths');
    }
    return BigInt(value);
  }
  return BigInt(value);
}

/**
 * Build an UNSIGNED proof claim from the issue input. Floats in `inputs` are
 * rejected exactly as the Python path does.
 */
export function buildAuthorityProof(input: IssueAuthorityProofInput): ProofOfAuthority {
  const minor = asMinor(input.amountMinor);
  const inputs = input.inputs ?? {};
  for (const [k, v] of Object.entries(inputs)) {
    if (typeof v === 'number' && !Number.isInteger(v)) {
      throw new TypeError(`float input ${JSON.stringify(k)} forbidden on authority-proof path`);
    }
  }
  return {
    typ: TYP,
    alg: ALG,
    issuer: ISSUER,
    proofId: input.proofId ?? newProofId(),
    actionId: input.actionId,
    agent: input.agent,
    amountMinor: minor,
    amount: input.amount ?? minor.toString(),
    currency: input.currency,
    counterparty: input.counterparty,
    policyHash: input.policyHash ?? '',
    mandateHash: input.mandateHash ?? '',
    spendingMandateId: input.spendingMandateId ?? '',
    decision: 'ALLOWED',
    issuedAt: input.issuedAt ?? new Date().toISOString().replace('Z', '+00:00'),
    inputs,
    delegationChain: reduceDelegationChain(input.delegationChain),
    contentHash: '',
    signature: '',
  };
}

/**
 * Sign an (unsigned) proof claim with an Ed25519 private seed, mutating it in
 * place with the content hash + base64url signature (mirrors
 * `AuthorityProof.sign`). Returns the same object for chaining.
 */
export function signAuthorityProof(
  proof: ProofOfAuthority,
  seed: Uint8Array | string,
): ProofOfAuthority {
  if (proof.decision !== 'ALLOWED') {
    throw new Error('AuthorityProof is only emitted for ALLOWED decisions');
  }
  const bytes = toCanonicalBytes(proof);
  proof.contentHash = sha256Hex(bytes);
  const sig = signEd25519(bytes, decodeSeed(seed));
  proof.signature = b64urlEncode(sig);
  return proof;
}

/**
 * Build + sign a portable Proof-of-Authority for an ALLOWED action — the TS
 * mirror of `build_authority_proof`. A proof minted here verifies in Python
 * (and via `verifyAuthorityProof`) with only the published public key.
 */
export function issueAuthorityProof(
  input: IssueAuthorityProofInput,
  seed: Uint8Array | string = devSeed(),
): ProofOfAuthority {
  return signAuthorityProof(buildAuthorityProof(input), seed);
}
