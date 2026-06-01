/** Pure offline verifiers — proofs, evidence, and (later) protocol checks. */
export * from './canonical-json.js';
export * from './jcs.js';
export * from './authority-proof.js';

// The HMAC proofs share helper names (computeDecisionHash / computeSignature);
// re-export the verify entry points top-level and the helpers under namespaces.
export { verifyDelegationEvidence } from './delegation-evidence.js';
export { verifyRevocationProof, computeOutcome } from './revocation-proof.js';
export * as delegationEvidence from './delegation-evidence.js';
export * as revocationProof from './revocation-proof.js';
export * from './ap2.js';
export * from './drift.js';
export * from './tap.js';
export * from './x402.js';
export * from './eip712.js';
