/**
 * Agent identity — issue + verify the portable Proof-of-Authority.
 *
 * The issue side (sign) mirrors `AuthorityProof.sign` / `build_authority_proof`
 * and the key helpers; the verify side is re-exported from `../verify` so a
 * consumer importing `@sardis/reference/identity` gets the full symmetric
 * surface: a TS-issued proof verifies in Python and vice-versa, both signing
 * byte-identical canonical claims.
 */
export {
  newProofId,
  decodeSeed,
  devSeed,
  publicKeyBytes,
  publicKeyB64url,
  publicJwk,
  reduceDelegationChain,
  computeContentHash,
  buildAuthorityProof,
  signAuthorityProof,
  issueAuthorityProof,
  type ChainLink,
  type IssueAuthorityProofInput,
} from './authority-proof.js';

// Verify side (offline, published-key-only) — re-exported for symmetry.
export {
  verifyAuthorityProof,
  fromJws,
  toJws,
  toCanonicalBytes,
  canonicalString,
  buildClaim,
} from '../verify/authority-proof.js';
