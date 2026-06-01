import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { verifyAuthorityProof, fromJws, toCanonicalBytes, publicJwk } from '../src/verify/authority-proof.js';
import { b64urlDecode } from '../src/crypto/base64url.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface AuthorityProofVectors {
  publicKeyB64u: string;
  valid: { jws: string; expectValid: boolean };
  tampered_amount: { jws: string; expectValid: boolean };
  tampered_counterparty: { jws: string; expectValid: boolean };
  wrong_key: { jws: string; publicKeyB64u: string; expectValid: boolean };
}

const vec: AuthorityProofVectors = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'authority-proof.json'), 'utf8'),
);

describe('verifyAuthorityProof — the moat: Python signs, TS verifies offline', () => {
  it('a proof signed in Python verifies in TS with only the published key', () => {
    const proof = fromJws(vec.valid.jws);
    expect(verifyAuthorityProof(proof, vec.publicKeyB64u)).toBe(true);
  });

  it('TS recomputes the EXACT canonical bytes that Python signed (byte-identical)', () => {
    const proof = fromJws(vec.valid.jws);
    const tsCanonical = toCanonicalBytes(proof);
    // The JWS payload IS the canonical bytes Python signed.
    const payloadB64 = vec.valid.jws.split('.')[0]!;
    const pyCanonical = b64urlDecode(payloadB64);
    expect(Buffer.from(tsCanonical).equals(Buffer.from(pyCanonical))).toBe(true);
  });

  it('rejects a tampered amount (claim patched, original signature kept)', () => {
    const proof = fromJws(vec.tampered_amount.jws);
    expect(verifyAuthorityProof(proof, vec.publicKeyB64u)).toBe(false);
  });

  it('rejects a tampered counterparty', () => {
    const proof = fromJws(vec.tampered_counterparty.jws);
    expect(verifyAuthorityProof(proof, vec.publicKeyB64u)).toBe(false);
  });

  it('rejects verification with the wrong public key', () => {
    const proof = fromJws(vec.wrong_key.jws);
    expect(verifyAuthorityProof(proof, vec.wrong_key.publicKeyB64u)).toBe(false);
  });

  it('rejects a non-ALLOWED decision and a missing signature', () => {
    const proof = fromJws(vec.valid.jws);
    expect(verifyAuthorityProof({ ...proof, decision: 'DENIED' as never }, vec.publicKeyB64u)).toBe(false);
    expect(verifyAuthorityProof({ ...proof, signature: '' }, vec.publicKeyB64u)).toBe(false);
  });

  it('rejects a truncated / reordered delegation chain by re-deriving the claim', () => {
    const proof = fromJws(vec.valid.jws);
    // Inject a delegation hop the signer never bound — must fail.
    const widened = {
      ...proof,
      delegationChain: [
        { kind: 'delegation' as const, ref: 'dlg_injected', depth: 1, amountCap: '999', currency: 'USDC', scopeHash: 'x' },
      ],
    };
    expect(verifyAuthorityProof(widened, vec.publicKeyB64u)).toBe(false);
  });

  it('publicJwk has the expected OKP/Ed25519 shape', () => {
    const jwk = publicJwk(vec.publicKeyB64u);
    expect(jwk).toMatchObject({ kty: 'OKP', crv: 'Ed25519', use: 'sig', alg: 'EdDSA', x: vec.publicKeyB64u });
  });
});
