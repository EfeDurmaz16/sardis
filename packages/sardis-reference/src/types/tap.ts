/**
 * TAP (Trusted Agent Protocol) types — structural identity verification.
 *
 * Mirrors `protocol/tap.py`.
 */

export const TAP_ALLOWED_TAGS = ['agent-browser-auth', 'agent-payer-auth'] as const;
export const TAP_ALLOWED_MESSAGE_ALGS = ['ed25519', 'ecdsa-p256'] as const;
export const TAP_MAX_TIME_WINDOW_SECONDS = 8 * 60;
export const TAP_SUPPORTED_VERSIONS = ['1.0'] as const;

export interface TapSignatureInput {
  label: string;
  components: string[];
  created: number;
  expires: number;
  keyid: string;
  alg: string;
  nonce: string;
  tag: string;
}

export interface TapVerificationResult {
  accepted: boolean;
  reason?: string;
  signatureInput?: TapSignatureInput;
  signatureB64?: string;
  signatureBase?: string;
}
