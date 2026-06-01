import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { verifyTapRequest, parseSignatureInput } from '../src/verify/tap.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface TapVector {
  name: string;
  signatureInput: string;
  signature: string;
  now: number;
  expected: { accepted: boolean; reason: string | null };
}

const vectors: TapVector[] = JSON.parse(readFileSync(join(__dirname, 'vectors', 'tap.json'), 'utf8'));

describe('verifyTapRequest — structural (vs Python validate_tap_headers)', () => {
  for (const v of vectors) {
    it(`${v.name} → accepted=${v.expected.accepted} reason=${v.expected.reason ?? '(none)'}`, () => {
      const res = verifyTapRequest(v.signatureInput, v.signature, { now: v.now, nonceCache: new Set() });
      expect(res.accepted).toBe(v.expected.accepted);
      expect(res.reason ?? null).toBe(v.expected.reason);
    });
  }

  it('fails closed when no nonce cache is supplied', () => {
    const valid = vectors.find((v) => v.name === 'valid')!;
    const res = verifyTapRequest(valid.signatureInput, valid.signature, { now: valid.now });
    expect(res.reason).toBe('tap_nonce_cache_required');
  });

  it('detects nonce replay within a shared cache', () => {
    const valid = vectors.find((v) => v.name === 'valid')!;
    const cache = new Set<string>();
    expect(verifyTapRequest(valid.signatureInput, valid.signature, { now: valid.now, nonceCache: cache }).accepted).toBe(true);
    const replay = verifyTapRequest(valid.signatureInput, valid.signature, { now: valid.now, nonceCache: cache });
    expect(replay.reason).toBe('tap_nonce_replayed');
  });

  it('parseSignatureInput extracts the structured fields', () => {
    const valid = vectors.find((v) => v.name === 'valid')!;
    const si = parseSignatureInput(valid.signatureInput);
    expect(si.components).toContain('@authority');
    expect(si.components).toContain('@path');
    expect(si.tag).toBe('agent-payer-auth');
    expect(si.alg).toBe('ed25519');
  });
});
