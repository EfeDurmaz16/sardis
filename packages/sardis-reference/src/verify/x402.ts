/**
 * x402 / ERC-3009 authorization verification — mirror of
 * `verify_transfer_authorization` / `validate_authorization_timing`.
 *
 * Dependency-light split (per founder sign-off on deps):
 *   - `validateAuthorizationTiming` — pure timing window check (full fidelity).
 *   - `eip712Digest` (eip712.ts) — the exact bytes the signer committed to.
 *   - `verifyTimingAndBinding(auth, recoveredSigner, ...)` — timing + binding
 *     (signer == auth.from, signer == expectedPayer) given a CALLER-SUPPLIED
 *     recovered signer address. The secp256k1 ecrecover step itself is NOT
 *     bundled (it would add @noble/curves, a 3rd dependency — flagged for
 *     founder sign-off). With @noble/curves, a caller computes
 *     `recoverAddress(eip712Digest(auth, network), signature)` and passes the
 *     result here for the complete check.
 */
import type { ERC3009Authorization, X402VerificationResult } from '../types/x402.js';
import { eip712Digest } from './eip712.js';

/** Mirrors `validate_authorization_timing` exactly. */
export function validateAuthorizationTiming(
  auth: ERC3009Authorization,
  now?: number,
): X402VerificationResult {
  const current = now ?? Math.floor(Date.now() / 1000);
  if (auth.validAfter >= auth.validBefore) {
    return { ok: false, reason: 'valid_after_must_be_before_valid_before' };
  }
  if (current < auth.validAfter) {
    return { ok: false, reason: 'authorization_not_yet_valid' };
  }
  if (current >= auth.validBefore) {
    return { ok: false, reason: 'authorization_expired' };
  }
  return { ok: true };
}

export interface VerifyBindingOptions {
  network: string;
  expectedPayer?: string;
  now?: number;
}

/**
 * Verify timing + signer binding. Mirrors the non-crypto half of
 * `verify_transfer_authorization`: timing → signer == auth.from → signer ==
 * expectedPayer. The `recoveredSigner` is supplied by the caller (recovered
 * from `eip712Digest(auth, network)` + the signature via secp256k1 ecrecover).
 */
export function verifyTimingAndBinding(
  auth: ERC3009Authorization,
  recoveredSigner: string,
  opts: VerifyBindingOptions,
): X402VerificationResult {
  const ts = validateAuthorizationTiming(auth, opts.now);
  if (!ts.ok) {
    return ts;
  }
  // Touch the digest to validate the network/domain resolves (mirrors the
  // domain-binding precondition of the Python recover step).
  eip712Digest(auth, opts.network);

  if (recoveredSigner.toLowerCase() !== auth.fromAddress.toLowerCase()) {
    return { ok: false, reason: 'signer_mismatch_authorization_from' };
  }
  if (opts.expectedPayer != null && recoveredSigner.toLowerCase() !== opts.expectedPayer.toLowerCase()) {
    return { ok: false, reason: 'signer_mismatch_payer_address' };
  }
  return { ok: true };
}
