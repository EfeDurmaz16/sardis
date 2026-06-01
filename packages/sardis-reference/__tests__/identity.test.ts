import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  issueAuthorityProof,
  buildAuthorityProof,
  signAuthorityProof,
  publicKeyB64url,
  publicKeyBytes,
  publicJwk,
  devSeed,
  decodeSeed,
  reduceDelegationChain,
  computeContentHash,
  newProofId,
} from '../src/identity/authority-proof.js';
import {
  verifyAuthorityProof,
  fromJws,
  toJws,
  toCanonicalBytes,
} from '../src/verify/authority-proof.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface IdentityIssueVector {
  publicKeyB64u: string;
  jws: string;
  issuedAt: string;
  expectValid: boolean;
}
const issueVec: IdentityIssueVector = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'identity-issue.json'), 'utf8'),
);

// The Python-SIGNED proof (existing vector) — used to prove TS issue produces
// byte-identical canonical bytes for the same claim.
interface PySignedVector {
  publicKeyB64u: string;
  valid: { jws: string };
}
const pyVec: PySignedVector = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'authority-proof.json'), 'utf8'),
);

const ISSUED = '2026-01-01T12:00:00+00:00';

function fixedProofInput() {
  return {
    proofId: 'poauth_fixed_identity_1',
    actionId: 'act_ts_issue',
    agent: 'agent_b',
    amountMinor: 5_000_000n,
    currency: 'USDC',
    counterparty: 'merchant.example',
    policyHash: 'ph_abc',
    mandateHash: 'mh_def',
    spendingMandateId: 'mandate_root',
    amount: '5.0',
    inputs: { rail: 'usdc', chain: 'base', token: 'USDC', category: 'cloud' },
    delegationChain: null,
    issuedAt: ISSUED,
  };
}

describe('identity — TS issues a Proof-of-Authority that verifies offline', () => {
  it('round-trips: a TS-minted proof verifies in TS with the published key', () => {
    const proof = issueAuthorityProof(fixedProofInput());
    expect(verifyAuthorityProof(proof, publicKeyB64url(devSeed()))).toBe(true);
  });

  it('the committed TS-minted JWS (== Python-verified) re-verifies in TS', () => {
    const proof = fromJws(issueVec.jws);
    expect(verifyAuthorityProof(proof, issueVec.publicKeyB64u)).toBe(true);
  });

  it('TS issue produces a deterministic JWS for a fixed claim (matches committed vector)', () => {
    const proof = issueAuthorityProof(fixedProofInput());
    expect(toJws(proof)).toBe(issueVec.jws);
  });

  it('the moat (reverse direction): a PYTHON-signed proof has byte-identical TS canonical bytes', () => {
    // Same logical claim, signed in Python (authority-proof.json) — TS rebuilds
    // identical canonical bytes from the parsed proof. (Asserts the issue-side
    // canonicalization equals the verify-side, both equal to Python.)
    const pyProof = fromJws(pyVec.valid.jws);
    const tsBytes = toCanonicalBytes(pyProof);
    const pyBytes = Buffer.from(pyVec.valid.jws.split('.')[0]!, 'base64url');
    expect(Buffer.from(tsBytes).equals(pyBytes)).toBe(true);
  });

  it('signing then tampering the amount breaks verification', () => {
    const proof = issueAuthorityProof(fixedProofInput());
    const tampered = { ...proof, amountMinor: 9_999_999n };
    expect(verifyAuthorityProof(tampered, publicKeyB64url(devSeed()))).toBe(false);
  });

  it('signing then tampering the counterparty breaks verification', () => {
    const proof = issueAuthorityProof(fixedProofInput());
    const tampered = { ...proof, counterparty: 'attacker.example' };
    expect(verifyAuthorityProof(tampered, publicKeyB64url(devSeed()))).toBe(false);
  });

  it('a proof minted with one seed does not verify under another key', () => {
    const proof = issueAuthorityProof(fixedProofInput());
    const otherSeed = decodeSeed('11'.repeat(32));
    expect(verifyAuthorityProof(proof, publicKeyB64url(otherSeed))).toBe(false);
  });

  it('binds the delegation chain — a widened cap invalidates the signature', () => {
    const proof = issueAuthorityProof({
      ...fixedProofInput(),
      delegationChain: [
        { kind: 'mandate', ref: 'mandate_root', depth: 0, amountCap: '50', currency: 'USDC', scopeHash: 'sh0' },
        { kind: 'delegation', ref: 'dlg_1', depth: 1, amountCap: '25', currency: 'USDC', scopeHash: 'sh1' },
      ],
    });
    expect(verifyAuthorityProof(proof, publicKeyB64url(devSeed()))).toBe(true);
    const widened = {
      ...proof,
      delegationChain: proof.delegationChain.map((h) =>
        h.kind === 'delegation' ? { ...h, amountCap: '999' } : h,
      ),
    };
    expect(verifyAuthorityProof(widened, publicKeyB64url(devSeed()))).toBe(false);
  });

  it('refuses to sign a non-ALLOWED decision', () => {
    const unsigned = buildAuthorityProof(fixedProofInput());
    expect(() => signAuthorityProof({ ...unsigned, decision: 'DENIED' as never }, devSeed())).toThrow();
  });

  it('rejects float money and float inputs (no-float money path)', () => {
    expect(() => buildAuthorityProof({ ...fixedProofInput(), amountMinor: 5.5 as never })).toThrow();
    expect(() =>
      buildAuthorityProof({ ...fixedProofInput(), inputs: { ratio: 0.5 } }),
    ).toThrow();
  });

  it('content hash matches the recomputed canonical bytes hash', () => {
    const proof = issueAuthorityProof(fixedProofInput());
    expect(proof.contentHash).toBe(computeContentHash(proof));
    expect(proof.contentHash).toHaveLength(64); // sha256 hex
  });

  it('publicJwk has the expected OKP/Ed25519 shape and key helpers agree', () => {
    expect(publicKeyBytes(devSeed())).toHaveLength(32);
    expect(publicKeyB64url(devSeed())).toBe(issueVec.publicKeyB64u);
    expect(publicJwk(devSeed())).toMatchObject({
      kty: 'OKP',
      crv: 'Ed25519',
      use: 'sig',
      alg: 'EdDSA',
      x: issueVec.publicKeyB64u,
    });
  });

  it('newProofId is well-formed (poauth_<ts>_<rand>)', () => {
    expect(newProofId(new Date('2026-01-01T12:00:00Z'))).toMatch(/^poauth_[0-9a-z]+_[0-9a-f]{8}$/);
  });

  it('reduceDelegationChain normalizes hops and defaults depth by kind', () => {
    const hops = reduceDelegationChain([
      { kind: 'mandate', ref: 'm' },
      { kind: 'delegation', ref: 'd' },
    ]);
    expect(hops[0]).toMatchObject({ kind: 'mandate', depth: 0, amountCap: null });
    expect(hops[1]).toMatchObject({ kind: 'delegation', depth: 1, amountCap: null });
    expect(reduceDelegationChain(null)).toEqual([]);
  });
});
