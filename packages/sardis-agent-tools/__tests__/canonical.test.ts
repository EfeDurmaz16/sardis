import { describe, it, expect } from 'vitest';
import { canonicalJson, createCommitHash, sha256Hex } from '../src/canonical.js';
import type { SardisToolContext } from '../src/types.js';

const ctx = { client: {} as never, walletId: 'wal_1', agentId: 'agt_1' } as SardisToolContext;

describe('canonical commit hash', () => {
  it('is order-independent (sorted keys)', () => {
    expect(canonicalJson({ b: 1, a: 2 })).toBe(canonicalJson({ a: 2, b: 1 }));
    expect(canonicalJson({ a: 2, b: 1 })).toBe('{"a":2,"b":1}');
  });

  it('sorts nested object keys recursively', () => {
    expect(canonicalJson({ z: { y: 1, x: 2 } })).toBe('{"z":{"x":2,"y":1}}');
  });

  it('sha256Hex matches a known vector', async () => {
    // echo -n "" | sha256sum
    expect(await sha256Hex('')).toBe(
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    );
  });

  it('createCommitHash is deterministic and sardis_-prefixed', async () => {
    const a = await createCommitHash('sardis_spend', { to: 'x', amount: '1' }, ctx, 'compensatable');
    const b = await createCommitHash('sardis_spend', { amount: '1', to: 'x' }, ctx, 'compensatable');
    expect(a).toBe(b);
    expect(a).toMatch(/^sardis_[0-9a-f]{40}$/);
  });

  it('different args produce different commit hashes', async () => {
    const a = await createCommitHash('sardis_spend', { to: 'x', amount: '1' }, ctx, 'compensatable');
    const b = await createCommitHash('sardis_spend', { to: 'x', amount: '2' }, ctx, 'compensatable');
    expect(a).not.toBe(b);
  });
});
