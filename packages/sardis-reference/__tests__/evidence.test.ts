import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { verifyDelegationEvidence } from '../src/verify/delegation-evidence.js';
import { verifyRevocationProof, computeOutcome } from '../src/verify/revocation-proof.js';
import type { DelegationEvidence } from '../src/types/delegation.js';
import type { RevocationProof, KillStatus } from '../src/types/revocation.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

const delVec: { secret: string; valid: DelegationEvidence; expectValid: boolean } = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'delegation-evidence.json'), 'utf8'),
);

const revVec: {
  secret: string;
  valid: RevocationProof;
  expectValid: boolean;
  outcomeMatrix: { statuses: KillStatus[]; expected: string }[];
} = JSON.parse(readFileSync(join(__dirname, 'vectors', 'revocation-proof.json'), 'utf8'));

describe('verifyDelegationEvidence — Python signs, TS verifies (HMAC tamper-evidence)', () => {
  it('verifies a delegation evidence signed in Python with the shared secret', () => {
    expect(verifyDelegationEvidence(delVec.valid, delVec.secret)).toBe(true);
  });

  it('rejects a one-byte tamper to a bound field', () => {
    const tampered: DelegationEvidence = { ...delVec.valid, amountCap: '999' };
    expect(verifyDelegationEvidence(tampered, delVec.secret)).toBe(false);
  });

  it('rejects with the wrong secret', () => {
    expect(verifyDelegationEvidence(delVec.valid, 'wrong-secret')).toBe(false);
  });
});

describe('verifyRevocationProof + computeOutcome (fail-closed)', () => {
  it('verifies a revocation proof signed in Python', () => {
    expect(verifyRevocationProof(revVec.valid, revVec.secret)).toBe(true);
  });

  it('rejects a tampered target list (truncation)', () => {
    const tampered: RevocationProof = { ...revVec.valid, targets: revVec.valid.targets.slice(0, 1) };
    expect(verifyRevocationProof(tampered, revVec.secret)).toBe(false);
  });

  it('rejects with the wrong secret', () => {
    expect(verifyRevocationProof(revVec.valid, 'nope')).toBe(false);
  });

  it('computeOutcome matches Python on a mixed kill-status matrix', () => {
    for (const row of revVec.outcomeMatrix) {
      const targets = row.statuses.map((s, i) => ({ kind: 'mandate' as const, ref: `m${i}`, killStatus: s }));
      expect(computeOutcome(targets)).toBe(row.expected);
    }
  });

  it('computeOutcome is fail-closed: any unconfirmed → blocked_pending_downstream', () => {
    expect(computeOutcome([{ kind: 'mandate', ref: 'm', killStatus: 'killed' }])).toBe('propagated');
    expect(computeOutcome([{ kind: 'mandate', ref: 'm', killStatus: 'blocked_pending' }])).toBe('blocked_pending_downstream');
    expect(computeOutcome([{ kind: 'mandate', ref: 'm', killStatus: 'failed' }])).toBe('blocked_pending_downstream');
  });
});
