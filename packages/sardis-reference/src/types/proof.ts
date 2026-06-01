/**
 * ProofOfAuthority — portable, offline-verifiable Proof-of-Authority.
 *
 * Mirrors `AuthorityProof` field-for-field: canonical claim, sorted delegation
 * chain, Ed25519 signature over the canonical bytes, JWS envelope.
 */

export interface DelegationChainHop {
  kind: 'mandate' | 'delegation';
  ref: string;
  depth: number;
  /** token units as a string, or null. */
  amountCap: string | null;
  currency: string;
  scopeHash: string;
}

export interface ProofOfAuthority {
  typ: 'sardis-authority-proof+v1';
  alg: 'EdDSA';
  issuer: string;
  proofId: string;
  actionId: string;
  agent: string;
  /** Money in minor units (integer, never float). */
  amountMinor: bigint;
  /** token-major display string, also bound into the claim. */
  amount: string;
  currency: string;
  counterparty: string;
  policyHash: string;
  mandateHash: string;
  spendingMandateId: string;
  decision: 'ALLOWED';
  /** RFC3339 timestamp. */
  issuedAt: string;
  /** Canonicalized evaluated inputs (no floats, sorted). */
  inputs: Record<string, unknown>;
  delegationChain: DelegationChainHop[];
  contentHash: string;
  /** base64url EdDSA signature over the canonical claim. */
  signature: string;
}
