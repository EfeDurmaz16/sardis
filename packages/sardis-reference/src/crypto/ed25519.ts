/**
 * Ed25519 — thin wrapper over `@noble/ed25519`, with the SHA-512 sync hook wired
 * once so synchronous verify/sign work (noble v3 requires this for sync APIs).
 *
 * Matches the Python `cryptography` Ed25519 path used by `AuthorityProof`.
 */
import * as ed from '@noble/ed25519';
import { sha512 } from '@noble/hashes/sha2.js';

// Wire the synchronous SHA-512 hook required by @noble/ed25519 v3 sync APIs.
// Idempotent — assigning the same function twice is harmless.
ed.hashes.sha512 = sha512;

/** Verify a raw Ed25519 signature over `message` with a raw 32-byte public key. */
export function verifyEd25519(
  signature: Uint8Array,
  message: Uint8Array,
  publicKey: Uint8Array,
): boolean {
  try {
    return ed.verify(signature, message, publicKey);
  } catch {
    return false;
  }
}

/** Sign `message` with a raw 32-byte Ed25519 private seed. (Test/dev use.) */
export function signEd25519(message: Uint8Array, privateSeed: Uint8Array): Uint8Array {
  return ed.sign(message, privateSeed);
}

/** Derive the raw 32-byte public key from a raw 32-byte private seed. */
export function publicKeyFromSeed(privateSeed: Uint8Array): Uint8Array {
  return ed.getPublicKey(privateSeed);
}
