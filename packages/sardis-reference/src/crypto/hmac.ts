/**
 * HMAC-SHA256 + SHA-256 helpers over `@noble/hashes`.
 *
 * Mirrors the Python `hmac.new(key, msg, hashlib.sha256)` /
 * `hashlib.sha256(...).hexdigest()` used by DelegationEvidence / RevocationProof.
 */
import { hmac } from '@noble/hashes/hmac.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { bytesToHex } from '@noble/hashes/utils.js';

const ENCODER = new TextEncoder();

/** Hex SHA-256 of a UTF-8 string (mirrors `hashlib.sha256(s.encode()).hexdigest()`). */
export function sha256Hex(input: string | Uint8Array): string {
  const bytes = typeof input === 'string' ? ENCODER.encode(input) : input;
  return bytesToHex(sha256(bytes));
}

/** Hex HMAC-SHA256 (mirrors `hmac.new(key, msg, sha256).hexdigest()`). */
export function hmacSha256Hex(key: string | Uint8Array, msg: string | Uint8Array): string {
  const keyBytes = typeof key === 'string' ? ENCODER.encode(key) : key;
  const msgBytes = typeof msg === 'string' ? ENCODER.encode(msg) : msg;
  return bytesToHex(hmac(sha256, keyBytes, msgBytes));
}

/** Constant-time string compare (mirrors `hmac.compare_digest`). */
export function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}
