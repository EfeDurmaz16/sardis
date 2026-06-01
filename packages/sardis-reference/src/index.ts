/**
 * @sardis/reference — how Sardis decides if an agent may spend.
 *
 * Pure, deterministic, money-free TS mirror of the Sardis authority-decision
 * and protocol-verification logic. No network, no provider clients, no DB, no
 * key custody, no `fetch`. It never executes a payment — the private backend
 * owns execution; this package owns the decision contract so the ecosystem can
 * audit it offline.
 *
 * Public surface:
 *   - types   : the authority-primitive contract (Money, SpendObject,
 *               SpendingPolicy, Mandate, Delegation, Revocation,
 *               ProofOfAuthority, AP2/TAP/x402 types, 9 ProviderPorts).
 *   - policy  : simulateSpend / checkExecutionContext / checkMandate /
 *               checkAttenuation / resolveChain  (the decision engine).
 *   - verify  : verifyAuthorityProof / verifyDelegationEvidence /
 *               verifyRevocationProof / verifyChainStructure / computeDrift /
 *               verifyTapRequest / validateAuthorizationTiming /
 *               verifyTimingAndBinding / eip712Digest  (the verifiers).
 */

export * from './types/index.js';
export * from './policy/index.js';
export * from './verify/index.js';
export * as identity from './identity/index.js';
