import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { canonicalize, canonicalBytes, type CanonicalValue } from '../src/verify/canonical-json.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface CanonVector {
  name: string;
  value: CanonicalValue;
  canonical: string;
  canonicalHex: string;
}

const vectors: CanonVector[] = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'canonical-json.json'), 'utf8'),
);

describe('canonical-json — byte-identical to Python json.dumps(sort_keys, ensure_ascii)', () => {
  for (const v of vectors) {
    it(`${v.name} matches the Python canonical string`, () => {
      expect(canonicalize(v.value)).toBe(v.canonical);
    });
    it(`${v.name} matches the Python canonical bytes (hex)`, () => {
      const hex = Buffer.from(canonicalBytes(v.value)).toString('hex');
      expect(hex).toBe(v.canonicalHex);
    });
  }

  it('rejects float values (forbidden on the authority-proof path)', () => {
    expect(() => canonicalize(1.5)).toThrow();
  });
});
